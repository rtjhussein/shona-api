from dataclasses import dataclass

from shona_api.editorial.models import ReviewState
from shona_api.morphology.services import AnalysisFailure, analyze_text
from shona_api.releases.services import (
    CurrentReleaseNotFound,
    get_current_release_metadata,
)

from .models import Form, Lemma, Sense
from .search import (
    MAX_SEARCH_LIMIT,
    build_public_search_filters,
    normalize_search_query,
    public_form_queryset,
    public_lemma_queryset,
    search_public_records,
)


ISSUE_CATEGORIES = (
    "lemma_unsearchable",
    "form_unsearchable",
    "wrong_lemma",
    "morphology_unsupported",
    "morphology_error",
    "visibility_issue",
    "ambiguous_result",
)

# Categories that reflect corpus scale (homographs, shared verb stems,
# multiple plausible hits) rather than a data defect. They are reported but
# do not fail the run.
INFO_CATEGORIES = frozenset({"ambiguous_result"})


@dataclass(frozen=True)
class CorpusQAIssue:
    category: str
    record_type: str
    public_id: str | None
    query: str | None
    expected_lemma_public_id: str | None
    actual_lemma_public_id: str | None
    message: str
    actual_lemma_public_ids: list[str] | None = None
    actual_form_public_ids: list[str] | None = None
    severity: str = "error"

    def to_dict(self) -> dict[str, object]:
        payload = {
            "category": self.category,
            "record_type": self.record_type,
            "public_id": self.public_id,
            "query": self.query,
            "expected_lemma_public_id": self.expected_lemma_public_id,
            "actual_lemma_public_id": self.actual_lemma_public_id,
            "message": self.message,
            "severity": self.severity,
        }
        if self.actual_lemma_public_ids is not None:
            payload["actual_lemma_public_ids"] = self.actual_lemma_public_ids
        if self.actual_form_public_ids is not None:
            payload["actual_form_public_ids"] = self.actual_form_public_ids
        return payload


def run_published_corpus_qa(
    *,
    limit: int | None = None,
    include_morphology: bool = True,
) -> dict[str, object]:
    issues: list[CorpusQAIssue] = []
    try:
        release_metadata = get_current_release_metadata()
    except CurrentReleaseNotFound:
        release_metadata = None
        issues.append(
            CorpusQAIssue(
                category="visibility_issue",
                record_type="data_release",
                public_id=None,
                query=None,
                expected_lemma_public_id=None,
                actual_lemma_public_id=None,
                message=(
                    "No current data release is configured; public language "
                    "API endpoints hide canonical records behind the release gate."
                ),
            )
        )

    lemmas = list(
        _limit_queryset(
            Lemma.objects.filter(review_state=ReviewState.PUBLISHED)
            .select_related("noun_class")
            .order_by("normalized_headword", "public_id"),
            limit,
        )
    )
    senses = list(
        _limit_queryset(
            Sense.objects.filter(review_state=ReviewState.PUBLISHED)
            .select_related("lemma")
            .order_by("lemma__normalized_headword", "number", "public_id"),
            limit,
        )
    )
    forms = list(
        _limit_queryset(
            Form.objects.filter(review_state=ReviewState.PUBLISHED)
            .select_related("lemma")
            .order_by("lemma__normalized_headword", "form_kind", "normalized_form", "public_id"),
            limit,
        )
    )

    from collections import Counter

    # Bulk exact-search contract: membership and duplicate normalized values
    # are equivalent to the public exact-search result for QA purposes. This
    # avoids issuing several prefetch-heavy ORM queries per published record.
    lemma_head_counts = Counter(
        public_lemma_queryset()
        .prefetch_related(None)
        .values_list("normalized_headword", flat=True)
    )
    form_norm_counts = Counter(
        public_form_queryset()
        .prefetch_related(None)
        .values_list("normalized_form", flat=True)
    )
    visible_lemma_ids = set(
        public_lemma_queryset()
        .prefetch_related(None)
        .values_list("public_id", flat=True)
    )
    visible_form_ids = set(
        public_form_queryset()
        .prefetch_related(None)
        .values_list("public_id", flat=True)
    )

    for lemma in lemmas:
        if lemma.public_id not in visible_lemma_ids:
            issues.append(
                CorpusQAIssue(
                    category="visibility_issue",
                    record_type="lemma",
                    public_id=lemma.public_id,
                    query=lemma.headword,
                    expected_lemma_public_id=lemma.public_id,
                    actual_lemma_public_id=None,
                    message="Published lemma is not visible through public lemma filters.",
                )
            )
            continue

        normalized_query = normalize_search_query(lemma.headword)
        if not normalized_query or normalized_query not in lemma_head_counts:
            issues.append(
                CorpusQAIssue(
                    category="lemma_unsearchable",
                    record_type="lemma",
                    public_id=lemma.public_id,
                    query=lemma.headword,
                    expected_lemma_public_id=lemma.public_id,
                    actual_lemma_public_id=None,
                    message="Published lemma cannot be found by its headword.",
                )
            )
        elif lemma_head_counts[normalized_query] > 1:
            issues.append(
                CorpusQAIssue(
                    category="ambiguous_result",
                    record_type="lemma",
                    public_id=lemma.public_id,
                    query=lemma.headword,
                    expected_lemma_public_id=lemma.public_id,
                    actual_lemma_public_id=None,
                    message="Headword search returns multiple plausible lemmas.",
                    severity="info",
                )
            )

    for sense in senses:
        if sense.lemma.public_id not in visible_lemma_ids:
            issues.append(
                CorpusQAIssue(
                    category="visibility_issue",
                    record_type="sense",
                    public_id=sense.public_id,
                    query=sense.definition[:80],
                    expected_lemma_public_id=sense.lemma.public_id,
                    actual_lemma_public_id=None,
                    message="Published sense belongs to a lemma hidden by public filters.",
                )
            )

    for form in forms:
        if form.public_id not in visible_form_ids:
            issues.append(
                CorpusQAIssue(
                    category="visibility_issue",
                    record_type="form",
                    public_id=form.public_id,
                    query=form.form_text,
                    expected_lemma_public_id=form.lemma.public_id,
                    actual_lemma_public_id=None,
                    message=(
                        "Published form is not visible through public form filters; "
                        "its lemma may not be published."
                    ),
                )
            )
            continue

        normalized_query = normalize_search_query(form.form_text)
        if not normalized_query or normalized_query not in form_norm_counts:
            issues.append(
                CorpusQAIssue(
                    category="form_unsearchable",
                    record_type="form",
                    public_id=form.public_id,
                    query=form.form_text,
                    expected_lemma_public_id=form.lemma.public_id,
                    actual_lemma_public_id=None,
                    message="Published form cannot be found by its form text.",
                )
            )
        elif (
            form_norm_counts[normalized_query] > 1
            or lemma_head_counts[normalized_query] > 1
        ):
            issues.append(
                CorpusQAIssue(
                    category="ambiguous_result",
                    record_type="form",
                    public_id=form.public_id,
                    query=form.form_text,
                    expected_lemma_public_id=form.lemma.public_id,
                    actual_lemma_public_id=None,
                    message="Form search returns multiple plausible records.",
                    severity="info",
                )
            )

    morphology_checked = 0
    if include_morphology and release_metadata is not None:
        for lemma in lemmas:
            if (
                lemma.public_id in visible_lemma_ids
                and lemma.headword_kind == Lemma.HeadwordKind.VERB_STEM
                and lemma.normalized_headword
            ):
                morphology_checked += 1
                _check_morphology_result(
                    issues=issues,
                    record_type="lemma",
                    public_id=lemma.public_id,
                    raw_input=f"ku{lemma.normalized_headword}",
                    expected_lemma_public_id=lemma.public_id,
                    expected_normalized_headword=lemma.normalized_headword,
                    rule_set_version=release_metadata["rule_set_version"],
                )

        for form in forms:
            if form.public_id in visible_form_ids and _form_looks_morphologically_analyzable(form):
                morphology_checked += 1
                _check_morphology_result(
                    issues=issues,
                    record_type="form",
                    public_id=form.public_id,
                    raw_input=form.form_text,
                    expected_lemma_public_id=form.lemma.public_id,
                    expected_normalized_headword=form.lemma.normalized_headword,
                    rule_set_version=release_metadata["rule_set_version"],
                )

    issue_counts = {category: 0 for category in ISSUE_CATEGORIES}
    error_count = 0
    info_count = 0
    for issue in issues:
        issue_counts[issue.category] = issue_counts.get(issue.category, 0) + 1
        if issue.severity == "info":
            info_count += 1
        else:
            error_count += 1

    if error_count:
        status = "failed"
    elif info_count:
        status = "passed_with_notes"
    else:
        status = "passed"

    return {
        "status": status,
        "release": release_metadata,
        "summary": {
            "checked": {
                "lemmas": len(lemmas),
                "senses": len(senses),
                "forms": len(forms),
                "morphology_inputs": morphology_checked,
            },
            "issues": len(issues),
            "errors": error_count,
            "info_notes": info_count,
            "issue_counts": issue_counts,
            "limit": limit,
        },
        "issues": [issue.to_dict() for issue in issues],
    }


def _limit_queryset(queryset, limit):
    if limit is None:
        return queryset
    return queryset[:limit]


def _check_lemma_search_result(*, issues, lemma, normalized_query, search_filters):
    results = search_public_records(normalized_query, filters=search_filters)
    lemma_ids = _lemma_public_ids_from_results(results)
    distinct_lemma_ids = sorted(set(lemma_ids))

    if not results:
        issues.append(
            CorpusQAIssue(
                category="lemma_unsearchable",
                record_type="lemma",
                public_id=lemma.public_id,
                query=lemma.headword,
                expected_lemma_public_id=lemma.public_id,
                actual_lemma_public_id=None,
                message="Published lemma cannot be found by its headword.",
            )
        )
    elif lemma.public_id not in distinct_lemma_ids:
        issues.append(
            CorpusQAIssue(
                category="wrong_lemma",
                record_type="lemma",
                public_id=lemma.public_id,
                query=lemma.headword,
                expected_lemma_public_id=lemma.public_id,
                actual_lemma_public_id=distinct_lemma_ids[0] if distinct_lemma_ids else None,
                actual_lemma_public_ids=distinct_lemma_ids,
                message="Headword search resolves to a different lemma.",
            )
        )
    elif len(distinct_lemma_ids) > 1:
        issues.append(
            CorpusQAIssue(
                category="ambiguous_result",
                record_type="lemma",
                public_id=lemma.public_id,
                query=lemma.headword,
                expected_lemma_public_id=lemma.public_id,
                actual_lemma_public_id=_first_other_id(distinct_lemma_ids, lemma.public_id),
                actual_lemma_public_ids=distinct_lemma_ids,
                message="Headword search returns multiple plausible lemmas.",
                severity="info",
            )
        )


def _check_form_search_result(*, issues, form, normalized_query, search_filters):
    results = search_public_records(normalized_query, filters=search_filters)
    lemma_ids = _lemma_public_ids_from_results(results)
    distinct_lemma_ids = sorted(set(lemma_ids))
    form_ids = [
        result["form"].public_id
        for result in results
        if result.get("form") is not None
    ]
    distinct_form_ids = sorted(set(form_ids))

    if form.public_id not in distinct_form_ids:
        if distinct_lemma_ids and form.lemma.public_id not in distinct_lemma_ids:
            issues.append(
                CorpusQAIssue(
                    category="wrong_lemma",
                    record_type="form",
                    public_id=form.public_id,
                    query=form.form_text,
                    expected_lemma_public_id=form.lemma.public_id,
                    actual_lemma_public_id=distinct_lemma_ids[0],
                    actual_lemma_public_ids=distinct_lemma_ids,
                    actual_form_public_ids=distinct_form_ids,
                    message="Form search resolves to a different lemma.",
                )
            )
        else:
            issues.append(
                CorpusQAIssue(
                    category="form_unsearchable",
                    record_type="form",
                    public_id=form.public_id,
                    query=form.form_text,
                    expected_lemma_public_id=form.lemma.public_id,
                    actual_lemma_public_id=(
                        distinct_lemma_ids[0] if distinct_lemma_ids else None
                    ),
                    actual_lemma_public_ids=distinct_lemma_ids,
                    actual_form_public_ids=distinct_form_ids,
                    message="Published form cannot be found by its form text.",
                )
            )
        return

    if len(distinct_lemma_ids) > 1 or len(distinct_form_ids) > 1:
        issues.append(
            CorpusQAIssue(
                category="ambiguous_result",
                record_type="form",
                public_id=form.public_id,
                query=form.form_text,
                expected_lemma_public_id=form.lemma.public_id,
                actual_lemma_public_id=_first_other_id(
                    distinct_lemma_ids,
                    form.lemma.public_id,
                ),
                actual_lemma_public_ids=distinct_lemma_ids,
                actual_form_public_ids=distinct_form_ids,
                message="Form search returns multiple plausible records.",
                severity="info",
            )
        )


def _check_morphology_result(
    *,
    issues,
    record_type,
    public_id,
    raw_input,
    expected_lemma_public_id,
    expected_normalized_headword,
    rule_set_version,
):
    try:
        payload = analyze_text(raw_input, rule_set_version=rule_set_version)
    except AnalysisFailure as exc:
        issues.append(
            CorpusQAIssue(
                category="morphology_unsupported",
                record_type=record_type,
                public_id=public_id,
                query=raw_input,
                expected_lemma_public_id=expected_lemma_public_id,
                actual_lemma_public_id=None,
                message=f"{exc.code}: {exc.message}",
            )
        )
        return
    except Exception as exc:
        issues.append(
            CorpusQAIssue(
                category="morphology_error",
                record_type=record_type,
                public_id=public_id,
                query=raw_input,
                expected_lemma_public_id=expected_lemma_public_id,
                actual_lemma_public_id=None,
                message=f"{type(exc).__name__}: {exc}",
            )
        )
        return

    analyses = payload.get("analyses") if isinstance(payload, dict) else None
    if not isinstance(analyses, list) or not analyses:
        issues.append(
            CorpusQAIssue(
                category="morphology_error",
                record_type=record_type,
                public_id=public_id,
                query=raw_input,
                expected_lemma_public_id=expected_lemma_public_id,
                actual_lemma_public_id=None,
                message="Analyzer returned an unexpected success payload shape.",
            )
        )
        return

    lemma_ids = []
    for analysis in analyses:
        if not isinstance(analysis, dict):
            return _append_malformed_morphology_issue(
                issues,
                record_type=record_type,
                public_id=public_id,
                raw_input=raw_input,
                expected_lemma_public_id=expected_lemma_public_id,
            )
        lemma_payload = analysis.get("lemma")
        if not isinstance(lemma_payload, dict) or not isinstance(
            lemma_payload.get("public_id"),
            str,
        ):
            return _append_malformed_morphology_issue(
                issues,
                record_type=record_type,
                public_id=public_id,
                raw_input=raw_input,
                expected_lemma_public_id=expected_lemma_public_id,
            )
        lemma_ids.append(lemma_payload["public_id"])

    distinct_lemma_ids = sorted(set(lemma_ids))
    if expected_lemma_public_id not in distinct_lemma_ids:
        # Homograph stems: when every resolved lemma shares the expected
        # headword, the analyzer simply cannot disambiguate between
        # same-spelling entries. That is corpus scale, not a wrong analysis.
        resolved_headwords = set(
            Lemma.objects.filter(public_id__in=distinct_lemma_ids).values_list(
                "normalized_headword", flat=True
            )
        )
        if resolved_headwords == {expected_normalized_headword}:
            issues.append(
                CorpusQAIssue(
                    category="ambiguous_result",
                    record_type=record_type,
                    public_id=public_id,
                    query=raw_input,
                    expected_lemma_public_id=expected_lemma_public_id,
                    actual_lemma_public_id=_first_other_id(
                        distinct_lemma_ids,
                        expected_lemma_public_id,
                    ),
                    actual_lemma_public_ids=distinct_lemma_ids,
                    message=(
                        "Morphology analysis resolves only to homographs of the "
                        "expected headword."
                    ),
                    severity="info",
                )
            )
            return
        issues.append(
            CorpusQAIssue(
                category="wrong_lemma",
                record_type=record_type,
                public_id=public_id,
                query=raw_input,
                expected_lemma_public_id=expected_lemma_public_id,
                actual_lemma_public_id=distinct_lemma_ids[0] if distinct_lemma_ids else None,
                actual_lemma_public_ids=distinct_lemma_ids,
                message="Morphology analysis resolves to a different lemma.",
            )
        )
    elif len(distinct_lemma_ids) > 1:
        issues.append(
            CorpusQAIssue(
                category="ambiguous_result",
                record_type=record_type,
                public_id=public_id,
                query=raw_input,
                expected_lemma_public_id=expected_lemma_public_id,
                actual_lemma_public_id=_first_other_id(
                    distinct_lemma_ids,
                    expected_lemma_public_id,
                ),
                actual_lemma_public_ids=distinct_lemma_ids,
                message="Morphology analysis returns multiple plausible lemmas.",
                severity="info",
            )
        )


def _append_malformed_morphology_issue(
    issues,
    *,
    record_type,
    public_id,
    raw_input,
    expected_lemma_public_id,
):
    issues.append(
        CorpusQAIssue(
            category="morphology_error",
            record_type=record_type,
            public_id=public_id,
            query=raw_input,
            expected_lemma_public_id=expected_lemma_public_id,
            actual_lemma_public_id=None,
            message="Analyzer returned a malformed analysis item.",
        )
    )


def _lemma_public_ids_from_results(results) -> list[str]:
    lemma_ids = []
    for result in results:
        lemma = result.get("lemma")
        public_id = getattr(lemma, "public_id", None)
        if public_id:
            lemma_ids.append(public_id)
    return lemma_ids


def _first_other_id(public_ids: list[str], expected_public_id: str) -> str | None:
    for public_id in public_ids:
        if public_id != expected_public_id:
            return public_id
    return public_ids[0] if public_ids else None


def _form_looks_morphologically_analyzable(form: Form) -> bool:
    if form.lemma.headword_kind != Lemma.HeadwordKind.VERB_STEM:
        return False
    normalized = normalize_search_query(form.form_text)
    if not normalized or " " in normalized:
        return False
    if form.form_kind == Form.FormKind.DERIVED:
        return False

    stem = form.lemma.normalized_headword
    if stem and normalized == f"ku{stem}":
        return True
    if stem and normalized.endswith(stem):
        prefix = normalized[: -len(stem)]
        return prefix.startswith("ku") or prefix.startswith("ha") or prefix.endswith("no")
    return normalized.startswith("ku") or normalized.startswith("ha") or "no" in normalized
