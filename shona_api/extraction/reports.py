from collections import Counter

from shona_api.editorial.models import ReviewState

from .models import ExtractionUnit


def build_batch_quality_report(batch_id: str) -> dict[str, object]:
    units = list(
        ExtractionUnit.objects.filter(provenance__batch_id=batch_id).select_related(
            "source",
            "canonical_record_content_type",
        )
    )
    total = len(units)
    parser_status_counts = _choice_counter(
        (unit.parser_status for unit in units),
        ExtractionUnit.ParserStatus.values,
    )
    review_state_counts = _choice_counter(
        (unit.review_state for unit in units),
        ReviewState.values,
    )
    published_count = sum(
        1
        for unit in units
        if unit.review_state == ReviewState.PUBLISHED
        and unit.canonical_record_object_id
    )
    parseable_count = (
        parser_status_counts[ExtractionUnit.ParserStatus.PARSED]
        + parser_status_counts[ExtractionUnit.ParserStatus.PARSED_WITH_UNCERTAINTY]
    )
    return {
        "batch_id": batch_id,
        "imported_count": total,
        "parser_status_counts": dict(parser_status_counts),
        "review_state_counts": dict(review_state_counts),
        "parseable_rate": _rate(parseable_count, total),
        "published_count": published_count,
        "failed_count": parser_status_counts[ExtractionUnit.ParserStatus.FAILED],
        "uncertain_count": parser_status_counts[
            ExtractionUnit.ParserStatus.PARSED_WITH_UNCERTAINTY
        ],
        "common_error_codes": _common_markers(units, "errors"),
        "common_uncertainty_codes": _common_markers(units, "uncertainties"),
    }


def get_batch_units(batch_id: str):
    return ExtractionUnit.objects.filter(provenance__batch_id=batch_id)


def _choice_counter(values, choices):
    counter = Counter(values)
    return Counter({choice: counter.get(choice, 0) for choice in choices})


def _rate(count, total):
    if total == 0:
        return 0.0
    return round(count / total, 4)


def _common_markers(units, field_name):
    counter = Counter()
    for unit in units:
        markers = (unit.parser_output or {}).get(field_name) or []
        for marker in markers:
            if not isinstance(marker, dict):
                counter[str(marker)] += 1
                continue
            key = (
                marker.get("code")
                or marker.get("path")
                or marker.get("message")
                or "unknown"
            )
            counter[str(key)] += 1
    return [{"code": code, "count": count} for code, count in counter.most_common()]
