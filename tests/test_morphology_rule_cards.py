import json
from pathlib import Path


RULE_CARD_README = Path("docs/morphology/rules/README.md")
RULE_CARD_DIR = Path("docs/morphology/rules/cards")

ALLOWED_RULE_DOMAINS = {
    "noun_class_inventory",
    "concords",
    "nominal_morphology",
    "morphophonemics",
    "verbal_constructions",
    "ideophonic_constructions",
    "derivational_rules",
}
ALLOWED_REVIEW_STATES = {"draft", "extracted", "approved", "published", "rejected"}
REQUIRED_API_SAFETY_FLAGS = {
    "analyzer_consumes",
    "generator_consumes",
    "public_endpoint_safe",
    "requires_review_before_public",
    "backward_compatibility",
}


def _load_rule_cards():
    assert RULE_CARD_DIR.exists()
    paths = sorted(RULE_CARD_DIR.glob("*.json"))
    assert paths
    return [(path, json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def test_morphology_rule_card_readme_defines_reviewable_contract():
    content = RULE_CARD_README.read_text(encoding="utf-8")

    required_phrases = [
        "# Morphology Rule Cards",
        "rule_card_schema_version",
        "source_key",
        "source_locator",
        "rule_domain",
        "qa.review_state",
        "evidence.examples",
        "api_safety.public_endpoint_safe",
        "Review States",
        "API Safety Gate",
    ]

    for phrase in required_phrases:
        assert phrase in content


def test_rule_cards_cover_initial_infinitive_and_extension_lanes():
    rule_ids = {card["rule_id"] for _, card in _load_rule_cards()}

    assert "fortune.verbal.infinitive.001" in rule_ids
    assert "fortune.verbal.extensions.001" in rule_ids


def test_rule_cards_preserve_required_source_review_and_api_safety_fields():
    for path, card in _load_rule_cards():
        assert card["rule_id"] == path.stem
        assert card["source_key"] == "source_fortune"
        assert card["source_locator"].strip()
        assert card["rule_domain"] in ALLOWED_RULE_DOMAINS
        assert card["rule_type"].strip()
        assert card["rule_summary"].strip()
        assert card["affected_rule_set"].startswith("morphology-rules-")

        examples = card["evidence"]["examples"]
        assert examples
        for example in examples:
            assert example["surface"].strip()
            assert example["status"].strip()

        qa = card["qa"]
        assert qa["review_state"] in ALLOWED_REVIEW_STATES
        assert isinstance(qa["extraction_confidence"], (int, float))
        assert qa["review_decision"].strip()

        api_safety = card["api_safety"]
        assert REQUIRED_API_SAFETY_FLAGS <= set(api_safety)
        assert isinstance(api_safety["analyzer_consumes"], bool)
        assert isinstance(api_safety["generator_consumes"], bool)
        assert isinstance(api_safety["public_endpoint_safe"], bool)
        assert isinstance(api_safety["requires_review_before_public"], bool)
        assert api_safety["backward_compatibility"].strip()


def test_draft_rule_cards_cannot_be_public_endpoint_safe():
    for _, card in _load_rule_cards():
        if card["qa"]["review_state"] != "draft":
            continue

        assert card["source_locator"].startswith("PENDING_FORTUNE_LOCATOR:")
        assert card["api_safety"]["analyzer_consumes"] is False
        assert card["api_safety"]["generator_consumes"] is False
        assert card["api_safety"]["public_endpoint_safe"] is False
        assert card["api_safety"]["requires_review_before_public"] is True


def test_public_endpoint_safe_cards_require_reviewed_source_locator():
    for _, card in _load_rule_cards():
        if not card["api_safety"]["public_endpoint_safe"]:
            continue

        assert card["qa"]["review_state"] in {"approved", "published"}
        assert not card["source_locator"].startswith("PENDING_FORTUNE_LOCATOR:")
        assert card["api_safety"]["requires_review_before_public"] is False
