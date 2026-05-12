from pathlib import Path


ENRICHMENT_PLAN = Path("docs/figurative_language/enrichment_plan.md")


def test_figurative_language_enrichment_plan_covers_required_policy():
    content = ENRICHMENT_PLAN.read_text(encoding="utf-8")

    required_phrases = [
        "# Figurative Language Enrichment Plan",
        "source_shona_yedu",
        "source_tsumo_tsika",
        "Candidate Import Strategy",
        "Authority Policy",
        "Dedupe Guidance",
        "Theme Enrichment Guidance",
        "Future Madunhurirwa Lane",
        "candidate",
        "canonical",
    ]

    for phrase in required_phrases:
        assert phrase in content
