"""Durable gate for the source-backed morphology evaluation (repaired edition).

- Corpus gate: frozen corpus (hash-verified, schema-validated) scores clean.
- Contract parity: finite a|a deferral never surfaces as matched morphology.
- False-pass reproductions (supervisor findings 1-6): each demonstrated
  false pass now fails through the repaired evaluator.
- Builder integrity: tampered hash, unknown keys, empty scored cases, and
  non-determinism are rejected; identical inputs rebuild identically.
- Isolation: the eval settings module ignores DATABASE_URL (subprocess proof
  that never touches a real database).
"""

import copy
import json
import os
import subprocess
import sys
import pytest
from pathlib import Path
from django.core.cache import caches

from tools.build_source_backed_corpus import (
    CorpusError,
    build_corpus,
    validate_corpus,
    verify_hash,
)
from tools.evaluate_source_backed import (
    compute_metrics,
    create_fixtures,
    evaluate,
    evaluate_case,
    match_reading,
    match_value,
    write_report,
)

CORPUS_PATH = (
    Path(__file__).parent.parent / "evaluation" / "source_backed" / "v1" / "corpus.json"
)
PARTS_DIR = Path(__file__).parent.parent / "evaluation" / "source_backed" / "v1"


@pytest.fixture(autouse=True)
def eval_gate_settings(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "source-backed-eval-gate",
        }
    }
    caches["default"].clear()


def load_verified_corpus():
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    verify_hash(corpus)
    validate_corpus(corpus)
    return corpus


def case_by_id(corpus, case_id):
    for case in corpus["cases"]:
        if case["case_id"] == case_id:
            return copy.deepcopy(case)
    raise AssertionError(f"case {case_id} missing from corpus")


# --- Full corpus gate --------------------------------------------------------


@pytest.mark.django_db
def test_source_backed_corpus_scores_clean(client, tmp_path):
    corpus = load_verified_corpus()
    raw_key, lemma_ids = create_fixtures(corpus)
    out = evaluate(client, raw_key, corpus, lemma_ids)
    failed = [r for r in out["results"] if r["status"] == "fail"]
    assert not failed, f"{len(failed)} scored case(s) failed: " + "; ".join(
        f"{r['case_id']}: {'; '.join(r['failures'])[:200]}" for r in failed[:10]
    )
    metrics = compute_metrics(corpus, out)
    assert metrics["overall"]["not_evaluated"], (
        "evidence-only cases must be reported, not pass"
    )
    for cid in metrics["overall"]["not_evaluated"]:
        assert not next(c for c in corpus["cases"] if c["case_id"] == cid)["scored"]
    ling, cont = metrics["linguistic"], metrics["contract"]
    assert ling["generation_correct"][1] > 0 and cont["generation_correct"][1] > 0
    assert ling["required_recall"][1] > 0 and cont["required_recall"][1] > 0
    assert ling["agreement_gen_analyze"][1] > 0
    report = write_report(corpus, out, metrics, "test-rev", True, "test-eval", tmp_path)
    text = Path(report).read_text(encoding="utf-8")
    for needle in (
        "correct generation among scored supported requests",
        "required-analysis recall",
        "explicitly prohibited readings produced",
        "unadjudicated extra analyses",
        "refusals of declared supported requests",
        "correct deferred/invalid-request handling",
        "generation-to-analysis agreement",
        "analysis-to-search agreement",
        "not evaluated (evidence-only",
    ):
        assert needle in text, f"report omits promised metric: {needle}"
    assert "100%" not in text and "accuracy" not in text.lower().replace(
        "required-analysis recall", ""
    )


@pytest.mark.django_db
def test_finite_boundary_search_never_matched(client):
    corpus = load_verified_corpus()
    raw_key, _ = create_fixtures(corpus)
    response = client.get(
        "/v1/search",
        {"q": "vanovambura"},
        HTTP_AUTHORIZATION=f"Api-Key {raw_key}",
    )
    assert response.status_code == 200, response.content
    body = response.json()["data"]
    assert "morphology" not in body
    if body["count"] == 0:
        enrichment = body["zero_result"]["morphology_enrichment"]
        assert enrichment["status"] == "unsupported"
        assert any(
            lane["code"] == "deferred_finite_boundary"
            for lane in enrichment["detail"]["future_lanes"]
        )
    else:
        assert "morphology_enrichment" not in body


# --- False-pass reproductions -------------------------------------------------
WRONG_POLARITY_NEUTER = {
    "analysis_type": "infinitive",
    "rule_id": "fortune.verbal.infinitive.001",
    "lemma": {"public_id": "lemma_ziva", "headword": "-ziva"},
    "slots": {
        "polarity": {"value": "negative"},
        "verb_stem": {"surface": "zivika"},
        "extensions": [],
    },
}

RIGHT_NEUTER = {
    "analysis_type": "infinitive",
    "rule_id": "fortune.verbal.infinitive.001",
    "lemma": {"public_id": "lemma_ziva", "headword": "-ziva"},
    "slots": {
        "subject": None,
        "tense_aspect": None,
        "polarity": {"value": "positive"},
        "object": None,
        "reflexive": None,
        "verb_stem": {"surface": "zivika"},
        "extensions": [{"surface": "ik", "type": "neuter"}],
    },
}


def _stub_response(status_code, payload):
    class StubResponse:
        def __init__(self):
            self.status_code = status_code
            self.content = json.dumps(payload).encode("utf-8")

        def json(self):
            return payload

    return StubResponse()


class _StubClient:
    def __init__(self, post=None, get=None):
        self._post = post or {}
        self._get = get or {}

    def post(self, path, *args, **kwargs):
        return self._post[path]

    def get(self, path, *args, **kwargs):
        return self._get[path]


class _CallbackClient:
    """Routes analyze calls by requested text (for generated-vs-fixed tests)."""

    def __init__(self, generate_response, analyze_by_text, get=None):
        self._generate_response = generate_response
        self._analyze_by_text = analyze_by_text
        self._get = get or {}

    def post(self, path, payload, *args, **kwargs):
        if path == "/v1/generate":
            return self._generate_response
        assert path == "/v1/analyze"
        return self._analyze_by_text[payload["text"]]

    def get(self, path, *args, **kwargs):
        return self._get[path]


def _lemma_ids():
    return {
        "ziva": "lemma_ziva",
        "isa": "lemma_isa",
        "taura": "lemma_taura",
        "ti": "lemma_ti",
    }


def test_false_pass_1_wrong_polarity_and_missing_extension_now_fails():
    """Supervisor probe 1: lemma/rule-only matching let a wrong-polarity,
    extension-less kuzivika reading pass. The repaired SRC-046 rejects it."""
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    case = case_by_id(corpus, "SRC-046")
    case["flows"] = ["analyze"]
    case.pop("round_trip", None)
    wrong = _stub_response(200, {"data": {"analyses": [WRONG_POLARITY_NEUTER]}})
    result = evaluate_case(
        _StubClient(post={"/v1/analyze": wrong}), "k", case, _lemma_ids()
    )
    assert result["status"] == "fail"
    assert any(
        c["name"].startswith("analyze_required") and not c["passed"]
        for c in result["checks"]
    )
    right = _stub_response(200, {"data": {"analyses": [RIGHT_NEUTER]}})
    ok_case = copy.deepcopy(case)
    ok_case.pop("round_trip", None)
    ok_case["flows"] = ["analyze"]
    result = evaluate_case(
        _StubClient(post={"/v1/analyze": right}), "k", ok_case, _lemma_ids()
    )
    assert result["status"] == "pass", result["checks"]


def test_false_pass_1b_missing_neuter_extension_fails():
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    case = case_by_id(corpus, "SRC-046")
    case["flows"] = ["analyze"]
    case.pop("round_trip", None)
    reading = copy.deepcopy(RIGHT_NEUTER)
    reading["slots"]["extensions"] = []
    stub = _stub_response(200, {"data": {"analyses": [reading]}})
    result = evaluate_case(
        _StubClient(post={"/v1/analyze": stub}), "k", case, _lemma_ids()
    )
    assert result["status"] == "fail"


def test_false_pass_1c_wrong_extension_classification_fails():
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    case = case_by_id(corpus, "SRC-046")
    case["flows"] = ["analyze"]
    case.pop("round_trip", None)
    reading = copy.deepcopy(RIGHT_NEUTER)
    reading["slots"]["extensions"] = [{"surface": "ik", "type": "causative"}]
    stub = _stub_response(200, {"data": {"analyses": [reading]}})
    result = evaluate_case(
        _StubClient(post={"/v1/analyze": stub}), "k", case, _lemma_ids()
    )
    assert result["status"] == "fail"


def test_false_pass_2_exhaustive_extra_reading_now_fails():
    """Supervisor probe 2: an unrelated imperative analysis on exhaustive kuti
    reported zero extras. Unmatched readings are now counted and rejected."""
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    case = case_by_id(corpus, "SRC-057")
    case["flows"] = ["analyze"]
    case.pop("round_trip", None)
    kuti = {
        "analysis_type": "infinitive",
        "lemma": {"public_id": "lemma_ti"},
        "slots": {
            "subject": None,
            "tense_aspect": None,
            "polarity": {"value": "positive"},
            "object": None,
            "reflexive": None,
            "verb_stem": {"surface": "ti"},
            "extensions": [],
        },
    }
    stray = {
        "analysis_type": "imperative",
        "lemma": {"public_id": "lemma_ti"},
        "slots": {},
    }
    stub = _stub_response(200, {"data": {"analyses": [kuti, stray]}})
    result = evaluate_case(
        _StubClient(post={"/v1/analyze": stub}), "k", case, _lemma_ids()
    )
    assert result["status"] == "fail"
    assert any(
        c["name"] == "analyze_exhaustive" and not c["passed"] for c in result["checks"]
    )


def test_false_pass_3_generated_form_rejection_not_hidden():
    """Supervisor probe 3: the runner analyzed the fixed corpus input instead
    of the generated form. A generated form that analyzes as 422 must fail."""
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    case = case_by_id(corpus, "SRC-038")
    generate = _stub_response(
        200,
        {
            "data": {
                "generated": {
                    "form": "usariise",
                    "rule_id": "fortune.verbal.imperative.negative.001",
                }
            }
        },
    )
    fixed_ok = _stub_response(
        200,
        {
            "data": {
                "analyses": [
                    {
                        "analysis_type": "imperative",
                        "lemma": {"public_id": "lemma_isa"},
                        "slots": {"verb_stem": {"surface": "isa"}},
                    }
                ]
            }
        },
    )
    generated_rejected = _stub_response(
        422, {"error": {"code": "ANALYSIS_UNSUPPORTED"}}
    )
    client = _CallbackClient(
        generate,
        {"usariisa": fixed_ok, "usariise": generated_rejected},
    )
    result = evaluate_case(client, "k", case, _lemma_ids())
    # The fixed-input analysis is accepted (status 200) while the generated
    # form's rejection fails the round trip: the checks are separated, so a
    # fixed-input success can no longer hide a generated-form rejection.
    assert any(c["name"] == "analyze_status" and c["passed"] for c in result["checks"])


def test_false_pass_search_wrong_lemma_or_reading_fails():
    """Supervisor probe 3b: search 'matched' with the wrong lemma/reading, and
    an excluded reading exposed only through search, must both fail."""
    wrong_lemma = {
        "analysis_type": "infinitive",
        "rule_id": "fortune.verbal.infinitive.001",
        "lemma": {"public_id": "lemma_WRONG", "headword": "-wrong"},
        "slots": {"polarity": {"value": "positive"}},
    }
    payload = {
        "data": {
            "results": [],
            "morphology": {"analyses": [wrong_lemma]},
            "morphology_enrichment": {"status": "matched"},
        }
    }
    case = {
        "case_id": "SELF-SEARCH-01",
        "scored": True,
        "flows": ["search"],
        "search": {
            "q": "kuzviziva",
            "expected_status": 200,
            "expected_enrichment_status": "matched",
            "required_readings": [
                {
                    "analysis_type": "infinitive",
                    "lemma": {"lemma_key": "ziva"},
                    "slots": {"reflexive": {"value": True}},
                }
            ],
        },
    }
    result = evaluate_case(
        _StubClient(get={"/v1/search": _stub_response(200, payload)}),
        "k",
        case,
        _lemma_ids(),
    )
    assert result["status"] == "fail"
    assert any(
        c["name"].startswith("search_morphology_required") and not c["passed"]
        for c in result["checks"]
    )

    excluded = {
        "analysis_type": "verb_form",
        "lemma": {"public_id": "lemma_taura"},
        "slots": {},
    }
    payload2 = {"data": {"results": [], "morphology": {"analyses": [excluded]}}}
    case2 = {
        "case_id": "SELF-SEARCH-02",
        "scored": True,
        "flows": ["search"],
        "search": {
            "q": "ndinotauridza",
            "expected_status": 200,
            "prohibited_readings": [
                {"analysis_type": "verb_form", "lemma": {"lemma_key": "taura"}}
            ],
        },
    }
    result2 = evaluate_case(
        _StubClient(get={"/v1/search": _stub_response(200, payload2)}),
        "k",
        case2,
        _lemma_ids(),
    )
    assert result2["status"] == "fail"
    assert any(
        c["name"].startswith("search_morphology_prohibited") and not c["passed"]
        for c in result2["checks"]
    )


def test_report_metrics_have_explicit_denominators():
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    metrics = compute_metrics(
        corpus,
        {
            "results": [
                {
                    "case_id": c["case_id"],
                    "status": "not_evaluated" if not c.get("flows") else "pass",
                    "checks": [],
                    "scored": c.get("scored", True),
                    "calls": 1 if c.get("flows") else 0,
                }
                for c in corpus["cases"]
            ]
        },
    )
    assert metrics["overall"]["not_evaluated"]
    for cid in metrics["overall"]["not_evaluated"]:
        assert not next(c for c in corpus["cases"] if c["case_id"] == cid)["scored"]
    assert metrics["overall"]["unresolved_evidence"] == ["SRC-059", "SRC-062"]
    for bucket in ("linguistic", "contract"):
        for key in (
            "generation_correct",
            "required_recall",
            "deferred_invalid_ok",
            "agreement_gen_analyze",
            "agreement_analyze_search",
        ):
            num, denom = metrics[bucket][key]
            assert isinstance(num, int) and isinstance(denom, int)


# --- Matching semantics -------------------------------------------------------


def test_match_distinguishes_missing_null_and_empty_list():
    ok, _ = match_value({"a": None}, {"a": None}, "s")
    assert ok
    ok, detail = match_value({}, {"a": None}, "s")
    assert not ok and "missing" in detail
    ok, _ = match_value({"e": []}, {"e": []}, "s")
    assert ok
    ok, detail = match_value({"e": None}, {"e": []}, "s")
    assert not ok and "list" in detail
    ok, detail = match_value(
        {"e": [{"type": "neuter"}, {"type": "x"}]}, {"e": [{"type": "neuter"}]}, "s"
    )
    assert not ok and "1 item(s), got 2" in detail


def test_match_rejects_unknown_expectation_keys():
    ok, detail = match_reading(
        {"analysis_type": "infinitive"}, {"analysis_type": "infinitive", "bogus": 1}
    )
    assert not ok and "unknown expectation key" in detail


def test_match_extension_order_is_significant():
    actual = {"extensions": [{"type": "reciprocal"}, {"type": "applicative"}]}
    ok, _ = match_value(
        actual, {"extensions": [{"type": "applicative"}, {"type": "reciprocal"}]}, "s"
    )
    assert not ok


# --- Corpus integrity ----------------------------------------------------------


def test_corpus_hash_rejects_tampered_contents(tmp_path):
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(corpus)
    tampered["cases"][0]["analyze"]["text"] = "tampered-surface"
    with pytest.raises(CorpusError, match="hash mismatch"):
        verify_hash(tampered)


def test_corpus_schema_rejects_unknown_assertion_keys():
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    bad = copy.deepcopy(corpus)
    bad["cases"][0]["analyze"]["future_magic"] = True
    with pytest.raises(CorpusError, match="unknown analyze expectation key"):
        validate_corpus(bad)


def test_corpus_schema_rejects_empty_scored_case():
    bad = {
        "version": "x",
        "fixtures": {"noun_classes": [], "lemmas": []},
        "cases": [
            {
                "case_id": "SRC-999",
                "category": "FIN-POS",
                "evidence_class": "source_attested",
                "review_status": "proposed",
                "scored": True,
                "flows": ["analyze"],
                "analyze": {
                    "text": "x",
                    "expected_status": 200,
                    "exhaustive": True,
                    "required_readings": [],
                },
            }
        ],
    }
    with pytest.raises(CorpusError, match="at least one required reading"):
        validate_corpus(bad)


def test_corpus_schema_rejects_scored_cases_without_flows():
    bad = {
        "version": "x",
        "fixtures": {"noun_classes": [], "lemmas": []},
        "cases": [
            {
                "case_id": "SRC-999",
                "category": "FIN-POS",
                "evidence_class": "source_attested",
                "review_status": "proposed",
                "scored": True,
                "flows": [],
            }
        ],
    }
    with pytest.raises(CorpusError, match="no flows"):
        validate_corpus(bad)


def test_corpus_build_is_deterministic(tmp_path):
    first, first_bytes = build_corpus(PARTS_DIR)
    second, second_bytes = build_corpus(PARTS_DIR)
    assert first_bytes == second_bytes
    assert first["hash"] == second["hash"] and first["hash"].startswith("sha256:")
    assert len(first["hash"]) == len("sha256:") + 64
    out = tmp_path / "corpus.json"
    out.write_bytes(first_bytes)
    rebuilt = json.loads(out.read_text(encoding="utf-8"))
    verify_hash(rebuilt)
    validate_corpus(rebuilt)


def test_eval_settings_ignore_database_url():
    """Supervisor probe 6 (isolation): with DATABASE_URL aimed at a decoy file
    and EVAL_DB_PATH at an isolated file, the eval settings must resolve to
    the isolated file — and the decoy must never be created. No real database
    is touched: the decoy lives in tmp_path."""
    decoy = Path(str(__import__("tempfile").mkdtemp())) / "decoy.sqlite3"
    target_dir = Path(str(__import__("tempfile").mkdtemp()))
    target = target_dir / "eval.sqlite3"
    code = (
        "import os;"
        "os.environ['DJANGO_SETTINGS_MODULE']='config.settings.eval';"
        f"os.environ['EVAL_DB_PATH']={str(target.as_posix())!r};"
        "import django; django.setup();"
        "from django.db import connections;"
        "print(connections['default'].settings_dict['NAME'])"
    )
    env = dict(os.environ, DATABASE_URL=f"sqlite:///{decoy}")
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert proc.stdout.strip() == target.as_posix()
    assert not decoy.exists(), "isolation failure: decoy database file was created"


# --- Fix 1: response-independent denominators ----------------------------------


def _metric_case(case_id, required=1):
    return {
        "case_id": case_id,
        "category": "T",
        "scored": True,
        "flows": ["analyze"],
        "analyze": {
            "text": f"text-{case_id}",
            "expected_status": 200,
            "exhaustive": False,
            "required_readings": [
                {
                    "analysis_type": "infinitive",
                    "slots": {"polarity": {"value": "positive"}},
                }
            ][:required]
            if required
            else [],
        },
    }


def _metric_deferred(case_id="CT-REF-99"):
    return {
        "case_id": case_id,
        "category": "T",
        "scored": True,
        "flows": ["analyze"],
        "analyze": {
            "text": "bad",
            "expected_status": 422,
            "expected_code": "ANALYSIS_UNSUPPORTED",
        },
    }


_METRIC_GOOD = {
    "analysis_type": "infinitive",
    "slots": {"polarity": {"value": "positive"}},
}


def test_metrics_unexpected_422_counts_missing_as_unrecovered():
    """Fix 1 repro: one 200-correct + one 422 on supported analyze requests
    plus one correctly refused deferred request must report required_recall
    [1, 2] (not [1, 1]) and supported_refusals [1, 2] (not [1, 3])."""
    c1, c2, c3 = (
        _metric_case("CT-REF-01"),
        _metric_case("CT-REF-02"),
        _metric_deferred(),
    )
    r1 = evaluate_case(
        _StubClient(
            post={
                "/v1/analyze": _stub_response(
                    200, {"data": {"analyses": [_METRIC_GOOD]}}
                )
            }
        ),
        "k",
        c1,
        _lemma_ids(),
    )
    r2 = evaluate_case(
        _StubClient(
            post={"/v1/analyze": _stub_response(422, {"error": {"code": "X"}})}
        ),
        "k",
        c2,
        _lemma_ids(),
    )
    r3 = evaluate_case(
        _StubClient(
            post={
                "/v1/analyze": _stub_response(
                    422, {"error": {"code": "ANALYSIS_UNSUPPORTED"}}
                )
            }
        ),
        "k",
        c3,
        _lemma_ids(),
    )
    assert r1["status"] == "pass"
    assert r2["status"] == "fail"
    assert r3["status"] == "pass"
    metrics = compute_metrics(
        {"version": "t", "fixtures": {}, "cases": [c1, c2, c3]},
        {"results": [r1, r2, r3]},
    )
    assert metrics["contract"]["required_recall"] == [1, 2]
    assert metrics["contract"]["supported_refusals"] == [1, 2]


def test_metrics_success_reports_full_recall_and_no_refusal():
    c1, c2 = _metric_case("CT-REF-11"), _metric_case("CT-REF-12")
    stub = _stub_response(200, {"data": {"analyses": [_METRIC_GOOD]}})
    r1 = evaluate_case(_StubClient(post={"/v1/analyze": stub}), "k", c1, _lemma_ids())
    r2 = evaluate_case(_StubClient(post={"/v1/analyze": stub}), "k", c2, _lemma_ids())
    metrics = compute_metrics(
        {"version": "t", "fixtures": {}, "cases": [c1, c2]},
        {"results": [r1, r2]},
    )
    assert metrics["contract"]["required_recall"] == [2, 2]
    assert metrics["contract"]["supported_refusals"] == [0, 2]


def test_metrics_unexpected_500_not_a_refusal_but_unrecovered():
    """5xx stays in every denominator but never counts as an HTTP refusal."""
    c1, c2 = _metric_case("CT-REF-21"), _metric_case("CT-REF-22")
    ok = _stub_response(200, {"data": {"analyses": [_METRIC_GOOD]}})
    bad = _stub_response(500, {"error": {"code": "INTERNAL"}})
    r1 = evaluate_case(_StubClient(post={"/v1/analyze": ok}), "k", c1, _lemma_ids())
    r2 = evaluate_case(_StubClient(post={"/v1/analyze": bad}), "k", c2, _lemma_ids())
    assert r2["status"] == "fail"
    metrics = compute_metrics(
        {"version": "t", "fixtures": {}, "cases": [c1, c2]},
        {"results": [r1, r2]},
    )
    assert metrics["contract"]["required_recall"] == [1, 2]
    assert metrics["contract"]["supported_refusals"] == [0, 2]


def test_metrics_malformed_body_counts_as_unrecovered_not_refused():
    c1, c2 = _metric_case("CT-REF-31"), _metric_case("CT-REF-32")

    class _BadBody:
        status_code = 200
        content = b"not-json"

        def json(self):
            raise ValueError("bad")

    r1 = evaluate_case(
        _StubClient(
            post={
                "/v1/analyze": _stub_response(
                    200, {"data": {"analyses": [_METRIC_GOOD]}}
                )
            }
        ),
        "k",
        c1,
        _lemma_ids(),
    )
    r2 = evaluate_case(
        _StubClient(post={"/v1/analyze": _BadBody()}), "k", c2, _lemma_ids()
    )
    assert any(c["name"] == "analyze_body" and not c["passed"] for c in r2["checks"])
    metrics = compute_metrics(
        {"version": "t", "fixtures": {}, "cases": [c1, c2]},
        {"results": [r1, r2]},
    )
    assert metrics["contract"]["required_recall"] == [1, 2]
    assert metrics["contract"]["supported_refusals"] == [0, 2]


def test_metrics_search_empty_does_not_add_extra_reading():
    """Missing search enrichment emits a diagnostic, not an extra denominator."""
    case = {
        "case_id": "CT-REF-41",
        "category": "S",
        "scored": True,
        "flows": ["search"],
        "search": {
            "q": "kX",
            "expected_status": 200,
            "expected_enrichment_status": "matched",
            "required_readings": [
                {
                    "analysis_type": "infinitive",
                    "slots": {"polarity": {"value": "positive"}},
                }
            ],
        },
    }
    payload = {
        "data": {
            "results": [],
            "morphology": {"analyses": []},
            "morphology_enrichment": {"status": "matched"},
        }
    }
    result = evaluate_case(
        _StubClient(get={"/v1/search": _stub_response(200, payload)}),
        "k",
        case,
        _lemma_ids(),
    )
    assert result["status"] == "fail"
    assert not any(
        c["name"] == "search_morphology_required:*" for c in result["checks"]
    ), "aggregate must not masquerade as a reading check"
    metrics = compute_metrics(
        {"version": "t", "fixtures": {}, "cases": [case]}, {"results": [result]}
    )
    assert metrics["contract"]["required_recall"] == [0, 1]


def test_metrics_mixed_supported_deferred_flows():
    """A generate-422 + analyze-200 case contributes one deferred request and
    one supported request (and one reading) independently."""

    def _mixed_case():
        return {
            "case_id": "CT-REF-51",
            "category": "M",
            "scored": True,
            "flows": ["generate", "analyze"],
            "generate": {
                "features": {},
                "expected_status": 422,
                "expected_code": "GENERATION_UNSUPPORTED",
            },
            "analyze": {
                "text": "kuti",
                "expected_status": 200,
                "exhaustive": False,
                "required_readings": [{"analysis_type": "infinitive"}],
            },
        }

    class _BothOk:
        def post(self, path, payload, *args, **kwargs):
            if path == "/v1/generate":
                return _stub_response(
                    422, {"error": {"code": "GENERATION_UNSUPPORTED"}}
                )
            return _stub_response(
                200, {"data": {"analyses": [{"analysis_type": "infinitive"}]}}
            )

        def get(self, path, *args, **kwargs):
            raise AssertionError("no search in fixture")

    class _AnalyzeRefused:
        def post(self, path, payload, *args, **kwargs):
            if path == "/v1/generate":
                return _stub_response(
                    422, {"error": {"code": "GENERATION_UNSUPPORTED"}}
                )
            return _stub_response(422, {"error": {"code": "ANALYSIS_UNSUPPORTED"}})

        def get(self, path, *args, **kwargs):
            raise AssertionError("no search in fixture")

    ok_result = evaluate_case(_BothOk(), "k", _mixed_case(), _lemma_ids())
    assert ok_result["status"] == "pass"
    ok_metrics = compute_metrics(
        {"version": "t", "fixtures": {}, "cases": [_mixed_case()]},
        {"results": [ok_result]},
    )
    assert ok_metrics["contract"]["required_recall"] == [1, 1]
    assert ok_metrics["contract"]["supported_refusals"] == [0, 1]
    assert ok_metrics["contract"]["deferred_invalid_ok"] == [1, 1]

    refused_result = evaluate_case(_AnalyzeRefused(), "k", _mixed_case(), _lemma_ids())
    assert refused_result["status"] == "fail"
    refused_metrics = compute_metrics(
        {"version": "t", "fixtures": {}, "cases": [_mixed_case()]},
        {"results": [refused_result]},
    )
    assert refused_metrics["contract"]["required_recall"] == [0, 1]
    assert refused_metrics["contract"]["supported_refusals"] == [1, 1]
    assert refused_metrics["contract"]["deferred_invalid_ok"] == [1, 1]


def test_metrics_generation_unreadable_not_correct():
    """A supported generate returning 200 with an unreadable body is not correct."""
    case = {
        "case_id": "CT-REF-61",
        "category": "G",
        "scored": True,
        "flows": ["generate"],
        "generate": {
            "lemma_key": "ziva",
            "features": {},
            "expected_status": 200,
            "expected_surface": "x",
        },
    }

    class _BadGen:
        status_code = 200
        content = b"not-json"

        def json(self):
            raise ValueError("bad")

    result = evaluate_case(
        _StubClient(post={"/v1/generate": _BadGen()}), "k", case, _lemma_ids()
    )
    assert result["status"] == "fail"
    metrics = compute_metrics(
        {"version": "t", "fixtures": {}, "cases": [case]}, {"results": [result]}
    )
    assert metrics["contract"]["generation_correct"] == [0, 1]


# --- Fix 2: malformed nested expectations rejected -----------------------------


def _nested_bad_corpus(
    case_id, readings_patch, flow="analyze", list_key="prohibited_readings"
):
    analyze = {
        "text": "kux",
        "expected_status": 200,
        "exhaustive": False,
        "required_readings": [{"analysis_type": "infinitive"}],
        "prohibited_readings": [],
        "also_allowed": [],
    }
    analyze[list_key] = readings_patch
    return {
        "version": "v",
        "fixtures": {"noun_classes": [], "lemmas": []},
        "cases": [
            {
                "case_id": case_id,
                "category": "T",
                "evidence_class": "source_attested",
                "review_status": "proposed",
                "scored": True,
                "flows": [flow],
                flow: analyze
                if flow == "analyze"
                else {
                    "q": "kux",
                    "expected_status": 200,
                    "required_readings": [{"analysis_type": "infinitive"}],
                    list_key
                    if list_key != "prohibited_readings"
                    else "prohibited_readings": readings_patch,
                },
            }
        ],
    }


def test_corpus_rejects_nested_slot_typo_in_prohibited():
    """Fix 2 repro: misspelled 'polairty' in a prohibited pattern must be
    rejected with a corpus locator, not accepted as a silent non-match."""
    bad = _nested_bad_corpus(
        "SRC-991", [{"slots": {"polairty": {"value": "negative"}}}]
    )
    with pytest.raises(CorpusError, match="SRC-991.*polairty"):
        validate_corpus(bad)


def test_corpus_rejects_nested_slot_typo_in_allowed():
    bad = _nested_bad_corpus(
        "SRC-992",
        [{"slots": {"polairty": {"value": "negative"}}}],
        list_key="also_allowed",
    )
    with pytest.raises(CorpusError, match="SRC-992.*polairty"):
        validate_corpus(bad)


def test_corpus_rejects_nested_field_typo():
    bad = _nested_bad_corpus("SRC-993", [{"slots": {"polarity": {"valu": "negative"}}}])
    with pytest.raises(CorpusError, match="SRC-993.*valu"):
        validate_corpus(bad)


def test_corpus_rejects_malformed_extension_entries():
    with pytest.raises(CorpusError, match="SRC-994.*typ"):
        validate_corpus(
            _nested_bad_corpus(
                "SRC-994", [{"slots": {"extensions": [{"typ": "neuter"}]}}]
            )
        )
    with pytest.raises(CorpusError, match="SRC-995.*extension entry must be an object"):
        validate_corpus(
            _nested_bad_corpus("SRC-995", [{"slots": {"extensions": ["neuter"]}}])
        )
    with pytest.raises(CorpusError, match="SRC-996.*extensions must be a list"):
        validate_corpus(
            _nested_bad_corpus(
                "SRC-996", [{"slots": {"extensions": {"type": "neuter"}}}]
            )
        )
    with pytest.raises(CorpusError, match="SRC-997"):
        validate_corpus(
            _nested_bad_corpus("SRC-997", [{"slots": {"polarity": ["negative"]}}])
        )


def test_corpus_accepts_legitimate_partial_null_list():
    """Partial maps, explicit null, empty and ordered extension lists stay valid."""
    good = {
        "version": "v",
        "fixtures": {"noun_classes": [], "lemmas": []},
        "cases": [
            {
                "case_id": "SRC-998",
                "category": "T",
                "evidence_class": "source_attested",
                "review_status": "proposed",
                "scored": True,
                "flows": ["analyze"],
                "analyze": {
                    "text": "kux",
                    "expected_status": 200,
                    "exhaustive": False,
                    "required_readings": [
                        {
                            "analysis_type": "infinitive",
                            "slots": {
                                "polarity": {"value": "positive"},
                                "subject": None,
                                "object": None,
                                "reflexive": None,
                                "tense_aspect": None,
                                "verb_stem": {"surface": "ziva"},
                                "extensions": [],
                            },
                        },
                        {
                            "analysis_type": "infinitive",
                            "slots": {
                                "verb_stem": {"surface": "zivika"},
                                "extensions": [{"type": "neuter"}],
                            },
                        },
                        {
                            "analysis_type": "infinitive",
                            "slots": {
                                "extensions": [
                                    {"type": "applicative"},
                                    {"type": "reciprocal"},
                                ]
                            },
                        },
                    ],
                },
            }
        ],
    }
    validate_corpus(good)


def test_malformed_prohibited_never_passes_as_non_match():
    """The Fix 2 end-to-end false pass: the intended negative prohibited
    reading is present, but the misspelled pattern would previously pass."""
    case = {
        "case_id": "CT-REF-71",
        "category": "T",
        "scored": True,
        "flows": ["analyze"],
        "analyze": {
            "text": "kux",
            "expected_status": 200,
            "exhaustive": False,
            "required_readings": [{"analysis_type": "infinitive"}],
            "prohibited_readings": [{"slots": {"polairty": {"value": "negative"}}}],
        },
    }
    payload = {
        "data": {
            "analyses": [
                {
                    "analysis_type": "infinitive",
                    "slots": {"polarity": {"value": "negative"}},
                }
            ]
        }
    }
    result = evaluate_case(
        _StubClient(post={"/v1/analyze": _stub_response(200, payload)}),
        "k",
        case,
        _lemma_ids(),
    )
    assert result["status"] == "fail", result["checks"]
    assert any(
        c["name"] == "analyze_expectation" and not c["passed"] for c in result["checks"]
    )
    assert not any(
        c["name"].startswith("analyze_prohibited") and c["passed"]
        for c in result["checks"]
    ), "malformed expectation must never surface as a passed prohibited check"


def test_malformed_search_expectation_fails_loudly():
    case = {
        "case_id": "CT-REF-72",
        "category": "T",
        "scored": True,
        "flows": ["search"],
        "search": {
            "q": "kux",
            "expected_status": 200,
            "required_readings": [{"analysis_type": "infinitive"}],
            "prohibited_readings": [{"slots": {"polarity": {"valu": "x"}}}],
        },
    }
    payload = {
        "data": {
            "results": [],
            "morphology": {"analyses": []},
            "morphology_enrichment": {"status": "matched"},
        }
    }
    result = evaluate_case(
        _StubClient(get={"/v1/search": _stub_response(200, payload)}),
        "k",
        case,
        _lemma_ids(),
    )
    assert result["status"] == "fail"
    assert any(
        c["name"] == "search_expectation" and not c["passed"] for c in result["checks"]
    )


def test_invalid_corpus_rejected_before_endpoint_requests():
    """Corpus validation precedes any endpoint request: a malformed corpus
    raises before the (recording) client is ever touched."""
    bad = _nested_bad_corpus(
        "SRC-999", [{"slots": {"polairty": {"value": "negative"}}}]
    )

    class _RecordingClient:
        def __init__(self):
            self.calls = 0

        def post(self, *args, **kwargs):
            self.calls += 1
            raise AssertionError("must not reach endpoint with invalid corpus")

        def get(self, *args, **kwargs):
            self.calls += 1
            raise AssertionError("must not reach endpoint with invalid corpus")

    client = _RecordingClient()
    with pytest.raises(CorpusError, match="SRC-999"):
        validate_corpus(bad)
    assert client.calls == 0


def test_match_reading_reports_nested_unknown_keys():
    ok, detail = match_reading(
        {"analysis_type": "infinitive", "slots": {"polarity": {"value": "negative"}}},
        {"slots": {"polairty": {"value": "negative"}}},
    )
    assert not ok and "polairty" in detail
    ok, detail = match_reading(
        {"analysis_type": "infinitive", "slots": {"polarity": {"value": "negative"}}},
        {"slots": {"polarity": {"valu": "negative"}}},
    )
    assert not ok and "valu" in detail


# --- Malformed response robustness ---------------------------------------------


def test_malformed_analyses_containers_fail_with_diagnostics():
    """Valid JSON with null/object/string analyses must fail the flow with a
    field-specific diagnostic — never crash, never pass as an empty result."""
    for label, raw in (
        ("null", None),
        ("object", {}),
        ("string", "bad"),
        ("number", 42),
    ):
        case = _metric_case(f"CT-MAL-{label}")
        result = evaluate_case(
            _StubClient(
                post={"/v1/analyze": _stub_response(200, {"data": {"analyses": raw}})}
            ),
            "k",
            case,
            _lemma_ids(),
        )
        assert result["status"] == "fail", label
        body = next(c for c in result["checks"] if c["name"] == "analyze_body")
        assert not body["passed"] and "data.analyses" in body["detail"], label
        assert any(
            c["name"].startswith("analyze_required") and not c["passed"]
            for c in result["checks"]
        ), label


def test_malformed_analyses_entries_fail_without_crashing():
    for label, analyses in (
        ("scalar-entry", ["bad"]),
        ("null-entry", [None]),
        ("mixed-entries", [{"analysis_type": "infinitive"}, 42]),
    ):
        case = _metric_case(f"CT-MAL-{label}")
        result = evaluate_case(
            _StubClient(
                post={
                    "/v1/analyze": _stub_response(200, {"data": {"analyses": analyses}})
                }
            ),
            "k",
            case,
            _lemma_ids(),
        )
        assert result["status"] == "fail", label
        assert any(
            c["name"] == "analyze_body" and not c["passed"] for c in result["checks"]
        ), label


def test_malformed_data_envelope_fails_with_diagnostics():
    for label, body in (
        ("data-null", {"data": None}),
        ("data-list", {"data": []}),
        ("data-missing", {}),
    ):
        case = _metric_case(f"CT-MAL-{label}")
        result = evaluate_case(
            _StubClient(post={"/v1/analyze": _stub_response(200, body)}),
            "k",
            case,
            _lemma_ids(),
        )
        assert result["status"] == "fail", label
        assert any(
            c["name"] == "analyze_body" and not c["passed"] for c in result["checks"]
        ), label


def test_matcher_tolerates_malformed_nested_readings():
    """Non-object analyses and nested values must report non-match, not raise."""
    ok, detail = match_reading("bad", {"analysis_type": "infinitive"})
    assert not ok and "malformed reading" in detail
    ok, detail = match_reading(
        {"analysis_type": "infinitive", "slots": 5},
        {"analysis_type": "infinitive", "slots": {"polarity": {"value": "positive"}}},
    )
    assert not ok and "slots" in detail
    ok, detail = match_reading(
        {"analysis_type": "infinitive", "lemma": "x"},
        {"analysis_type": "infinitive", "lemma": {"lemma_public_id": "a"}},
    )
    assert not ok and "lemma" in detail


def test_malformed_search_containers_fail_with_diagnostics():
    def _search_case(cid):
        return {
            "case_id": cid,
            "category": "S",
            "scored": True,
            "flows": ["search"],
            "search": {
                "q": "kX",
                "expected_status": 200,
                "expected_enrichment_status": "matched",
                "required_readings": [{"analysis_type": "infinitive"}],
            },
        }

    good_enrichment = {"status": "matched"}
    for label, body in (
        ("morphology-string", {"results": [], "morphology": "x"}),
        ("morphology-list", {"results": [], "morphology": ["x"]}),
        (
            "morphology-analyses-string",
            {"results": [], "morphology": {"analyses": "x"}},
        ),
        (
            "morphology-analyses-scalar",
            {
                "results": [],
                "morphology": {"analyses": [{"analysis_type": "x"}, "bad"]},
            },
        ),
        ("results-object", {"results": {}, "morphology": {"analyses": []}}),
        ("results-scalar-entry", {"results": ["x"], "morphology": {"analyses": []}}),
        (
            "result-lemma-string",
            {"results": [{"lemma": "x"}], "morphology": {"analyses": []}},
        ),
        ("data-null", None),
    ):
        payload = {"data": body if body is not None else None}
        if isinstance(body, dict):
            payload["data"].setdefault("morphology_enrichment", good_enrichment)
        case = _search_case(f"CT-MAL-{label}")
        result = evaluate_case(
            _StubClient(get={"/v1/search": _stub_response(200, payload)}),
            "k",
            case,
            _lemma_ids(),
        )
        assert result["status"] == "fail", label
        assert any(
            c["name"] == "search_body" and not c["passed"] for c in result["checks"]
        ), label


def test_search_absent_enrichment_stays_legitimate():
    """Absent morphology (unsupported lane) and empty lists must not raise a
    body failure: the flow fails only on its declared assertions."""
    case = {
        "case_id": "CT-MAL-ABSENT",
        "category": "S",
        "scored": True,
        "flows": ["search"],
        "search": {
            "q": "kX",
            "expected_status": 200,
            "expected_enrichment_status": "matched",
            "required_readings": [{"analysis_type": "infinitive"}],
        },
    }
    payload = {
        "data": {
            "results": [],
            "morphology": {"analyses": []},
            "morphology_enrichment": {"status": "matched"},
        }
    }
    result = evaluate_case(
        _StubClient(get={"/v1/search": _stub_response(200, payload)}),
        "k",
        case,
        _lemma_ids(),
    )
    assert result["status"] == "fail"
    assert not any(
        c["name"] == "search_body" and not c["passed"] for c in result["checks"]
    )


def test_malformed_generate_responses_fail_with_diagnostics():
    def _gen_case(cid):
        return {
            "case_id": cid,
            "category": "G",
            "scored": True,
            "flows": ["generate"],
            "generate": {
                "features": {},
                "expected_status": 200,
                "expected_surface": "kX",
            },
        }

    for label, body in (
        ("generated-string", {"generated": "x"}),
        ("generated-missing", {}),
        ("data-null", None),
    ):
        payload = {"data": body} if body is not None else {"data": None}
        case = _gen_case(f"CT-MAL-{label}")
        result = evaluate_case(
            _StubClient(post={"/v1/generate": _stub_response(200, payload)}),
            "k",
            case,
            _lemma_ids(),
        )
        assert result["status"] == "fail", label
        assert any(
            c["name"] == "generate_body" and not c["passed"] for c in result["checks"]
        ), label
    metrics = compute_metrics(
        {"version": "t", "fixtures": {}, "cases": [_gen_case("CT-MAL-GX")]},
        {
            "results": [
                evaluate_case(
                    _StubClient(
                        post={"/v1/generate": _stub_response(200, {"data": {}})}
                    ),
                    "k",
                    _gen_case("CT-MAL-GX"),
                    _lemma_ids(),
                )
            ]
        },
    )
    assert metrics["contract"]["generation_correct"] == [0, 1]


def test_malformed_round_trip_responses_fail_without_crashing():
    class _GenOkRoundTripBad:
        def __init__(self, round_trip_body):
            self._round_trip_body = round_trip_body

        def post(self, path, payload, *args, **kwargs):
            if path == "/v1/generate":
                return _stub_response(
                    200, {"data": {"generated": {"form": "genX", "rule_id": "r"}}}
                )
            assert path == "/v1/analyze"
            if payload.get("text") == "genX":
                return _stub_response(200, self._round_trip_body)
            return _stub_response(200, {"data": {"analyses": [_METRIC_GOOD]}})

        def get(self, path, *args, **kwargs):
            raise AssertionError("no search in fixture")

    def _rt_case(cid):
        return {
            "case_id": cid,
            "category": "R",
            "scored": True,
            "flows": ["generate", "analyze"],
            "generate": {
                "features": {},
                "expected_status": 200,
                "expected_surface": "genX",
            },
            "analyze": {
                "text": "kX",
                "expected_status": 200,
                "exhaustive": False,
                "required_readings": [_METRIC_GOOD],
            },
            "round_trip": {"required_reading": {"analysis_type": "infinitive"}},
        }

    for label, round_trip_body in (
        ("rt-null", {"data": {"analyses": None}}),
        ("rt-scalar", {"data": {"analyses": ["bad"]}}),
    ):
        result = evaluate_case(
            _GenOkRoundTripBad(round_trip_body),
            "k",
            _rt_case(f"CT-MAL-{label}"),
            _lemma_ids(),
        )
        assert result["status"] == "fail", label
        assert any(
            c["name"] == "round_trip_recovered" and not c["passed"]
            for c in result["checks"]
        ), label


def test_malformed_multi_case_recall_report_and_continuation(tmp_path):
    """One correct + one malformed + one later-correct supported response:
    recall [2, 3], later case executes, results + report still produced."""

    class _SequencedClient:
        def __init__(self, bodies):
            self._bodies = list(bodies)
            self.calls = 0

        def post(self, path, payload, *args, **kwargs):
            assert path == "/v1/analyze"
            body = self._bodies[self.calls]
            self.calls += 1
            return _stub_response(200, body)

        def get(self, path, *args, **kwargs):
            raise AssertionError("no search in fixture")

    cases = [
        _metric_case("CT-MAL-M1"),
        _metric_case("CT-MAL-M2"),
        _metric_case("CT-MAL-M3"),
    ]
    client = _SequencedClient(
        [
            {"data": {"analyses": [_METRIC_GOOD]}},
            {"data": {"analyses": None}},
            {"data": {"analyses": [_METRIC_GOOD]}},
        ]
    )
    out = evaluate(client, "k", {"cases": cases}, _lemma_ids())
    assert client.calls == 3, "later case must still execute after a malformed response"
    by_id = {r["case_id"]: r for r in out["results"]}
    assert by_id["CT-MAL-M1"]["status"] == "pass"
    assert by_id["CT-MAL-M2"]["status"] == "fail"
    assert any(
        c["name"] == "analyze_body" and not c["passed"]
        for c in by_id["CT-MAL-M2"]["checks"]
    )
    assert by_id["CT-MAL-M3"]["status"] == "pass"
    metrics = compute_metrics({"version": "t", "fixtures": {}, "cases": cases}, out)
    assert metrics["contract"]["required_recall"] == [2, 3]
    assert metrics["contract"]["supported_refusals"] == [0, 3]
    corpus = {
        "version": "t",
        "hash": "sha256:" + "0" * 64,
        "fixtures": {},
        "cases": cases,
    }
    report = write_report(
        corpus, out, metrics, "test-rev", False, "test-eval", tmp_path
    )
    text = Path(report).read_text(encoding="utf-8")
    assert "required-analysis recall" in text
    assert "CT-MAL-M2" in text
