"""One command that verifies this repository.

Continuous integration is not running for this project, so the safety net has
to live in the repository and be runnable by anyone -- a contributor, or an
agent that has just changed something. This runs every gate in order and exits
non-zero if any of them fails.

Stages, cheapest first:

1. language readiness       -- the current release and stored phonology fields
                               match the rules this checkout implements
2. lexical QA               -- the published lexicon against the Hannan lines it
                               came from, compared with a frozen baseline
3. source-backed morphology -- the rule engine against its frozen corpus
4. test suite               -- the durable pytest gate

Stages run **sequentially**, never in parallel: two of them open the same
SQLite database, and concurrent access has already produced a `database is
locked` failure during this project. Each stage writes its artefacts outside
the repository so a verification run never dirties the working tree.

Usage::

    python tools/verify.py
    python tools/verify.py --only tests          # one stage
    python tools/verify.py --list
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

LEXICAL_CORPUS = "evaluation/lexical_qa/v1/corpus.json"
LEXICAL_BASELINE = "evaluation/lexical_qa/v1/baseline.json"
MORPHOLOGY_CORPUS = "evaluation/source_backed/v1/corpus.json"

TAIL_LINES = 6


@dataclass(frozen=True)
class Stage:
    name: str
    argv: list[str]
    note: str


@dataclass(frozen=True)
class StageResult:
    stage: Stage
    returncode: int
    output: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def build_stages(*, out_dir: Path) -> list[Stage]:
    """The gates, cheapest first. Artefacts go to ``out_dir``, never the repo."""
    python = sys.executable
    return [
        Stage(
            name="readiness",
            argv=[python, "manage.py", "check_language_readiness"],
            note="release rule-set version and phonology inventory match the code",
        ),
        Stage(
            name="lexical-qa",
            argv=[
                python,
                "tools/evaluate_lexical_qa.py",
                "--corpus",
                LEXICAL_CORPUS,
                "--out",
                str(out_dir / "lexical-qa"),
                "--baseline",
                LEXICAL_BASELINE,
            ],
            note="published lexicon vs source lines, against the frozen baseline",
        ),
        Stage(
            name="morphology-corpus",
            argv=[
                python,
                "tools/evaluate_source_backed.py",
                "--corpus",
                MORPHOLOGY_CORPUS,
                "--out",
                str(out_dir / "morphology-corpus"),
            ],
            note="morphology engine vs the frozen source-backed corpus",
        ),
        Stage(
            name="tests",
            argv=[python, "-m", "pytest", "-q"],
            note="the durable pytest gate",
        ),
    ]


def run_stage(stage: Stage, *, runner=None) -> StageResult:
    runner = runner or subprocess.run
    completed = runner(
        stage.argv,
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    return StageResult(stage=stage, returncode=completed.returncode, output=output)


def run_stages(stages: list[Stage], *, runner=None, echo=print) -> list[StageResult]:
    """Run every stage in order and return the results, continuing past failures.

    Every gate runs even after one fails: a partial report sends the reader back
    to re-run the rest by hand, which is the thing this command exists to avoid.
    """
    results: list[StageResult] = []
    for index, stage in enumerate(stages, start=1):
        echo(f"[{index}/{len(stages)}] {stage.name} -- {stage.note}")
        result = run_stage(stage, runner=runner)
        results.append(result)
        tail = result.output.strip().splitlines()[-TAIL_LINES:]
        for line in tail:
            echo(f"    {line}")
        echo(f"    -> {'ok' if result.ok else f'FAILED (exit {result.returncode})'}")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", action="append", help="Run only the named stage(s).")
    parser.add_argument("--list", action="store_true", help="List the stages and exit.")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="shona-verify-") as tmp:
        stages = build_stages(out_dir=Path(tmp))
        if args.list:
            for stage in stages:
                print(f"{stage.name}: {stage.note}")
            return 0
        if args.only:
            known = {stage.name for stage in stages}
            unknown = sorted(set(args.only) - known)
            if unknown:
                print(f"unknown stage(s): {', '.join(unknown)}; known: {', '.join(sorted(known))}")
                return 2
            stages = [stage for stage in stages if stage.name in set(args.only)]

        results = run_stages(stages)

    failed = [result.stage.name for result in results if not result.ok]
    print()
    if failed:
        print(f"VERIFY FAILED: {', '.join(failed)}")
        return 1
    print(f"VERIFY PASSED: {len(results)} stage(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
