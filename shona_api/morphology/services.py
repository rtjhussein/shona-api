from dataclasses import dataclass

from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Lemma, NounClass
from shona_api.lexicon.search import SEARCH_NORMALIZER_VERSION, normalize_search_query
from shona_api.phonology import compute_phonology_fields


ANALYZER_VERSION = "shona-morphology-analyzer-v1"
GENERATOR_VERSION = "shona-morphology-generator-v1"
SUPPORTED_RULE_ID = "fortune.verbal.slots.001"
INFINITIVE_RULE_ID = "fortune.verbal.infinitive.001"
EXTENSIONS_RULE_ID = "fortune.verbal.extensions.001"
INFINITIVE_SOURCE_LOCATOR = (
    "Fortune Grammatical Constructions, section 3.3.18 Noun Class 15, "
    "PDF pages 90-91 (printed pp. 78-79)"
)
SUPPORTED_TENSE_ASPECT_MARKER = "no"
SUPPORTED_ANALYSIS_SHAPE = (
    "ku + reviewed verb_stem / subject_concord + no + [object_concord] + "
    "verb_stem / ha + subject_concord + [object_concord] + "
    "verb_stem_ending_in_e"
)
SUPPORTED_ANALYSIS_RULE_IDS = [
    INFINITIVE_RULE_ID,
    SUPPORTED_RULE_ID,
    "fortune.verbal.negation.001",
    "fortune.concord.object.001",
]
EXTENSION_LIKE_SUFFIXES = (
    "irirwa",
    "erwa",
    "irwa",
    "iswa",
    "eswa",
    "idzwa",
    "udzwa",
    "dzirwa",
    "zwa",
    "wa",
)
SUPPORTED_REVIEW_STATES = (
    ReviewState.APPROVED,
    ReviewState.PUBLISHED,
)


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

    analyses = []
    infinitive_analysis = _analyze_ku_infinitive(normalized)
    if infinitive_analysis is not None:
        analyses.append(infinitive_analysis)

    analyses.extend([
        analysis
        for candidate in candidates
        if (analysis := _analyze_present_positive(normalized, candidate)) is not None
    ])
    
    analyses.extend([
        analysis
        for candidate in neg_candidates
        if (analysis := _analyze_present_negative(normalized, candidate)) is not None
    ])

    if not analyses:
        detail = {
            "normalized": normalized,
            "supported_shape": SUPPORTED_ANALYSIS_SHAPE,
            "supported_rule_ids": SUPPORTED_ANALYSIS_RULE_IDS,
        }
        future_lanes = _unsupported_future_lanes(normalized)
        if future_lanes:
            detail["future_lanes"] = future_lanes
        raise AnalysisFailure(
            code="ANALYSIS_UNSUPPORTED",
            message=(
                "No supported v1 analysis matched the input. Supported v1 forms "
                "are ku- infinitive forms (ku + reviewed verb stem), "
                "positive present verb forms (subject concord + 'no' + "
                "[object_concord] + verb_stem), and negative present verb forms "
                "(ha- + subject concord + [object_concord] + verb_stem ending in -e)."
            ),
            detail=detail,
        )

    analyses.sort(key=lambda item: item["confidence"], reverse=True)
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
    _validate_supported_generation_features(features)
    subject_candidate = _resolve_generation_subject(features["subject"])
    object_candidate = _resolve_generation_object(features.get("object"))

    polarity = features.get("polarity", "positive")
    has_object = object_candidate is not None

    # Handle optional extensions
    extensions_feature = features.get("extensions", [])
    normalized_exts = []
    for ext in extensions_feature:
        if isinstance(ext, str):
            normalized_exts.append({"type": ext})
        elif isinstance(ext, dict):
            normalized_exts.append(ext)

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
        if stem_val.endswith("a"):
            stem_mutated = stem_val[:-1] + "e"
        else:
            stem_mutated = stem_val + "e"
        
        # Apply coalescence/contraction rule
        if has_object:
            oc = object_candidate["surface"]
            if oc.endswith("a") and stem_mutated.startswith("a"):
                oc_surface = oc[:-1]
            else:
                oc_surface = oc
            form = f"ha{sc}{oc_surface}{stem_mutated}"
        else:
            if sc.endswith("a") and stem_mutated.startswith("a"):
                sc_surface = sc[:-1]
            else:
                sc_surface = sc
            form = f"ha{sc_surface}{stem_mutated}"

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
                    "surface": "e",
                    "value": "e",
                },
            },
            "phonology": compute_phonology_fields(form),
        }
    else:
        sc = subject_candidate["surface"]
        if has_object:
            oc = object_candidate["surface"]
            if oc.endswith("a") and stem_val.startswith("a"):
                oc_surface = oc[:-1]
            else:
                oc_surface = oc
            form = f"{sc}{SUPPORTED_TENSE_ASPECT_MARKER}{oc_surface}{stem_val}"
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
        warnings.append({
            "code": "TONE_NOT_GENERATED",
            "message": "Tone, negative forms, and extensions are not generated." if has_object else "Tone, object markers, negative forms, and extensions are not generated.",
        })
    else:
        warnings.append({
            "code": "TONE_NOT_GENERATED",
            "message": "Tone and extensions are not generated." if has_object else "Tone, object markers, and extensions are not generated.",
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
                "ha + subject_concord + [object_concord] + verb_stem_ending_in_e"
            ),
            "supported_rule_ids": [generated["rule_id"]],
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


def _analyze_ku_infinitive(normalized: str) -> dict[str, object] | None:
    if not normalized.startswith("ku") or len(normalized) <= 2:
        return None

    verb_stem = normalized.removeprefix("ku")
    lemma, extensions = _get_stem_and_extensions(verb_stem)
    if lemma is None:
        return None

    return {
        "analysis_type": "infinitive",
        "confidence": 0.82,
        "rule_id": INFINITIVE_RULE_ID,
        "lemma": _lemma_payload(lemma),
        "source": {
            "rule_card_id": INFINITIVE_RULE_ID,
            "source_key": "source_fortune",
            "source_locator": INFINITIVE_SOURCE_LOCATOR,
        },
        "slots": {
            "infinitive_prefix": {
                "surface": "ku",
                "type": "class_15_infinitive_prefix",
                "label": "class 15 infinitive prefix",
            },
            "subject": None,
            "tense_aspect": None,
            "polarity": None,
            "object": None,
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
            "v1 analyzes only simple ku + reviewed verb-stem infinitives.",
            "Infinitive complements, negation, objects, and tone are not analyzed.",
            "Infinitive generation is not supported.",
        ],
    }


def _unsupported_future_lanes(normalized: str) -> list[dict[str, object]]:
    lanes = []
    if normalized.startswith("ku") and len(normalized) > 2:
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
    if _looks_passive_or_extension_like(normalized):
        lanes.append(
            {
                "code": "passive_or_extension_like",
                "message": (
                    "This looks like a passive or extension-like verb surface. "
                    "Those forms are a future review lane and are not analyzed in v1."
                ),
                "support_status": "not_supported",
                "rule_card_ids": [EXTENSIONS_RULE_ID],
            }
        )
    return lanes


def _looks_passive_or_extension_like(normalized: str) -> bool:
    if len(normalized) < 5:
        return False
    return any(
        normalized.endswith(suffix)
        for suffix in EXTENSION_LIKE_SUFFIXES
    )


def _decompose_stem(surface_stem: str) -> tuple[str, list[dict[str, object]]] | None:
    if surface_stem.endswith("a"):
        fv = "a"
        base = surface_stem[:-1]
    elif surface_stem.endswith("e"):
        fv = "e"
        base = surface_stem[:-1]
    else:
        return None

    extensions = []

    while True:
        # Check passive suffixes first (since passive is outermost)
        if base.endswith("w") and not base.endswith("iw") and not base.endswith("ew"):
            extensions.append({
                "surface": "w",
                "type": "passive",
                "label": "passive extension (-w-)",
            })
            base = base[:-1]
            continue
        elif base.endswith("iw"):
            extensions.append({
                "surface": "iw",
                "type": "passive",
                "label": "passive extension (-iw-)",
            })
            base = base[:-2]
            continue
        elif base.endswith("ew"):
            extensions.append({
                "surface": "ew",
                "type": "passive",
                "label": "passive extension (-ew-)",
            })
            base = base[:-2]
            continue

        # Causative suffixes
        if base.endswith("is"):
            extensions.append({
                "surface": "is",
                "type": "causative",
                "label": "causative extension (-is- / -es-)",
            })
            base = base[:-2]
            continue
        elif base.endswith("es"):
            extensions.append({
                "surface": "es",
                "type": "causative",
                "label": "causative extension (-is- / -es-)",
            })
            base = base[:-2]
            continue

        # Applicative suffixes
        if base.endswith("ir"):
            extensions.append({
                "surface": "ir",
                "type": "applicative",
                "label": "applicative extension (-ir- / -er-)",
            })
            base = base[:-2]
            continue
        elif base.endswith("er"):
            extensions.append({
                "surface": "er",
                "type": "applicative",
                "label": "applicative extension (-ir- / -er-)",
            })
            base = base[:-2]
            continue

        # Reciprocal suffix
        if base.endswith("an"):
            extensions.append({
                "surface": "an",
                "type": "reciprocal",
                "label": "reciprocal extension (-an-)",
            })
            base = base[:-2]
            continue

        # Neuter suffix
        if base.endswith("ik"):
            extensions.append({
                "surface": "ik",
                "type": "neuter",
                "label": "neuter extension (-ik- / -ek-)",
            })
            base = base[:-2]
            continue
        elif base.endswith("ek"):
            extensions.append({
                "surface": "ek",
                "type": "neuter",
                "label": "neuter extension (-ik- / -ek-)",
            })
            base = base[:-2]
            continue

        # Causative style 'dz'
        if base.endswith("idz"):
            extensions.append({
                "surface": "idz",
                "type": "causative",
                "style": "dz",
                "label": "causative extension (-idz- / -edz-)",
            })
            base = base[:-3]
            continue
        elif base.endswith("edz"):
            extensions.append({
                "surface": "edz",
                "type": "causative",
                "style": "dz",
                "label": "causative extension (-idz- / -edz-)",
            })
            base = base[:-3]
            continue

        # Causative style 'ts'
        if base.endswith("its"):
            extensions.append({
                "surface": "its",
                "type": "causative",
                "style": "ts",
                "label": "causative extension (-its- / -ets-)",
            })
            base = base[:-3]
            continue
        elif base.endswith("ets"):
            extensions.append({
                "surface": "ets",
                "type": "causative",
                "style": "ts",
                "label": "causative extension (-its- / -ets-)",
            })
            base = base[:-3]
            continue

        # Reversive suffix (check long first)
        if base.endswith("unur"):
            extensions.append({
                "surface": "unur",
                "type": "reversive",
                "style": "long",
                "label": "reversive extension (-unur- / -onor-)",
            })
            base = base[:-4]
            continue
        elif base.endswith("onor"):
            extensions.append({
                "surface": "onor",
                "type": "reversive",
                "style": "long",
                "label": "reversive extension (-unur- / -onor-)",
            })
            base = base[:-4]
            continue
        elif base.endswith("urur"):
            extensions.append({
                "surface": "urur",
                "type": "reversive",
                "style": "long",
                "label": "reversive extension (-urur- / -oror-)",
            })
            base = base[:-4]
            continue
        elif base.endswith("oror"):
            extensions.append({
                "surface": "oror",
                "type": "reversive",
                "style": "long",
                "label": "reversive extension (-urur- / -oror-)",
            })
            base = base[:-4]
            continue
        elif base.endswith("ur"):
            extensions.append({
                "surface": "ur",
                "type": "reversive",
                "style": "short",
                "label": "reversive extension (-ur- / -or-)",
            })
            base = base[:-2]
            continue
        elif base.endswith("or"):
            extensions.append({
                "surface": "or",
                "type": "reversive",
                "style": "short",
                "label": "reversive extension (-ur- / -or-)",
            })
            base = base[:-2]
            continue

        break

    # If no extensions were parsed, return None (this was a simple stem)
    if not extensions:
        return None

    extensions.reverse()
    canonical_stem = base + "a"
    return canonical_stem, extensions


def _validate_extension_harmony(base_root: str, extensions: list[dict[str, object]]) -> bool:
    current_stem = base_root
    for ext in extensions:
        ext_type = ext["type"]
        ext_surface = ext["surface"]

        if ext_surface == "w":
            current_stem += "w"
            continue

        trigger_vowel = None
        for char in reversed(current_stem):
            if char in "aeiou":
                trigger_vowel = char
                break

        if trigger_vowel is None:
            trigger_vowel = "a"

        is_mid_trigger = trigger_vowel in ("e", "o")
        expected_vowel = "e" if is_mid_trigger else "i"

        if ext_type == "causative":
            style = ext.get("style")
            if style == "dz":
                if ext_surface != f"{expected_vowel}dz":
                    return False
            elif style == "ts":
                if ext_surface != f"{expected_vowel}ts":
                    return False
            else:
                if ext_surface != f"{expected_vowel}s":
                    return False
        elif ext_type == "applicative":
            if ext_surface != f"{expected_vowel}r":
                return False
        elif ext_type == "passive":
            if ext_surface != f"{expected_vowel}w":
                return False
        elif ext_type == "neuter":
            if ext_surface != f"{expected_vowel}k":
                return False
        elif ext_type == "reversive":
            # Reversives have mid-vowel harmony strictly on trigger vowel 'o'
            is_reversive_mid = trigger_vowel == "o"
            v = "o" if is_reversive_mid else "u"
            style = ext.get("style")
            if style == "long_urur":
                if ext_surface != f"{v}r{v}r":
                    return False
            elif style == "long_unur":
                if ext_surface != f"{v}n{v}r":
                    return False
            elif style == "long":
                if ext_surface not in (f"{v}r{v}r", f"{v}n{v}r"):
                    return False
            else:
                if ext_surface != f"{v}r":
                    return False

        current_stem += ext_surface
    return True


def _apply_extensions(canonical_stem: str, extensions: list[dict[str, object]]) -> tuple[str, list[dict[str, object]]]:
    if canonical_stem.endswith("a"):
        base = canonical_stem[:-1]
    else:
        base = canonical_stem

    applied = []

    for ext in extensions:
        ext_type = ext.get("type")

        trigger_vowel = None
        for char in reversed(base):
            if char in "aeiou":
                trigger_vowel = char
                break
        if trigger_vowel is None:
            trigger_vowel = "a"

        is_mid_trigger = trigger_vowel in ("e", "o")

        if ext_type == "causative":
            style = ext.get("style")
            if style == "dz":
                suffix = "edz" if is_mid_trigger else "idz"
                label = "causative extension (-idz- / -edz-)"
            elif style == "ts":
                suffix = "ets" if is_mid_trigger else "its"
                label = "causative extension (-its- / -ets-)"
            else:
                suffix = "es" if is_mid_trigger else "is"
                label = "causative extension (-is- / -es-)"
            base += suffix
            item = {
                "surface": suffix,
                "type": "causative",
                "label": label,
            }
            if style is not None:
                item["style"] = style
            applied.append(item)
        elif ext_type == "applicative":
            suffix = "er" if is_mid_trigger else "ir"
            base += suffix
            applied.append({
                "surface": suffix,
                "type": "applicative",
                "label": "applicative extension (-ir- / -er-)",
            })
        elif ext_type == "passive":
            has_vowels = any(c in "aeiou" for c in base)
            if not has_vowels or len(base) <= 2:
                suffix = "ew" if is_mid_trigger else "iw"
            else:
                suffix = "w"
            base += suffix
            applied.append({
                "surface": suffix,
                "type": "passive",
                "label": "passive extension (-w-)" if suffix == "w" else f"passive extension (-{suffix}-)",
            })
        elif ext_type == "neuter":
            suffix = "ek" if is_mid_trigger else "ik"
            base += suffix
            applied.append({
                "surface": suffix,
                "type": "neuter",
                "label": "neuter extension (-ik- / -ek-)",
            })
        elif ext_type == "reciprocal":
            suffix = "an"
            base += suffix
            applied.append({
                "surface": suffix,
                "type": "reciprocal",
                "label": "reciprocal extension (-an-)",
            })
        elif ext_type == "reversive":
            style = ext.get("style")
            # Reversives have mid-vowel harmony strictly on trigger vowel 'o'
            is_reversive_mid = trigger_vowel == "o"
            v = "o" if is_reversive_mid else "u"
            if style == "long_urur" or style == "urur" or style == "oror" or style == "long":
                # Default long reversive to -urur- / -oror- style if style is long or urur/oror
                suffix = f"{v}r{v}r"
                label = "reversive extension (-urur- / -oror-)"
                style_val = "long"
            elif style == "long_unur" or style == "unur" or style == "onor":
                suffix = f"{v}n{v}r"
                label = "reversive extension (-unur- / -onor-)"
                style_val = "long"
            else:
                suffix = f"{v}r"
                label = "reversive extension (-ur- / -or-)"
                style_val = "short"
            base += suffix
            applied.append({
                "surface": suffix,
                "type": "reversive",
                "style": style_val,
                "label": label,
            })

    return base, applied


def _get_stem_and_extensions(stem_candidate: str) -> tuple[Lemma | None, list[dict[str, object]]]:
    lemma = _get_reviewed_verb_stem(stem_candidate)
    extensions = []
    if lemma is None:
        decomp = _decompose_stem(stem_candidate)
        if decomp is not None:
            canonical_stem, ext_candidates = decomp
            base_root = canonical_stem[:-1] if canonical_stem.endswith("a") else canonical_stem
            if _validate_extension_harmony(base_root, ext_candidates):
                lemma = _get_reviewed_verb_stem(canonical_stem)
                if lemma is not None:
                    extensions = ext_candidates
    return lemma, extensions


def _analyze_present_positive(
    normalized: str, subject_candidate: dict[str, object]
) -> dict[str, object] | None:
    subject_surface = subject_candidate["surface"]
    prefix = f"{subject_surface}{SUPPORTED_TENSE_ASPECT_MARKER}"
    if not normalized.startswith(prefix):
        return None

    verb_stem = normalized.removeprefix(prefix)
    if not verb_stem:
        return None

    # Check if there is an object concord prefixing the stem
    for oc_candidate in _candidate_object_concords():
        oc_surface = oc_candidate["surface"]
        if verb_stem.startswith(oc_surface):
            rest = verb_stem.removeprefix(oc_surface)
            # Possibility 1: No coalescence
            if rest:
                lemma, extensions = _get_stem_and_extensions(rest)
                if lemma is not None:
                    phonology = compute_phonology_fields(normalized)
                    return {
                        "analysis_type": "verb_form",
                        "confidence": min(subject_candidate["confidence"], oc_candidate["confidence"]),
                        "rule_id": "fortune.concord.object.001",
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
                            "object": _subject_slot(oc_candidate),
                            "verb_stem": {
                                "surface": rest,
                                "lemma_public_id": lemma.public_id,
                            },
                            "extensions": extensions,
                            "final_vowel": {
                                "surface": rest[-1],
                                "value": rest[-1],
                            },
                        },
                        "phonology": phonology,
                        "limitations": [
                            "v1 supports only single-token positive present verb forms.",
                            "Negative forms and tone are not analyzed.",
                        ],
                    }
            # Possibility 2: Coalescence (only possible if oc_surface ends in "a")
            if oc_surface.endswith("a"):
                rest_coalesced = "a" + rest
                lemma, extensions = _get_stem_and_extensions(rest_coalesced)
                if lemma is not None:
                    phonology = compute_phonology_fields(normalized)
                    return {
                        "analysis_type": "verb_form",
                        "confidence": min(subject_candidate["confidence"], oc_candidate["confidence"]),
                        "rule_id": "fortune.concord.object.001",
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
                            "object": _subject_slot(oc_candidate),
                            "verb_stem": {
                                "surface": rest_coalesced,
                                "lemma_public_id": lemma.public_id,
                            },
                            "extensions": extensions,
                            "final_vowel": {
                                "surface": rest_coalesced[-1],
                                "value": rest_coalesced[-1],
                            },
                        },
                        "phonology": phonology,
                        "limitations": [
                            "v1 supports only single-token positive present verb forms.",
                            "Negative forms and tone are not analyzed.",
                        ],
                    }

    # No object concord matched
    lemma, extensions = _get_stem_and_extensions(verb_stem)
    if lemma is None:
        return None

    phonology = compute_phonology_fields(normalized)
    return {
        "analysis_type": "verb_form",
        "confidence": subject_candidate["confidence"],
        "rule_id": SUPPORTED_RULE_ID,
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
            "object": None,
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
        "phonology": phonology,
        "limitations": [
            "v1 supports only single-token positive present verb forms.",
            "Object markers, negative forms, and tone are not analyzed.",
        ],
    }


def _analyze_present_negative(
    normalized: str, subject_candidate: dict[str, object]
) -> dict[str, object] | None:
    if not normalized.startswith("ha"):
        return None
    rest = normalized.removeprefix("ha")
    sc_surface = subject_candidate["surface"]
    if not rest.startswith(sc_surface):
        return None

    verb_stem = rest.removeprefix(sc_surface)
    if not verb_stem:
        return None

    # Let's check stem candidates WITH object concord first
    for oc_candidate in _candidate_object_concords():
        oc_surface = oc_candidate["surface"]
        if verb_stem.startswith(oc_surface):
            inner_stem = verb_stem.removeprefix(oc_surface)
            
            # Check two stem candidates: Possibility A (No coalescence) and Possibility B (Coalescence)
            stem_candidates = []
            if inner_stem:
                stem_candidates.append((inner_stem, False))
            if oc_surface.endswith("a"):
                stem_candidates.append(("a" + inner_stem, True))

            for stem, coalesced in stem_candidates:
                if not stem.endswith("e"):
                    continue
                normalized_stem = stem[:-1] + "a"
                lemma, extensions = _get_stem_and_extensions(normalized_stem)
                if lemma is not None:
                    phonology = compute_phonology_fields(normalized)
                    return {
                        "analysis_type": "verb_form",
                        "confidence": min(subject_candidate["confidence"], oc_candidate["confidence"]),
                        "rule_id": "fortune.concord.object.001",
                        "lemma": _lemma_payload(lemma),
                        "slots": {
                            "subject": _subject_slot(subject_candidate),
                            "tense_aspect": None,
                            "polarity": {
                                "surface": "ha",
                                "value": "negative",
                                "label": "present negative marker",
                            },
                            "object": _subject_slot(oc_candidate),
                            "verb_stem": {
                                "surface": stem,
                                "lemma_public_id": lemma.public_id,
                            },
                            "extensions": extensions,
                            "final_vowel": {
                                "surface": "e",
                                "value": "e",
                            },
                        },
                        "phonology": phonology,
                        "limitations": [
                            "v1 supports only single-token negative present verb forms.",
                            "Tone is not analyzed.",
                        ],
                    }

    # No object concord matched
    stem_candidates = []
    if verb_stem:
        stem_candidates.append((verb_stem, False))

    if sc_surface.endswith("a"):
        stem_candidates.append(("a" + verb_stem, True))

    for stem, coalesced in stem_candidates:
        if not stem.endswith("e"):
            continue
        # Mutate "e" back to "a" for database lookup
        normalized_stem = stem[:-1] + "a"
        lemma, extensions = _get_stem_and_extensions(normalized_stem)
        if lemma is not None:
            phonology = compute_phonology_fields(normalized)
            return {
                "analysis_type": "verb_form",
                "confidence": subject_candidate["confidence"],
                "rule_id": "fortune.verbal.negation.001",
                "lemma": _lemma_payload(lemma),
                "slots": {
                    "subject": _subject_slot(subject_candidate),
                    "tense_aspect": None,
                    "polarity": {
                        "surface": "ha",
                        "value": "negative",
                        "label": "present negative marker",
                    },
                    "object": None,
                    "verb_stem": {
                        "surface": stem,
                        "lemma_public_id": lemma.public_id,
                    },
                    "extensions": extensions,
                    "final_vowel": {
                        "surface": "e",
                        "value": "e",
                    },
                },
                "phonology": phonology,
                "limitations": [
                    "v1 supports only single-token negative present verb forms.",
                    "Object markers, positive forms, and tone are not analyzed.",
                ],
            }
    return None


def _get_reviewed_verb_stem(normalized_stem: str) -> Lemma | None:
    return (
        Lemma.objects.filter(
            review_state__in=SUPPORTED_REVIEW_STATES,
            headword_kind=Lemma.HeadwordKind.VERB_STEM,
            normalized_headword=normalized_stem,
        )
        .order_by("normalized_headword", "public_id")
        .first()
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
        exts = features.get("extensions")
        if not isinstance(exts, list):
            raise _unsupported_generation(
                field="extensions",
                received=exts,
                supported=["list of extensions"],
            )
        for ext in exts:
            if not isinstance(ext, (str, dict)):
                raise _unsupported_generation(
                    field="extensions",
                    received=exts,
                    supported=["list of strings or dicts"],
                )
            ext_type = ext if isinstance(ext, str) else ext.get("type")
            if ext_type not in ("passive", "causative", "applicative", "neuter", "reciprocal", "reversive"):
                raise _unsupported_generation(
                    field="extensions",
                    received=ext_type,
                    supported=["passive", "causative", "applicative", "neuter", "reciprocal", "reversive"],
                )


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
            "supported_shape": "subject_concord + no + [object_concord] + verb_stem / ha + subject_concord + [object_concord] + verb_stem_ending_in_e",
            "supported_rule_ids": [SUPPORTED_RULE_ID, "fortune.verbal.negation.001", "fortune.concord.object.001"],
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
