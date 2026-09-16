import logging

from django.db.models.functions import Length
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
from .part_of_speech import CANONICAL_POS_CODES
from .search import (
    DEFAULT_SEARCH_LIMIT,
    DEFAULT_WORDLIST_LIMIT,
    MAX_SEARCH_LIMIT,
    MAX_WORDLIST_LIMIT,
    SEARCH_NORMALIZER_VERSION,
    compile_grapheme_pattern,
    filter_json_array,
    filter_public_lemmas,
    normalize_search_query,
    order_public_ids_by_seed,
    public_lemma_queryset,
    search_public_lemmas_by_grapheme_pattern,
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
    WordlistEntrySerializer,
)


logger = logging.getLogger(__name__)

HEADWORD_KIND_FILTERS = {
    Lemma.HeadwordKind.WORD,
    Lemma.HeadwordKind.NOUN,
    Lemma.HeadwordKind.VERB_STEM,
    Lemma.HeadwordKind.IDEOPHONE,
    Lemma.HeadwordKind.UNKNOWN,
}
POS_FILTERS = set(CANONICAL_POS_CODES)
DIALECT_FILTERS = {
    "k": "K",
    "ko": "Ko",
    "m": "M",
    "z": "Z",
}

# Wordlist filters the product requirements name but the published lexicon
# cannot back. They are refused rather than ignored: accepting `guessable=true`
# and returning unfiltered lemmas would report a filter that was never applied.
UNSUPPORTED_WORDLIST_FILTERS = {
    "guessable": "no published field records whether a lemma is guessable",
    "character_length": (
        "character length is not stored; use 'length', 'min_length', or 'max_length'"
    ),
    "labels": "published lemmas carry no labels field",
    "exclude_labels": "published lemmas carry no labels field",
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

        # Tier 3: an inflected form resolves to its lemma. The product
        # requirements make this a search tier, not a side channel -- a client
        # searching "ndinobuda" was shown no results at all, only an enrichment
        # blob it had to interpret. It runs only when exact lemma and form
        # matches found nothing, so a lexical hit is never displaced.
        if not results:
            results = self._morphology_lemma_results(
                morphology_analysis, filters=filters
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

    def _morphology_lemma_results(self, morphology_analysis, *, filters):
        """Return the lemmas an inflected query resolves to, in reading order.

        Only readings the analyzer produced under its evidence gates reach this
        point, so an excluded or deferred derivation (an unverified extension
        style, a deferred vowel boundary) yields no result -- exactly as it
        yields no enrichment. Order follows the analyzer's confidence ranking so
        the most likely reading is the first result, rather than the model's
        alphabetical default.
        """
        if not morphology_analysis:
            return []

        lemma_ids: list[str] = []
        for analysis in morphology_analysis.get("analyses", []):
            verb_stem = (analysis.get("slots") or {}).get("verb_stem") or {}
            lemma_id = verb_stem.get("lemma_public_id")
            if isinstance(lemma_id, str) and lemma_id and lemma_id not in lemma_ids:
                lemma_ids.append(lemma_id)
        if not lemma_ids:
            return []

        lemmas = {
            lemma.public_id: lemma
            for lemma in filter_public_lemmas(
                public_lemma_queryset(filters).filter(public_id__in=lemma_ids),
                filters,
            )
        }
        return [
            {
                "result_type": "lemma",
                "match_type": "morphology_lemma",
                "lemma": lemmas[lemma_id],
                "form": None,
            }
            for lemma_id in lemma_ids
            if lemma_id in lemmas
        ][: filters["limit"]]

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
        from shona_api.morphology.services import (
            AnalysisFailure,
            RulesVersionError,
            analyze_text,
            ensure_rules_version_supported,
        )

        try:
            ensure_rules_version_supported(release_metadata["rule_set_version"])
            morphology_analysis = analyze_text(
                raw_query,
                rule_set_version=release_metadata["rule_set_version"],
            )
            self._attach_morphology_lemma_details(morphology_analysis)
        except RulesVersionError as exc:
            # A release whose rule-set version this deployment does not
            # implement must stay visible: search results still return, but the
            # enrichment is explicitly unavailable, never silently dropped.
            record_metric(
                "search.morphology_enrichment.unavailable",
                tags={"code": exc.code},
            )
            return None, {
                "status": "unavailable",
                "code": exc.code,
                "message": str(exc),
                "detail": exc.detail,
            }
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
            # `count` is how many results are in this response, which is all it
            # has ever meant. A client that needs to know whether more exist had
            # no way to ask: reaching the limit is the signal, and it is stated
            # rather than left to be inferred from count == limit.
            "limit": filters["limit"],
            "truncated": len(results) >= filters["limit"],
            "results": SearchResultSerializer(results, many=True).data,
        }
        active_filters = self._active_filter_payload(filters)
        if active_filters:
            payload["query"]["filters"] = active_filters
        if morphology_analysis:
            payload["morphology"] = morphology_analysis
        if morphology_enrichment and morphology_enrichment["status"] in (
            "matched",
            "unavailable",
        ):
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
            queryset = queryset.order_by("normalized_headword", "headword", "public_id")

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


class WordlistView(APIView):
    """Bounded wordlist of published lemmas for word games and drills.

    The catalogue order is the total `public_id` order, optionally rotated by
    `seed`: a daily puzzle asks for the same seed and gets the same sequence,
    and a different seed gets a different one, with no shuffle that would
    change between two identical calls.
    """

    def get(self, request):
        try:
            release_metadata = get_current_release_metadata()
        except CurrentReleaseNotFound:
            return build_current_release_missing_response()

        filters, filter_error = self._parse_filters(request)
        if filter_error:
            return filter_error

        queryset = self._filtered_queryset(filters)
        if filters["seed"] is not None:
            queryset = order_public_ids_by_seed(queryset, filters["seed"])

        limit = filters["limit"]
        offset = filters["offset"]
        lemmas = list(queryset[offset : offset + limit])

        data = {
            # Same contract as /v1/search: `count` is how many lemmas this
            # response holds, and reaching the limit is what says more exist.
            "count": len(lemmas),
            "limit": limit,
            "offset": offset,
            "truncated": len(lemmas) >= limit,
            "results": WordlistEntrySerializer(lemmas, many=True).data,
        }
        active_filters = {
            key: value
            for key, value in filters.items()
            if value is not None and key not in ("limit", "offset")
        }
        if active_filters:
            data["filters"] = active_filters

        return Response(
            build_success_envelope(
                data=data,
                release_metadata=release_metadata,
            ),
            status=status.HTTP_200_OK,
        )

    def _filtered_queryset(self, filters):
        # A wordlist page holds up to 500 flat entries and reads no related
        # rows, so the senses/forms/tone-record prefetches the reading endpoints
        # carry would be paid for and thrown away. The noun class join stays:
        # the entry payload includes it.
        queryset = public_lemma_queryset(filters).prefetch_related(None)
        if filters["dialect"]:
            queryset = filter_json_array(queryset, "dialects", filters["dialect"])
        if filters["grapheme_length"] is not None:
            queryset = queryset.filter(grapheme_count=filters["grapheme_length"])
        if filters["syllable_count"] is not None:
            queryset = queryset.filter(syllable_count=filters["syllable_count"])
        if any(
            filters[key] is not None for key in ("length", "min_length", "max_length")
        ):
            # `length` bounds the headword's characters, which is what the
            # PRD's `min_length`/`max_length` game grids ask for. The lexicon
            # stores no character_length column, so it is measured in SQL.
            queryset = queryset.annotate(headword_length=Length("headword"))
            if filters["length"] is not None:
                queryset = queryset.filter(headword_length=filters["length"])
            if filters["min_length"] is not None:
                queryset = queryset.filter(headword_length__gte=filters["min_length"])
            if filters["max_length"] is not None:
                queryset = queryset.filter(headword_length__lte=filters["max_length"])
        return queryset.order_by("public_id")

    def _parse_filters(self, request):
        unsupported = sorted(
            field
            for field in UNSUPPORTED_WORDLIST_FILTERS
            if field in request.query_params
        )
        if unsupported:
            return None, self._unsupported_filter_response(
                field=unsupported[0],
                value=request.query_params.get(unsupported[0], ""),
            )

        filters = {
            "pos": None,
            "frequency_tier": None,
            "learner_level": None,
            "dialect": None,
            "length": None,
            "min_length": None,
            "max_length": None,
            "grapheme_length": None,
            "syllable_count": None,
            "seed": None,
            "limit": DEFAULT_WORDLIST_LIMIT,
            "offset": 0,
        }

        for param, choice_class in (
            ("frequency_tier", Lemma.FrequencyTier),
            ("learner_level", Lemma.LearnerLevel),
        ):
            value = request.query_params.get(param, "").strip()
            if value:
                if value not in choice_class.values:
                    return None, self._invalid_filter_response(
                        field=param,
                        value=value,
                        allowed=choice_class.values,
                    )
                filters[param] = value

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

        for param in (
            "length",
            "min_length",
            "max_length",
            "grapheme_length",
            "syllable_count",
        ):
            raw_value = request.query_params.get(param, "").strip()
            if not raw_value:
                continue
            try:
                value = int(raw_value)
            except ValueError:
                value = 0
            if value < 1:
                return None, self._invalid_filter_response(
                    field=param,
                    value=raw_value,
                    allowed=["positive integer"],
                )
            filters[param] = value

        raw_seed = request.query_params.get("seed", "").strip()
        if raw_seed:
            try:
                filters["seed"] = int(raw_seed)
            except ValueError:
                return None, self._invalid_filter_response(
                    field="seed",
                    value=raw_seed,
                    allowed=["integer"],
                )

        raw_limit = request.query_params.get("limit", "").strip()
        if raw_limit:
            try:
                limit = int(raw_limit)
            except ValueError:
                limit = 0
            if limit < 1 or limit > MAX_WORDLIST_LIMIT:
                return None, self._invalid_filter_response(
                    field="limit",
                    value=raw_limit,
                    allowed=[f"1..{MAX_WORDLIST_LIMIT}"],
                )
            filters["limit"] = limit

        raw_offset = request.query_params.get("offset", "").strip()
        if raw_offset:
            try:
                offset = int(raw_offset)
            except ValueError:
                offset = -1
            if offset < 0:
                return None, self._invalid_filter_response(
                    field="offset",
                    value=raw_offset,
                    allowed=["0.."],
                )
            filters["offset"] = offset

        return filters, None

    def _unsupported_filter_response(self, *, field, value):
        return Response(
            build_error_envelope(
                code="WORDLIST_FILTER_UNSUPPORTED",
                message=(
                    f"Unsupported wordlist filter '{field}': the published "
                    "lexicon cannot apply it, so results would not be filtered."
                ),
                detail={
                    "field": field,
                    "value": value,
                    "reason": UNSUPPORTED_WORDLIST_FILTERS[field],
                },
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _invalid_filter_response(self, *, field, value, allowed):
        return Response(
            build_error_envelope(
                code="WORDLIST_FILTER_INVALID",
                message=f"Invalid wordlist filter '{field}'.",
                detail={
                    "field": field,
                    "value": value,
                    "allowed_values": allowed,
                },
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )


class PatternSearchView(APIView):
    """Grapheme-aware wildcard search over published lemma headwords.

    `?` matches exactly one stored grapheme and `*` matches zero or more, so
    `s?a` never matches `sha`: `sh` is one grapheme and `sha` is two. Candidate
    rows are narrowed in SQL on the stored `grapheme_count` before any pattern
    is applied in Python, which bounds the scan to rows that could match.
    """

    def get(self, request):
        raw_query = request.query_params.get("q", "")
        pattern_tokens = compile_grapheme_pattern(raw_query)
        if not pattern_tokens:
            return Response(
                build_error_envelope(
                    code="PATTERN_QUERY_REQUIRED",
                    message=(
                        "Pattern search requires a non-empty 'q' query "
                        "parameter."
                    ),
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

        lemmas = search_public_lemmas_by_grapheme_pattern(
            pattern_tokens,
            filters={"pos": filters["pos"]},
            grapheme_length=filters["length"],
            limit=filters["limit"],
        )
        results = [
            {
                "result_type": "lemma",
                "match_type": "grapheme_pattern",
                "lemma": lemma,
                "form": None,
            }
            for lemma in lemmas
        ]

        data = {
            "query": {
                "raw": raw_query,
                # The compiled pattern is echoed because it is what actually
                # matched: `sh` is one token, not two characters.
                "graphemes": list(pattern_tokens),
            },
            "count": len(results),
            "limit": filters["limit"],
            "truncated": len(results) >= filters["limit"],
            "results": SearchResultSerializer(results, many=True).data,
        }
        active_filters = self._active_filter_payload(filters)
        if active_filters:
            data["query"]["filters"] = active_filters

        return Response(
            build_success_envelope(
                data=data,
                release_metadata=release_metadata,
            ),
            status=status.HTTP_200_OK,
        )

    def _parse_filters(self, request):
        filters = {
            "pos": None,
            "length": None,
            "limit": DEFAULT_SEARCH_LIMIT,
        }

        pos = request.query_params.get("pos", "").strip()
        if pos:
            if pos not in POS_FILTERS:
                return None, self._invalid_filter_response(
                    field="pos",
                    value=pos,
                    allowed=sorted(POS_FILTERS),
                )
            filters["pos"] = pos

        raw_length = request.query_params.get("length", "").strip()
        if raw_length:
            try:
                length = int(raw_length)
            except ValueError:
                length = 0
            if length < 1:
                return None, self._invalid_filter_response(
                    field="length",
                    value=raw_length,
                    allowed=["positive integer"],
                )
            filters["length"] = length

        raw_limit = request.query_params.get("limit", "").strip()
        if raw_limit:
            try:
                limit = int(raw_limit)
            except ValueError:
                limit = 0
            if limit < 1 or limit > MAX_SEARCH_LIMIT:
                return None, self._invalid_filter_response(
                    field="limit",
                    value=raw_limit,
                    allowed=[f"1..{MAX_SEARCH_LIMIT}"],
                )
            filters["limit"] = limit

        return filters, None

    def _active_filter_payload(self, filters):
        active = {
            key: value for key, value in filters.items() if value and key != "limit"
        }
        if filters["limit"] != DEFAULT_SEARCH_LIMIT:
            active["limit"] = filters["limit"]
        return active

    def _invalid_filter_response(self, *, field, value, allowed):
        return Response(
            build_error_envelope(
                code="PATTERN_FILTER_INVALID",
                message=f"Invalid pattern search filter '{field}'.",
                detail={
                    "field": field,
                    "value": value,
                    "allowed_values": allowed,
                },
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )
