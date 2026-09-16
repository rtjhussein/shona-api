import pytest

from shona_api.parsers.hannan import (
    HannanParseError,
    parse_hannan_entry,
    read_attested_noun_classes,
)
from tests.fixtures.hannan import iter_hannan_fixture_entries


def assert_expected_subset(actual, expected):
    for key, expected_value in expected.items():
        assert actual[key] == expected_value


@pytest.mark.parametrize(
    "fixture_entry",
    list(iter_hannan_fixture_entries()),
    ids=lambda entry: entry["id"],
)
def test_hannan_parser_matches_fixture_expected_parse(fixture_entry):
    parsed = parse_hannan_entry(fixture_entry["raw_entry_text"])

    assert_expected_subset(parsed, fixture_entry["expected_parse"])
    assert "uncertainties" in parsed
    assert "errors" in parsed
    assert parsed["errors"] == []


def test_hannan_parser_reports_uncertainty_for_ambiguous_fixture_notation():
    parsed = parse_hannan_entry(
        "-buda [H] KKoMZ vi Come out. 2. Rise (sun). 3. KZ Be well. "
        "cp -simba KKoMZ. 4. KMZ Fade (past tense). 5. KMZ Run "
        "(present tense; e.g. shirt being washed). > mbudo; rubudiko. "
        "Ndinobuda muhotwe: my nose is bleeding. Ndabuda basa: I have left "
        "my employment. Gumbezi iri rakabuda: this blanket has lost its original colour."
    )

    assert parsed["uncertainties"]
    assert any(
        uncertainty["path"] == "senses[0].examples"
        for uncertainty in parsed["uncertainties"]
    )


def test_hannan_parser_fails_softly_for_unparseable_entry_text():
    parsed = parse_hannan_entry("not a compact Hannan entry")

    assert parsed["headword"] == "not"
    assert parsed["tone_pattern"] is None
    assert parsed["senses"] == []
    assert parsed["errors"]
    assert any(error["code"] == "missing_tone_pattern" for error in parsed["errors"])


def test_hannan_parser_can_raise_on_unparseable_entry_text_when_requested():
    with pytest.raises(HannanParseError):
        parse_hannan_entry("not a compact Hannan entry", fail_soft=False)


# --- noun classes -----------------------------------------------------------
#
# Hannan distinguishes sub-classes (1a is not 1, 2a is not 2) and may give a
# dialect-qualified alternative ("n 1a (M), 5 (Z)"). The parsers that produced
# the published corpus dropped the letter, so these cases pin the reading of the
# source line itself.


@pytest.mark.parametrize(
    "line, expected",
    [
        ("Chikumi [LHH]KMZ n 1a June.", ["1a"]),
        ("zingondi [LHL]KM n 2a Big male baboon.", ["2a"]),
        ("bimhidza [LHL]KZ n 5 Bad chest cold.", ["5"]),
        ("godzonga [HH]Z n 1a & 5 Tyrant.", ["1a", "5"]),
        ("gufu [LH]MZ n 1a (M), 5 (Z), pl: vana- (M), mag- (Z), Toad.", ["1a", "5"]),
        ("bimhiri [LLL]M n 12/14 Whole cob of maize.", ["12", "14"]),
        ("-bikura [H]KZ v t Snatch and carry away.", []),
        ("†moyo [LL]KKo n 3, pl: moyo, Heart.", ["3"]),
    ],
)
def test_attested_noun_classes_reads_the_source_line(line, expected):
    assert read_attested_noun_classes(line) == expected


def test_hannan_parser_keeps_the_sub_class_letter():
    """Regression: `\\d+` could not match `1a`, so the class list came back empty."""
    parsed = parse_hannan_entry("Chikumi [LHH]KMZ n 1a June.")

    assert parsed["noun"]["classes"] == ["1a"]


def test_hannan_parser_reads_a_class_without_a_plural_list():
    """A class is not conditional on `pl:` being present."""
    parsed = parse_hannan_entry("bimhidza [LHL]KZ n 5 Bad chest cold with temperature. Chill.")

    assert parsed["noun"]["classes"] == ["5"]
    assert parsed["noun"]["plural_prefixes"] == []
    assert parsed["senses"][0]["definition"].startswith("Bad chest cold")


def test_hannan_parser_keeps_every_plural_prefix():
    parsed = parse_hannan_entry("bimha [LL]KMZ n 5, pl: map-, mab- (M), Reedbuck R 292.")

    assert parsed["noun"]["plural_prefixes"] == ["map-", "mab- (M)"]
    assert parsed["senses"][0]["definition"].startswith("Reedbuck")


def test_hannan_parser_does_not_swallow_a_short_definition_as_a_plural():
    parsed = parse_hannan_entry("biku [HL]K n 5, pl: mab-, Huddle. Itaiwo biku.")

    assert parsed["noun"]["plural_prefixes"] == ["mab-"]
    assert parsed["senses"][0]["definition"].startswith("Huddle")
