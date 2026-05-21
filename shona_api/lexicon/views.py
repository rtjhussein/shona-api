from django.http import Http404
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from shona_api.editorial.models import ReviewState
from shona_api.releases.services import get_current_release_metadata

from .models import Form, Lemma
from .search import SEARCH_NORMALIZER_VERSION, normalize_search_query
from .serializers import LemmaReadSerializer, SearchResultSerializer


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


class LemmaReadView(APIView):
    def get(self, request, public_id):
        lemma = self._get_lemma(public_id)
        serializer = LemmaReadSerializer(lemma)
        release_metadata = get_current_release_metadata()
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

        results = self._search(normalized_query)
        release_metadata = get_current_release_metadata()

        morphology_analysis = None
        try:
            from shona_api.morphology.services import analyze_text
            from .serializers import LemmaCoreSerializer, SenseSerializer, ToneRecordSerializer, FormSerializer

            morphology_analysis = analyze_text(
                raw_query,
                rule_set_version=release_metadata["rule_set_version"],
            )
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
                    lemma_data["senses"] = SenseSerializer(lemma_obj.senses.all(), many=True).data
                    lemma_data["tone_records"] = ToneRecordSerializer(lemma_obj.tone_records.all(), many=True).data
                    lemma_data["forms"] = FormSerializer(lemma_obj.forms.all(), many=True).data
                    analysis["lemma_details"] = lemma_data
        except Exception:
            pass

        return Response(
            build_success_envelope(
                data=self._build_search_payload(
                    raw_query=raw_query,
                    normalized_query=normalized_query,
                    results=results,
                    morphology_analysis=morphology_analysis,
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

    def _build_search_payload(self, *, raw_query, normalized_query, results, morphology_analysis=None):
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
        if not results and not morphology_analysis:
            payload["zero_result"] = {
                "code": "NO_MATCH",
                "message": "No reviewed lemma or form matched the query.",
            }
        return payload
