import pytest

from shona_api.phonology import (
    DEFAULT_GRAPHEME_INVENTORY,
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


def test_default_inventory_treats_labialised_and_pre_reform_clusters_as_one_grapheme():
    """A grapheme is one phoneme, not one character.

    shona-core-v1 split these clusters, so `grapheme_length` (the field word
    games filter on) was wrong for every word containing one. `mbwa` (dog) is
    core vocabulary and was counted as three graphemes.
    """
    assert segment_graphemes("mbwa") == ["mbw", "a"]
    assert segment_graphemes("ngwe") == ["ngw", "e"]
    assert segment_graphemes("ndwandwe") == ["ndw", "a", "ndw", "e"]
    assert segment_graphemes("kunzwisisa") == ["k", "u", "nzw", "i", "s", "i", "s", "a"]
    assert segment_graphemes("bvekenyedzwa") == ["bv", "e", "k", "e", "ny", "e", "dzw", "a"]
    assert segment_graphemes("kutya") == ["k", "u", "ty", "a"]
    assert segment_graphemes("tshumba") == ["tsh", "u", "mb", "a"]


def test_inventory_version_bump_does_not_change_syllabification():
    assert syllabify_word("ngwe") == ["ngwe"]
    assert syllabify_word("mbwa") == ["mbwa"]
    assert syllabify_word("ndwandwe") == ["ndwa", "ndwe"]
    assert syllabify_word("kutya") == ["ku", "tya"]


def test_syllabify_word_returns_stable_syllables_for_representative_forms():
    assert syllabify_word("chikoro") == ["chi", "ko", "ro"]
    assert syllabify_word("mhoro") == ["mho", "ro"]
    assert syllabify_word("nzvimbo") == ["nzvi", "mbo"]
    assert syllabify_word("zvakanaka") == ["zva", "ka", "na", "ka"]


def test_compute_phonology_fields_returns_payload_for_future_save_hooks():
    assert compute_phonology_fields("Zimbabwe") == {
        "phonology_inventory_version": DEFAULT_GRAPHEME_INVENTORY.version,
        "graphemes": ["z", "i", "mb", "a", "bw", "e"],
        "grapheme_count": 6,
        "syllables": ["zi", "mba", "bwe"],
        "syllable_count": 3,
    }


def test_v3_reads_breathy_and_labialised_consonants_as_one_grapheme():
    """Fortune lists /bh/ and /dh/ as single phonemes (1.6), and states that
    most consonants combine with /w/ (1.8) -- which the inventory already
    encoded for `bw`, `kw`, and others but not for these.

    shona-core-v2 split them, so `grapheme_count` was wrong for every word
    containing one, and the noun-plural rule could not read a prefix like
    `mabh-` at all.
    """
    assert segment_graphemes("bhachi") == ["bh", "a", "ch", "i"]
    assert segment_graphemes("dhani") == ["dh", "a", "n", "i"]
    assert segment_graphemes("barwe") == ["b", "a", "rw", "e"]
    assert segment_graphemes("dwitwi") == ["dw", "i", "tw", "i"]
    assert segment_graphemes("chidywa") == ["ch", "i", "dyw", "a"]
    # Syllabification is unaffected: a syllable still closes on its vowel.
    assert syllabify_word("bhachi") == ["bha", "chi"]
    assert syllabify_word("barwe") == ["ba", "rwe"]


def test_every_inventory_version_stays_registered():
    """A stored record names the inventory that produced it, so old versions
    must keep resolving."""
    for version in ("shona-core-v1", "shona-core-v2", "shona-core-v3"):
        assert get_grapheme_inventory(version).version == version

    v1 = get_grapheme_inventory("shona-core-v1")
    v2 = get_grapheme_inventory("shona-core-v2")
    v3 = get_grapheme_inventory("shona-core-v3")
    assert set(v1.graphemes) <= set(v2.graphemes) <= set(v3.graphemes)
