from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView
from django.views import View
from pathlib import Path

from shona_api.api_auth.models import APIKey
from shona_api.editorial.models import ReviewState
from shona_api.extraction.ingestion import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PARSER_REPO_PATH,
    DEFAULT_PDF_PATH,
    TRUSTED_GPT_5_5_PARSER,
    build_ingestion_readiness,
    save_gemini_key,
    start_ingestion_run_async,
)
from shona_api.extraction.models import IngestionRun

from .progress import build_data_progress_snapshot


class StaffRequiredMixin(UserPassesTestMixin):
    login_url = "/admin/login/"

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_staff


class DictionarySearchView(TemplateView):
    template_name = "web/dictionary_search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_endpoint"] = reverse("search")
        context["entry_url_template"] = reverse(
            "dictionary-entry",
            kwargs={"public_id": "__PUBLIC_ID__"},
        )
        context["local_api_key_endpoint"] = reverse("local-api-key-create")
        return context


class DictionaryEntryView(TemplateView):
    template_name = "web/dictionary_entry.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        public_id = self.kwargs["public_id"]
        context["lemma_public_id"] = public_id
        context["lemma_endpoint"] = reverse(
            "lemma-read",
            kwargs={"public_id": public_id},
        )
        context["search_url"] = reverse("dictionary-search")
        context["tsumo_endpoint"] = reverse("tsumo-list")
        context["madimikira_endpoint"] = reverse("madimikira-list")
        return context


class DataProgressView(StaffRequiredMixin, TemplateView):
    template_name = "web/data_progress.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["snapshot"] = build_data_progress_snapshot()
        return context


class IngestionDashboardView(StaffRequiredMixin, TemplateView):
    template_name = "web/ingestion_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        latest_runs = IngestionRun.objects.filter(
            run_kind=IngestionRun.RunKind.PRECOMPILED_JSONL,
        ).order_by("-created_at")
        context["readiness"] = build_ingestion_readiness()
        context["latest_runs"] = latest_runs[:8]
        context["latest_run"] = latest_runs.first()
        latest_run = context["latest_run"]
        context["latest_run_review_state_filter"] = (
            ReviewState.APPROVED
            if latest_run and latest_run.auto_approve and not latest_run.auto_publish
            else ReviewState.NEEDS_REVIEW
        )
        context["start_endpoint"] = reverse("ingestion-run-start")
        context["save_key_endpoint"] = reverse("ingestion-gemini-key-save")
        context["jsonl_list_endpoint"] = reverse("ingestion-jsonl-list")
        context["status_url_template"] = reverse(
            "ingestion-run-status",
            kwargs={"pk": 0},
        ).replace("/0/", "/__RUN_ID__/")
        return context


class SaveGeminiKeyView(StaffRequiredMixin, View):
    def post(self, request):
        key = request.POST.get("gemini_api_key", "")
        try:
            save_gemini_key(key)
        except ValueError as exc:
            return JsonResponse({"ok": False, "error": str(exc)}, status=400)
        return JsonResponse({"ok": True, "readiness": build_ingestion_readiness()})


class JsonlFileListView(StaffRequiredMixin, View):
    def get(self, request):
        output_dir = DEFAULT_OUTPUT_DIR
        files = []
        if output_dir.exists():
            import_runs_by_path = _jsonl_import_runs_by_path()
            files = [
                _jsonl_file_payload(
                    path,
                    import_runs_by_path.get(_normalize_jsonl_path(path)),
                )
                for path in sorted(
                    output_dir.glob("*.jsonl"),
                    key=lambda item: item.stat().st_mtime,
                    reverse=True,
                )
                if path.is_file()
            ]
        return JsonResponse(
            {
                "ok": True,
                "folder": str(output_dir),
                "files": files,
            }
        )


class CreateLocalAPIKeyView(StaffRequiredMixin, View):
    def post(self, request):
        name = request.POST.get("name", "").strip() or "Reference web local key"
        api_key, raw_key = APIKey.objects.create_key(
            name=name,
            plan=APIKey.Plan.DEVELOPER,
            rate_limit_per_minute=60,
        )
        return JsonResponse(
            {
                "ok": True,
                "prefix": api_key.prefix,
                "raw_key": raw_key,
                "message": "Local API key created. Store it now; only the hash is saved.",
            }
        )


class StartIngestionRunView(StaffRequiredMixin, View):
    def post(self, request):
        run_kind = request.POST.get("run_kind", IngestionRun.RunKind.GEMINI_PIPELINE)
        if run_kind == IngestionRun.RunKind.PRECOMPILED_JSONL:
            if IngestionRun.objects.filter(
                run_kind=IngestionRun.RunKind.PRECOMPILED_JSONL,
                status=IngestionRun.Status.RUNNING,
            ).exists():
                return JsonResponse(
                    {"ok": False, "error": "Another JSONL import is already running."},
                    status=409,
                )
            return self._start_precompiled_jsonl_run(request)
        if run_kind != IngestionRun.RunKind.GEMINI_PIPELINE:
            return JsonResponse(
                {"ok": False, "error": "Choose a valid ingestion mode."},
                status=400,
            )
        if IngestionRun.objects.filter(
            run_kind=IngestionRun.RunKind.GEMINI_PIPELINE,
            status=IngestionRun.Status.RUNNING,
        ).exists():
            return JsonResponse(
                {"ok": False, "error": "Another Gemini pipeline run is already running."},
                status=409,
            )

        return self._start_gemini_pipeline_run(request)

    def _start_gemini_pipeline_run(self, request):
        try:
            start_page = int(request.POST.get("start_page", ""))
            end_page = int(request.POST.get("end_page") or start_page)
        except ValueError:
            return JsonResponse(
                {"ok": False, "error": "Start and end page must be numbers."},
                status=400,
            )
        if start_page < 1 or end_page < start_page:
            return JsonResponse(
                {"ok": False, "error": "Choose a valid PDF page range."},
                status=400,
            )

        batch_id = request.POST.get("batch_id", "").strip()
        if not batch_id:
            batch_id = timezone.now().strftime("GEMINI-%Y%m%d-%H%M%S")

        run = IngestionRun.objects.create(
            run_kind=IngestionRun.RunKind.GEMINI_PIPELINE,
            batch_id=batch_id,
            start_page=start_page,
            end_page=end_page,
            parser_repo_path=str(DEFAULT_PARSER_REPO_PATH),
            pdf_path=str(DEFAULT_PDF_PATH),
            output_dir=str(DEFAULT_OUTPUT_DIR),
            dry_run=request.POST.get("dry_run") == "on",
            overwrite_pages=request.POST.get("overwrite_pages") == "on",
            skip_duplicates=request.POST.get("skip_duplicates", "on") == "on",
            auto_publish=request.POST.get("auto_publish") == "on",
            created_by=request.user,
        )
        start_ingestion_run_async(run.pk)
        return JsonResponse({"ok": True, "run": _run_payload(run)})

    def _start_precompiled_jsonl_run(self, request):
        jsonl_path = request.POST.get("jsonl_path", "").strip().strip('"')
        if not jsonl_path:
            return JsonResponse(
                {"ok": False, "error": "Choose a precompiled JSONL file."},
                status=400,
            )

        batch_id = request.POST.get("jsonl_batch_id", "").strip()
        if not batch_id:
            batch_id = timezone.now().strftime("GPT-5.5-%Y%m%d-%H%M%S")

        parser_name = (
            request.POST.get("import_parser_name", "").strip()
            or TRUSTED_GPT_5_5_PARSER
        )
        run = IngestionRun.objects.create(
            run_kind=IngestionRun.RunKind.PRECOMPILED_JSONL,
            batch_id=batch_id,
            start_page=1,
            end_page=1,
            parser_repo_path=str(DEFAULT_PARSER_REPO_PATH),
            pdf_path=str(DEFAULT_PDF_PATH),
            output_dir=str(DEFAULT_OUTPUT_DIR),
            source_jsonl_path=jsonl_path,
            import_parser_name=parser_name,
            dry_run=request.POST.get("jsonl_dry_run") == "on",
            skip_duplicates=request.POST.get("jsonl_skip_duplicates", "on") == "on",
            auto_approve=request.POST.get("auto_approve") == "on",
            auto_publish=request.POST.get("jsonl_auto_publish") == "on",
            created_by=request.user,
        )
        start_ingestion_run_async(run.pk)
        return JsonResponse({"ok": True, "run": _run_payload(run)})


class IngestionRunStatusView(StaffRequiredMixin, View):
    def get(self, request, pk):
        try:
            run = IngestionRun.objects.get(pk=pk)
        except IngestionRun.DoesNotExist:
            return JsonResponse({"ok": False, "error": "Run not found."}, status=404)
        return JsonResponse({"ok": True, "run": _run_payload(run)})


def _run_payload(run):
    review_state_filter = (
        ReviewState.APPROVED
        if run.auto_approve and not run.auto_publish
        else ReviewState.NEEDS_REVIEW
    )
    return {
        "id": run.pk,
        "batch_id": run.batch_id,
        "status": run.status,
        "page_label": run.page_label,
        "run_kind": run.run_kind,
        "dry_run": run.dry_run,
        "skip_duplicates": run.skip_duplicates,
        "auto_approve": run.auto_approve,
        "auto_publish": run.auto_publish,
        "imported_count": run.imported_count,
        "duplicate_count": run.duplicate_count,
        "publishable_count": run.publishable_count,
        "published_count": run.published_count,
        "failed_publish_count": run.failed_publish_count,
        "log_text": run.log_text,
        "error_message": run.error_message,
        "created_at": run.created_at.isoformat() if run.created_at else "",
        "started_at": run.started_at.isoformat() if run.started_at else "",
        "finished_at": run.finished_at.isoformat() if run.finished_at else "",
        "review_url": (
            reverse("admin:extraction_extractionunit_changelist")
            + f"?batch_id__exact={run.batch_id}&review_state__exact={review_state_filter}"
        ),
        "published_url": reverse("dictionary-search"),
    }


def _jsonl_import_runs_by_path():
    runs_by_path = {}
    runs = (
        IngestionRun.objects.filter(
            run_kind=IngestionRun.RunKind.PRECOMPILED_JSONL,
        )
        .exclude(source_jsonl_path="")
        .order_by("-created_at")
    )
    for run in runs:
        normalized_path = _normalize_jsonl_path(run.source_jsonl_path)
        if normalized_path and normalized_path not in runs_by_path:
            runs_by_path[normalized_path] = run
    return runs_by_path


def _jsonl_file_payload(path, latest_run):
    stat = path.stat()
    payload = {
        "name": path.name,
        "path": str(path),
        "size": stat.st_size,
        "modified": timezone.datetime.fromtimestamp(
            stat.st_mtime,
            tz=timezone.get_current_timezone(),
        ).isoformat(),
    }
    if latest_run is None:
        payload["import_status"] = {
            "state": "not_imported",
            "label": "Not imported",
            "detail": "No import run found for this file.",
        }
        return payload

    payload["import_status"] = {
        "state": _jsonl_import_state(latest_run),
        "label": _jsonl_import_label(latest_run),
        "detail": _jsonl_import_detail(latest_run),
        "batch_id": latest_run.batch_id,
        "run_status": latest_run.status,
        "imported_count": latest_run.imported_count,
        "duplicate_count": latest_run.duplicate_count,
        "dry_run": latest_run.dry_run,
        "created_at": latest_run.created_at.isoformat() if latest_run.created_at else "",
        "finished_at": latest_run.finished_at.isoformat() if latest_run.finished_at else "",
    }
    return payload


def _jsonl_import_state(run):
    if run.status == IngestionRun.Status.RUNNING:
        return "running"
    if run.status == IngestionRun.Status.FAILED:
        return "failed"
    if run.dry_run:
        return "dry_run"
    if run.status == IngestionRun.Status.SUCCEEDED:
        return "imported"
    return "pending"


def _jsonl_import_label(run):
    return {
        "running": "Import running",
        "failed": "Import failed",
        "dry_run": "Dry run only",
        "imported": "Imported",
        "pending": "Import pending",
    }[_jsonl_import_state(run)]


def _jsonl_import_detail(run):
    if run.status == IngestionRun.Status.SUCCEEDED and not run.dry_run:
        return (
            f"Batch {run.batch_id}: imported {run.imported_count}, "
            f"duplicates {run.duplicate_count}."
        )
    if run.status == IngestionRun.Status.FAILED:
        return f"Batch {run.batch_id} failed."
    if run.status == IngestionRun.Status.RUNNING:
        return f"Batch {run.batch_id} is still running."
    if run.dry_run:
        return f"Batch {run.batch_id} was a dry run."
    return f"Batch {run.batch_id} has status {run.status}."


def _normalize_jsonl_path(path):
    path_text = str(path or "").strip()
    if not path_text:
        return ""
    return str(Path(path_text).expanduser().resolve()).casefold()
