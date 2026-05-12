import pytest
from django.contrib import admin

from shona_api.editorial.models import ReviewState
from shona_api.lexicon.admin import LemmaAdmin
from shona_api.lexicon.models import Form, Lemma, Sense, ToneRecord


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


def test_lexicon_admin_exposes_linked_records_for_crud():
    lemma_admin = LemmaAdmin(Lemma, admin.site)

    assert lemma_admin.list_display == (
        "headword",
        "headword_kind",
        "part_of_speech_code",
        "review_state",
        "updated_at",
    )
    assert {inline.model for inline in lemma_admin.inlines} == {
        Sense,
        ToneRecord,
        Form,
    }
