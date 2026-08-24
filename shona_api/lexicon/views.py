import logging

from django.http import Http404
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

from .models import Lemma
from .search import (
    DEFAULT_SEARCH_LIMIT,
    MAX_SEARCH_LIMIT,
    SEARCH_NORMALIZER_VERSION,
    filter_json_array,
    normalize_search_query,
    search_public_records,
    search_public_records_fuzzy,
)
from .serializers import (
    FormSerializer,
    LemmaCoreSerializer,
    LemmaReadSerializer,
    SearchResultSerializer,
    SenseSerializer,
    ToneRecordSerializer,
)


logger = logging.getLogger(__name__)

HEADWORD_KIND_FILTERS = {
    Lemma.HeadwordKind.WORD,
    Lemma.HeadwordKind.NOUN,
    Lemma.HeadwordKind.VERB_STEM,
    Lemma.HeadwordKind.IDEOPHONE,
    Lemma.HeadwordKind.UNKNOWN,
}
POS_FILTERS = {"n", "vi", "vt", "v t", "v i", "adj", "adv", "ideo", "interj"}
DIALECT_FILTERS = {
    "k": "K",
    "ko": "Ko",
    "m": "M",
    "z": "Z",
}


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

        filters, filter_error = self._parse_filters(request)
        if filter_error:
            return filter_error

        results = self._search(normalized_query, filters=filters)

        morphology_analysis, morphology_enrichment = self._build_morphology_enrichment(
            raw_query=raw_query,
            release_metadata=release_metadata,
        )

        if not results and not (morphology_analysis and morphology_analysis.get("analyses")):
            results = self._search_fuzzy(normalized_query, filters=filters)

        if filters.get("random") and results:
            import random
            random.shuffle(results)

        return Response(
            build_success_envelope(
                data=self._build_search_payload(
                    raw_query=raw_query,
                    normalized_query=normalized_query,
                    filters=filters,
                    results=results,
                    morphology_analysis=morphology_analysis,
                    morphology_enrichment=morphology_enrichment,
                ),
                release_metadata=release_metadata,
            ),
            status=status.HTTP_200_OK,
        )

    def _search(self, normalized_query, *, filters):
        return search_public_records(normalized_query, filters=filters)

    def _search_fuzzy(self, normalized_query, *, filters):
        return search_public_records_fuzzy(normalized_query, filters=filters)

    def _parse_filters(self, request):
        filters = {
            "headword_kind": None,
            "pos": None,
            "dialect": None,
            "limit": DEFAULT_SEARCH_LIMIT,
            "learner_level": None,
            "curriculum_stage": None,
            "frequency_tier": None,
            "communication_context": None,
            "noun_class": None,
            "random": False,
        }
        headword_kind = request.query_params.get("headword_kind", "").strip()
        if headword_kind:
            if headword_kind not in HEADWORD_KIND_FILTERS:
                return None, self._invalid_filter_response(
                    field="headword_kind",
                    value=headword_kind,
                    allowed=sorted(HEADWORD_KIND_FILTERS),
                )
            filters["headword_kind"] = headword_kind

        pos = request.query_params.get("pos", "").strip()
        if pos:
            if pos not in POS_FILTERS:
                return None, self._invalid_filter_response(
                    field="pos",
                    value=pos,
                    allowed=sorted(POS_FILTERS),
                )
            filters["pos"] = pos

        raw_dialect = request.query_params.get("dialect", "").strip()
        if raw_dialect:
            dialect = DIALECT_FILTERS.get(raw_dialect.casefold())
            if not dialect:
                return None, self._invalid_filter_response(
                    field="dialect",
                    value=raw_dialect,
                    allowed=sorted(DIALECT_FILTERS.values()),
                )
            filters["dialect"] = dialect

        # Pedagogy filters validation
        for param, choice_class, filter_key in [
            ("learner_level", Lemma.LearnerLevel, "learner_level"),
            ("curriculum_stage", Lemma.CurriculumStage, "curriculum_stage"),
            ("frequency_tier", Lemma.FrequencyTier, "frequency_tier")
        ]:
            val = request.query_params.get(param, "").strip()
            if val:
                if val not in choice_class.values:
                    return None, self._invalid_filter_response(
                        field=param,
                        value=val,
                        allowed=choice_class.values,
                    )
                filters[filter_key] = val

        allowed_contexts = ["conversation", "narrative", "description", "letter_writing", "school_composition", "formal_speech", "greetings", "family", "environment", "time"]
        context = request.query_params.get("communication_context", "").strip()
        if context:
            if context not in allowed_contexts:
                return None, self._invalid_filter_response(
                    field="communication_context",
                    value=context,
                    allowed=allowed_contexts,
                )
            filters["communication_context"] = context

        noun_class = request.query_params.get("noun_class", "").strip()
        if noun_class:
            filters["noun_class"] = noun_class

        raw_random = request.query_params.get("random", "").strip().casefold()
        if raw_random:
            if raw_random in ("true", "1", "yes"):
                filters["random"] = True
            elif raw_random in ("false", "0", "no"):
                filters["random"] = False
            else:
                return None, self._invalid_filter_response(
                    field="random",
                    value=raw_random,
                    allowed=["true", "false"],
                )

        raw_limit = request.query_params.get("limit", "").strip()
        if raw_limit:
            try:
                limit = int(raw_limit)
            except ValueError:
                return None, self._invalid_filter_response(
                    field="limit",
                    value=raw_limit,
                    allowed=[f"1..{MAX_SEARCH_LIMIT}"],
                )
            if limit < 1 or limit > MAX_SEARCH_LIMIT:
                return None, self._invalid_filter_response(
                    field="limit",
                    value=raw_limit,
                    allowed=[f"1..{MAX_SEARCH_LIMIT}"],
                )
            filters["limit"] = limit

        return filters, None

    def _invalid_filter_response(self, *, field, value, allowed):
        return Response(
            build_error_envelope(
                code="SEARCH_FILTER_INVALID",
                message=f"Invalid search filter '{field}'.",
                detail={
                    "field": field,
                    "value": value,
                    "allowed_values": allowed,
                },
            ),
            status=status.HTTP_400_BAD_REQUEST,
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
            enrichment = {
                "status": "unsupported",
                "code": exc.code,
                "message": exc.message,
            }
            if exc.detail and exc.detail.get("future_lanes"):
                enrichment["detail"] = exc.detail
            return None, enrichment
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
        filters,
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
        active_filters = self._active_filter_payload(filters)
        if active_filters:
            payload["query"]["filters"] = active_filters
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

    def _active_filter_payload(self, filters):
        active = {
            key: value
            for key, value in filters.items()
            if value and key != "limit"
        }
        if filters["limit"] != DEFAULT_SEARCH_LIMIT:
            active["limit"] = filters["limit"]
        return active


class LemmaListView(APIView):
    public_review_states = (ReviewState.PUBLISHED,)

    def get(self, request):
        try:
            release_metadata = get_current_release_metadata()
        except CurrentReleaseNotFound:
            return build_current_release_missing_response()

        filters, filter_error = self._parse_list_filters(request)
        if filter_error:
            return filter_error

        queryset = Lemma.objects.filter(
            review_state__in=self.public_review_states
        ).select_related(
            "noun_class",
            "noun_class__default_plural_class",
        ).prefetch_related(
            "senses",
            "tone_records__form",
            "forms__sense",
        )

        # Apply pedagogy & lexical filters
        if filters["learner_level"]:
            queryset = queryset.filter(learner_level=filters["learner_level"])
        if filters["curriculum_stage"]:
            queryset = queryset.filter(curriculum_stage=filters["curriculum_stage"])
        if filters["curriculum_domain"]:
            queryset = filter_json_array(queryset, "curriculum_domains", filters["curriculum_domain"])
        if filters["learning_function"]:
            queryset = filter_json_array(queryset, "learning_functions", filters["learning_function"])
        if filters["communication_context"]:
            queryset = filter_json_array(queryset, "communication_contexts", filters["communication_context"])
        if filters["register_tag"]:
            queryset = filter_json_array(queryset, "register_tags", filters["register_tag"])
        if filters["frequency_tier"]:
            queryset = queryset.filter(frequency_tier=filters["frequency_tier"])
        if filters["headword_kind"]:
            queryset = queryset.filter(headword_kind=filters["headword_kind"])
        if filters["pos"]:
            queryset = queryset.filter(part_of_speech_code=filters["pos"])
        if filters["noun_class"]:
            queryset = queryset.filter(noun_class__class_number=filters["noun_class"])

        # Handle random ordering vs normal order
        if filters["random"]:
            queryset = queryset.order_by("?")
        else:
            queryset = queryset.order_by("normalized_headword", "headword")

        # Apply limit/slicing
        limit = filters["limit"]
        lemmas = list(queryset[:limit])

        serializer = LemmaCoreSerializer(lemmas, many=True)
        return Response(
            build_success_envelope(
                data={
                    "count": len(lemmas),
                    "filters": {k: v for k, v in filters.items() if v is not None and k != "limit"},
                    "results": serializer.data,
                },
                release_metadata=release_metadata,
            ),
            status=status.HTTP_200_OK,
        )

    def _parse_list_filters(self, request):
        filters = {
            "learner_level": None,
            "curriculum_stage": None,
            "curriculum_domain": None,
            "learning_function": None,
            "communication_context": None,
            "register_tag": None,
            "frequency_tier": None,
            "headword_kind": None,
            "pos": None,
            "noun_class": None,
            "random": False,
            "limit": DEFAULT_SEARCH_LIMIT,
        }

        # Validate standard choices
        for param, choice_class, filter_key in [
            ("learner_level", Lemma.LearnerLevel, "learner_level"),
            ("curriculum_stage", Lemma.CurriculumStage, "curriculum_stage"),
            ("frequency_tier", Lemma.FrequencyTier, "frequency_tier"),
            ("headword_kind", Lemma.HeadwordKind, "headword_kind")
        ]:
            val = request.query_params.get(param, "").strip()
            if val:
                if val not in choice_class.values:
                    return None, self._invalid_list_filter_response(param, val, choice_class.values)
                filters[filter_key] = val

        # Validate list/contains filters
        for param, allowed_values in [
            ("curriculum_domain", ["orthography", "grammar", "vocabulary", "composition", "comprehension", "register", "oral_communication", "figurative_language", "culture"]),
            ("learning_function", ["vocabulary", "example_sentence", "dialogue_practice", "writing_guidance", "usage_warning", "cultural_interpretation", "assessment_support"]),
            ("communication_context", ["conversation", "narrative", "description", "letter_writing", "school_composition", "formal_speech", "greetings", "family", "environment", "time"]),
            ("register_tag", ["formal", "informal", "respectful", "school_appropriate", "avoid_in_school_context"])
        ]:
            val = request.query_params.get(param, "").strip()
            if val:
                if val not in allowed_values:
                    return None, self._invalid_list_filter_response(param, val, allowed_values)
                filters[param] = val

        # Simple string/POS/Class filters
        pos = request.query_params.get("pos", "").strip()
        if pos:
            if pos not in POS_FILTERS:
                return None, self._invalid_list_filter_response("pos", pos, sorted(POS_FILTERS))
            filters["pos"] = pos

        noun_class = request.query_params.get("noun_class", "").strip()
        if noun_class:
            filters["noun_class"] = noun_class

        # Validate random boolean
        raw_random = request.query_params.get("random", "").strip().casefold()
        if raw_random:
            if raw_random in ("true", "1", "yes"):
                filters["random"] = True
            elif raw_random in ("false", "0", "no"):
                filters["random"] = False
            else:
                return None, self._invalid_list_filter_response("random", raw_random, ["true", "false"])

        # Validate limit
        raw_limit = request.query_params.get("limit", "").strip()
        if raw_limit:
            try:
                limit = int(raw_limit)
            except ValueError:
                return None, self._invalid_list_filter_response("limit", raw_limit, [f"1..{MAX_SEARCH_LIMIT}"])
            if limit < 1 or limit > MAX_SEARCH_LIMIT:
                return None, self._invalid_list_filter_response("limit", raw_limit, [f"1..{MAX_SEARCH_LIMIT}"])
            filters["limit"] = limit

        return filters, None

    def _invalid_list_filter_response(self, field, value, allowed):
        return Response(
            build_error_envelope(
                code="LEMMA_LIST_FILTER_INVALID",
                message=f"Invalid list filter '{field}'.",
                detail={
                    "field": field,
                    "value": value,
                    "allowed_values": allowed,
                },
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )
