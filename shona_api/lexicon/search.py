from django.db import connection
from django.db.models import Case, Prefetch, Value, When

from shona_api.editorial.models import ReviewState
from shona_api.phonology import segment_graphemes
from shona_api.phonology.orthography import normalize_orthography

from .models import Form, Lemma

SEARCH_NORMALIZER_VERSION = "shona-orthography-normalizer-v2"


DEFAULT_SEARCH_LIMIT = 20
MAX_SEARCH_LIMIT = 50
DEFAULT_WORDLIST_LIMIT = 20
MAX_WORDLIST_LIMIT = 500
PUBLIC_REVIEW_STATES = (ReviewState.PUBLISHED,)

# `/v1/search/pattern` wildcards, counted in graphemes rather than characters.
PATTERN_ONE_GRAPHEME = "?"
PATTERN_MANY_GRAPHEMES = "*"


def normalize_search_query(value):
    """Normalize a search query with the canonical orthography helper."""
    return normalize_orthography(value)


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


def compile_grapheme_pattern(pattern):
    """Tokenize a wildcard pattern into graphemes and wildcard tokens.

    Literal text is segmented with the same inventory, and normalized with the
    same helper, that `Lemma.save` uses for the stored `graphemes` list: `sha`
    is the two graphemes `sh` and `a`, never three characters. `?` and `*` are
    kept as tokens of their own, so they survive normalization -- the orthography
    helper strips leading `*` as a Hannan annotation marker and would otherwise
    eat the wildcard.
    """
    tokens: list[str] = []
    literal: list[str] = []

    def flush_literal():
        if literal:
            tokens.extend(segment_graphemes(normalize_search_query("".join(literal))))
            literal.clear()

    for character in pattern:
        if character in (PATTERN_ONE_GRAPHEME, PATTERN_MANY_GRAPHEMES):
            flush_literal()
            tokens.append(character)
        else:
            literal.append(character)
    flush_literal()
    return tuple(tokens)


def grapheme_pattern_length_bounds(tokens):
    """Return the (minimum, maximum) grapheme counts a pattern can match."""
    minimum = sum(1 for token in tokens if token != PATTERN_MANY_GRAPHEMES)
    if PATTERN_MANY_GRAPHEMES in tokens:
        return minimum, None
    return minimum, minimum


def matches_grapheme_pattern(graphemes, tokens):
    """Match stored graphemes against compiled pattern tokens.

    `?` consumes exactly one stored grapheme, `*` zero or more. Backtracking on
    the last `*` keeps `s*a` matching both `sa` and `sadza`.
    """
    grapheme_index = 0
    token_index = 0
    star_token_index = -1
    star_grapheme_index = 0

    while grapheme_index < len(graphemes):
        token = tokens[token_index] if token_index < len(tokens) else None
        if token is not None and (
            token == PATTERN_ONE_GRAPHEME or token == graphemes[grapheme_index]
        ):
            grapheme_index += 1
            token_index += 1
        elif token == PATTERN_MANY_GRAPHEMES:
            star_token_index = token_index
            star_grapheme_index = grapheme_index
            token_index += 1
        elif star_token_index >= 0:
            star_grapheme_index += 1
            grapheme_index = star_grapheme_index
            token_index = star_token_index + 1
        else:
            return False

    while token_index < len(tokens) and tokens[token_index] == PATTERN_MANY_GRAPHEMES:
        token_index += 1
    return token_index == len(tokens)


def bound_pattern_candidates(queryset, tokens, *, grapheme_length=None):
    """Narrow the candidate rows in SQL before any pattern runs in Python.

    `grapheme_count` is stored on every lemma, so the pattern's own length
    bounds -- or an explicit exact grapheme length -- decide in the database
    which rows could match at all.
    """
    if grapheme_length is not None:
        return queryset.filter(grapheme_count=grapheme_length)
    minimum, maximum = grapheme_pattern_length_bounds(tokens)
    if maximum is None:
        return queryset.filter(grapheme_count__gte=minimum)
    return queryset.filter(grapheme_count=maximum)


def search_public_lemmas_by_grapheme_pattern(
    tokens,
    *,
    filters=None,
    grapheme_length=None,
    limit=DEFAULT_SEARCH_LIMIT,
):
    """Return published lemmas whose stored graphemes match the pattern.

    Candidates are read as ids and stored graphemes only and the scan stops as
    soon as `limit` matches are found, so a broad pattern cannot pull the whole
    lexicon into memory. Matched lemmas are then loaded once, through the same
    public queryset the other endpoints use, in match order.
    """
    filters = build_public_search_filters(**(filters or {}))
    candidates = bound_pattern_candidates(
        public_lemma_queryset(filters)
        .order_by("normalized_headword", "headword", "public_id")
        .values_list("public_id", "graphemes"),
        tokens,
        grapheme_length=grapheme_length,
    )

    matched_public_ids: list[str] = []
    for public_id, graphemes in candidates.iterator():
        if matches_grapheme_pattern(graphemes or [], tokens):
            matched_public_ids.append(public_id)
            if len(matched_public_ids) >= limit:
                break

    if not matched_public_ids:
        return []
    lemmas = {
        lemma.public_id: lemma
        for lemma in public_lemma_queryset(filters).filter(
            public_id__in=matched_public_ids,
        )
    }
    return [
        lemmas[public_id]
        for public_id in matched_public_ids
        if public_id in lemmas
    ]


def order_public_ids_by_seed(queryset, seed):
    """Order a queryset by `public_id`, rotated by `seed`.

    The rotation is a cyclic shift of the total public_id order, resolved to a
    pivot row in the database rather than shuffled row by row: the same seed
    always yields the same sequence, seeds that differ modulo the number of
    matching rows yield different ones, and pagination stays a slice of one
    deterministic ordering instead of a fresh shuffle per page. `random()` and
    `order_by("?")` are deliberately not used -- they change between calls,
    which is exactly what a reproducible daily puzzle cannot tolerate.
    """
    ordered = queryset.order_by("public_id")
    total = ordered.count()
    if total < 2:
        return ordered
    rotation = seed % total
    pivot = list(
        ordered.values_list("public_id", flat=True)[rotation : rotation + 1]
    )
    if not pivot:
        return ordered
    return ordered.annotate(
        seed_rotation=Case(
            When(public_id__lt=pivot[0], then=Value(1)),
            default=Value(0),
        )
    ).order_by("seed_rotation", "public_id")


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
        .order_by("-similarity", "public_id")
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
        .order_by("-similarity", "public_id")
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
