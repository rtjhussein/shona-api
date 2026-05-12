import pytest

from shona_api.phonology import (
    GraphemeInventory,
    compute_phonology_fields,
    get_grapheme_inventory,
    segment_graphemes,
    syllabify_word,
)


def test_segment_graphemes_uses_greedy_longest_match_for_shona_forms():
    assert segment_graphemes("chikoro") == ["ch", "i", "k", "o", "r", "o"]
    assert segment_graphemes("mhoro") == ["mh", "o", "r", "o"]
    assert segment_graphemes("mwana") == ["mw", "a", "n", "a"]
    assert segment_graphemes("nzvimbo") == ["nzv", "i", "mb", "o"]
    assert segment_graphemes("pfumo") == ["pf", "u", "m", "o"]
    assert segment_graphemes("shumba") == ["sh", "u", "mb", "a"]


def test_grapheme_inventory_is_versioned_and_configurable():
    inventory = get_grapheme_inventory("shona-core-v1")

    assert inventory.version == "shona-core-v1"
    assert {"ch", "mb", "ny", "sh", "sv", "zv"}.issubset(inventory.graphemes)

    custom_inventory = GraphemeInventory(
        version="test-v1",
        graphemes=("aa", "a", "w"),
    )
    assert segment_graphemes("aawa", inventory=custom_inventory) == ["aa", "w", "a"]

    with pytest.raises(ValueError, match="Unknown grapheme inventory version"):
        get_grapheme_inventory("missing")


def test_syllabify_word_returns_stable_syllables_for_representative_forms():
    assert syllabify_word("chikoro") == ["chi", "ko", "ro"]
    assert syllabify_word("mhoro") == ["mho", "ro"]
    assert syllabify_word("nzvimbo") == ["nzvi", "mbo"]
    assert syllabify_word("zvakanaka") == ["zva", "ka", "na", "ka"]


def test_compute_phonology_fields_returns_payload_for_future_save_hooks():
    assert compute_phonology_fields("Zimbabwe") == {
        "phonology_inventory_version": "shona-core-v1",
        "graphemes": ["z", "i", "mb", "a", "bw", "e"],
        "grapheme_count": 6,
        "syllables": ["zi", "mba", "bwe"],
        "syllable_count": 3,
    }
