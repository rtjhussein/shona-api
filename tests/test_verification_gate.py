"""Tests for the repository verification gate.

Continuous integration does not run for this project, so these gates are the
safety net. Two properties matter and are tested here:

- the baseline comparison fails on a regression and is not fooled by a stale or
  mismatched baseline, and
- the runner reports failure honestly -- including running every stage, so a
  partial result cannot be mistaken for a full one.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.evaluate_lexical_qa import CHECKS, baseline_regressions
from tools.verify import REPOSITORY_ROOT, build_stages, run_stage, run_stages

CORPUS_PATH = Path(__file__).parent.parent / "evaluation" / "lexical_qa" / "v1" / "corpus.json"
BASELINE_PATH = Path(__file__).parent.parent / "evaluation" / "lexical_qa" / "v1" / "baseline.json"


def _metrics(**overrides):
    metrics = {
        check: {"passed": 10, "failed": 0, "not_applicable": 0, "denominator": 10}
        for check in CHECKS
    }
    metrics.update(overrides)
    return metrics


def _baseline(corpus_hash="sha256:frozen", **metric_overrides):
    return {
        "corpus_hash": corpus_hash,
        "metrics": {
            check: {"passed": 10, "denominator": 10} for check in CHECKS
        }
        | metric_overrides,
        "coverage": {"nouns_with_source_plural": 42, "with_a_published_form": 0},
    }


def test_baseline_passes_when_the_run_matches_it():
    problems = baseline_regressions(
        metrics=_metrics(),
        coverage={"nouns_with_source_plural": 42, "with_a_published_form": 0},
        baseline=_baseline(),
        corpus_hash="sha256:frozen",
    )

    assert problems == []


def test_baseline_accepts_an_improvement():
    """A fix raises the number; only a drop is a regression."""
    problems = baseline_regressions(
        metrics=_metrics(headword={"passed": 12, "failed": 0, "not_applicable": 0, "denominator": 10}),
        coverage={"nouns_with_source_plural": 42, "with_a_published_form": 3},
        baseline=_baseline(),
        corpus_hash="sha256:frozen",
    )

    assert problems == []


def test_baseline_reports_a_regression_with_both_numbers():
    problems = baseline_regressions(
        metrics=_metrics(headword={"passed": 7, "failed": 3, "not_applicable": 0, "denominator": 10}),
        coverage={"nouns_with_source_plural": 42, "with_a_published_form": 0},
        baseline=_baseline(),
        corpus_hash="sha256:frozen",
    )

    assert len(problems) == 1
    assert "headword" in problems[0]
    assert "7/10" in problems[0] and "10/10" in problems[0]


def test_baseline_rejects_a_changed_denominator():
    """A moved denominator means the measure itself changed, not the data."""
    problems = baseline_regressions(
        metrics=_metrics(tone={"passed": 12, "failed": 0, "not_applicable": 0, "denominator": 12}),
        coverage={"nouns_with_source_plural": 42, "with_a_published_form": 0},
        baseline=_baseline(),
        corpus_hash="sha256:frozen",
    )

    assert any("denominator moved" in problem for problem in problems)


def test_baseline_rejects_a_baseline_for_a_different_corpus():
    """A regenerated corpus invalidates the baseline rather than silently passing."""
    problems = baseline_regressions(
        metrics=_metrics(),
        coverage={"nouns_with_source_plural": 42, "with_a_published_form": 0},
        baseline=_baseline(corpus_hash="sha256:other"),
        corpus_hash="sha256:frozen",
    )

    assert len(problems) == 1
    assert "written for corpus" in problems[0]


def test_frozen_baseline_matches_the_frozen_corpus():
    """The committed baseline must describe the committed corpus."""
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    assert baseline["corpus_hash"] == corpus["hash"]
    assert set(baseline["metrics"]) == set(CHECKS)


# --- runner -----------------------------------------------------------------


def _completed(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_run_stages_reports_every_failure_instead_of_stopping():
    """A partial report sends the reader back to run the rest by hand."""
    stages = build_stages(out_dir=Path("/tmp/does-not-matter"))
    codes = {"readiness": 1, "lexical-qa": 0, "morphology-corpus": 1, "tests": 0}
    calls: list[str] = []

    def fake_runner(argv, **kwargs):
        name = stages[len(calls)].name
        calls.append(name)
        return _completed(codes[name])

    results = run_stages(stages, runner=fake_runner, echo=lambda *_args: None)

    assert len(calls) == len(stages), "every stage must run"
    assert [result.ok for result in results] == [False, True, False, True]


def test_run_stage_merges_streams_and_reports_the_exit_code():
    stage = build_stages(out_dir=Path("/tmp/does-not-matter"))[0]

    result = run_stage(stage, runner=lambda argv, **kwargs: _completed(3, "out", "err"))

    assert result.returncode == 3
    assert "out" in result.output and "err" in result.output
    assert result.ok is False


def test_stage_artefacts_are_written_outside_the_repository():
    """A verification run must not dirty the working tree it is verifying."""
    for stage in build_stages(out_dir=Path("/tmp/verify-artefacts")):
        for index, argument in enumerate(stage.argv):
            if argument == "--out":
                resolved = Path(stage.argv[index + 1]).resolve()
                assert not resolved.is_relative_to(REPOSITORY_ROOT), (
                    f"{stage.name} writes into the repository: {resolved}"
                )


def test_verify_lists_the_same_stages_it_runs():
    """`--list` is the documentation; it must not drift from the real stages."""
    completed = subprocess.run(
        [sys.executable, "tools/verify.py", "--list"],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    for stage in build_stages(out_dir=Path("/tmp/does-not-matter")):
        assert stage.name in completed.stdout


@pytest.mark.parametrize("unknown", ["nonsense"])
def test_verify_rejects_an_unknown_stage(unknown):
    completed = subprocess.run(
        [sys.executable, "tools/verify.py", "--only", unknown],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
