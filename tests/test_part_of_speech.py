import pytest

from shona_api.lexicon.part_of_speech import (
    CANONICAL_POS_CODES,
    canonical_pos_code,
)


@pytest.mark.parametrize(
    "stored, expected",
    [
        ("v t", "vt"),
        ("vt", "vt"),
        ("v i", "vi"),
        ("vi", "vi"),
        ("v t & i", "vti"),
        ("vt&i", "vti"),
        ("vt_i", "vti"),
        ("vi&t", "vti"),
        ("vit", "vti"),
        ("defective v", "defective_v"),
        ("def v", "defective_v"),
        ("sfx", "suffix"),
        ("v sfx", "suffix"),
        ("infx", "infix"),
        ("tense sign", "tense_sign"),
        ("orthographic_note", "note"),
        ("none", "unknown"),
        ("", "unknown"),
        ("  v   t  ", "vt"),
        ("V T", "vt"),
    ],
)
def test_canonical_pos_code_collapses_spellings_of_one_category(stored, expected):
    """A client filtering on `vt` must reach every transitive verb.

    The same word class arrives as "vt", "v t", "vt&i" and more, so the stored
    code cannot be used as a filter key until the spellings are collapsed.
    """
    assert canonical_pos_code(stored) == expected


@pytest.mark.parametrize(
    "distinct",
    [
        "adj_pron",  # adjective or pronoun
        "interrog adv",  # interrogative adverb
        "enum",  # enumerative
        "quant c",  # quantitative concord
        "poss st",  # possessive stem
        "adj, pron",
    ],
)
def test_canonical_pos_code_does_not_merge_distinct_categories(distinct):
    """Only re-spellings are collapsed; grammatical distinctions are preserved.

    No source here authorises dropping the interrogative, enumerative, or
    concord distinctions these labels carry.
    """
    assert canonical_pos_code(distinct) == distinct


def test_canonical_pos_code_preserves_unknown_values_verbatim():
    """An unfamiliar code stays visible instead of being relabelled."""
    assert canonical_pos_code("dialect particle") == "dialect particle"


def test_canonical_pos_code_rejects_non_strings():
    assert canonical_pos_code(None) == ""
    assert canonical_pos_code(5) == ""
    assert canonical_pos_code(["vt"]) == ""


def test_canonical_vocabulary_contains_every_mapping_target():
    from shona_api.lexicon.part_of_speech import CANONICAL_POS_ALIASES

    assert set(CANONICAL_POS_ALIASES.values()).issubset(CANONICAL_POS_CODES)
