"""Gate for the lexical QA harness.

Two properties matter and both are tested here:

- The reader reads Hannan lines correctly, because every expectation in the
  corpus comes from it.
- The evaluator fails on wrong data. A harness that cannot fail would report a
  clean lexicon no matter what the database held.
"""

import ast
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.build_lexical_qa_corpus import corpus_hash, verify_hash
from tools.evaluate_lexical_qa import CHECKS, compute_metrics, evaluate_case
from tools.lexical_qa import HannanLineError, read_hannan_line

CORPUS_PATH = Path(__file__).parent.parent / "evaluation" / "lexical_qa" / "v1" / "corpus.json"


# --- reader -----------------------------------------------------------------


def test_reader_parses_a_noun_with_class_and_plural():
    source = read_hannan_line("bimha [LL]KMZ n 5, pl: map-, mab- (M), Reedbuck R 292.")

    assert source["headword"] == "bimha"
    assert source["headword_kind"] == "noun"
    assert source["noun_class"] == "5"
    assert source["tone_patterns"] == ["LL"]
    assert source["plural_forms"] == ["map-", "mab- (M)"]


def test_reader_keeps_the_sub_class_letter():
    """`n 1a` is a different class from `n 1`, and the reader must not merge them."""
    assert read_hannan_line("Chikumi [LHH]KMZ n 1a June.")["noun_class"] == "1a"
    assert read_hannan_line("zingondi [LHL]KM n 2a Big male baboon.")["noun_class"] == "2a"


def test_reader_parses_a_verb_and_its_dialect_restriction():
    source = read_hannan_line("-bikura [H]KZ v t Snatch and carry away.")

    assert source["headword"] == "bikura"
    assert source["headword_kind"] == "verb_stem"
    assert source["noun_class"] is None
    assert source["dialects"] == ["KZ"]


def test_reader_splits_compound_tone_brackets_into_alternatives():
    """A bracket may give one tone per dialect: `[H M; LHLH Z]`."""
    source = read_hannan_line("-bimhidza [H M; LHLH Z]MZ v t, see -bhimhidza.")

    assert source["tone_patterns"] == ["H", "LHLH"]
    assert source["headword_kind"] == "verb_stem"


def test_reader_treats_a_multi_word_headword_pattern_as_one_alternative():
    """`[LLL HH]` is one pattern for the two-word headword, not a pattern `LLL`."""
    source = read_hannan_line(
        "munhondo churu [LLL HH]Z n 3 sp Medium-sized tree: Schotia brachypetala."
    )

    assert source["tone_patterns"] == ["LLL HH"]
    assert source["headword"] == "munhondo churu"
    assert source["source_shape"] == "multiword_headword"


def test_reader_handles_marker_glyphs_and_defective_verbs():
    source = read_hannan_line("†-ti [L]KKoMZ defective v Say. Think. Do.")

    assert source["headword"] == "ti"
    assert source["headword_kind"] == "verb_stem"


def test_reader_handles_parenthesised_dialect_runs():
    source = read_hannan_line("chibayamakono [LLLLHH]KKo(B)Z n 7 sp Small shrub.")

    assert source["headword_kind"] == "noun"
    assert source["noun_class"] == "7"


@pytest.mark.parametrize(
    "line",
    [
        "",
        "a represents, in Shona, the sound heard in the first element of a diphthong.",
        "-ama KKoMZ v sfx > stative ext of R; kukomba > kukombama.",
    ],
)
def test_reader_rejects_lines_without_a_structured_entry_shape(line):
    with pytest.raises(HannanLineError):
        read_hannan_line(line)


@pytest.mark.parametrize(
    "line, expected",
    [
        ("biku [HL]K n 5, pl: mab-, Huddle.", "noun_with_plural"),
        ("gundumure [LLLL]K n 1a Big-headed person.", "noun_subclass"),
        ("bimhidza [LHL]KZ n 5 Bad chest cold.", "noun_plain"),
        ("-bikura [H]KZ v t Snatch and carry away.", "verb_transitive"),
        ("-bima [H]K v i Sit quietly.", "verb_intransitive"),
        ("-pfutura [L]Z v t & i Do a thing thoroughly.", "verb_ambitransitive"),
        ("piku [LL]KMZ ideo of Taking up.", "ideophone"),
        ("wara wara [LL LL]Z ideo of Following closely.", "multiword_headword"),
    ],
)
def test_reader_classifies_source_shape_from_the_line_only(line, expected):
    assert read_hannan_line(line)["source_shape"] == expected


# --- independence -----------------------------------------------------------


def test_reader_does_not_import_the_implementation():
    """Expectations must not be produced by the code they are used to judge.

    Independence is the whole basis for comparing the reader against the
    published corpus: a reader that imported the project's own parser or
    normalizer could only ever agree with it.
    """
    tree = ast.parse(Path("tools/lexical_qa.py").read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)

    assert not [name for name in imported if name.startswith("shona_api")]


# --- evaluator --------------------------------------------------------------


def _case(**source_overrides):
    source = {
        "headword": "bimha",
        "headword_kind": "noun",
        "noun_class": "5",
        "tone_patterns": ["LL"],
        "plural_forms": ["map-"],
        "source_shape": "noun_with_plural",
    }
    source.update(source_overrides)
    return {"case_id": "case:1", "source": source}


def _record(**overrides):
    record = {
        "headword": "bimha",
        "normalized_headword": "bimha",
        "headword_kind": "noun",
        "part_of_speech_code": "n",
        "part_of_speech_label": "noun",
        "noun_class": "5",
        "tone_patterns": ["LL"],
        "forms": [],
    }
    record.update(overrides)
    return record


def test_evaluator_passes_a_record_that_matches_its_source_line():
    result = evaluate_case(_case(), _record())

    assert [result["checks"][check]["status"] for check in CHECKS] == ["pass"] * len(CHECKS)


@pytest.mark.parametrize(
    "check, overrides",
    [
        ("word_class", {"headword_kind": "word"}),
        ("noun_class", {"noun_class": "1"}),
        ("tone", {"tone_patterns": []}),
        ("part_of_speech_label", {"part_of_speech_label": "o n 3, pl: moyo, Heart."}),
        ("headword", {"normalized_headword": "bimh"}),
    ],
)
def test_evaluator_fails_each_check_when_the_published_record_is_wrong(check, overrides):
    """Each check must be able to fail; a green report has to mean something."""
    result = evaluate_case(_case(), _record(**overrides))

    assert result["checks"][check]["status"] == "fail"
    assert compute_metrics([result])[check]["failed"] == 1


def test_evaluator_accepts_tone_grouping_differences():
    """`[H H H]` and `HHH` are the same pattern written differently."""
    result = evaluate_case(_case(tone_patterns=["H H H"]), _record(tone_patterns=["HHH"]))

    assert result["checks"]["tone"]["status"] == "pass"


def test_evaluator_fails_when_no_published_record_exists():
    result = evaluate_case(_case(), None)

    assert result["unresolved"] is True
    assert all(result["checks"][check]["status"] == "fail" for check in CHECKS)
    assert compute_metrics([result])["unresolved_records"] == 1


def test_evaluator_marks_noun_class_not_applicable_for_verbs():
    result = evaluate_case(_case(headword_kind="verb_stem", noun_class=None), _record(headword_kind="verb_stem"))

    assert result["checks"]["noun_class"]["status"] == "not_applicable"
    assert compute_metrics([result])["noun_class"]["denominator"] == 0


def test_metrics_derive_denominators_from_checks_not_from_status():
    results = [
        evaluate_case(_case(), _record()),
        evaluate_case(_case(), _record(noun_class="1")),
        evaluate_case(_case(noun_class=None, headword_kind="verb_stem"), _record(headword_kind="verb_stem")),
    ]
    metrics = compute_metrics(results)

    assert metrics["word_class"] == {
        "passed": 3,
        "failed": 0,
        "not_applicable": 0,
        "denominator": 3,
    }
    assert metrics["noun_class"]["denominator"] == 2
    assert metrics["noun_class"]["not_applicable"] == 1


# --- corpus integrity -------------------------------------------------------


def test_frozen_corpus_verifies_and_reports_its_strata():
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))

    verify_hash(corpus)
    assert corpus["version"] == "lexical-qa-v1"
    assert corpus["cases"], "frozen corpus must not be empty"
    assert {case["source"]["source_shape"] for case in corpus["cases"]} >= {
        "noun_subclass",
        "multiword_headword",
    }, "the corpus must include the source shapes where parsing is hard"


def test_corpus_hash_rejects_a_tampered_case():
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(corpus)
    tampered["cases"][0]["source"]["noun_class"] = "19"

    assert corpus_hash(tampered) != corpus["hash"]
    with pytest.raises(SystemExit):
        verify_hash(tampered)
