import json
from io import StringIO

import pytest
from django.core.management import call_command

from shona_api.editorial.models import ReviewState
from shona_api.lexicon.models import Form, Lemma, Sense
from shona_api.morphology.services import AnalysisFailure
from shona_api.releases.models import DataRelease


@pytest.fixture
def current_release():
    return DataRelease.objects.create(
        version="2026.05.0",
        label="May 2026 release",
        rule_set_version="morphology-rules-v1",
        is_current=True,
    )


def create_published_entry(
    *,
    headword="-buda",
    headword_kind=Lemma.HeadwordKind.VERB_STEM,
    part_of_speech_code="vi",
    form_text="mbudo",
    form_kind=Form.FormKind.DERIVED,
):
    lemma = Lemma.objects.create(
        headword=headword,
        headword_kind=headword_kind,
        part_of_speech_code=part_of_speech_code,
        part_of_speech_label=part_of_speech_code,
        review_state=ReviewState.PUBLISHED,
    )
    sense = Sense.objects.create(
        lemma=lemma,
        number=1,
        definition=f"Definition for {headword}.",
        review_state=ReviewState.PUBLISHED,
    )
    form = None
    if form_text is not None:
        form = Form.objects.create(
            lemma=lemma,
            sense=sense,
            form_text=form_text,
            form_kind=form_kind,
            review_state=ReviewState.PUBLISHED,
        )
    return lemma, sense, form


def run_qa_command(**options):
    stdout = StringIO()
    call_command("qa_published_corpus", stdout=stdout, **options)
    return json.loads(stdout.getvalue())


@pytest.mark.django_db
def test_published_corpus_qa_clean_corpus_returns_zero_issues(current_release):
    create_published_entry()

    report = run_qa_command()

    assert report["status"] == "passed"
    assert report["summary"]["checked"] == {
        "lemmas": 1,
        "senses": 1,
        "forms": 1,
        "morphology_inputs": 1,
    }
    assert report["summary"]["issues"] == 0
    assert report["summary"]["errors"] == 0
    assert report["summary"]["info_notes"] == 0
    assert report["issues"] == []


@pytest.mark.django_db
def test_published_corpus_qa_categorizes_unsearchable_lemma_and_form(
    current_release,
    monkeypatch,
):
    create_published_entry()

    from shona_api.lexicon import qa as lexicon_qa

    real_normalize = lexicon_qa.normalize_search_query

    def hide_expected_records(value):
        if value in {"-buda", "mbudo"}:
            return "missing-query"
        return real_normalize(value)

    monkeypatch.setattr(lexicon_qa, "normalize_search_query", hide_expected_records)

    report = run_qa_command()

    assert report["status"] == "failed"
    categories = {issue["category"] for issue in report["issues"]}
    assert {"lemma_unsearchable", "form_unsearchable"} <= categories
    assert all(issue["severity"] == "error" for issue in report["issues"])


@pytest.mark.django_db
def test_published_corpus_qa_categorizes_ambiguous_headword_search(current_release):
    first, *_ = create_published_entry(
        headword="imba",
        headword_kind=Lemma.HeadwordKind.WORD,
        part_of_speech_code="n",
        form_text=None,
    )
    second, *_ = create_published_entry(
        headword="imba",
        headword_kind=Lemma.HeadwordKind.WORD,
        part_of_speech_code="n",
        form_text=None,
    )

    report = run_qa_command()

    ambiguous = [
        issue for issue in report["issues"] if issue["category"] == "ambiguous_result"
    ]
    assert {issue["public_id"] for issue in ambiguous} == {
        first.public_id,
        second.public_id,
    }
    assert all(issue["record_type"] == "lemma" for issue in ambiguous)
    assert all(issue["severity"] == "info" for issue in ambiguous)
    assert report["status"] == "passed_with_notes"
    assert report["summary"]["errors"] == 0
    assert report["summary"]["info_notes"] == len(ambiguous)


@pytest.mark.django_db
def test_published_corpus_qa_categorizes_morphology_unsupported(
    current_release,
    monkeypatch,
):
    lemma, *_ = create_published_entry()

    def unsupported(raw_text, *, rule_set_version):
        raise AnalysisFailure(
            code="ANALYSIS_UNSUPPORTED",
            message="No supported analysis matched.",
        )

    monkeypatch.setattr("shona_api.lexicon.qa.analyze_text", unsupported)

    report = run_qa_command()

    assert report["issues"] == [
        {
            "category": "morphology_unsupported",
            "record_type": "lemma",
            "public_id": lemma.public_id,
            "query": "kubuda",
            "expected_lemma_public_id": lemma.public_id,
            "actual_lemma_public_id": None,
            "message": "ANALYSIS_UNSUPPORTED: No supported analysis matched.",
            "severity": "error",
        }
    ]


@pytest.mark.django_db
def test_published_corpus_qa_categorizes_morphology_error(
    current_release,
    monkeypatch,
):
    lemma, *_ = create_published_entry()

    def broken(raw_text, *, rule_set_version):
        raise RuntimeError("boom")

    monkeypatch.setattr("shona_api.lexicon.qa.analyze_text", broken)

    report = run_qa_command()

    assert report["issues"] == [
        {
            "category": "morphology_error",
            "record_type": "lemma",
            "public_id": lemma.public_id,
            "query": "kubuda",
            "expected_lemma_public_id": lemma.public_id,
            "actual_lemma_public_id": None,
            "message": "RuntimeError: boom",
            "severity": "error",
        }
    ]


@pytest.mark.django_db
def test_published_corpus_qa_skip_morphology_bypasses_analysis_replays(
    current_release,
    monkeypatch,
):
    lemma, *_ = create_published_entry()

    def broken(raw_text, *, rule_set_version):
        raise RuntimeError("morphology must not run")

    monkeypatch.setattr("shona_api.lexicon.qa.analyze_text", broken)

    report = run_qa_command(skip_morphology=True)

    assert report["status"] == "passed"
    assert report["summary"]["checked"]["morphology_inputs"] == 0
    assert report["issues"] == []


@pytest.mark.django_db
def test_published_corpus_qa_homograph_resolution_is_info_not_error(
    current_release,
    monkeypatch,
):
    lemma, *_ = create_published_entry(headword="-buda", form_text=None)
    homograph, *_ = create_published_entry(
        headword="buda",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        form_text=None,
    )
    assert homograph.normalized_headword == lemma.normalized_headword

    def resolve_to_homograph(raw_text, *, rule_set_version):
        return {
            "analyses": [
                {"lemma": {"public_id": homograph.public_id}},
            ]
        }

    monkeypatch.setattr(
        "shona_api.lexicon.qa.analyze_text", resolve_to_homograph
    )

    report = run_qa_command()

    categories = {issue["category"] for issue in report["issues"]}
    assert "wrong_lemma" not in categories
    homograph_issues = [
        issue
        for issue in report["issues"]
        if issue["category"] == "ambiguous_result"
        and issue["record_type"] == "lemma"
    ]
    assert homograph_issues
    assert all(issue["severity"] == "info" for issue in homograph_issues)
    assert report["status"] == "passed_with_notes"


@pytest.mark.django_db
def test_published_corpus_qa_different_stem_resolution_is_error(
    current_release,
    monkeypatch,
):
    lemma, *_ = create_published_entry(headword="-buda", form_text=None)
    other, *_ = create_published_entry(
        headword="-bona",
        form_text=None,
    )

    def resolve_to_other(raw_text, *, rule_set_version):
        return {
            "analyses": [
                {"lemma": {"public_id": other.public_id}},
            ]
        }

    monkeypatch.setattr("shona_api.lexicon.qa.analyze_text", resolve_to_other)

    report = run_qa_command()

    wrong = [
        issue for issue in report["issues"] if issue["category"] == "wrong_lemma"
    ]
    assert wrong
    assert all(issue["severity"] == "error" for issue in wrong)
    assert report["status"] == "failed"
