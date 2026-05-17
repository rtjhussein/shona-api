from django.db.models import Count

from shona_api.editorial.models import ReviewState
from shona_api.extraction.models import ExtractionUnit
from shona_api.figurative_language.models import FigurativeExpression
from shona_api.lexicon.models import Form, Lemma, NounClass, Sense, ToneRecord
from shona_api.releases.services import CurrentReleaseNotFound, get_current_release
from shona_api.sources.models import Source


MVP_TARGETS = {
    "published_lemmas": 3000,
    "public_tsumo": 150,
}


def build_data_progress_snapshot() -> dict[str, object]:
    published_lemmas = Lemma.objects.filter(review_state=ReviewState.PUBLISHED).count()
    public_tsumo = FigurativeExpression.objects.filter(
        subtype=FigurativeExpression.Subtype.TSUMO,
        subtype_readiness=FigurativeExpression.SubtypeReadiness.ACTIVE,
        review_state__in=(ReviewState.APPROVED, ReviewState.PUBLISHED),
    ).count()
    extraction_units = ExtractionUnit.objects.all()
    batches = _batch_summary()
    active_batch = _batch_detail(batches["active"]) if batches["active"] else None
    return {
        "targets": {
            "published_lemmas": _target_payload(
                published_lemmas,
                MVP_TARGETS["published_lemmas"],
            ),
            "public_tsumo": _target_payload(public_tsumo, MVP_TARGETS["public_tsumo"]),
        },
        "sources": {
            "count": Source.objects.count(),
            "registered_keys": list(
                Source.objects.order_by("source_key").values_list(
                    "source_key",
                    flat=True,
                )
            ),
            "coverage": _source_coverage_rows(),
        },
        "extraction": {
            "total": extraction_units.count(),
            "parser_status_counts": _count_by_choice(
                extraction_units,
                "parser_status",
                ExtractionUnit.ParserStatus.values,
            ),
            "review_state_counts": _count_by_choice(
                extraction_units,
                "review_state",
                ReviewState.values,
            ),
        },
        "canonical": {
            "published_lemmas": published_lemmas,
            "total_lemmas": Lemma.objects.count(),
            "published_senses": Sense.objects.filter(
                review_state=ReviewState.PUBLISHED
            ).count(),
            "published_forms": Form.objects.filter(
                review_state=ReviewState.PUBLISHED
            ).count(),
            "published_tone_records": ToneRecord.objects.filter(
                review_state=ReviewState.PUBLISHED
            ).count(),
            "published_noun_classes": NounClass.objects.filter(
                review_state=ReviewState.PUBLISHED
            ).count(),
        },
        "figurative_language": {
            "public_tsumo": public_tsumo,
            "public_madimikira": FigurativeExpression.objects.filter(
                subtype=FigurativeExpression.Subtype.MADIMIKIRA,
                subtype_readiness=FigurativeExpression.SubtypeReadiness.ACTIVE,
                review_state__in=(ReviewState.APPROVED, ReviewState.PUBLISHED),
            ).count(),
            "total": FigurativeExpression.objects.count(),
        },
        "release": _current_release_payload(),
        "batches": batches,
        "active_batch": active_batch,
    }


def _target_payload(current, target):
    percent = 0 if target == 0 else round((current / target) * 100, 2)
    return {
        "current": current,
        "target": target,
        "remaining": max(target - current, 0),
        "percent": percent,
    }


def _count_by_choice(queryset, field_name, choices):
    counts = {choice: 0 for choice in choices}
    for row in queryset.values(field_name).annotate(count=Count("pk")):
        counts[row[field_name]] = row["count"]
    return counts


def _current_release_payload():
    try:
        release = get_current_release()
    except CurrentReleaseNotFound:
        return None
    return {
        "version": release.version,
        "label": release.label,
        "rule_set_version": release.rule_set_version,
    }


def _batch_summary():
    batch_ids = []
    for provenance in (
        ExtractionUnit.objects.order_by("created_at", "pk").values_list(
            "provenance",
            flat=True,
        )
    ):
        if isinstance(provenance, dict):
            batch_id = provenance.get("batch_id")
            if batch_id and batch_id not in batch_ids:
                batch_ids.append(batch_id)
    return {
        "count": len(batch_ids),
        "active": batch_ids[-1] if batch_ids else "",
        "latest": batch_ids[-5:],
    }


def _batch_detail(batch_id):
    units = ExtractionUnit.objects.filter(provenance__batch_id=batch_id)
    total = units.count()
    parser_counts = _count_by_choice(
        units,
        "parser_status",
        ExtractionUnit.ParserStatus.values,
    )
    review_counts = _count_by_choice(units, "review_state", ReviewState.values)
    parsed_count = (
        parser_counts[ExtractionUnit.ParserStatus.PARSED]
        + parser_counts[ExtractionUnit.ParserStatus.PARSED_WITH_UNCERTAINTY]
    )
    approved_unpublished = units.filter(
        review_state=ReviewState.APPROVED,
        canonical_record_object_id="",
    ).count()
    pipeline = [
        {
            "key": "imported",
            "label": "Imported",
            "count": total,
            "percent": _percent(total, total),
            "tone": "info",
        },
        {
            "key": "parsed",
            "label": "Parsed",
            "count": parsed_count,
            "percent": _percent(parsed_count, total),
            "tone": "good",
        },
        {
            "key": "needs_review",
            "label": "Needs review",
            "count": review_counts[ReviewState.NEEDS_REVIEW],
            "percent": _percent(review_counts[ReviewState.NEEDS_REVIEW], total),
            "tone": "warning",
        },
        {
            "key": "approved",
            "label": "Approved",
            "count": review_counts[ReviewState.APPROVED],
            "percent": _percent(review_counts[ReviewState.APPROVED], total),
            "tone": "ready",
        },
        {
            "key": "published",
            "label": "Published",
            "count": review_counts[ReviewState.PUBLISHED],
            "percent": _percent(review_counts[ReviewState.PUBLISHED], total),
            "tone": "published",
        },
    ]
    return {
        "batch_id": batch_id,
        "total": total,
        "parser_status_counts": parser_counts,
        "review_state_counts": review_counts,
        "parsed_count": parsed_count,
        "failed_count": parser_counts[ExtractionUnit.ParserStatus.FAILED],
        "uncertain_count": parser_counts[
            ExtractionUnit.ParserStatus.PARSED_WITH_UNCERTAINTY
        ],
        "needs_review_count": review_counts[ReviewState.NEEDS_REVIEW],
        "approved_count": review_counts[ReviewState.APPROVED],
        "approved_unpublished_count": approved_unpublished,
        "published_count": review_counts[ReviewState.PUBLISHED],
        "pipeline": pipeline,
        "parseable_percent": _percent(parsed_count, total),
        "reviewed_percent": _percent(
            total - review_counts[ReviewState.NEEDS_REVIEW],
            total,
        ),
        "published_percent": _percent(review_counts[ReviewState.PUBLISHED], total),
    }


def _source_coverage_rows():
    rows = []
    for source in Source.objects.order_by("source_key"):
        extraction_count = ExtractionUnit.objects.filter(source=source).count()
        published_lemmas = Lemma.objects.filter(
            review_state=ReviewState.PUBLISHED,
            provenance__source_key=source.source_key,
        ).count()
        rows.append(
            {
                "source_key": source.source_key,
                "title": source.title,
                "authority_level": source.authority_level,
                "extraction_count": extraction_count,
                "published_lemmas": published_lemmas,
                "status": _source_status(extraction_count, published_lemmas),
            }
        )
    return rows


def _source_status(extraction_count, published_lemmas):
    if published_lemmas:
        return "publishing"
    if extraction_count:
        return "candidate queue"
    return "registered"


def _percent(count, total):
    if total == 0:
        return 0
    return round((count / total) * 100, 2)
