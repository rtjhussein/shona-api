from pathlib import Path


FORTUNE_RULE_PLAN = Path("docs/morphology/fortune_rule_plan.md")


def test_fortune_rule_plan_covers_required_morphology_extraction_contract():
    content = FORTUNE_RULE_PLAN.read_text(encoding="utf-8")

    required_phrases = [
        "# Fortune Morphology Rule Extraction Plan",
        "source_fortune",
        "fortune_grammatical_constructions.pdf",
        "Rule Domains",
        "noun_class_inventory",
        "concords",
        "morphophonemics",
        "verbal_constructions",
        "Rule Card Shape",
        "Starter Rule Reference",
        "fortune.noun_class.inventory.001",
        "fortune.concord.subject.001",
        "fortune.morphophonemics.prefix_stem.001",
        "fortune.verbal.slots.001",
        "Analyzer and Generator Consumption",
        "Extraction QA Checklist",
    ]

    for phrase in required_phrases:
        assert phrase in content

