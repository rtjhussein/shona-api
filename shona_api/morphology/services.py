from dataclasses import dataclass

from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Lemma, NounClass
from shona_api.lexicon.search import SEARCH_NORMALIZER_VERSION, normalize_search_query
from shona_api.phonology import compute_phonology_fields


ANALYZER_VERSION = "shona-morphology-analyzer-v1"
GENERATOR_VERSION = "shona-morphology-generator-v1"
# The rule-set version implemented by this code. Public endpoints validate the
# serving release's rule_set_version against it (Finding 5 policy): responses
# never echo a version label the engine does not execute.
MORPHOLOGY_RULES_VERSION = "morphology-rules-v5"
RULES_VERSION_ERROR_CODE = "MORPHOLOGY_RULES_VERSION_UNSUPPORTED"
SUPPORTED_RULE_ID = "fortune.verbal.slots.001"
INFINITIVE_RULE_ID = "fortune.verbal.infinitive.001"
EXTENSIONS_RULE_ID = "fortune.verbal.extensions.001"
REVERSIVE_RULE_ID = "fortune.verbal.reversive.001"
REPETITIVE_RULE_ID = "fortune.verbal.repetitive.001"
RECIPROCAL_RULE_ID = "fortune.verbal.reciprocal.001"
RETAINED_EXTENSIONS_RULE_ID = "fortune.verbal.extensions.retained.001"
EXTENSIONS_SOURCE_LOCATOR = (
    "Fortune, Shona Grammatical Constructions Vol. 1 (1985), "
    "section 2.10.2.3.3 'Extended radicals', PDF p. 33 (printed p. 21)"
)
INFINITIVE_SOURCE_LOCATOR = (
    "Fortune Grammatical Constructions, section 3.3.18 Noun Class 15, "
    "PDF pages 90-91 (printed pp. 78-79)"
)
SUPPORTED_TENSE_ASPECT_MARKER = "no"
INFINITIVE_PREFIX = "ku"
INFINITIVE_NEGATIVE_MARKER = "sa"
INFINITIVE_REFLEXIVE_SURFACE = "zvi"
INFINITIVE_ANALYZER_CONFIDENCE = 0.82
# Bounded infinitive ambiguity budget: at most this many ku- readings
# (polarity x no-object/reflexive/object-concord x stem candidates) are
# collected before the remaining segmentations are skipped.
_MAX_INFINITIVE_ANALYSES = 12
SUPPORTED_ANALYSIS_SHAPE = (
    "ku + [sa] + [object_concord | zvi-reflexive] + reviewed verb_stem / "
    "subject_concord + no + [object_concord] + verb_stem / "
    "ha + subject_concord + [object_concord] + verb_stem_ending_in_i"
)
SUPPORTED_ANALYSIS_RULE_IDS = [
    INFINITIVE_RULE_ID,
    SUPPORTED_RULE_ID,
    "fortune.verbal.negation.001",
    "fortune.concord.object.001",
]
# Extension-like endings used only to label unmatched 422 surfaces; the real
# segmentation inventory lives in _EXTENSION_SURFACES below.
EXTENSION_LIKE_SUFFIXES = (
    "anur",
    "enur",
    "inur",
    "onor",
    "unur",
    "urur",
    "oror",
    "irirwa",
    "erwa",
    "irwa",
    "iswa",
    "eswa",
    "idzwa",
    "edza",
    "udzwa",
    "dzirwa",
    "itsa",
    "etsa",
    "idz",
    "edz",
    "its",
    "ets",
    "ika",
    "eka",
    "ana",
    "zwa",
    "wa",
)
SUPPORTED_REVIEW_STATES = (
    ReviewState.APPROVED,
    ReviewState.PUBLISHED,
)
#
# Shared verb-extension rule table.
#
# Single source of truth for the generator (_apply_extensions) and the analyzer
# (_candidate_decompositions) so the two sides cannot drift. Grounded in
# Fortune Vol. 1, section 2.10.2.3.3 (PDF p. 33 / printed p. 21):
# - Height harmony: -iC- allomorphs surface as -eC- after radical /e/ or /o/.
# - Reversive vowel copy: the first vowel copies the radical vowel
#   (a -> -anur-, e -> -enur-, i -> -inur-, o -> -onor-, u -> -unur-).
# - Repetitive (-urur-, or -oror- after /o/) is distinct from reversive.
# - Causative (1) -idz-/-edz-: shape attested in section (d), but the full
#   lexical distribution is deferred to Volume 2 section 4.2.6.3.2, which is
#   not available; treat per-lemma productivity as restricted.
# - Reciprocal -an-, short reversive -ur-/-or- and causative -its-/-ets- have
#   no locator in the available volume and are explicitly retained (see the
#   retained rule card), never silently presented as source-backed.
#
# (surface, type, style or None) ordered longest-first for segmentation.
_EXTENSION_SURFACES: tuple[tuple[str, str, str | None], ...] = (
    ("anur", "reversive", "long"),
    ("enur", "reversive", "long"),
    ("inur", "reversive", "long"),
    ("onor", "reversive", "long"),
    ("unur", "reversive", "long"),
    ("urur", "repetitive", None),
    ("oror", "repetitive", None),
    ("idz", "causative", "dz"),
    ("edz", "causative", "dz"),
    ("its", "causative", "ts"),
    ("ets", "causative", "ts"),
    ("is", "causative", None),
    ("es", "causative", None),
    ("ir", "applicative", None),
    ("er", "applicative", None),
    ("ik", "neuter", None),
    ("ek", "neuter", None),
    ("iw", "passive", None),
    ("ew", "passive", None),
    ("an", "reciprocal", None),
    ("ur", "reversive", "short"),
    ("or", "reversive", "short"),
    ("w", "passive", None),
)
_MID_VOWELS = frozenset({"e", "o"})
# Extension types accepted by v1 generation, in supported application order.
# Fortune 2.10.2.3.3 states "R + extension(s)" and gives allomorphy per
# extension, but no ordering rule; attested multi-extension radicals appear in
# section 3.4.2.8 (e.g. -pamhidz-ir-an-, PDF p. 110 / printed p. 98). The
# canonical order below is therefore a documented product convention that
# generation and analysis share (Finding 3 policy), not a claimed grammar rule.
_SUPPORTED_EXTENSION_TYPES = (
    "causative",
    "applicative",
    "reciprocal",
    "reversive",
    "repetitive",
    "neuter",
    "passive",
)
# Styles accepted per type; empty means the type takes no style argument.
_EXTENSION_STYLES: dict[str, tuple[str, ...]] = {
    "passive": (),
    "causative": ("dz", "ts"),
    "applicative": (),
    "neuter": (),
    "reciprocal": (),
    "reversive": ("long", "short"),
    "repetitive": (),
}
# Legacy reversive style names that named -urur-/-oror- surfaces. Those are
# the repetitive extension now; generation rejects them with a pointer.
_REVERSIVE_REPETITIVE_STYLE_NAMES = frozenset({"long_urur", "urur", "oror"})
# Legacy names for the long -VnVr- reversive before vowel copy was enforced.
_REVERSIVE_LONG_STYLE_ALIASES = frozenset({"long_unur", "unur", "onor"})
#
# Evidence-gated generation (Finding 4 policy).
#
# The analyzer may still recognize these allomorphs on attested surfaces, but
# the generator must not synthesize them for an arbitrary lemma:
# - causative "dz": -idz-/-edz- shape and vowel conditioning are attested
#   (Fortune section (d); Hannan -edza p. 158, -idza p. 240), but which lemma
#   takes -idz- versus -is- is a per-lemma choice; the distribution section
#   (Fortune 4.2.6.3.2) is not available.
# - causative "ts": no source attests an -its-/-ets- extension allomorph at
#   all (Hannan derives -ts- only via radical mutation, e.g. -muk- + -y-).
# - reversive "short": Fortune lists only the long vowel-copy forms; Hannan's
#   suffix list (printed p. xii) names a -ura suffix, but its dictionary entry
#   (conditioning, base pairs) could not be located in the available sources.
_UNVERIFIED_GENERATION_STYLES = frozenset({"dz", "ts"})
_UNVERIFIED_GENERATION_TYPE_STYLES = frozenset({("reversive", "short")})
EXTENSION_UNVERIFIED_ERROR_CODE = "EXTENSION_UNVERIFIED"
_MAX_EXTENSIONS_PER_REQUEST = 3
_MAX_STEM_CANDIDATES = 8
_MAX_EXTENSION_DEPTH = 3
_MAX_ANALYSES = 25
# Bounded ambiguity budget per subject candidate: at most this many distinct
# readings (no-object + object concords x stem candidates) are collected before
# the remaining segmentations are skipped (Finding 2 bounds).
_MAX_ANALYSES_PER_SUBJECT = 12


@dataclass(frozen=True)
class AnalysisFailure(Exception):
    code: str
    message: str
    detail: dict[str, object] | None = None


@dataclass(frozen=True)
class GenerationFailure(Exception):
    code: str
    message: str
    detail: dict[str, object] | None = None



class RulesVersionError(Exception):
    """The serving release declares a rule-set version this code does not run.

    Raised before any analyze/generate work when the configured release's
    rule_set_version does not match MORPHOLOGY_RULES_VERSION, so responses can
    never echo a version label the engine does not execute (Finding 5).
    """

    def __init__(
        self,
        *,
        received: str,
        implemented: str,
    ) -> None:
        self.code = RULES_VERSION_ERROR_CODE
        self.received = received
        self.implemented = implemented
        super().__init__(
            f"Data release declares rule-set version {received!r}, but this "
            f"deployment implements {implemented!r}. Publish a release whose "
            "rule_set_version matches the implemented rules."
        )

    @property
    def detail(self) -> dict[str, object]:
        return {
            "field": "rule_set_version",
            "received": self.received,
            "implemented": self.implemented,
            "setup_command": (
                "python manage.py ensure_current_release --version <version> "
                f'--label "<label>" --rule-set-version {self.implemented}'
            ),
        }


def ensure_rules_version_supported(rule_set_version: str) -> None:
    """Gate public endpoints on the implemented morphology rules version."""
    if rule_set_version != MORPHOLOGY_RULES_VERSION:
        raise RulesVersionError(
            received=rule_set_version,
            implemented=MORPHOLOGY_RULES_VERSION,
        )


PERSON_SUBJECT_CONCORDS = (
    {
        "surface": "ndi",
        "slot_type": "person",
        "person": "first",
        "number": "singular",
        "label": "1st person singular subject concord",
        "confidence": 0.86,
    },
    {
        "surface": "u",
        "slot_type": "person",
        "person": "second",
        "number": "singular",
        "label": "2nd person singular subject concord",
        "confidence": 0.84,
    },
    {
        "surface": "ti",
        "slot_type": "person",
        "person": "first",
        "number": "plural",
        "label": "1st person plural subject concord",
        "confidence": 0.84,
    },
    {
        "surface": "mu",
        "slot_type": "person",
        "person": "second",
        "number": "plural",
        "label": "2nd person plural subject concord",
        "confidence": 0.82,
    },
)

PERSON_OBJECT_CONCORDS = (
    {
        "surface": "ndi",
        "slot_type": "person",
        "person": "first",
        "number": "singular",
        "label": "1st person singular object concord",
        "confidence": 0.86,
    },
    {
        "surface": "ku",
        "slot_type": "person",
        "person": "second",
        "number": "singular",
        "label": "2nd person singular object concord",
        "confidence": 0.84,
    },
    {
        "surface": "ti",
        "slot_type": "person",
        "person": "first",
        "number": "plural",
        "label": "1st person plural object concord",
        "confidence": 0.84,
    },
    {
        "surface": "mu",
        "slot_type": "person",
        "person": "third",
        "number": "singular",
        "label": "3rd person singular object concord",
        "confidence": 0.84,
    },
    {
        "surface": "va",
        "slot_type": "person",
        "person": "third",
        "number": "plural",
        "label": "3rd person plural object concord",
        "confidence": 0.84,
    },
    {
        "surface": "mu",
        "slot_type": "person",
        "person": "second",
        "number": "plural",
        "label": "2nd person plural object concord",
        "confidence": 0.82,
    },
)


def analyze_text(raw_text: str, *, rule_set_version: str) -> dict[str, object]:
    normalized = normalize_search_query(raw_text)
    if not normalized:
        raise AnalysisFailure(
            code="ANALYSIS_TEXT_REQUIRED",
            message="Analysis requires a non-empty 'text' string.",
        )
    if " " in normalized:
        raise AnalysisFailure(
            code="ANALYSIS_UNSUPPORTED",
            message="Only single-token verb forms are supported by analyze v1.",
            detail={"normalized": normalized},
        )

    candidates = _candidate_subject_concords()

    # Build negative candidate overrides (Class 1 & 1a subject concord "u" -> "a")
    neg_candidates = []
    for candidate in candidates:
        neg_cand = dict(candidate)
        if neg_cand.get("slot_type") == "noun_class" and neg_cand.get("class_number") in ("1", "1a"):
            neg_cand["surface"] = "a"
        neg_candidates.append(neg_cand)
    # Sort negative candidates by surface length descending
    neg_candidates.sort(key=lambda candidate: len(candidate["surface"]), reverse=True)

    analyses: list[dict[str, object]] = []
    infinitive_deferred: list[str] = []
    finite_deferred: list[str] = []
    pro_verb_exclusions: list[str] = []
    analyses.extend(_analyze_ku_infinitive(normalized, infinitive_deferred))

    analyses.extend([
        analysis
        for candidate in candidates
        for analysis in _analyze_present_positive(normalized, candidate, finite_deferred)
    ])

    analyses.extend([
        analysis
        for candidate in neg_candidates
        for analysis in _analyze_present_negative(
            normalized, candidate, finite_deferred, pro_verb_exclusions
        )
    ])

    if not analyses:
        detail = {
            "normalized": normalized,
            "supported_shape": SUPPORTED_ANALYSIS_SHAPE,
            "supported_rule_ids": SUPPORTED_ANALYSIS_RULE_IDS,
        }
        future_lanes = _unsupported_future_lanes(
            normalized, infinitive_deferred, finite_deferred, pro_verb_exclusions
        )
        if future_lanes:
            detail["future_lanes"] = future_lanes
        raise AnalysisFailure(
            code="ANALYSIS_UNSUPPORTED",
            message=(
                "No supported v1 analysis matched the input. Supported v1 forms "
                "are ku- infinitive forms (ku + [sa] + [object_concord | "
                "zvi-reflexive] + reviewed verb stem), positive present verb "
                "forms (subject concord + 'no' + [object_concord] + verb_stem), "
                "and negative present verb forms (ha- + subject concord + "
                "[object_concord] + verb_stem ending in -i, with the attested "
                "Zezuru -e spelling analyzed as a dialect variant)."
            ),
            detail=detail,
        )

    analyses.sort(key=lambda item: item["confidence"], reverse=True)
    del analyses[_MAX_ANALYSES:]
    return {
        "query": {
            "raw": raw_text,
            "normalized": normalized,
            "normalizer": SEARCH_NORMALIZER_VERSION,
        },
        "analyzer_version": ANALYZER_VERSION,
        "rule_set_version": rule_set_version,
        "count": len(analyses),
        "analyses": analyses,
    }


def generate_form(
    *,
    lemma_public_id: str,
    features: dict[str, object],
    rule_set_version: str,
) -> dict[str, object]:
    lemma = _get_generation_verb_stem(lemma_public_id)
    if features.get("generation_type") == "infinitive":
        return _generate_infinitive(
            lemma_public_id=lemma_public_id,
            lemma=lemma,
            features=features,
            rule_set_version=rule_set_version,
        )
    _validate_supported_generation_features(features)
    subject_candidate = _resolve_generation_subject(features["subject"])
    object_candidate = _resolve_generation_object(features.get("object"))

    polarity = features.get("polarity", "positive")
    has_object = object_candidate is not None

    # Handle optional extensions through the strict validation gate: unknown
    # types/styles, repeats, unsupported orders and over-long stacks raise
    # structured GENERATION_UNSUPPORTED instead of falling back to a default.
    normalized_exts = _normalize_generation_extensions(features.get("extensions", []))

    canonical_headword = lemma.normalized_headword
    if normalized_exts:
        extended_base, applied_extensions = _apply_extensions(canonical_headword, normalized_exts)
        stem_val = extended_base + "a"
    else:
        stem_val = canonical_headword
        applied_extensions = []

    if polarity == "negative":
        # Standard negative Class 1 override:
        if subject_candidate.get("slot_type") == "noun_class" and subject_candidate.get("class_number") in ("1", "1a"):
            subject_candidate["surface"] = "a"

        sc = subject_candidate["surface"]
        if canonical_headword in _PRO_VERB_STEMS:
            raise GenerationFailure(
                code="GENERATION_UNSUPPORTED",
                message=(
                    "Unsupported v1 generation feature: lemma_stem. The "
                    "defective pro-verb stem does not participate in the "
                    "negated -no- present terminal rule, so no supported "
                    "finite negative shape applies to it."
                ),
                detail={
                    "field": "lemma_stem",
                    "received": lemma.headword,
                    "reason": "defective_pro_verb_stem",
                    "supported": [
                        "lexical verb stems whose negated -no- present "
                        "terminal is derivable; the defective pro-verb -na "
                        "carries its own -ne/-na paradigm (Hannan front "
                        "matter; FSI Unit 12: pro-verb stems keep their "
                        "final vowels) and its attested forms resolve only "
                        "as their own reviewed lemmas"
                    ],
                    "supported_shape": "subject_concord + no + [object_concord] + verb_stem / ha + subject_concord + [object_concord] + verb_stem_ending_in_i",
                    "supported_rule_ids": [
                        SUPPORTED_RULE_ID,
                        "fortune.verbal.negation.001",
                        "fortune.concord.object.001",
                    ],
                },
            )
        if stem_val.endswith("a"):
            # Negated -no- present terminal: final -a becomes -i (Standard
            # Shona: Hannan front-matter paradigm "Handidyi St. Sh.", FSI
            # Unit 12 Handízíví/Handítaúrí; the Zezuru -e variant
            # "Handidye Z" / Fortune ha-ndí-zív-é is analyzed as a dialect
            # spelling, not generated). Stems that do not end in -a
            # (divergent stems such as -ti, -nzi, Fortune 3.3.18) are taken
            # as-is; no terminal is appended.
            stem_mutated = stem_val[:-1] + "i"
        else:
            stem_mutated = stem_val

        boundary = _finite_boundary_deferred(
            polarity="negative",
            subject_surface=sc,
            object_surface=object_candidate["surface"] if has_object else None,
            stem_surface=stem_mutated,
        )
        if boundary is not None:
            raise _deferred_finite_generation(boundary=boundary, features=features)

        if has_object:
            form = f"ha{sc}{object_candidate['surface']}{stem_mutated}"
        else:
            form = f"ha{sc}{stem_mutated}"

        confidence = min(subject_candidate["confidence"], object_candidate["confidence"]) if has_object else subject_candidate["confidence"]
        rule_id = "fortune.concord.object.001" if has_object else "fortune.verbal.negation.001"

        generated = {
            "generation_type": "verb_form",
            "form": form,
            "normalized": normalize_search_query(form),
            "confidence": confidence,
            "rule_id": rule_id,
            "lemma": _lemma_payload(lemma),
            "slots": {
                "subject": _subject_slot(subject_candidate),
                "tense_aspect": None,
                "polarity": {
                    "surface": "ha",
                    "value": "negative",
                    "label": "present negative marker",
                },
                "object": _subject_slot(object_candidate) if has_object else None,
                "verb_stem": {
                    "surface": stem_mutated,
                    "lemma_public_id": lemma.public_id,
                },
                "extensions": applied_extensions,
                "final_vowel": {
                    "surface": stem_mutated[-1],
                    "value": stem_mutated[-1],
                },
            },
            "phonology": compute_phonology_fields(form),
        }
    else:
        sc = subject_candidate["surface"]
        if has_object:
            oc = object_candidate["surface"]
            boundary = _finite_boundary_deferred(
                polarity="positive",
                object_surface=oc,
                stem_surface=stem_val,
            )
            if boundary is not None:
                raise _deferred_finite_generation(boundary=boundary, features=features)
            form = f"{sc}{SUPPORTED_TENSE_ASPECT_MARKER}{oc}{stem_val}"
        else:
            form = f"{sc}{SUPPORTED_TENSE_ASPECT_MARKER}{stem_val}"
        confidence = min(subject_candidate["confidence"], object_candidate["confidence"]) if has_object else subject_candidate["confidence"]
        rule_id = "fortune.concord.object.001" if has_object else SUPPORTED_RULE_ID

        generated = {
            "generation_type": "verb_form",
            "form": form,
            "normalized": normalize_search_query(form),
            "confidence": confidence,
            "rule_id": rule_id,
            "lemma": _lemma_payload(lemma),
            "slots": {
                "subject": _subject_slot(subject_candidate),
                "tense_aspect": {
                    "surface": SUPPORTED_TENSE_ASPECT_MARKER,
                    "value": "present",
                    "label": "positive present marker",
                },
                "polarity": {
                    "surface": "",
                    "value": "positive",
                    "label": "No negative marker generated in supported v1 pattern.",
                },
                "object": _subject_slot(object_candidate) if has_object else None,
                "verb_stem": {
                    "surface": stem_val,
                    "lemma_public_id": lemma.public_id,
                },
                "extensions": applied_extensions,
                "final_vowel": {
                    "surface": stem_val[-1],
                    "value": stem_val[-1],
                },
            },
            "phonology": compute_phonology_fields(form),
        }

    has_extensions = bool(applied_extensions)
    warnings = [
        {
            "code": "GENERATION_PARTIAL_RULE_SET",
            "message": (
                "v1 generation supports only single-token positive present verb forms."
                if polarity == "positive" else
                "v1 generation supports only single-token negative present verb forms."
            ),
        },
    ]
    if polarity == "positive":
        if has_extensions:
            tone_message = (
                "Tone and negative forms are not generated."
                if has_object else
                "Tone, object markers, and negative forms are not generated."
            )
        else:
            tone_message = "Tone, negative forms, and extensions are not generated." if has_object else "Tone, object markers, negative forms, and extensions are not generated."
        warnings.append({
            "code": "TONE_NOT_GENERATED",
            "message": tone_message,
        })
    else:
        if has_extensions:
            tone_message = (
                "Tone is not generated."
                if has_object else
                "Tone and object markers are not generated."
            )
        else:
            tone_message = "Tone and extensions are not generated." if has_object else "Tone, object markers, and extensions are not generated."
        warnings.append({
            "code": "TONE_NOT_GENERATED",
            "message": tone_message,
        })

    return {
        "input": {
            "lemma_public_id": lemma_public_id,
            "features": features,
        },
        "generator_version": GENERATOR_VERSION,
        "rule_set_version": rule_set_version,
        "confidence": generated["confidence"],
        "generated": generated,
        "warnings": warnings,
        "metadata": {
            "supported_shape": (
                "subject_concord + no + [object_concord] + verb_stem"
                if polarity == "positive" else
                "ha + subject_concord + [object_concord] + verb_stem_ending_in_i"
            ),
            "supported_rule_ids": [generated["rule_id"], *_rule_ids_for_extensions(applied_extensions)],
            "normalizer": SEARCH_NORMALIZER_VERSION,
        },
    }


def _candidate_subject_concords() -> list[dict[str, object]]:
    candidates = [dict(candidate) for candidate in PERSON_SUBJECT_CONCORDS]
    candidates.extend(_noun_class_subject_concords())
    return sorted(candidates, key=lambda candidate: len(candidate["surface"]), reverse=True)


def _noun_class_subject_concords() -> list[dict[str, object]]:
    return [
        {
            "surface": noun_class.subject_concord.casefold(),
            "slot_type": "noun_class",
            "class_number": noun_class.class_number,
            "noun_class_public_id": noun_class.public_id,
            "label": noun_class.label,
            "confidence": 0.78,
        }
        for noun_class in NounClass.objects.filter(
            review_state__in=SUPPORTED_REVIEW_STATES,
        )
        .exclude(subject_concord="")
        .order_by("display_order", "class_number")
    ]


def _noun_class_object_concords() -> list[dict[str, object]]:
    return [
        {
            "surface": noun_class.object_concord.casefold(),
            "slot_type": "noun_class",
            "class_number": noun_class.class_number,
            "noun_class_public_id": noun_class.public_id,
            "label": noun_class.label,
            "confidence": 0.78,
        }
        for noun_class in NounClass.objects.filter(
            review_state__in=SUPPORTED_REVIEW_STATES,
        )
        .exclude(object_concord="")
        .order_by("display_order", "class_number")
    ]


def _candidate_object_concords() -> list[dict[str, object]]:
    candidates = [dict(candidate) for candidate in PERSON_OBJECT_CONCORDS]
    candidates.extend(_noun_class_object_concords())
    return sorted(candidates, key=lambda candidate: len(candidate["surface"]), reverse=True)


def _infinitive_polarity_slot(polarity: str) -> dict[str, object]:
    """Shared infinitive polarity slot; analyzer and generator agree on it."""
    if polarity == "negative":
        return {
            "surface": INFINITIVE_NEGATIVE_MARKER,
            "value": "negative",
            "label": "infinitive negative marker",
        }
    return {
        "surface": "",
        "value": "positive",
        "label": "No negative marker in the supported infinitive pattern.",
    }


def _reflexive_slot() -> dict[str, object]:
    """Reflexive zvi slot, represented distinctly from object agreement.

    Fortune 3.3.18(a) lists object and reflexive prefixes together but glosses
    them apart (kuzvitora "to take them" versus kuzviziva "to know oneself"),
    so a reflexive reading is never folded into an object-concord slot.
    """
    return {
        "surface": INFINITIVE_REFLEXIVE_SURFACE,
        "value": True,
        "label": "reflexive prefix",
    }


def _build_infinitive_analysis(
    *,
    normalized: str,
    polarity: str,
    object_candidate: dict[str, object] | None,
    reflexive: bool,
    verb_stem: str,
    lemma,
    extensions: list[dict[str, object]],
) -> dict[str, object]:
    confidence = INFINITIVE_ANALYZER_CONFIDENCE
    if object_candidate is not None:
        confidence = min(confidence, object_candidate["confidence"])
    return {
        "analysis_type": "infinitive",
        "confidence": confidence,
        "rule_id": INFINITIVE_RULE_ID,
        "lemma": _lemma_payload(lemma),
        "source": {
            "rule_card_id": INFINITIVE_RULE_ID,
            "source_key": "source_fortune",
            "source_locator": INFINITIVE_SOURCE_LOCATOR,
        },
        "slots": {
            "infinitive_prefix": {
                "surface": INFINITIVE_PREFIX,
                "type": "class_15_infinitive_prefix",
                "label": "class 15 infinitive prefix",
            },
            "subject": None,
            "tense_aspect": None,
            "polarity": _infinitive_polarity_slot(polarity),
            "object": _subject_slot(object_candidate) if object_candidate is not None else None,
            "reflexive": _reflexive_slot() if reflexive else None,
            "verb_stem": {
                "surface": verb_stem,
                "lemma_public_id": lemma.public_id,
            },
            "extensions": extensions,
            "final_vowel": {
                "surface": verb_stem[-1],
                "value": verb_stem[-1],
            },
        },
        "phonology": compute_phonology_fields(normalized),
        "limitations": [
            "v1 analyzes only single-token ku- infinitives, optionally negative and with at most one object concord or the reflexive prefix.",
            "Progressive/exclusive formatives, complements, nominal plurals, and tone are not analyzed.",
            "Divergent stems without terminal -a resolve only as their own reviewed lemmas.",
        ],
    }


def _infinitive_negative_stem_options(
    stem: str, object_candidate: dict[str, object] | None
) -> list[tuple[str, str]]:
    """Stem readings inside a ku-sa- infinitive.

    Unlike finite negatives there is no -e/-a mutation (kusaziva keeps the
    terminal -a). Readings are full-prefix strips only; a-vowel contacts
    that lack applicable evidence are excluded later by
    _infinitive_boundary_deferred, not here. Every option still needs a
    lexical hit.
    """
    if object_candidate is None:
        readings = [stem]
    else:
        inner = stem.removeprefix(object_candidate["surface"])
        readings = [inner] if inner else []
    return [(surface, surface) for surface in readings if surface]


def _infinitive_positive_stem_options(
    inner: str, object_candidate: dict[str, object]
) -> list[tuple[str, str]]:
    """Full-prefix strip for positive infinitive object readings.

    Only the exact remainder can resolve lexically; a-vowel contacts that
    lack applicable evidence are excluded later by
    _infinitive_boundary_deferred, not here.
    """
    rest = inner.removeprefix(object_candidate["surface"])
    return [(rest, rest)] if rest else []


def _analyze_ku_infinitive(
    normalized: str, deferred: list[str] | None = None
) -> list[dict[str, object]]:
    """Bounded ku- infinitive readings: polarity x object/reflexive x stems.

    Every reading is lexically gated: the remaining stem must resolve to a
    reviewed verb stem (exactly, or through an evidence-backed derivation),
    so a lexical stem that merely begins with sa- or zvi- never invents a
    negative/object/reflexive construction, and no reading invents a stem.
    """
    if not normalized.startswith(INFINITIVE_PREFIX) or len(normalized) <= 2:
        return []
    rest = normalized.removeprefix(INFINITIVE_PREFIX)
    if not rest:
        return []
    polarity_inners = [("positive", rest)]
    if rest.startswith(INFINITIVE_NEGATIVE_MARKER):
        inner = rest.removeprefix(INFINITIVE_NEGATIVE_MARKER)
        if inner:
            polarity_inners.append(("negative", inner))

    analyses: list[dict[str, object]] = []
    seen: set[tuple[object, ...]] = set()

    def add(
        polarity: str,
        stem_surface: str,
        lookup_stem: str,
        object_candidate: dict[str, object] | None,
        reflexive: bool,
    ) -> bool:
        """Append readings for one segmentation; True when the budget is spent."""
        if not lookup_stem:
            return False
        stem_candidates = _get_stem_candidates(lookup_stem)
        if not stem_candidates:
            return False
        boundary = _infinitive_boundary_deferred(
            polarity=polarity,
            object_surface=object_candidate["surface"] if object_candidate is not None else None,
            reflexive=reflexive,
            stem_surface=stem_surface,
        )
        if boundary is not None:
            if deferred is not None and boundary not in deferred:
                deferred.append(boundary)
            return False
        for lemma, extensions in stem_candidates:
            key = (
                lemma.public_id,
                stem_surface,
                tuple(
                    (item["type"], item.get("style"), item["surface"])
                    for item in extensions
                ),
                polarity,
                _object_features_key(object_candidate),
                reflexive,
            )
            if key in seen:
                continue
            seen.add(key)
            analyses.append(
                _build_infinitive_analysis(
                    normalized=normalized,
                    polarity=polarity,
                    object_candidate=object_candidate,
                    reflexive=reflexive,
                    verb_stem=stem_surface,
                    lemma=lemma,
                    extensions=extensions,
                )
            )
            if len(analyses) >= _MAX_INFINITIVE_ANALYSES:
                return True
        return False

    for polarity, inner in polarity_inners:
        if polarity == "positive":
            plain_options = [(inner, inner)]
        else:
            plain_options = _infinitive_negative_stem_options(inner, None)
        for stem_surface, lookup_stem in plain_options:
            if add(polarity, stem_surface, lookup_stem, None, False):
                return analyses
        if inner.startswith(INFINITIVE_REFLEXIVE_SURFACE):
            reflexive_stem = inner.removeprefix(INFINITIVE_REFLEXIVE_SURFACE)
            if reflexive_stem and add(polarity, reflexive_stem, reflexive_stem, None, True):
                return analyses
        for object_candidate in _candidate_object_concords():
            oc_surface = object_candidate["surface"]
            if not inner.startswith(oc_surface):
                continue
            if polarity == "positive":
                options = _infinitive_positive_stem_options(inner, object_candidate)
            else:
                options = _infinitive_negative_stem_options(inner, object_candidate)
            for stem_surface, lookup_stem in options:
                if add(polarity, stem_surface, lookup_stem, object_candidate, False):
                    return analyses
    return analyses


def _unsupported_future_lanes(
    normalized: str,
    deferred_boundaries: list[str] | tuple[str, ...] = (),
    finite_deferred_boundaries: list[str] | tuple[str, ...] = (),
    pro_verb_exclusions: list[str] | tuple[str, ...] = (),
) -> list[dict[str, object]]:
    lanes = []
    if pro_verb_exclusions:
        lanes.append(
            {
                "code": "excluded_defective_pro_verb_stem",
                "message": (
                    "This surface matches a negated -no- present reading "
                    "derived through the ordinary terminal-vowel rule from the "
                    f"defective pro-verb stem {sorted(set(pro_verb_exclusions))[0]} "
                    "(its own -ne/-na paradigm; FSI Unit 12: pro-verb stems "
                    "keep their final vowels). That reading is not inferred "
                    "and is not claimed to be ungrammatical; the surface "
                    "still resolves through an independently reviewed "
                    "lexical stem."
                ),
                "support_status": "not_supported",
                "excluded_stem_headwords": sorted(set(pro_verb_exclusions)),
                "rule_card_ids": [SUPPORTED_RULE_ID],
            }
        )
    for boundary in deferred_boundaries:
        lanes.append(
            {
                "code": "deferred_infinitive_boundary",
                "message": (
                    "This surface matches a ku- infinitive construction across "
                    "a vowel boundary deferred pending linguistic evidence "
                    f"({boundary}); it is not claimed to be ungrammatical, "
                    "and no reading is inferred for it."
                ),
                "support_status": "deferred_pending_evidence",
                "boundary": boundary,
                "rule_card_ids": [INFINITIVE_RULE_ID],
            }
        )
    for boundary in finite_deferred_boundaries:
        lanes.append(
            {
                "code": "deferred_finite_boundary",
                "message": (
                    "This surface matches a finite present construction across "
                    "a vowel boundary deferred pending linguistic evidence "
                    f"({boundary}); it is not claimed to be ungrammatical, "
                    "and no reading is inferred for it."
                ),
                "support_status": "deferred_pending_evidence",
                "boundary": boundary,
                "rule_card_ids": [SUPPORTED_RULE_ID],
            }
        )
    if (
        not deferred_boundaries
        and not finite_deferred_boundaries
        and normalized.startswith("ku")
        and len(normalized) > 2
    ):
        lanes.append(
            {
                "code": "ku_infinitive_unmatched_stem",
                "message": (
                    "This looks like a ku- infinitive candidate, but no reviewed "
                    "verb stem matched the remaining surface."
                ),
                "support_status": "not_supported",
                "rule_card_ids": [INFINITIVE_RULE_ID],
            }
        )
    if _has_unverified_derivation_candidate(normalized):
        lanes.append(
            {
                "code": "unverified_extension_derivation",
                "message": (
                    "The surface decomposes through an extension allomorph whose "
                    "per-lemma distribution is not source-verified (causative "
                    "-idz-/-edz-, -its-/-ets-, or short reversive -ur-/-or-; see the "
                    "retained rule card). A reviewed base lemma is not evidence for "
                    "that derivation, so it is excluded from analyses; the surface "
                    "resolves only when the full form is published as its own "
                    "reviewed verb-stem lemma."
                ),
                "support_status": "not_supported",
                "rule_card_ids": [RETAINED_EXTENSIONS_RULE_ID],
            }
        )
    if _looks_passive_or_extension_like(normalized):
        lanes.append(
            {
                "code": "passive_or_extension_like",
                "message": (
                    "This surface contains extension-like material but no supported "
                    "v1 construction matched it. Check vowel harmony and the lexical "
                    "stem; the supported extension boundary is documented in the "
                    "verbal extension rule cards."
                ),
                "support_status": "not_supported",
                "rule_card_ids": [
                    EXTENSIONS_RULE_ID,
                    REVERSIVE_RULE_ID,
                    REPETITIVE_RULE_ID,
                    RETAINED_EXTENSIONS_RULE_ID,
                ],
            }
        )
    return lanes


def _has_unverified_derivation_candidate(normalized: str) -> bool:
    return any(
        _derivation_is_evidence_gated(extensions)
        for _, extensions in _candidate_decompositions(normalized)
    )


def _looks_passive_or_extension_like(normalized: str) -> bool:
    if len(normalized) < 5:
        return False
    return any(
        normalized.endswith(suffix)
        for suffix in EXTENSION_LIKE_SUFFIXES
    )


def _last_vowel(text: str) -> str | None:
    for char in reversed(text):
        if char in "aeiou":
            return char
    return None


_REVERSIVE_LONG_SURFACES = {
    "a": "anur",
    "e": "enur",
    "i": "inur",
    "o": "onor",
    "u": "unur",
}


def _extension_label(*, ext_type: str, style: str | None, surface: str) -> str:
    if ext_type == "passive":
        if surface == "w":
            return "passive extension (-w-)"
        return f"passive extension (-{surface}-)"
    labels = {
        ("causative", None): "causative extension (-is- / -es-)",
        ("causative", "dz"): "causative extension (-idz- / -edz-)",
        ("causative", "ts"): "causative extension (-its- / -ets-)",
        ("applicative", None): "applicative extension (-ir- / -er-)",
        ("neuter", None): "neuter extension (-ik- / -ek-)",
        ("reciprocal", None): "reciprocal extension (-an-)",
        ("reversive", "long"): (
            "reversive extension (-anur- / -enur- / -inur- / -onor- / -unur-)"
        ),
        ("reversive", "short"): "reversive extension (-ur- / -or-)",
        ("repetitive", None): "repetitive extension (-urur- / -oror-)",
    }
    return labels[(ext_type, style)]


def _extension_surface_valid(
    *, ext_type: str, style: str | None, surface: str, trigger: str | None
) -> bool:
    """Shared analyzer/generator allomorph gate.

    `trigger` is the final vowel of the radical being extended, or None for
    vowelless (C) radicals, which take the high-vowel allomorphs.
    """
    mid = trigger in _MID_VOWELS
    if ext_type == "passive":
        if surface == "w":
            return True
        return (surface == "ew") == mid
    if ext_type == "causative":
        if style == "dz":
            return (surface == "edz") == mid
        if style == "ts":
            return (surface == "ets") == mid
        return (surface == "es") == mid
    if ext_type == "applicative":
        return (surface == "er") == mid
    if ext_type == "neuter":
        return (surface == "ek") == mid
    if ext_type == "reciprocal":
        return surface == "an"
    if ext_type == "repetitive":
        if trigger is None:
            return surface == "urur"
        return surface == ("oror" if trigger == "o" else "urur")
    if ext_type == "reversive":
        if style == "short":
            if trigger is None:
                return False
            return surface == ("or" if trigger == "o" else "ur")
        return surface == _REVERSIVE_LONG_SURFACES.get(trigger)
    return False


def _extension_item(*, ext_type: str, style: str | None, surface: str) -> dict[str, object]:
    item: dict[str, object] = {
        "surface": surface,
        "type": ext_type,
        "label": _extension_label(ext_type=ext_type, style=style, surface=surface),
    }
    if style is not None:
        item["style"] = style
    return item


def _extension_types_violation(types: list[str] | tuple[str, ...]) -> str | None:
    """Shared extension-sequence policy (Finding 3).

    Returns the violation kind ("count", "repeat", or "order") for a sequence
    of extension types in application (innermost-first) order, or None when the
    sequence satisfies the documented product convention. Both the generator's
    request validation and the analyzer's decompositions enforce exactly this
    one policy. The convention is a conservative product limit (deterministic
    output, bounded work, matching round-trips); Fortune 2.10.2.3.3 states the
    constructional pattern "R + extension(s)" without an ordering rule, so no
    violation here is claimed to be ungrammatical.
    """
    if len(types) > _MAX_EXTENSIONS_PER_REQUEST:
        return "count"
    seen: set[str] = set()
    order: list[int] = []
    for ext_type in types:
        if ext_type in seen:
            return "repeat"
        seen.add(ext_type)
        order.append(_SUPPORTED_EXTENSION_TYPES.index(ext_type))
    if order != sorted(order):
        return "order"
    return None



def _candidate_decompositions(surface_stem: str) -> list[tuple[str, list[dict[str, object]]]]:
    """Bounded segmentation of an extension-bearing stem.

    Explores every suffix path in _EXTENSION_SURFACES (up to
    _MAX_EXTENSION_DEPTH extensions) and returns (canonical_stem, extensions)
    pairs whose leftover base still needs a lexical check by the caller.
    Lexical stems at intermediate boundaries are preserved as candidates
    instead of being stripped past, and results are ordered deterministically
    by extension count then surface so the caller can bound them.
    """
    if surface_stem.endswith(("a", "e")):
        start_base = surface_stem[:-1]
    else:
        return []

    found: list[tuple[str, list[dict[str, object]]]] = []
    seen: set[tuple[str, tuple[tuple[str, str, str | None], ...]]] = set()
    stack: list[tuple[str, list[tuple[str, str, str | None]]]] = [(start_base, [])]
    while stack:
        remaining, stripped = stack.pop()
        for surface, ext_type, style in _EXTENSION_SURFACES:
            if not remaining.endswith(surface):
                continue
            inner = remaining[: -len(surface)]
            if not inner:
                continue
            trigger = _last_vowel(inner)
            if not _extension_surface_valid(
                ext_type=ext_type, style=style, surface=surface, trigger=trigger
            ):
                continue
            # Stripping runs outermost-first, so prepend to keep application
            # (innermost-first) order in the reported sequence.
            sequence = [(surface, ext_type, style)] + stripped
            # Shared Finding 3 policy: violations are monotone under
            # prepending, so prune the branch as soon as it appears.
            if _extension_types_violation([ext for _, ext, _ in sequence]):
                continue

            state = (inner, tuple(sequence))
            if state in seen:
                continue
            seen.add(state)
            canonical = inner + "a"
            found.append((
                canonical,
                [
                    _extension_item(ext_type=item_type, style=item_style, surface=item_surface)
                    for item_surface, item_type, item_style in sequence
                ],
            ))
            if len(sequence) < _MAX_EXTENSION_DEPTH:
                stack.append((inner, sequence))

    deduped: dict[tuple[str, tuple[str, ...]], list[dict[str, object]]] = {}
    for canonical, extensions in found:
        key = (canonical, tuple(extension["surface"] for extension in extensions))
        deduped.setdefault(key, extensions)
    ordered = [(canonical, extensions) for (canonical, _), extensions in deduped.items()]
    ordered.sort(key=lambda candidate: (len(candidate[1]), [item["surface"] for item in candidate[1]]))
    return ordered


def _get_reviewed_verb_stems(normalized_stem: str) -> list:
    return list(
        Lemma.objects.filter(
            review_state__in=SUPPORTED_REVIEW_STATES,
            headword_kind=Lemma.HeadwordKind.VERB_STEM,
            normalized_headword=normalized_stem,
        ).order_by("normalized_headword", "public_id")
    )


def _get_stem_candidates(stem_candidate: str) -> list[tuple[object, list[dict[str, object]]]]:
    """Lexicon-aware stem resolution.

    Exact reviewed lemmas always resolve first (one entry per homograph
    lemma, in public_id order), with no extensions claim. Derivational
    readings follow only when every extension in the reading is
    evidence-backed: a reviewed base lemma is not evidence for an arbitrary
    derivation, so readings passing through a gated allomorph (causative
    -idz-/-edz-, -its-/-ets-, short reversive -ur-/-or-) are excluded instead
    of being presented as supported analyses (supervisor blocker, 2026-09-09).
    An attested derived form resolves as its own reviewed verb-stem lemma via
    the exact path. Extension-looking endings on a lexical root (e.g. -ambura
    ending in -ur-) therefore keep the exact reading instead of being stripped
    past it. Capped at _MAX_STEM_CANDIDATES entries.
    """
    candidates: list[tuple[object, list[dict[str, object]]]] = []
    for lemma in _get_reviewed_verb_stems(stem_candidate):
        candidates.append((lemma, []))
    for canonical, extensions in _candidate_decompositions(stem_candidate):
        if canonical == stem_candidate:
            continue
        if _derivation_is_evidence_gated(extensions):
            continue
        for lemma in _get_reviewed_verb_stems(canonical):
            candidates.append((lemma, [dict(item) for item in extensions]))
        if len(candidates) >= _MAX_STEM_CANDIDATES:
            break
    return candidates[:_MAX_STEM_CANDIDATES]


def _rule_ids_for_extensions(applied_extensions: list[dict[str, object]]) -> list[str]:
    rule_ids: list[str] = []
    for item in applied_extensions:
        ext_type = item.get("type")
        style = item.get("style")
        if ext_type == "reversive":
            ids = (REVERSIVE_RULE_ID,)
        elif ext_type == "repetitive":
            ids = (REPETITIVE_RULE_ID,)
        elif ext_type == "reciprocal":
            ids = (RECIPROCAL_RULE_ID,)
        else:
            ids = (EXTENSIONS_RULE_ID,)
        for rule_id in ids:
            if rule_id not in rule_ids:
                rule_ids.append(rule_id)
    return rule_ids


def _extension_is_evidence_gated(ext_type: str, style: str | None) -> bool:
    """True when this extension lacks source-backed evidence.

    The single Finding 4 predicate, shared by generation
    (_normalize_generation_extensions, _apply_extensions) and analysis
    (_derivation_is_evidence_gated) so the two sides cannot drift: neither side
    may synthesize or present an allomorph the available sources do not justify
    generalizing to an arbitrary lemma.
    """
    if style in _UNVERIFIED_GENERATION_STYLES:
        return True
    return (ext_type, style) in _UNVERIFIED_GENERATION_TYPE_STYLES


def _derivation_is_evidence_gated(extensions: list[dict[str, object]]) -> bool:
    """True when an inferred derivational reading asserts a gated allomorph.

    Applied to analyzer-side candidates: a reviewed base lemma is not evidence
    for a restricted derivation, so such readings are excluded from analyses
    unless the full surface is itself a reviewed lemma (exact path, which
    carries no derivation claim). Uses the same gate as generation.
    """
    return any(
        _extension_is_evidence_gated(item.get("type"), item.get("style"))
        for item in extensions
    )


def _apply_extensions(canonical_stem: str, extensions: list[dict[str, object]]) -> tuple[str, list[dict[str, object]]]:
    if canonical_stem.endswith("a"):
        base = canonical_stem[:-1]
    else:
        base = canonical_stem

    applied = []


    for ext in extensions:
        ext_type = ext.get("type")
        style = ext.get("style")
        if _extension_is_evidence_gated(ext_type, style):
            raise _unverified_generation(ext=ext, ext_type=ext_type, style=style)
        trigger = _last_vowel(base)
        mid = trigger in _MID_VOWELS

        if ext_type == "causative":
            if style == "dz":
                suffix = "edz" if mid else "idz"
            elif style == "ts":
                suffix = "ets" if mid else "its"
            else:
                suffix = "es" if mid else "is"
            item_style = style
        elif ext_type == "applicative":
            suffix = "er" if mid else "ir"
            item_style = None
        elif ext_type == "passive":
            if trigger is None or len(base) <= 2:
                suffix = "ew" if mid else "iw"
            else:
                suffix = "w"
            item_style = None
        elif ext_type == "neuter":
            suffix = "ek" if mid else "ik"
            item_style = None
        elif ext_type == "reciprocal":
            suffix = "an"
            item_style = None
        elif ext_type == "repetitive":
            suffix = "oror" if trigger == "o" else "urur"
            item_style = None
        elif ext_type == "reversive" and (style is None or style == "long"):
            if trigger is None:
                raise _unsupported_generation(
                    field="extensions",
                    received=ext,
                    supported=["reversive on a vowel-final radical (vowel copy)"],
                )
            suffix = _REVERSIVE_LONG_SURFACES[trigger]
            item_style = "long"
        elif ext_type == "reversive":
            if trigger is None:
                raise _unsupported_generation(
                    field="extensions",
                    received=ext,
                    supported=["reversive on a vowel-final radical"],
                )
            suffix = "or" if trigger == "o" else "ur"
            item_style = "short"
        else:  # Unvalidated input must never reach here; validation gates it.
            raise _unsupported_generation(
                field="extensions",
                received=ext,
                supported=list(_SUPPORTED_EXTENSION_TYPES),
            )
        base += suffix
        applied.append(_extension_item(ext_type=ext_type, style=item_style, surface=suffix))

    return base, applied


def _build_positive_analysis(
    *,
    normalized: str,
    subject_candidate: dict[str, object],
    object_candidate: dict[str, object] | None,
    stem_surface: str,
    lemma,
    extensions: list[dict[str, object]],
) -> dict[str, object]:
    has_object = object_candidate is not None
    if has_object:
        rule_id = "fortune.concord.object.001"
        confidence = min(subject_candidate["confidence"], object_candidate["confidence"])
        limitations = [
            "v1 supports only single-token positive present verb forms.",
            "Negative forms and tone are not analyzed.",
        ]
    else:
        rule_id = SUPPORTED_RULE_ID
        confidence = subject_candidate["confidence"]
        limitations = [
            "v1 supports only single-token positive present verb forms.",
            "Object markers, negative forms, and tone are not analyzed.",
        ]
    return {
        "analysis_type": "verb_form",
        "confidence": confidence,
        "rule_id": rule_id,
        "lemma": _lemma_payload(lemma),
        "slots": {
            "subject": _subject_slot(subject_candidate),
            "tense_aspect": {
                "surface": SUPPORTED_TENSE_ASPECT_MARKER,
                "value": "present",
                "label": "positive present marker",
            },
            "polarity": {
                "surface": "",
                "value": "positive",
                "label": "No negative marker detected in supported v1 pattern.",
            },
            "object": _subject_slot(object_candidate) if has_object else None,
            "verb_stem": {
                "surface": stem_surface,
                "lemma_public_id": lemma.public_id,
            },
            "extensions": extensions,
            "final_vowel": {
                "surface": stem_surface[-1],
                "value": stem_surface[-1],
            },
        },
        "phonology": compute_phonology_fields(normalized),
        "limitations": limitations,
    }


def _object_features_key(object_candidate: dict[str, object] | None) -> tuple[object, ...]:
    """Deduplication key for an object reading's features (Finding 2).

    Distinct object concords sharing a surface (e.g. person 3rd-singular "mu"
    versus a class concord "mu") are distinct readings and must not merge;
    truly identical feature readings deduplicate.
    """
    if object_candidate is None:
        return (None,)
    return (
        object_candidate["surface"],
        object_candidate["slot_type"],
        object_candidate.get("person"),
        object_candidate.get("number"),
        object_candidate.get("class_number"),
    )


def _analyze_segmentations(
    *,
    normalized: str,
    subject_candidate: dict[str, object],
    verb_stem: str,
    stem_options_for,
    build_analysis,
    boundary_evaluator=None,
    deferred: list[str] | None = None,
    exclude_pro_verb_stems: bool = False,
    pro_verb_exclusions: list[str] | None = None,
) -> list[dict[str, object]]:
    analyses: list[dict[str, object]] = []
    seen: set[tuple[object, ...]] = set()

    def add(
        stem_surface: str,
        lookup_stem: str,
        object_candidate: dict[str, object] | None,
    ) -> None:
        if boundary_evaluator is not None:
            boundary = boundary_evaluator(stem_surface, object_candidate)
            if boundary is not None:
                # The deferred construction is recorded only when this reading
                # actually resolves to reviewed lexical material, matching the
                # infinitive lane: analysis excludes only the unsupported
                # inferred construction, never the surface.
                if _get_stem_candidates(lookup_stem):
                    if deferred is not None and boundary not in deferred:
                        deferred.append(boundary)
                return
        candidates = _get_stem_candidates(lookup_stem)
        if exclude_pro_verb_stems:
            # The negated -no- present terminal rule must not derive a
            # reading from a defective pro-verb stem: generation refuses it,
            # so analysis infers no such reading either. A negative reading
            # can only reach one of these lemmas through the mutated-lookup
            # or decomposition paths (the exact path requires the reading
            # itself, which never carries the citation terminal), so every
            # such candidate here is an ordinary-rule derivation. Independent
            # lemmas resolving on the same surface are untouched.
            kept: list[tuple[object, list[dict[str, object]]]] = []
            for lemma, extensions in candidates:
                if lemma.normalized_headword in _PRO_VERB_STEMS:
                    if (
                        pro_verb_exclusions is not None
                        and lemma.headword not in pro_verb_exclusions
                    ):
                        pro_verb_exclusions.append(lemma.headword)
                    continue
                kept.append((lemma, extensions))
            candidates = kept
        for lemma, extensions in candidates:
            features_key = (
                lemma.public_id,
                stem_surface,
                tuple(
                    (item["type"], item.get("style"), item["surface"])
                    for item in extensions
                ),
                _object_features_key(object_candidate),
            )
            if features_key in seen:
                continue
            seen.add(features_key)
            analyses.append(
                build_analysis(
                    normalized=normalized,
                    subject_candidate=subject_candidate,
                    object_candidate=object_candidate,
                    stem_surface=stem_surface,
                    lemma=lemma,
                    extensions=extensions,
                )
            )

    # No-object interpretation first: highest confidence (no object concord
    # multiplying the reading) and the originating lemma usually lives here.
    for stem_surface, lookup_stem in stem_options_for(verb_stem, None):
        add(stem_surface, lookup_stem, None)
        if len(analyses) >= _MAX_ANALYSES_PER_SUBJECT:
            return analyses

    for oc_candidate in _candidate_object_concords():
        oc_surface = oc_candidate["surface"]
        if not verb_stem.startswith(oc_surface):
            continue
        for stem_surface, lookup_stem in stem_options_for(verb_stem, oc_candidate):
            add(stem_surface, lookup_stem, oc_candidate)
            if len(analyses) >= _MAX_ANALYSES_PER_SUBJECT:
                return analyses
    return analyses


def _analyze_present_positive(
    normalized: str, subject_candidate: dict[str, object], deferred: list[str] | None = None
) -> list[dict[str, object]]:
    subject_surface = subject_candidate["surface"]
    prefix = f"{subject_surface}{SUPPORTED_TENSE_ASPECT_MARKER}"
    if not normalized.startswith(prefix):
        return []

    verb_stem = normalized.removeprefix(prefix)
    if not verb_stem:
        return []

    def stem_options(
        stem: str, object_candidate: dict[str, object] | None
    ) -> list[tuple[str, str]]:
        """Segmentation readings for the positive present stem slot.

        Plain strip reading first; when the object concord ends in "a" the
        contraction-recovery expansion ("a" + rest) is also emitted so the
        shared boundary evaluator can record the unattested coalesced contact
        when it resolves (morphology-rules-v5), instead of analyzing it.
        """
        if object_candidate is None:
            return [(stem, stem)]
        oc_surface = object_candidate["surface"]
        rest = stem.removeprefix(oc_surface)
        options = []
        if rest:
            options.append((rest, rest))
        if oc_surface.endswith("a"):
            options.append(("a" + rest, "a" + rest))
        return options

    return _analyze_segmentations(
        normalized=normalized,
        subject_candidate=subject_candidate,
        verb_stem=verb_stem,
        stem_options_for=stem_options,
        build_analysis=_build_positive_analysis,
        boundary_evaluator=lambda stem_surface, object_candidate: (
            _finite_boundary_deferred(
                polarity="positive",
                object_surface=(
                    object_candidate["surface"] if object_candidate is not None else None
                ),
                stem_surface=stem_surface,
            )
        ),
        deferred=deferred,
    )


def _build_negative_analysis(
    *,
    normalized: str,
    subject_candidate: dict[str, object],
    object_candidate: dict[str, object] | None,
    stem_surface: str,
    lemma,
    extensions: list[dict[str, object]],
) -> dict[str, object]:
    has_object = object_candidate is not None
    if has_object:
        rule_id = "fortune.concord.object.001"
        confidence = min(subject_candidate["confidence"], object_candidate["confidence"])
        limitations = [
            "v1 supports only single-token negative present verb forms.",
            "Tone is not analyzed.",
        ]
    else:
        rule_id = "fortune.verbal.negation.001"
        confidence = subject_candidate["confidence"]
        limitations = [
            "v1 supports only single-token negative present verb forms.",
            "Object markers, positive forms, and tone are not analyzed.",
        ]
    return {
        "analysis_type": "verb_form",
        "confidence": confidence,
        "rule_id": rule_id,
        "lemma": _lemma_payload(lemma),
        "slots": {
            "subject": _subject_slot(subject_candidate),
            "tense_aspect": None,
            "polarity": {
                "surface": "ha",
                "value": "negative",
                "label": "present negative marker",
            },
            "object": _subject_slot(object_candidate) if has_object else None,
            "verb_stem": {
                "surface": stem_surface,
                "lemma_public_id": lemma.public_id,
            },
            "extensions": extensions,
            "final_vowel": {
                "surface": stem_surface[-1],
                "value": stem_surface[-1],
            },
        },
        "phonology": compute_phonology_fields(normalized),
        "limitations": limitations,
    }


def _analyze_present_negative(
    normalized: str,
    subject_candidate: dict[str, object],
    deferred: list[str] | None = None,
    pro_verb_exclusions: list[str] | None = None,
) -> list[dict[str, object]]:
    if not normalized.startswith("ha"):
        return []
    rest = normalized.removeprefix("ha")
    sc_surface = subject_candidate["surface"]
    if not rest.startswith(sc_surface):
        return []

    verb_stem = rest.removeprefix(sc_surface)
    if not verb_stem:
        return []

    def stem_options(
        stem: str, object_candidate: dict[str, object] | None
    ) -> list[tuple[str, str]]:
        """Negative readings: terminal -i (generated) or -e (Zezuru variant).

        Plain readings come first; contraction-recovery expansions ("a" + stem
        slot) are emitted only so the shared boundary evaluator can record the
        unattested coalesced contact when such a reading would have resolved
        (morphology-rules-v5), instead of analyzing it. Adjacent `a` vowels are
        retained at the attested negative-prefix and subject|object contacts.

        Only readings whose terminal is -i or -e are viable negative spellings
        (FSI Unit 12 note: "-i in some dialects, -e in others"). Each yields
        two lookups: the terminal restored to -a (the lexical stem, e.g.
        zivi/zive -> ziva) and the surface itself (divergent stems such as
        -ti/-nzi whose citation form already carries the non-a terminal).
        """
        if object_candidate is None:
            readings = [stem]
            if sc_surface.endswith("a"):
                readings.append("a" + stem)
        else:
            inner = stem.removeprefix(object_candidate["surface"])
            readings = []
            if inner:
                readings.append(inner)
            if object_candidate["surface"].endswith("a"):
                readings.append("a" + inner)
        options: list[tuple[str, str]] = []
        for surface in readings:
            if not surface.endswith(("i", "e")):
                continue
            options.append((surface, surface[:-1] + "a"))
            options.append((surface, surface))
        return options

    return _analyze_segmentations(
        normalized=normalized,
        subject_candidate=subject_candidate,
        verb_stem=verb_stem,
        stem_options_for=stem_options,
        build_analysis=_build_negative_analysis,
        boundary_evaluator=lambda stem_surface, object_candidate: (
            _finite_boundary_deferred(
                polarity="negative",
                subject_surface=sc_surface if object_candidate is None else None,
                object_surface=(
                    object_candidate["surface"] if object_candidate is not None else None
                ),
                stem_surface=stem_surface,
            )
        ),
        deferred=deferred,
        exclude_pro_verb_stems=True,
        pro_verb_exclusions=pro_verb_exclusions,
    )


def _get_generation_verb_stem(lemma_public_id: str) -> Lemma:
    if not lemma_public_id:
        raise GenerationFailure(
            code="GENERATION_LEMMA_REQUIRED",
            message="Generation requires a non-empty 'lemma_public_id' string.",
            detail={"field": "lemma_public_id", "expected_type": "string"},
        )
    lemma = (
        Lemma.objects.filter(
            public_id=lemma_public_id,
            review_state__in=SUPPORTED_REVIEW_STATES,
            headword_kind=Lemma.HeadwordKind.VERB_STEM,
        )
        .order_by("public_id")
        .first()
    )
    if lemma is None:
        raise GenerationFailure(
            code="GENERATION_UNSUPPORTED",
            message=(
                "No supported v1 generation rule matched the lemma. Supported v1 "
                "generation requires a reviewed verb-stem lemma."
            ),
            detail={
                "field": "lemma_public_id",
                "received": lemma_public_id,
                "supported_lemma_kind": Lemma.HeadwordKind.VERB_STEM,
                "supported_review_states": list(SUPPORTED_REVIEW_STATES),
                "supported_shape": "subject_concord + no + verb_stem",
                "supported_rule_ids": [SUPPORTED_RULE_ID],
            },
        )
    if not lemma.normalized_headword:
        raise GenerationFailure(
            code="GENERATION_UNSUPPORTED",
            message="The lemma cannot be generated because it has no normalized stem.",
            detail={
                "field": "lemma_public_id",
                "received": lemma_public_id,
                "supported_shape": "subject_concord + no + verb_stem",
                "supported_rule_ids": [SUPPORTED_RULE_ID],
            },
        )
    return lemma


def _normalize_generation_extensions(extensions_feature: object) -> list[dict[str, object]]:
    """Strict gate for generation extension requests.

    Returns normalized [{"type": ..., "style"?}] entries or raises a structured
    GENERATION_UNSUPPORTED failure. Unknown types, unknown styles, styles on
    style-less types, repeated types, unsupported orders and over-long stacks
    are all rejected here instead of silently falling back to a default.

    Malformed JSON values never escape as errors: `type` must be a string in
    the supported set and `style` must be a string in the type's style set
    (Finding 1). Explicit `style: null` is accepted as "no style", matching an
    omitted style field.
    """
    if not isinstance(extensions_feature, list):
        raise _unsupported_generation(
            field="extensions",
            received=extensions_feature,
            supported=["list of extensions"],
        )
    normalized: list[dict[str, object]] = []
    for ext in extensions_feature:
        if isinstance(ext, str):
            ext_type, style = ext, None
        elif isinstance(ext, dict):
            ext_type, style = ext.get("type"), ext.get("style")
        else:
            raise _unsupported_generation(
                field="extensions",
                received=extensions_feature,
                supported=["list of strings or dicts"],
            )
        # Validate the type as a string before any membership or dict lookup:
        # lists/objects/booleans/numbers/null are client errors, not crashes.
        if not isinstance(ext_type, str) or ext_type not in _SUPPORTED_EXTENSION_TYPES:
            raise _unsupported_generation(
                field="extensions",
                received=ext_type,
                supported=list(_SUPPORTED_EXTENSION_TYPES),
            )
        allowed_styles = _EXTENSION_STYLES[ext_type]
        if style is None:
            normalized_style = None
        elif not isinstance(style, str):
            raise _unsupported_generation(
                field="extensions",
                received=ext,
                supported=[
                    f'{ext_type} with style in {list(allowed_styles) or ["no style"]} or null'
                ],
            )
        elif style not in allowed_styles:
            if ext_type == "reversive" and style in _REVERSIVE_REPETITIVE_STYLE_NAMES:
                raise GenerationFailure(
                    code="GENERATION_UNSUPPORTED",
                    message=(
                        "Unsupported v1 generation feature: extensions. "
                        f"Reversive style {style!r} names -urur-/-oror- surfaces, which are "
                            'the repetitive extension; request {"type": "repetitive"} instead.'
                    ),
                    detail={
                        "field": "extensions",
                        "received": ext,
                        "supported": ["repetitive (no style)", 'reversive with style "long" or "short"'],
                        "supported_shape": "subject_concord + no + [object_concord] + verb_stem / ha + subject_concord + [object_concord] + verb_stem_ending_in_i",
                        "supported_rule_ids": [SUPPORTED_RULE_ID, "fortune.verbal.negation.001", "fortune.concord.object.001"],
                    },
                )
            if ext_type == "reversive" and style in _REVERSIVE_LONG_STYLE_ALIASES:
                raise GenerationFailure(
                    code="GENERATION_UNSUPPORTED",
                    message=(
                        "Unsupported v1 generation feature: extensions. "
                        f"Reversive style {style!r} predates vowel-copy selection; "
                            'request {"type": "reversive", "style": "long"} instead.'
                    ),
                    detail={
                        "field": "extensions",
                        "received": ext,
                        "supported": ['reversive with style "long" or "short"'],
                        "supported_shape": "subject_concord + no + [object_concord] + verb_stem / ha + subject_concord + [object_concord] + verb_stem_ending_in_i",
                        "supported_rule_ids": [SUPPORTED_RULE_ID, "fortune.verbal.negation.001", "fortune.concord.object.001"],
                    },
                )
            raise _unsupported_generation(
                field="extensions",
                received=ext,
                supported=[
                    f'{ext_type} with style in {list(allowed_styles) or ["no style"]}'
                ],
            )
        else:
            normalized_style = style
        if _extension_is_evidence_gated(ext_type, normalized_style):
            raise _unverified_generation(ext=ext, ext_type=ext_type, style=normalized_style)
        if normalized_style is None:
            normalized.append({"type": ext_type})
        else:
            normalized.append({"type": ext_type, "style": normalized_style})
    violation = _extension_types_violation([entry["type"] for entry in normalized])
    if violation == "count":
        raise _unsupported_generation(
            field="extensions",
            received=extensions_feature,
            supported=[f"at most {_MAX_EXTENSIONS_PER_REQUEST} extensions per request"],
        )
    if violation == "repeat":
        raise _unsupported_generation(
            field="extensions",
            received=extensions_feature,
            supported=["each extension type at most once per request"],
        )
    if violation == "order":
        raise _unsupported_generation(
            field="extensions",
            received=extensions_feature,
            supported=[
                "extension order " + " < ".join(_SUPPORTED_EXTENSION_TYPES) + " (passive outermost)"
            ],
        )
    return normalized


_INFINITIVE_SUPPORTED_SHAPE = "ku + [sa] + [object_concord | zvi-reflexive] + verb_stem"
_INFINITIVE_SUPPORTED_RULE_IDS = [
    INFINITIVE_RULE_ID,
    "fortune.verbal.negation.001",
    "fortune.concord.object.001",
]


_INFINITIVE_ALLOWED_FEATURES = frozenset(
    {"generation_type", "polarity", "object", "reflexive", "extensions"}
)

INFINITIVE_DEFERRED_REASON = "deferred_pending_evidence"

#
# Negated -no- present terminal vowel (morphology-rules-v5): the final -a of a
# lexical stem becomes -i in the API's generated dialect. Sources:
# - FSI Unit 12, Note 1 (printed p. 118): the negative of the /-no-/ tense --
#   "The final vowel of the stem is /-i/ in some dialects, /-e/ in others.",
#   and pro-verb stems keep their final vowels; FSI's own forms are /-i/
#   (Handízíví, Handítaúrí, Haváazíví, Handíríveréngí, Havázvígadzírí);
# - FSI Unit 13, Note 1 (printed p. 126): /-sa-/ past negatives keep /-a/,
#   "does not become /-i/" -- scoping the mutation to the /-no-/-tense lane;
# - Hannan, front-matter TABLE OF VERB FORMS, Present Indicative negative
#   (PDF pp. 14-15): "Handidyi St. Sh." (Standard Shona, -i) versus
#   "Handidye Z" (Zezuru, -e), and the -ziva entry "Handimuzivi: I do not
#   know him" (terminal -i with object concord);
# - Fortune, TC VII (printed p. 25) and 2.10.2.4(b): the negative principal
#   present inflection ends /-e/,/-é/ ("ha-ndí-zív-é (I don't know)") --
#   the Zezuru variant, analyzed as a dialect spelling, never generated.
#

#
# Finite vowel-boundary policy (morphology-rules-v5).
#
# Attested retention of adjacent `a` vowels in verb forms, for the boundaries
# the finite shapes can realize:
# - tense sign before object concord: Hannan p. 25 concord list, "-a- ... oc 6:
#   Ndakaaona: I saw them"; FSI Unit 15 drills Ndaagadzira/Vaagadzira/Yaagadzira
#   (PDF p. 169); FSI p. 225 Ndaatora (nda-a-tor-a, class-6 object).
# - tense sign before stem: Hannan p. 26, "-ambura ... Umba yaambura: the house
#   is on fire" (class-9 subject + -a- tense + a-initial radical).
# - negative prefix before subject concord: FSI Unit 15 Haanayo/Haaudi samples;
#   Hannan "Mabhuku haakodzi" (class-6 subject a-).
# - subject concord before a-initial object concord: FSI Unit 15 "Havaazivi:
#   they don't know them" (ha-va-a-zivi).
# - non-identical vowel contacts at object|stem and no|object: FSI Unit 15
#   Ndamuona/Ndavaona (p. 166), Ndinoada/Ndinouda (PDF p. 170), Ndaiona.
# No available source witnesses an a-final subject or object concord
# immediately before an a-initial stem. FSI "Majaha arara" (PDF p. 41) is the
# fused hodiernal subject+tense form (Fortune, Series X subject-prefix
# allomorphs with tense sign /-a-/), not a subject|stem boundary, and Fortune's
# coalescence rule (3.3.9, mano/meno/meso) is explicitly nominal. Those
# contacts are therefore deferred: generation refuses them, analysis infers no
# reading across them, and no contracted or unattested-hiatus spelling is
# invented (same discipline as the infinitive deferrals).
#

FINITE_DEFERRED_REASON = "deferred_pending_evidence"

# The defective pro-verb stem whose negated -no- present is not derivable
# from a terminal rule (affirmative -ne, negative -na; Hannan front matter;
# FSI Unit 12: pro-verb stems keep their final vowels). Generation refuses it
# instead of inventing a form.
_PRO_VERB_STEMS = frozenset({"na"})


def _finite_boundary_deferred(
    *,
    polarity: str,
    subject_surface: str | None = None,
    object_surface: str | None = None,
    stem_surface: str,
) -> str | None:
    """Deferred a-vowel-boundary policy shared by finite generation/analysis.

    Returns a stable boundary code when the evaluated morphemes place an
    a-final subject or object concord immediately before an a-initial stem
    without applicable source evidence, else None. Adjacent identical `a`
    vowels are retained at attested contacts (negative prefix before the
    subject concord, subject concord before an a-initial object concord,
    tense sign before an object concord or stem); only the unattested
    concord|stem contacts are deferred. Arguments are morphemes (the effective
    subject and object surfaces and the stem as built after extensions and the
    negative terminal-vowel mutation), never substrings of the finished word.
    """
    if (
        object_surface is not None
        and object_surface.endswith("a")
        and stem_surface.startswith("a")
    ):
        return "object_before_a_initial_stem"
    if (
        polarity == "negative"
        and object_surface is None
        and subject_surface is not None
        and subject_surface.endswith("a")
        and stem_surface.startswith("a")
    ):
        return "subject_before_a_initial_stem"
    return None


def _deferred_finite_generation(
    *, boundary: str, features: dict[str, object]
) -> GenerationFailure:
    """Structured refusal for a deferred finite vowel boundary."""
    return GenerationFailure(
        code="GENERATION_UNSUPPORTED",
        message=(
            "Unsupported v1 generation feature: finite_boundary. This "
            "morpheme combination crosses a vowel boundary deferred pending "
            "linguistic evidence; it is not claimed to be grammatically "
            "impossible, and no alternative spelling is generated."
        ),
        detail={
            "field": "finite_boundary",
            "boundary": boundary,
            "reason": FINITE_DEFERRED_REASON,
            "received": features,
            "supported": [
                "finite present constructions that avoid an a-final subject or "
                "object concord immediately before an a-initial stem; adjacent "
                "a vowels are kept at attested contacts (ha + subject concord, "
                "subject concord + a-initial object concord) and never merged"
            ],
            "supported_shape": (
                "subject_concord + no + [object_concord] + verb_stem / "
                "ha + subject_concord + [object_concord] + verb_stem_ending_in_i"
            ),
            "supported_rule_ids": [
                SUPPORTED_RULE_ID,
                "fortune.verbal.negation.001",
                "fortune.concord.object.001",
            ],
        },
    )


def _infinitive_boundary_deferred(
    *,
    polarity: str,
    object_surface: str | None,
    reflexive: bool,
    stem_surface: str,
) -> str | None:
    """Deferred vowel-boundary policy for the infinitive lane only.

    Returns a stable boundary code when the morpheme sequence crosses an
    `a`-vowel boundary without applicable source evidence, else None. The
    two deferred boundaries are: negative `sa-` immediately followed by an
    `a`-initial object concord or an `a`-initial stem, and an `a`-final
    object concord immediately followed by an `a`-initial stem. Arguments
    are morphemes (the object surface, the reflexive flag, the stem as
    built after extensions), never substrings of the finished word, so
    supported combinations sharing letters (e.g. `kusaziva` from `sa` +
    `ziva`) are unaffected. Finite verb forms run the parallel
    _finite_boundary_deferred policy (morphology-rules-v5) with its own
    boundary codes and rule card.
    """
    if polarity == "negative":
        if object_surface is not None:
            if object_surface.startswith("a"):
                return "sa_before_a_initial_object"
        elif not reflexive and stem_surface.startswith("a"):
            return "sa_before_a_initial_stem"
    if (
        object_surface is not None
        and object_surface.endswith("a")
        and stem_surface.startswith("a")
    ):
        return "object_before_a_initial_stem"
    return None


def _deferred_infinitive_generation(
    *, boundary: str, features: dict[str, object]
) -> GenerationFailure:
    """Structured refusal for a deferred infinitive vowel boundary."""
    return GenerationFailure(
        code="GENERATION_UNSUPPORTED",
        message=(
            "Unsupported v1 generation feature: infinitive_boundary. This "
            "morpheme combination crosses a vowel boundary deferred pending "
            "linguistic evidence; it is not claimed to be grammatically "
            "impossible, and no alternative spelling is generated."
        ),
        detail={
            "field": "infinitive_boundary",
            "boundary": boundary,
            "reason": INFINITIVE_DEFERRED_REASON,
            "received": features,
            "supported": [
                "infinitive constructions that avoid sa- before an a-initial "
                "object concord or stem, and object concords ending in a "
                "before an a-initial stem"
            ],
            "supported_shape": _INFINITIVE_SUPPORTED_SHAPE,
            "supported_rule_ids": _INFINITIVE_SUPPORTED_RULE_IDS,
        },
    )


def _unsupported_infinitive_generation(*, field: str, received, supported) -> GenerationFailure:
    """GENERATION_UNSUPPORTED with the infinitive shape context.

    The shared extension/object gates report the finite shape; infinitive
    requests re-contextualize those errors instead of echoing a shape the
    caller did not request.
    """
    return GenerationFailure(
        code="GENERATION_UNSUPPORTED",
        message=f"Unsupported v1 generation feature: {field}.",
        detail={
            "field": field,
            "received": received,
            "supported": supported,
            "supported_shape": _INFINITIVE_SUPPORTED_SHAPE,
            "supported_rule_ids": _INFINITIVE_SUPPORTED_RULE_IDS,
        },
    )


def _normalize_infinitive_generation_extensions(extensions_feature: object) -> list[dict[str, object]]:
    """Shared extension gate (Finding 4 intact) with infinitive-shaped errors."""
    try:
        return _normalize_generation_extensions(extensions_feature)
    except GenerationFailure as exc:
        if exc.code != "GENERATION_UNSUPPORTED":
            raise
        raise _unsupported_infinitive_generation(
            field=exc.detail["field"],
            received=exc.detail["received"],
            supported=exc.detail["supported"],
        ) from exc


def _resolve_infinitive_generation_object(obj: dict[str, object] | None) -> dict[str, object] | None:
    """Shared object-concord resolution with infinitive-shaped errors."""
    try:
        return _resolve_generation_object(obj)
    except GenerationFailure as exc:
        if exc.code != "GENERATION_UNSUPPORTED":
            raise
        raise _unsupported_infinitive_generation(
            field=exc.detail["field"],
            received=exc.detail["received"],
            supported=exc.detail["supported"],
        ) from exc


def _validate_infinitive_generation_features(features: dict[str, object]) -> None:
    """Strict gate for the infinitive generation branch.

    An explicit allowlist names the only supported top-level fields
    (generation_type, polarity, object, reflexive, extensions); anything else
    — finite-only subject/tense_aspect, mood, or any other grammatical field —
    is rejected with 422 instead of silently ignored. Reflexivity is an
    explicit boolean (default False); at most one of object/reflexive may
    appear (no source-backed double-object or reflexive-plus-object rule
    exists in the available volume).
    """
    for field_name in features:
        if field_name not in _INFINITIVE_ALLOWED_FEATURES:
            raise _unsupported_infinitive_generation(
                field=field_name,
                received=features.get(field_name),
                supported=sorted(_INFINITIVE_ALLOWED_FEATURES),
            )
    if features.get("polarity", "positive") not in ("positive", "negative"):
        raise _unsupported_infinitive_generation(
            field="polarity",
            received=features.get("polarity"),
            supported=["positive", "negative"],
        )
    if not isinstance(features.get("reflexive", False), bool):
        raise _unsupported_infinitive_generation(
            field="reflexive",
            received=features.get("reflexive"),
            supported=[True, False],
        )
    obj = features.get("object", None)
    if obj is not None and obj != "" and not isinstance(obj, dict):
        raise _unsupported_infinitive_generation(
            field="object",
            received=obj,
            supported=["structured object feature or None"],
        )
    if features.get("reflexive", False) and obj not in (None, ""):
        raise _unsupported_infinitive_generation(
            field="object",
            received=obj,
            supported=["either one object marker or reflexivity, not both"],
        )
    if "extensions" in features:
        _normalize_infinitive_generation_extensions(features.get("extensions"))


def _join_infinitive_surface(parts: list[str]) -> str:
    """Concatenate infinitive morphemes with hiatus retained.

    No vowels are dropped or merged here; deferred a-vowel boundaries never
    reach this join because generation refuses them first (see
    _infinitive_boundary_deferred). Finite present generation joins plainly
    too under morphology-rules-v5: its deferred a-vowel boundaries are refused
    by _finite_boundary_deferred before the form is built.
    """
    return "".join(parts)


def _generate_infinitive(
    *,
    lemma_public_id: str,
    lemma,
    features: dict[str, object],
    rule_set_version: str,
) -> dict[str, object]:
    _validate_infinitive_generation_features(features)
    object_candidate = _resolve_infinitive_generation_object(features.get("object"))
    normalized_exts = _normalize_infinitive_generation_extensions(
        features.get("extensions", [])
    )

    canonical_headword = lemma.normalized_headword
    if not canonical_headword.endswith("a"):
        # Divergent stems (Fortune 3.3.18 footnote: -ti, -nzi and their
        # derived/extended forms take no terminal -a), so the ku + stem
        # concatenation has no source-backed shape; refuse instead of
        # fabricating a surface. Such stems still analyze as their own
        # reviewed lemmas.
        raise GenerationFailure(
            code="GENERATION_UNSUPPORTED",
            message=(
                "Unsupported v1 generation feature: lemma_stem. The lemma stem "
                "does not end in terminal -a, so no supported ku- infinitive "
                "shape applies to it."
            ),
            detail={
                "field": "lemma_stem",
                "received": lemma.headword,
                "reason": "divergent_stem_without_terminal_a",
                "supported": ["reviewed verb-stem lemmas ending in terminal -a"],
                "supported_shape": _INFINITIVE_SUPPORTED_SHAPE,
                "supported_rule_ids": _INFINITIVE_SUPPORTED_RULE_IDS,
            },
        )

    if normalized_exts:
        extended_base, applied_extensions = _apply_extensions(canonical_headword, normalized_exts)
        stem_val = extended_base + "a"
    else:
        stem_val = canonical_headword
        applied_extensions = []

    polarity = features.get("polarity", "positive")
    reflexive = features.get("reflexive", False)
    boundary = _infinitive_boundary_deferred(
        polarity=polarity,
        object_surface=object_candidate["surface"] if object_candidate is not None else None,
        reflexive=reflexive,
        stem_surface=stem_val,
    )
    if boundary is not None:
        raise _deferred_infinitive_generation(boundary=boundary, features=features)
    parts = [INFINITIVE_PREFIX]
    if polarity == "negative":
        parts.append(INFINITIVE_NEGATIVE_MARKER)
    if reflexive:
        parts.append(INFINITIVE_REFLEXIVE_SURFACE)
    elif object_candidate is not None:
        parts.append(object_candidate["surface"])
    parts.append(stem_val)
    form = _join_infinitive_surface(parts)

    if object_candidate is not None:
        confidence = min(INFINITIVE_ANALYZER_CONFIDENCE, object_candidate["confidence"])
    else:
        confidence = INFINITIVE_ANALYZER_CONFIDENCE
    generated = {
        "generation_type": "infinitive",
        "form": form,
        "normalized": normalize_search_query(form),
        "confidence": confidence,
        "rule_id": INFINITIVE_RULE_ID,
        "lemma": _lemma_payload(lemma),
        "slots": {
            "infinitive_prefix": {
                "surface": INFINITIVE_PREFIX,
                "type": "class_15_infinitive_prefix",
                "label": "class 15 infinitive prefix",
            },
            "subject": None,
            "tense_aspect": None,
            "polarity": _infinitive_polarity_slot(polarity),
            "object": _subject_slot(object_candidate) if object_candidate is not None else None,
            "reflexive": _reflexive_slot() if reflexive else None,
            "verb_stem": {
                "surface": stem_val,
                "lemma_public_id": lemma.public_id,
            },
            "extensions": applied_extensions,
            "final_vowel": {
                "surface": stem_val[-1],
                "value": stem_val[-1],
            },
        },
        "phonology": compute_phonology_fields(form),
    }
    warnings = [
        {
            "code": "GENERATION_PARTIAL_RULE_SET",
            "message": "v1 generation supports only single-token ku- infinitive forms.",
        },
        {
            "code": "TONE_NOT_GENERATED",
            "message": "Tone is not generated.",
        },
    ]
    supported_rule_ids = [INFINITIVE_RULE_ID]
    if object_candidate is not None:
        supported_rule_ids.append("fortune.concord.object.001")
    supported_rule_ids.extend(_rule_ids_for_extensions(applied_extensions))
    return {
        "input": {
            "lemma_public_id": lemma_public_id,
            "features": features,
        },
        "generator_version": GENERATOR_VERSION,
        "rule_set_version": rule_set_version,
        "confidence": generated["confidence"],
        "generated": generated,
        "warnings": warnings,
        "metadata": {
            "supported_shape": _INFINITIVE_SUPPORTED_SHAPE,
            "supported_rule_ids": supported_rule_ids,
            "normalizer": SEARCH_NORMALIZER_VERSION,
        },
    }


def _validate_supported_generation_features(features: dict[str, object]) -> None:
    if features.get("generation_type") != "verb_form":
        raise _unsupported_generation(
            field="generation_type",
            received=features.get("generation_type"),
            supported=["verb_form"],
        )
    if features.get("tense_aspect") != "present":
        raise _unsupported_generation(
            field="tense_aspect",
            received=features.get("tense_aspect"),
            supported=["present"],
        )
    if features.get("polarity") not in ("positive", "negative"):
        raise _unsupported_generation(
            field="polarity",
            received=features.get("polarity"),
            supported=["positive", "negative"],
        )
    if features.get("reflexive") not in (None, False):
        raise _unsupported_generation(
            field="reflexive",
            received=features.get("reflexive"),
            supported=["omit reflexive for verb_form generation; reflexivity is an infinitive-branch feature"],
        )
    if features.get("object") not in (None, ""):
        if not isinstance(features.get("object"), dict):
            raise _unsupported_generation(
                field="object",
                received=features.get("object"),
                supported=["structured object feature or None"],
            )
    if not isinstance(features.get("subject"), dict):
        raise _unsupported_generation(
            field="subject",
            received=features.get("subject"),
            supported=["structured subject object"],
        )
    if "extensions" in features:
        _normalize_generation_extensions(features.get("extensions"))


def _resolve_generation_subject(subject: dict[str, object]) -> dict[str, object]:
    subject_type = subject.get("type")
    if subject_type == "person":
        for candidate in PERSON_SUBJECT_CONCORDS:
            if (
                candidate["person"] == subject.get("person")
                and candidate["number"] == subject.get("number")
            ):
                return dict(candidate)
        raise _unsupported_generation(
            field="subject",
            received=subject,
            supported=[
                {
                    "type": "person",
                    "person": candidate["person"],
                    "number": candidate["number"],
                }
                for candidate in PERSON_SUBJECT_CONCORDS
            ],
        )
    if subject_type == "noun_class":
        noun_class = (
            NounClass.objects.filter(
                class_number=subject.get("class_number"),
                review_state__in=SUPPORTED_REVIEW_STATES,
            )
            .exclude(subject_concord="")
            .order_by("display_order", "class_number")
            .first()
        )
        if noun_class is not None:
            return {
                "surface": noun_class.subject_concord.casefold(),
                "slot_type": "noun_class",
                "class_number": noun_class.class_number,
                "noun_class_public_id": noun_class.public_id,
                "label": noun_class.label,
                "confidence": 0.78,
            }
    raise _unsupported_generation(
        field="subject",
        received=subject,
        supported=[
            "person subject with person and number",
            "reviewed noun_class subject with class_number and subject_concord",
        ],
    )


def _resolve_generation_object(obj: dict[str, object] | None) -> dict[str, object] | None:
    if obj is None or obj == "":
        return None
    obj_type = obj.get("type")
    if obj_type == "person":
        for candidate in PERSON_OBJECT_CONCORDS:
            if (
                candidate["person"] == obj.get("person")
                and candidate["number"] == obj.get("number")
            ):
                return dict(candidate)
        raise _unsupported_generation(
            field="object",
            received=obj,
            supported=[
                {
                    "type": "person",
                    "person": candidate["person"],
                    "number": candidate["number"],
                }
                for candidate in PERSON_OBJECT_CONCORDS
            ],
        )
    if obj_type == "noun_class":
        noun_class = (
            NounClass.objects.filter(
                class_number=obj.get("class_number"),
                review_state__in=SUPPORTED_REVIEW_STATES,
            )
            .exclude(object_concord="")
            .order_by("display_order", "class_number")
            .first()
        )
        if noun_class is not None:
            return {
                "surface": noun_class.object_concord.casefold(),
                "slot_type": "noun_class",
                "class_number": noun_class.class_number,
                "noun_class_public_id": noun_class.public_id,
                "label": noun_class.label,
                "confidence": 0.78,
            }
    raise _unsupported_generation(
        field="object",
        received=obj,
        supported=[
            "person object with person and number",
            "reviewed noun_class object with class_number and object_concord",
        ],
    )


def _unsupported_generation(*, field: str, received, supported) -> GenerationFailure:
    return GenerationFailure(
        code="GENERATION_UNSUPPORTED",
        message=f"Unsupported v1 generation feature: {field}.",
        detail={
            "field": field,
            "received": received,
            "supported": supported,
            "supported_shape": "subject_concord + no + [object_concord] + verb_stem / ha + subject_concord + [object_concord] + verb_stem_ending_in_i",
            "supported_rule_ids": [SUPPORTED_RULE_ID, "fortune.verbal.negation.001", "fortune.concord.object.001"],
        },
    )


def _unverified_generation(*, ext: object, ext_type: str, style: str | None) -> GenerationFailure:
    """Structured refusal for a generation operation without source evidence.

    Finding 4 policy: the analyzer may still recognize these allomorphs on
    attested surfaces (see the retained rule card), but generation does not
    generalize them to arbitrary lemmas until a reviewed source locator backs
    the per-lemma distribution.
    """
    return GenerationFailure(
        code=EXTENSION_UNVERIFIED_ERROR_CODE,
        message=(
            "Unsupported v1 generation feature: extensions. The requested "
            "extension allomorph is not source-verified for arbitrary stems, so "
            "generation refuses it instead of guessing a derived form."
        ),
        detail={
            "field": "extensions",
            "received": ext,
            "extension_type": ext_type,
            "style": style,
            "reason": "lexical_distribution_unverified",
            "supported": (
                "Review the derived form against the dictionary sources and "
                "publish it as its own reviewed verb-stem lemma; generation of "
                "verified extension patterns (for example causative -is-/-es-, "
                "applicative, passive, neuter, long reversive, repetitive, "
                "reciprocal) remains available."
            ),
            "supported_rule_ids": [SUPPORTED_RULE_ID, RETAINED_EXTENSIONS_RULE_ID],
        },
    )



def _lemma_payload(lemma: Lemma) -> dict[str, object]:
    return {
        "public_id": lemma.public_id,
        "headword": lemma.headword,
        "normalized_headword": lemma.normalized_headword,
        "part_of_speech_code": lemma.part_of_speech_code,
    }


def _subject_slot(subject_candidate: dict[str, object]) -> dict[str, object]:
    slot = {
        "surface": subject_candidate["surface"],
        "type": subject_candidate["slot_type"],
        "label": subject_candidate["label"],
    }
    for field_name in (
        "person",
        "number",
        "class_number",
        "noun_class_public_id",
    ):
        if field_name in subject_candidate:
            slot[field_name] = subject_candidate[field_name]
    return slot
