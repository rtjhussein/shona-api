import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError

from shona_api.editorial.models import ReviewState
from shona_api.lexicon.admin import LemmaAdmin, NounClassAdmin
from shona_api.lexicon.models import Form, Lemma, NounClass, Sense, ToneRecord


@pytest.mark.django_db
def test_lexical_core_records_share_canonical_metadata_and_relationships():
    lemma = Lemma.objects.create(
        headword="-buda",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        part_of_speech_code="vi",
        part_of_speech_label="intransitive verb",
        dialects=["K", "Ko", "M", "Z"],
        provenance={"source_key": "source_hannan", "entry_locator": "fixture:buda"},
        review_state=ReviewState.APPROVED,
    )
    sense = Sense.objects.create(
        lemma=lemma,
        number=1,
        definition="Come out.",
        grammar=["vi"],
        provenance=lemma.provenance,
        review_state=ReviewState.APPROVED,
    )
    tone = ToneRecord.objects.create(
        lemma=lemma,
        pattern="H",
        notation_system=ToneRecord.NotationSystem.HANNAN_BRACKET,
        provenance=lemma.provenance,
        review_state=ReviewState.APPROVED,
    )
    form = Form.objects.create(
        lemma=lemma,
        sense=sense,
        form_text="mbudo",
        form_kind=Form.FormKind.DERIVED,
        grammar=["nominalized"],
        provenance=lemma.provenance,
        review_state=ReviewState.APPROVED,
    )

    assert lemma.public_id.startswith("lemma_")
    assert sense.public_id.startswith("sense_")
    assert tone.public_id.startswith("tone_")
    assert form.public_id.startswith("form_")
    assert lemma.revision == 1
    assert lemma.provenance["source_key"] == "source_hannan"
    assert list(lemma.senses.all()) == [sense]
    assert list(lemma.tone_records.all()) == [tone]
    assert list(lemma.forms.all()) == [form]
    assert form.sense == sense


@pytest.mark.django_db
def test_lemma_and_form_compute_phonology_fields_on_save():
    lemma = Lemma.objects.create(
        headword="Zimbabwe",
        headword_kind=Lemma.HeadwordKind.NOUN,
        part_of_speech_code="n",
    )
    form = Form.objects.create(
        lemma=lemma,
        form_text="chikoro",
        form_kind=Form.FormKind.VARIANT,
    )

    assert lemma.normalized_headword == "Zimbabwe"
    assert lemma.phonology_inventory_version == "shona-core-v1"
    assert lemma.graphemes == ["z", "i", "mb", "a", "bw", "e"]
    assert lemma.grapheme_count == 6
    assert lemma.syllables == ["zi", "mba", "bwe"]
    assert lemma.syllable_count == 3

    assert form.normalized_form == "chikoro"
    assert form.graphemes == ["ch", "i", "k", "o", "r", "o"]
    assert form.syllables == ["chi", "ko", "ro"]

    lemma.headword = "mhoro"
    lemma.save(update_fields=("headword",))
    lemma.refresh_from_db()

    assert lemma.normalized_headword == "mhoro"
    assert lemma.graphemes == ["mh", "o", "r", "o"]
    assert lemma.syllables == ["mho", "ro"]


@pytest.mark.django_db
def test_noun_class_records_store_concords_and_link_to_noun_lemmas():
    plural_class = NounClass.objects.create(
        class_number="2",
        display_order=2,
        label="va- people",
        nominal_prefix="va",
        subject_concord="va",
        object_concord="va",
        possessive_concord="ve",
        review_state=ReviewState.APPROVED,
    )
    noun_class = NounClass.objects.create(
        class_number="1",
        display_order=1,
        label="mu- person",
        nominal_prefix="mu",
        prefix_allomorphs=["mu", "m"],
        default_plural_class=plural_class,
        subject_concord="u",
        object_concord="mu",
        possessive_concord="wa",
        adjectival_concord="mu",
        relative_concord="u",
        associative_concord="wa",
        demonstrative_proximal="uyu",
        demonstrative_medial="uwo",
        demonstrative_distal="uya",
        additional_concords={"enumerative": "umwe"},
        dialect_overrides={"Z": {"subject_concord": "u"}},
        review_state=ReviewState.APPROVED,
    )
    lemma = Lemma.objects.create(
        headword="munhu",
        headword_kind=Lemma.HeadwordKind.NOUN,
        part_of_speech_code="n",
        noun_class=noun_class,
        review_state=ReviewState.APPROVED,
    )

    assert noun_class.public_id.startswith("nounclass_")
    assert str(noun_class) == "Class 1 mu- person"
    assert noun_class.default_plural_class == plural_class
    assert noun_class.prefix_allomorphs == ["mu", "m"]
    assert noun_class.additional_concords["enumerative"] == "umwe"
    assert noun_class.dialect_overrides["Z"]["subject_concord"] == "u"
    assert lemma.noun_class == noun_class
    assert list(noun_class.lemmas.all()) == [lemma]


@pytest.mark.django_db
def test_noun_class_validation_keeps_future_override_shape_predictable():
    noun_class = NounClass(
        class_number="9",
        prefix_allomorphs={"bad": "shape"},
        additional_concords=[],
        dialect_overrides=[],
    )

    with pytest.raises(ValidationError) as exc_info:
        noun_class.full_clean()

    assert set(exc_info.value.message_dict) == {
        "prefix_allomorphs",
        "additional_concords",
        "dialect_overrides",
    }


@pytest.mark.django_db
def test_only_noun_lemmas_can_link_to_noun_class():
    noun_class = NounClass.objects.create(class_number="5", display_order=5)
    lemma = Lemma(
        headword="-enda",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        noun_class=noun_class,
    )

    with pytest.raises(ValidationError) as exc_info:
        lemma.full_clean()

    assert exc_info.value.message_dict["noun_class"] == [
        "Only noun lemmas can be linked to a noun class."
    ]


def test_lexicon_admin_exposes_linked_records_for_crud():
    lemma_admin = LemmaAdmin(Lemma, admin.site)
    noun_class_admin = NounClassAdmin(NounClass, admin.site)

    assert lemma_admin.list_display == (
        "headword",
        "headword_kind",
        "noun_class",
        "part_of_speech_code",
        "review_state",
        "updated_at",
    )
    assert {inline.model for inline in lemma_admin.inlines} == {
        Sense,
        ToneRecord,
        Form,
    }
    assert noun_class_admin.list_display == (
        "class_number",
        "label",
        "nominal_prefix",
        "subject_concord",
        "default_plural_class",
        "review_state",
        "updated_at",
    )
