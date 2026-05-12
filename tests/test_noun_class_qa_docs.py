from pathlib import Path


NOUN_CLASS_QA = Path("docs/language/noun_class_qa.md")


def test_noun_class_qa_document_covers_required_validation_workflow():
    content = NOUN_CLASS_QA.read_text(encoding="utf-8")

    required_phrases = [
        "# Noun-Class Validation and QA",
        "source_fortune",
        "source_maumbirwo",
        "Field Mapping",
        "Editorial Checklist",
        "Review Outcomes",
        "Admin Review Guidance",
        "Conflict Policy",
        "NounClass",
        "Lemma.noun_class",
        "dialect_overrides",
        "default_plural_class",
        "defer_morphology",
    ]

    for phrase in required_phrases:
        assert phrase in content

