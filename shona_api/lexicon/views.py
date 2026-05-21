import logging

from django.http import Http404
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from shona_api.editorial.models import ReviewState
from shona_api.observability.metrics import record_metric
from shona_api.releases.services import (
    CURRENT_RELEASE_NOT_CONFIGURED_CODE,
    CURRENT_RELEASE_NOT_CONFIGURED_MESSAGE,
    CurrentReleaseNotFound,
    get_current_release_metadata,
    get_current_release_setup_detail,
)

from .models import Form, Lemma
from .search import SEARCH_NORMALIZER_VERSION, normalize_search_query
from .serializers import (
    FormSerializer,
    LemmaCoreSerializer,
    LemmaReadSerializer,
    SearchResultSerializer,
    SenseSerializer,
    ToneRecordSerializer,
)


logger = logging.getLogger(__name__)


def build_success_envelope(*, data, release_metadata):
    return {
        "api_version": "v1",
        "data_release": release_metadata["release_version"],
        "rule_set_version": release_metadata["rule_set_version"],
        "generated_at": timezone.now().isoformat().replace("+00:00", "Z"),
        "data": data,
    }


def build_error_envelope(*, code, message, detail=None):
    return {
        "api_version": "v1",
        "error": {
            "code": code,
            "message": message,
            "detail": detail,
        },
    }


def build_current_release_missing_response():
    return Response(
        build_error_envelope(
            code=CURRENT_RELEASE_NOT_CONFIGURED_CODE,
            message=CURRENT_RELEASE_NOT_CONFIGURED_MESSAGE,
            detail=get_current_release_setup_detail(),
        ),
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


class LemmaReadView(APIView):
    def get(self, request, public_id):
        try:
            release_metadata = get_current_release_metadata()
        except CurrentReleaseNotFound:
            return build_current_release_missing_response()

        lemma = self._get_lemma(public_id)
        serializer = LemmaReadSerializer(lemma)
        return Response(
            build_success_envelope(
                data=serializer.data,
                release_metadata=release_metadata,
            ),
            status=status.HTTP_200_OK,
        )

    def _get_lemma(self, public_id):
        try:
            return (
                Lemma.objects.select_related(
                    "noun_class",
                    "noun_class__default_plural_class",
                )
                .prefetch_related(
                    "senses",
                    "tone_records__form",
                    "forms__sense",
                )
                .get(public_id=public_id)
            )
        except Lemma.DoesNotExist as exc:
            raise Http404 from exc

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            public_id = self.kwargs["public_id"]
            return Response(
                build_error_envelope(
                    code="LEMMA_NOT_FOUND",
                    message=f"No lemma found for public_id '{public_id}'",
                ),
                status=status.HTTP_404_NOT_FOUND,
            )
        return super().handle_exception(exc)


class SearchView(APIView):
    public_review_states = (ReviewState.PUBLISHED,)

    def get(self, request):
        raw_query = request.query_params.get("q", "")
        normalized_query = normalize_search_query(raw_query)
        if not normalized_query:
            return Response(
                build_error_envelope(
                    code="SEARCH_QUERY_REQUIRED",
                    message="Search requires a non-empty 'q' query parameter.",
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            release_metadata = get_current_release_metadata()
        except CurrentReleaseNotFound:
            return build_current_release_missing_response()

        results = self._search(normalized_query)

        morphology_analysis, morphology_enrichment = self._build_morphology_enrichment(
            raw_query=raw_query,
            release_metadata=release_metadata,
        )

        return Response(
            build_success_envelope(
                data=self._build_search_payload(
                    raw_query=raw_query,
                    normalized_query=normalized_query,
                    results=results,
                    morphology_analysis=morphology_analysis,
                    morphology_enrichment=morphology_enrichment,
                ),
                release_metadata=release_metadata,
            ),
            status=status.HTTP_200_OK,
        )

    def _search(self, normalized_query):
        lemma_results = [
            {
                "result_type": "lemma",
                "match_type": "exact_lemma",
                "lemma": lemma,
                "form": None,
            }
            for lemma in self._lemma_queryset().filter(
                normalized_headword=normalized_query,
            )[:20]
        ]
        remaining_limit = max(20 - len(lemma_results), 0)
        form_results = [
            {
                "result_type": "form",
                "match_type": "exact_form",
                "lemma": form.lemma,
                "form": form,
            }
            for form in self._form_queryset().filter(
                normalized_form=normalized_query,
            )[:remaining_limit]
        ]
        return lemma_results + form_results

    def _lemma_queryset(self):
        return Lemma.objects.filter(
            review_state__in=self.public_review_states,
        ).select_related(
            "noun_class",
            "noun_class__default_plural_class",
        ).prefetch_related(
            "senses",
            "tone_records__form",
            "forms__sense",
        )

    def _form_queryset(self):
        return (
            Form.objects.filter(
                review_state__in=self.public_review_states,
                lemma__review_state__in=self.public_review_states,
            )
            .select_related(
                "lemma",
                "lemma__noun_class",
                "lemma__noun_class__default_plural_class",
                "sense",
            )
            .prefetch_related(
                Prefetch(
                    "lemma__forms",
                    queryset=Form.objects.select_related("sense"),
                ),
                "lemma__senses",
                "lemma__tone_records__form",
            )
        )

    def _build_morphology_enrichment(self, *, raw_query, release_metadata):
        from shona_api.morphology.services import AnalysisFailure, analyze_text

        try:
            morphology_analysis = analyze_text(
                raw_query,
                rule_set_version=release_metadata["rule_set_version"],
            )
            self._attach_morphology_lemma_details(morphology_analysis)
        except AnalysisFailure as exc:
            record_metric(
                "search.morphology_enrichment.unsupported",
                tags={"code": exc.code},
            )
            return None, {
                "status": "unsupported",
                "code": exc.code,
                "message": exc.message,
            }
        except Exception as exc:
            record_metric(
                "search.morphology_enrichment.failed",
                tags={"error_type": type(exc).__name__},
            )
            logger.exception(
                "search_morphology_enrichment_failed",
                extra={
                    "raw_query": raw_query,
                    "rule_set_version": release_metadata["rule_set_version"],
                },
            )
            return None, {
                "status": "failed",
                "code": "MORPHOLOGY_ENRICHMENT_FAILED",
                "message": (
                    "Morphology enrichment failed; exact lexical search results "
                    "are still returned."
                ),
            }

        analysis_count = morphology_analysis.get("count", 0)
        record_metric(
            "search.morphology_enrichment.matched",
            value=analysis_count,
            tags={"rule_set_version": release_metadata["rule_set_version"]},
        )
        return morphology_analysis, {
            "status": "matched",
            "count": analysis_count,
        }

    def _attach_morphology_lemma_details(self, morphology_analysis):
        for analysis in morphology_analysis.get("analyses", []):
            lemma_id = analysis["lemma"]["public_id"]
            lemma_obj = (
                Lemma.objects.filter(public_id=lemma_id)
                .select_related("noun_class", "noun_class__default_plural_class")
                .prefetch_related("senses", "tone_records__form", "forms__sense")
                .first()
            )
            if lemma_obj:
                lemma_data = LemmaCoreSerializer(lemma_obj).data
                lemma_data["senses"] = SenseSerializer(
                    lemma_obj.senses.all(),
                    many=True,
                ).data
                lemma_data["tone_records"] = ToneRecordSerializer(
                    lemma_obj.tone_records.all(),
                    many=True,
                ).data
                lemma_data["forms"] = FormSerializer(
                    lemma_obj.forms.all(),
                    many=True,
                ).data
                analysis["lemma_details"] = lemma_data

    def _build_search_payload(
        self,
        *,
        raw_query,
        normalized_query,
        results,
        morphology_analysis=None,
        morphology_enrichment=None,
    ):
        payload = {
            "query": {
                "raw": raw_query,
                "normalized": normalized_query,
                "normalizer": SEARCH_NORMALIZER_VERSION,
            },
            "count": len(results),
            "results": SearchResultSerializer(results, many=True).data,
        }
        if morphology_analysis:
            payload["morphology"] = morphology_analysis
        if morphology_enrichment and morphology_enrichment["status"] == "matched":
            payload["morphology_enrichment"] = morphology_enrichment
        if not results and not morphology_analysis:
            zero_result = {
                "code": "NO_MATCH",
                "message": "No reviewed lemma or form matched the query.",
            }
            if morphology_enrichment:
                zero_result["morphology_enrichment"] = morphology_enrichment
            payload["zero_result"] = zero_result
        return payload
