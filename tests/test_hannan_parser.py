import pytest

from shona_api.parsers.hannan import HannanParseError, parse_hannan_entry
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
