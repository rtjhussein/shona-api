import pytest
from django.contrib.contenttypes.models import ContentType

from shona_api.editorial.models import ReviewState
from shona_api.extraction.models import ExtractionUnit
from shona_api.extraction.services import (
    ExtractionUnitPublishError,
    publish_reviewed_extraction_unit,
)
from shona_api.figurative_language.models import FigurativeExpression
from shona_api.lexicon.models import Form, Lemma, NounClass, Sense, ToneRecord
from shona_api.parsers.hannan import parse_hannan_entry
from shona_api.sources.models import Source


@pytest.fixture
def hannan_source():
    return Source.objects.create(
        source_key="source_hannan",
        title="Hannan Dictionary",
        authority_level="Backbone lexical authority",
        rights_usage_note="Local-only source material; do not upload source file to git.",
        ingestion_style="Digitized dictionary-entry parsing into structured candidates.",
        current_filename="hannan_dictionary.pdf",
    )


@pytest.fixture
def approved_extraction_unit(hannan_source):
    raw_text = "-buda [H] vi i Come out. 2. Fade. > mbudo; rubudiko."
    parsed = parse_hannan_entry(raw_text)

    return ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text=raw_text,
        parser_output=parsed,
        confidence=0.97,
        review_state=ReviewState.APPROVED,
        provenance={"batch_id": "publish-path-fixture"},
    )


@pytest.mark.django_db
def test_reviewed_extraction_unit_publishes_lemma_senses_tone_and_forms(
    approved_extraction_unit,
):
    bundle = publish_reviewed_extraction_unit(approved_extraction_unit)

    approved_extraction_unit.refresh_from_db()
    assert bundle.extraction_unit == approved_extraction_unit
    assert bundle.lemma.headword == "-buda"
    assert bundle.lemma.part_of_speech_code == "vi"
    assert bundle.lemma.part_of_speech_label == "intransitive verb"
    assert bundle.lemma.review_state == ReviewState.PUBLISHED
    assert [sense.definition for sense in bundle.senses] == ["Come out.", "Fade."]
    assert [tone.pattern for tone in bundle.tone_records] == ["H"]
    assert sorted(form.form_text for form in bundle.forms) == [
        "mbudo",
        "rubudiko",
    ]
    assert approved_extraction_unit.review_state == ReviewState.PUBLISHED
    assert approved_extraction_unit.canonical_record == bundle.lemma
    assert approved_extraction_unit.canonical_record_content_type == ContentType.objects.get_for_model(Lemma)
    assert approved_extraction_unit.canonical_record_object_id == str(bundle.lemma.pk)


@pytest.mark.django_db
def test_publish_accepts_flat_gpt_derived_forms(hannan_source):
    unit = ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan:page_015:entry_054:bhema",
        raw_text="-bhema [L] v t Puff tobacco. < Nguni. > bhemo. cp -svuta KMZ.",
        parser_output={
            "headword": "-bhema",
            "headword_kind": "verb_stem",
            "part_of_speech": {"code": "v t", "label": "transitive verb"},
            "dialects": [],
            "comparative_bantu_marker": False,
            "tone_pattern": "L",
            "senses": [{"number": 1, "definition": "Puff tobacco."}],
            "derived_forms": ["bhemo"],
            "parse_metadata": {
                "parser": "gpt-5.5-thinking",
                "completeness": "parsed",
            },
        },
        parser_name="gpt-5.5-thinking",
        parser_status=ExtractionUnit.ParserStatus.PARSED,
        confidence=1.0,
        review_state=ReviewState.APPROVED,
    )

    bundle = publish_reviewed_extraction_unit(unit)

    assert [form.form_text for form in bundle.forms] == ["bhemo"]


@pytest.mark.django_db
def test_publish_preserves_derived_form_relation_evidence_from_objects(hannan_source):
    unit = ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan:page_015:entry_054:bhema",
        raw_text="-bhema [L] v t Puff tobacco. > bhemo. cp -svuta KMZ.",
        parser_output={
            "headword": "-bhema",
            "headword_kind": "verb_stem",
            "part_of_speech": {"code": "v t", "label": "transitive verb"},
            "dialects": [],
            "comparative_bantu_marker": False,
            "tone_pattern": "L",
            "senses": [{"number": 1, "definition": "Puff tobacco."}],
            "derived_forms": [
                {
                    "marker": ">",
                    "forms": ["bhemo"],
                    "source_note": "> bhemo.",
                    "raw_source": "> bhemo. cp -svuta KMZ.",
                },
                {
                    "marker": "<-",
                    "form": "mubhemi",
                    "source_note": "<- mubhemi.",
                },
            ],
            "parse_metadata": {
                "parser": "gpt-5.5-thinking",
                "completeness": "parsed",
            },
        },
        parser_name="gpt-5.5-thinking",
        parser_status=ExtractionUnit.ParserStatus.PARSED,
        confidence=1.0,
        review_state=ReviewState.APPROVED,
    )

    bundle = publish_reviewed_extraction_unit(unit)

    forms_by_text = {form.form_text: form for form in bundle.forms}
    assert sorted(forms_by_text) == ["bhemo", "mubhemi"]
    assert forms_by_text["bhemo"].provenance["derived_form_evidence"] == {
        "marker": ">",
        "relation": "headword_to_derived_form",
        "source_note": "> bhemo.",
        "raw_source": "> bhemo. cp -svuta KMZ.",
        "source_path": "derived_forms[0]",
    }
    assert forms_by_text["mubhemi"].provenance["derived_form_evidence"] == {
        "marker": "<-",
        "relation": "derived_form_to_headword",
        "source_note": "<- mubhemi.",
        "source_path": "derived_forms[1]",
    }


@pytest.mark.django_db
def test_publish_standardizes_hannan_examples_and_preserves_raw_shape(hannan_source):
    raw_examples = [
        {
            "text": "Ndinobuda muhotwe",
            "translation": "my nose is bleeding",
            "source_note": "Ndinobuda muhotwe: my nose is bleeding.",
        },
        "Ndabuda basa: I have left my employment.",
    ]
    unit = ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi Come out. Ndinobuda muhotwe: my nose is bleeding.",
        parser_output={
            "headword": "-buda",
            "headword_kind": "verb_stem",
            "part_of_speech": {"code": "vi", "label": "intransitive verb"},
            "dialects": [],
            "comparative_bantu_marker": False,
            "tone_pattern": "H",
            "senses": [
                {
                    "number": 1,
                    "definition": "Come out.",
                    "examples": raw_examples,
                }
            ],
            "derived_forms": [],
            "parse_metadata": {
                "parser": "gpt-5.5-thinking",
                "completeness": "parsed",
            },
        },
        parser_name="gpt-5.5-thinking",
        parser_status=ExtractionUnit.ParserStatus.PARSED,
        confidence=1.0,
        review_state=ReviewState.APPROVED,
    )

    bundle = publish_reviewed_extraction_unit(unit)

    assert bundle.senses[0].examples == [
        {
            "shona": "Ndinobuda muhotwe",
            "english": "my nose is bleeding",
            "source_note": "Ndinobuda muhotwe: my nose is bleeding.",
        },
        {
            "shona": "Ndabuda basa",
            "english": "I have left my employment.",
        },
    ]
    assert bundle.senses[0].provenance["raw_examples"] == raw_examples
    assert bundle.senses[0].provenance["example_schema_version"] == (
        "hannan-example-pair-v1"
    )


@pytest.mark.django_db
def test_publish_prefers_v2_dialect_scoped_tone_records(hannan_source):
    unit = ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan:page_041:entry_063:bhogodza",
        raw_text=(
            "-bhogodza [H KM; LHLH Z]KMZ v t Break (something into pieces). "
            "2. KZ Cause to cook a large amount."
        ),
        parser_output={
            "schema_version": "hannan-gpt-jsonl-v2",
            "headword": "-bhogodza",
            "headword_kind": "verb_stem",
            "part_of_speech": {"code": "v t", "label": "transitive verb"},
            "dialects": ["K", "M", "Z"],
            "comparative_bantu_marker": False,
            "tone_pattern": None,
            "tone_records": [
                {"pattern": "H", "dialects": ["K", "M"]},
                {"pattern": "LHLH", "dialects": ["Z"]},
            ],
            "noun": None,
            "senses": [
                {
                    "number": 1,
                    "definition": "Break (something into pieces).",
                    "dialects": [],
                    "grammar": [],
                    "examples": [],
                    "cross_references": [],
                },
                {
                    "number": 2,
                    "definition": "Cause to cook a large amount.",
                    "dialects": ["K", "Z"],
                    "grammar": [],
                    "examples": [],
                    "cross_references": [],
                },
            ],
            "derived_forms": [],
            "raw_entry_text": (
                "-bhogodza [H KM; LHLH Z]KMZ v t Break (something into pieces). "
                "2. KZ Cause to cook a large amount."
            ),
            "parse_metadata": {
                "parser": "gpt-5.5-thinking",
                "completeness": "parsed",
            },
            "normalized_headword": "bhogodza",
        },
        parser_name="gpt-5.5-thinking",
        parser_status=ExtractionUnit.ParserStatus.PARSED,
        confidence=1.0,
        review_state=ReviewState.APPROVED,
    )

    bundle = publish_reviewed_extraction_unit(unit)

    assert [(tone.pattern, tone.dialects) for tone in bundle.tone_records] == [
        ("H", ["K", "M"]),
        ("LHLH", ["Z"]),
    ]
    assert [sense.definition for sense in bundle.senses] == [
        "Break (something into pieces).",
        "Cause to cook a large amount.",
    ]


@pytest.mark.django_db
def test_publish_accepts_multiword_hannan_tone_patterns(hannan_source):
    unit = ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan:page_390:entry_057:munhundurwa_mukuru",
        raw_text="munhundurwa mukuru [LLHL LHH]KZ n 1, see munhombororo.",
        parser_output={
            "schema_version": "hannan-gpt-jsonl-v2",
            "headword": "munhundurwa mukuru",
            "headword_kind": "noun",
            "part_of_speech": {"code": "n", "label": "noun"},
            "dialects": ["K", "Z"],
            "comparative_bantu_marker": False,
            "tone_pattern": "LLHL LHH",
            "tone_records": [{"pattern": "LLHL LHH", "dialects": ["K", "Z"]}],
            "noun": {"classes": ["1"], "plural_prefixes": []},
            "senses": [
                {
                    "number": 1,
                    "definition": "see munhombororo.",
                    "dialects": [],
                    "grammar": [],
                    "examples": [],
                    "cross_references": [
                        {"type": "see", "target": "munhombororo", "dialects": []}
                    ],
                }
            ],
            "derived_forms": [],
            "raw_entry_text": (
                "munhundurwa mukuru [LLHL LHH]KZ n 1, see munhombororo."
            ),
            "parse_metadata": {
                "parser": "gpt-5.5-thinking",
                "completeness": "parsed",
            },
            "normalized_headword": "munhundurwa mukuru",
        },
        parser_name="gpt-5.5-thinking",
        parser_status=ExtractionUnit.ParserStatus.PARSED,
        confidence=1.0,
        review_state=ReviewState.APPROVED,
    )

    bundle = publish_reviewed_extraction_unit(unit)

    assert bundle.lemma.headword == "munhundurwa mukuru"
    assert [(tone.pattern, tone.dialects) for tone in bundle.tone_records] == [
        ("LLHL LHH", ["K", "Z"])
    ]


@pytest.mark.django_db
def test_publish_rejects_collapsed_numbered_sense_definitions(hannan_source):
    unit = ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan:page_041:entry_063:bhogodza",
        raw_text=(
            "-bhogodza [H KM; LHLH Z]KMZ v t Break (something into pieces). "
            "2. KZ Cause to cook a large amount."
        ),
        parser_output={
            "headword": "-bhogodza",
            "headword_kind": "verb_stem",
            "part_of_speech": {"code": "v t", "label": "transitive verb"},
            "dialects": ["K", "M", "Z"],
            "comparative_bantu_marker": False,
            "tone_pattern": "HKM;LHLHZ",
            "senses": [
                {
                    "number": 1,
                    "definition": (
                        "Break (something into pieces). "
                        "2. KZ Cause to cook a large amount."
                    ),
                    "dialects": [],
                    "grammar": [],
                    "examples": [],
                    "cross_references": [],
                }
            ],
            "derived_forms": [],
            "parse_metadata": {
                "parser": "gpt-5.5-thinking",
                "completeness": "parsed",
            },
        },
        parser_name="gpt-5.5-thinking",
        parser_status=ExtractionUnit.ParserStatus.PARSED,
        confidence=1.0,
        review_state=ReviewState.APPROVED,
    )

    with pytest.raises(ExtractionUnitPublishError, match="numbered sense markers"):
        publish_reviewed_extraction_unit(unit)


@pytest.mark.django_db
def test_publish_links_gpt_noun_class_when_seeded(hannan_source):
    noun_class = NounClass.objects.create(
        class_number="5",
        display_order=5,
        label="Class 5",
    )
    unit = ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan:page_015:entry_002:bharasa",
        raw_text="bharasa [LHL]M n 5, pl: mabh-, see bharasi.",
        parser_output={
            "headword": "bharasa",
            "headword_kind": "noun",
            "part_of_speech": {"code": "n", "label": "noun"},
            "dialects": ["M"],
            "comparative_bantu_marker": False,
            "tone_pattern": "LHL",
            "noun": {"classes": ["5"], "plural_prefixes": ["mabh-"]},
            "senses": [{"number": 1, "definition": "see bharasi."}],
            "derived_forms": [],
            "parse_metadata": {
                "parser": "gpt-5.5-thinking",
                "completeness": "parsed",
            },
        },
        parser_name="gpt-5.5-thinking",
        parser_status=ExtractionUnit.ParserStatus.PARSED,
        confidence=1.0,
        review_state=ReviewState.APPROVED,
    )

    bundle = publish_reviewed_extraction_unit(unit)

    assert bundle.lemma.noun_class == noun_class


@pytest.mark.django_db
def test_publish_creates_reviewable_madimikira_from_embedded_hannan_idiom(
    hannan_source,
):
    raw_text = (
        "munhu [LL]KKoMZ n 1 Person. 2. KMZ Part of the ear (antitragus). "
        "Munhu chivhudzi (KZ): commoner (having no authority)."
    )
    unit = ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan:page_100:entry_001:munhu",
        raw_text=raw_text,
        parser_output={
            "schema_version": "hannan-gpt-jsonl-v3",
            "headword": "munhu",
            "headword_kind": "noun",
            "part_of_speech": {"code": "n", "label": "noun"},
            "dialects": ["K", "Ko", "M", "Z"],
            "comparative_bantu_marker": False,
            "tone_pattern": "LL",
            "tone_records": [{"pattern": "LL", "dialects": ["K", "Ko", "M", "Z"]}],
            "noun": {"classes": ["1"], "plural_prefixes": [], "plural_classes": []},
            "senses": [
                {
                    "number": 1,
                    "definition": "Person.",
                    "dialects": [],
                    "grammar": [],
                    "examples": [],
                    "cross_references": [],
                },
                {
                    "number": 2,
                    "definition": "Part of the ear (antitragus).",
                    "dialects": ["K", "M", "Z"],
                    "grammar": [],
                    "examples": [],
                    "cross_references": [],
                },
            ],
            "idiomatic_expressions": [
                {
                    "expression_text": "Munhu chivhudzi",
                    "idiomatic_meaning": "commoner (having no authority).",
                    "english_rendering": "commoner (having no authority).",
                    "dialects": ["K", "Z"],
                    "linked_headwords": ["munhu"],
                    "source_sense_number": None,
                    "usage_note": "",
                }
            ],
            "derived_forms": [],
            "raw_entry_text": raw_text,
            "parse_metadata": {
                "parser": "gpt-5.5-thinking",
                "completeness": "parsed",
            },
            "normalized_headword": "munhu",
        },
        parser_name="gpt-5.5-thinking",
        parser_status=ExtractionUnit.ParserStatus.PARSED,
        confidence=1.0,
        review_state=ReviewState.APPROVED,
    )

    bundle = publish_reviewed_extraction_unit(unit)

    expression = FigurativeExpression.objects.get()
    assert bundle.figurative_expressions == [expression]
    assert expression.expression_text == "Munhu chivhudzi"
    assert expression.subtype == FigurativeExpression.Subtype.MADIMIKIRA
    assert expression.subtype_readiness == FigurativeExpression.SubtypeReadiness.ACTIVE
    assert expression.review_state == ReviewState.NEEDS_REVIEW
    assert expression.idiomatic_meaning == "commoner (having no authority)."
    assert expression.english_rendering == "commoner (having no authority)."
    assert list(expression.linked_lemmas.all()) == [bundle.lemma]
    assert expression.provenance["source_location_reference"] == (
        "hannan:page_100:entry_001:munhu"
    )
    assert expression.provenance["dialects"] == ["K", "Z"]
    assert expression.provenance["raw_idiom_payload"]["expression_text"] == (
        "Munhu chivhudzi"
    )
    assert bundle.extraction_unit.provenance["publication"][
        "figurative_expression_public_ids"
    ] == [expression.public_id]


@pytest.mark.django_db
def test_publish_copies_provenance_to_each_canonical_record(approved_extraction_unit):
    bundle = publish_reviewed_extraction_unit(approved_extraction_unit)

    shared_provenance_keys = {
        "source_key",
        "source_location_reference",
        "parser",
        "parser_status",
        "extraction_unit_id",
        "parser_uncertainties",
    }

    for record in [bundle.lemma, *bundle.senses, *bundle.tone_records, *bundle.forms]:
        assert shared_provenance_keys.issubset(record.provenance)
        assert record.provenance["source_key"] == "source_hannan"
        assert record.provenance["source_location_reference"] == (
            "hannan_dictionary.pdf:p.42:entry:-buda"
        )
        assert record.provenance["parser"] == "hannan-v1-fixture-parser"
        assert record.provenance["extraction_unit_id"] == str(approved_extraction_unit.pk)

    assert bundle.lemma.provenance["record_type"] == "lemma"
    assert bundle.senses[0].provenance["record_type"] == "sense"
    assert bundle.senses[0].provenance["sense_number"] == 1
    assert bundle.tone_records[0].provenance["record_type"] == "tone_record"
    assert bundle.forms[0].provenance["record_type"] == "form"


@pytest.mark.django_db
def test_publish_rejects_unapproved_extraction_unit(hannan_source):
    unit = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi i Come out. 2. Fade. > mbudo; rubudiko.",
        parser_output=parse_hannan_entry("-buda [H] vi i Come out. 2. Fade. > mbudo; rubudiko."),
        confidence=0.8,
        review_state=ReviewState.NEEDS_REVIEW,
    )

    with pytest.raises(ExtractionUnitPublishError, match="approved"):
        publish_reviewed_extraction_unit(unit)

    assert Lemma.objects.count() == 0
    assert Sense.objects.count() == 0
    assert ToneRecord.objects.count() == 0
    assert Form.objects.count() == 0


@pytest.mark.django_db
def test_publish_rejects_failed_parser_output(hannan_source):
    unit = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.99:line:12",
        raw_text="not a compact Hannan entry",
        parser_output=parse_hannan_entry("not a compact Hannan entry"),
        confidence=0.1,
        review_state=ReviewState.APPROVED,
    )

    assert unit.parser_status == ExtractionUnit.ParserStatus.FAILED

    with pytest.raises(ExtractionUnitPublishError, match="parser"):
        publish_reviewed_extraction_unit(unit)

    assert Lemma.objects.count() == 0
    assert Sense.objects.count() == 0
    assert ToneRecord.objects.count() == 0
    assert Form.objects.count() == 0


@pytest.mark.django_db
def test_publish_preserves_parser_uncertainty_in_provenance(hannan_source):
    parsed = parse_hannan_entry(
        "-buda [H] vi i Come out. 2. Fade. > mbudo; rubudiko."
    )
    parsed["uncertainties"] = [
        {
            "path": "senses[1].definition",
            "message": "Second sense was editorially inferred from the fixture.",
        }
    ]

    unit = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi i Come out. 2. Fade. > mbudo; rubudiko.",
        parser_output=parsed,
        confidence=0.74,
        review_state=ReviewState.APPROVED,
    )

    assert unit.parser_status == ExtractionUnit.ParserStatus.PARSED_WITH_UNCERTAINTY

    bundle = publish_reviewed_extraction_unit(unit)

    assert bundle.lemma.provenance["parser_uncertainties"] == parsed["uncertainties"]
    assert bundle.lemma.provenance["parser_status"] == unit.parser_status
    assert bundle.senses[1].provenance["parser_uncertainties"] == parsed["uncertainties"]


@pytest.mark.django_db
def test_publish_records_audit_hook_for_the_state_change(approved_extraction_unit):
    bundle = publish_reviewed_extraction_unit(approved_extraction_unit)

    assert bundle.audit_log.action == "record_state_changed"
    assert bundle.audit_log.target == approved_extraction_unit
    assert bundle.audit_log.metadata["canonical_record_public_id"] == bundle.lemma.public_id
