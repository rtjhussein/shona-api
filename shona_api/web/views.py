from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView
from django.views import View

from shona_api.api_auth.models import APIKey
from shona_api.extraction.ingestion import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PARSER_REPO_PATH,
    DEFAULT_PDF_PATH,
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
        context["readiness"] = build_ingestion_readiness()
        context["latest_runs"] = IngestionRun.objects.order_by("-created_at")[:8]
        context["latest_run"] = IngestionRun.objects.order_by("-created_at").first()
        context["start_endpoint"] = reverse("ingestion-run-start")
        context["save_key_endpoint"] = reverse("ingestion-gemini-key-save")
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
        if IngestionRun.objects.filter(status=IngestionRun.Status.RUNNING).exists():
            return JsonResponse(
                {"ok": False, "error": "Another ingestion run is already running."},
                status=409,
            )

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
            batch_id=batch_id,
            start_page=start_page,
            end_page=end_page,
            parser_repo_path=str(DEFAULT_PARSER_REPO_PATH),
            pdf_path=str(DEFAULT_PDF_PATH),
            output_dir=str(DEFAULT_OUTPUT_DIR),
            dry_run=request.POST.get("dry_run") == "on",
            overwrite_pages=request.POST.get("overwrite_pages") == "on",
            auto_publish=request.POST.get("auto_publish") == "on",
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
    return {
        "id": run.pk,
        "batch_id": run.batch_id,
        "status": run.status,
        "page_label": run.page_label,
        "dry_run": run.dry_run,
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
            + f"?batch_id__exact={run.batch_id}&review_state__exact=needs_review"
        ),
        "published_url": reverse("dictionary-search"),
    }
