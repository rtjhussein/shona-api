from django.db import connection
from django.db.models import Prefetch

from shona_api.editorial.models import ReviewState

from .models import Form, Lemma


from shona_api.phonology.orthography import strip_annotation_markers

SEARCH_NORMALIZER_VERSION = "shona-orthography-normalizer-v2"


DEFAULT_SEARCH_LIMIT = 20
MAX_SEARCH_LIMIT = 50
PUBLIC_REVIEW_STATES = (ReviewState.PUBLISHED,)


def normalize_search_query(value):
    normalized = " ".join(value.strip().split()).casefold()
    # Annotation glyphs (dagger/asterisk) and hyphens are stripped from the
    # query start for the same reason Lemma.save / Form.save strip them from
    # stored normalized fields: they are typography, not part of the word.
    return strip_annotation_markers(normalized)

def filter_json_array(queryset, field_name, value):
    if connection.vendor == "sqlite":
        return queryset.filter(**{f"{field_name}__icontains": f'"{value}"'})
    return queryset.filter(**{f"{field_name}__contains": value})


def build_public_search_filters(*, limit=DEFAULT_SEARCH_LIMIT, **overrides):
    filters = {
        "headword_kind": None,
        "pos": None,
        "dialect": None,
        "limit": limit,
        "learner_level": None,
        "curriculum_stage": None,
        "frequency_tier": None,
        "communication_context": None,
        "noun_class": None,
        "random": False,
    }
    filters.update(overrides)
    return filters


def public_lemma_queryset(filters=None):
    filters = filters or {}
    queryset = Lemma.objects.filter(
        review_state__in=PUBLIC_REVIEW_STATES,
    ).select_related(
        "noun_class",
        "noun_class__default_plural_class",
    ).prefetch_related(
        "senses",
        "tone_records__form",
        "forms__sense",
    )
    if filters.get("headword_kind"):
        queryset = queryset.filter(headword_kind=filters["headword_kind"])
    if filters.get("pos"):
        queryset = queryset.filter(part_of_speech_code=filters["pos"])
    if filters.get("learner_level"):
        queryset = queryset.filter(learner_level=filters["learner_level"])
    if filters.get("curriculum_stage"):
        queryset = queryset.filter(curriculum_stage=filters["curriculum_stage"])
    if filters.get("frequency_tier"):
        queryset = queryset.filter(frequency_tier=filters["frequency_tier"])
    if filters.get("communication_context"):
        queryset = filter_json_array(
            queryset,
            "communication_contexts",
            filters["communication_context"],
        )
    if filters.get("noun_class"):
        queryset = queryset.filter(noun_class__class_number=filters["noun_class"])
    return queryset


def public_form_queryset(filters=None):
    filters = filters or {}
    queryset = (
        Form.objects.filter(
            review_state__in=PUBLIC_REVIEW_STATES,
            lemma__review_state__in=PUBLIC_REVIEW_STATES,
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
    if filters.get("headword_kind"):
        queryset = queryset.filter(lemma__headword_kind=filters["headword_kind"])
    if filters.get("pos"):
        queryset = queryset.filter(lemma__part_of_speech_code=filters["pos"])
    if filters.get("learner_level"):
        queryset = queryset.filter(lemma__learner_level=filters["learner_level"])
    if filters.get("curriculum_stage"):
        queryset = queryset.filter(lemma__curriculum_stage=filters["curriculum_stage"])
    if filters.get("frequency_tier"):
        queryset = queryset.filter(lemma__frequency_tier=filters["frequency_tier"])
    if filters.get("communication_context"):
        queryset = filter_json_array(
            queryset,
            "lemma__communication_contexts",
            filters["communication_context"],
        )
    if filters.get("noun_class"):
        queryset = queryset.filter(lemma__noun_class__class_number=filters["noun_class"])
    return queryset


def filter_public_lemmas(queryset, filters=None):
    lemmas = list(queryset)
    dialect = (filters or {}).get("dialect")
    if dialect:
        lemmas = [lemma for lemma in lemmas if dialect in (lemma.dialects or [])]
    return lemmas


def filter_public_forms(queryset, filters=None):
    forms = list(queryset)
    dialect = (filters or {}).get("dialect")
    if dialect:
        forms = [
            form
            for form in forms
            if dialect in (form.lemma.dialects or [])
        ]
    return forms


def search_public_records(normalized_query, *, filters=None):
    filters = build_public_search_filters(**(filters or {}))
    limit = filters["limit"]
    lemma_results = [
        {
            "result_type": "lemma",
            "match_type": "exact_lemma",
            "lemma": lemma,
            "form": None,
        }
        for lemma in filter_public_lemmas(
            public_lemma_queryset(filters).filter(
                normalized_headword=normalized_query,
            ),
            filters,
        )[:limit]
    ]
    remaining_limit = max(limit - len(lemma_results), 0)
    form_results = [
        {
            "result_type": "form",
            "match_type": "exact_form",
            "lemma": form.lemma,
            "form": form,
        }
        for form in filter_public_forms(
            public_form_queryset(filters).filter(
                normalized_form=normalized_query,
            ),
            filters,
        )[:remaining_limit]
    ]
    return lemma_results + form_results


def search_public_records_fuzzy(normalized_query, *, filters=None):
    from django.contrib.postgres.search import TrigramSimilarity

    filters = build_public_search_filters(**(filters or {}))
    limit = filters["limit"]

    lemma_queryset = (
        public_lemma_queryset(filters)
        .annotate(similarity=TrigramSimilarity("normalized_headword", normalized_query))
        .filter(similarity__gte=0.3)
        .order_by("-similarity")
    )
    lemma_results = [
        {
            "result_type": "lemma",
            "match_type": "fuzzy_lemma",
            "lemma": lemma,
            "form": None,
        }
        for lemma in filter_public_lemmas(lemma_queryset, filters)[:limit]
    ]

    remaining_limit = max(limit - len(lemma_results), 0)

    form_queryset = (
        public_form_queryset(filters)
        .annotate(similarity=TrigramSimilarity("normalized_form", normalized_query))
        .filter(similarity__gte=0.3)
        .order_by("-similarity")
    )
    form_results = [
        {
            "result_type": "form",
            "match_type": "fuzzy_form",
            "lemma": form.lemma,
            "form": form,
        }
        for form in filter_public_forms(form_queryset, filters)[:remaining_limit]
    ]

    return lemma_results + form_results
