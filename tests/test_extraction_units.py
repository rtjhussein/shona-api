import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory

from shona_api.editorial.models import ReviewState
from shona_api.extraction.admin import ExtractionUnitAdmin, ExtractionUnitAdminForm
from shona_api.extraction.models import ExtractionUnit
from shona_api.lexicon.models import Lemma
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


@pytest.mark.django_db
def test_extraction_unit_stores_hannan_parser_output_as_review_candidate(
    hannan_source,
):
    raw_text = "-buda [H] vi Come out. 2. Rise (sun)."
    parsed = parse_hannan_entry(raw_text)

    unit = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text=raw_text,
        parser_output=parsed,
        confidence=0.82,
    )

    unit.refresh_from_db()
    assert unit.source == hannan_source
    assert unit.source_key == "source_hannan"
    assert unit.parser_name == "hannan-v1-fixture-parser"
    assert unit.parser_status == ExtractionUnit.ParserStatus.PARSED
    assert unit.review_state == ReviewState.NEEDS_REVIEW
    assert unit.parser_output["headword"] == "-buda"
    assert unit.parser_output["senses"][0]["definition"] == "Come out."
    assert unit.provenance == {
        "source_key": "source_hannan",
        "source_location_reference": "hannan_dictionary.pdf:p.42:entry:-buda",
        "parser": "hannan-v1-fixture-parser",
    }


@pytest.mark.django_db
def test_extraction_unit_represents_failed_parse_for_review(hannan_source):
    raw_text = "not a compact Hannan entry"
    parsed = parse_hannan_entry(raw_text)

    unit = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.99:line:12",
        raw_text=raw_text,
        parser_output=parsed,
        confidence=0.1,
    )

    assert unit.parser_status == ExtractionUnit.ParserStatus.FAILED
    assert unit.review_state == ReviewState.NEEDS_REVIEW
    assert unit.parser_output["errors"]


@pytest.mark.django_db
def test_extraction_unit_can_link_to_future_canonical_record(hannan_source):
    unit = ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi Come out.",
        parser_output={"headword": "-buda"},
        parser_name="hannan-v1-fixture-parser",
        parser_status=ExtractionUnit.ParserStatus.PARSED,
        confidence=0.75,
        canonical_record_content_type=ContentType.objects.get_for_model(Source),
        canonical_record_object_id=str(hannan_source.pk),
    )

    assert unit.canonical_record == hannan_source


def test_extraction_unit_admin_exposes_review_queue_filters():
    model_admin = ExtractionUnitAdmin(ExtractionUnit, admin.site)

    assert model_admin.list_display == (
        "display_headword",
        "source_location_reference",
        "batch_id",
        "parser_name",
        "parser_status",
        "review_state",
        "publication_state",
        "confidence",
        "created_at",
    )
    assert model_admin.list_filter == (
        "review_state",
        "parser_status",
        "source",
        "parser_name",
        "batch_id",
        "created_at",
    )
    assert model_admin.search_fields == (
        "parser_output__headword",
        "source__source_key",
        "source_location_reference",
        "batch_id",
        "raw_text",
        "parser_output",
    )


@pytest.mark.django_db
def test_extraction_unit_admin_uses_headword_as_clickable_label(hannan_source):
    unit = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi Come out.",
        parser_output=parse_hannan_entry("-buda [H] vi Come out."),
        confidence=0.95,
    )
    model_admin = ExtractionUnitAdmin(ExtractionUnit, admin.site)

    assert model_admin.list_display_links == ("display_headword",)
    assert model_admin.display_headword(unit) == "-buda"


@pytest.mark.django_db
def test_extraction_unit_admin_publication_labels(hannan_source):
    model_admin = ExtractionUnitAdmin(ExtractionUnit, admin.site)
    approved = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi Come out.",
        parser_output=parse_hannan_entry("-buda [H] vi Come out."),
        confidence=0.95,
        review_state=ReviewState.APPROVED,
    )


@pytest.fixture
def staff_user():
    return get_user_model().objects.create_user(
        username="staff",
        password="pass",
        is_staff=True,
    )
    invalid_published = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.43:entry:-bata",
        raw_text="-bata [H] vt Hold.",
        parser_output=parse_hannan_entry("-bata [H] vt Hold."),
        confidence=0.95,
        review_state=ReviewState.PUBLISHED,
    )
    linked = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.44:entry:-bika",
        raw_text="-bika [H] vt Cook.",
        parser_output=parse_hannan_entry("-bika [H] vt Cook."),
        confidence=0.95,
        review_state=ReviewState.PUBLISHED,
    )
    lemma = Lemma.objects.create(headword="-bika", review_state=ReviewState.PUBLISHED)
    linked.canonical_record = lemma
    linked.save()

    assert model_admin.publication_state(approved) == "Needs publication"
    assert model_admin.publication_state(invalid_published) == "Invalid published state"
    assert model_admin.publication_state(linked) == "Published to dictionary"


@pytest.mark.django_db
def test_extraction_unit_admin_form_rejects_unlinked_manual_published_state(
    hannan_source,
):
    unit = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi Come out.",
        parser_output=parse_hannan_entry("-buda [H] vi Come out."),
        confidence=0.95,
    )

    form = ExtractionUnitAdminForm(
        data={
            "source": hannan_source.pk,
            "source_location_reference": unit.source_location_reference,
            "raw_text": unit.raw_text,
            "parser_output": unit.parser_output,
            "parser_name": unit.parser_name,
            "parser_status": unit.parser_status,
            "confidence": unit.confidence,
            "review_state": ReviewState.PUBLISHED,
            "provenance": unit.provenance,
            "batch_id": unit.batch_id,
            "canonical_record_content_type": "",
            "canonical_record_object_id": "",
        },
        instance=unit,
    )

    assert not form.is_valid()
    assert "Use the publish action" in str(form.errors)


@pytest.mark.django_db
def test_extraction_unit_admin_action_publishes_approved_units(
    hannan_source,
    staff_user,
):
    unit = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi Come out.",
        parser_output=parse_hannan_entry("-buda [H] vi Come out."),
        confidence=0.95,
        review_state=ReviewState.APPROVED,
    )
    request = RequestFactory().post("/admin/extraction/extractionunit/")
    request.user = staff_user
    model_admin = ExtractionUnitAdmin(ExtractionUnit, admin.site)
    model_admin.message_user = lambda *args, **kwargs: None

    model_admin.publish_selected_units(request, ExtractionUnit.objects.filter(pk=unit.pk))
    unit.refresh_from_db()

    assert unit.review_state == ReviewState.PUBLISHED
    assert unit.canonical_record == Lemma.objects.get(headword="-buda")


@pytest.mark.django_db
def test_deleting_published_extraction_unit_deletes_its_published_lemma(
    hannan_source,
    staff_user,
):
    unit = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi Come out.",
        parser_output=parse_hannan_entry("-buda [H] vi Come out."),
        confidence=0.95,
        review_state=ReviewState.APPROVED,
    )
    request = RequestFactory().post("/admin/extraction/extractionunit/")
    request.user = staff_user
    model_admin = ExtractionUnitAdmin(ExtractionUnit, admin.site)
    model_admin.message_user = lambda *args, **kwargs: None
    model_admin.publish_selected_units(request, ExtractionUnit.objects.filter(pk=unit.pk))
    unit.refresh_from_db()
    lemma_pk = unit.canonical_record_object_id

    unit.delete()

    assert not ExtractionUnit.objects.filter(pk=unit.pk).exists()
    assert not Lemma.objects.filter(pk=lemma_pk).exists()


@pytest.mark.django_db
def test_bulk_deleting_published_extraction_units_deletes_their_published_lemmas(
    hannan_source,
    staff_user,
):
    units = []
    for headword in ["-buda", "-bata"]:
        units.append(
            ExtractionUnit.objects.create_from_parser_output(
                source=hannan_source,
                source_location_reference=f"hannan_dictionary.pdf:p.42:entry:{headword}",
                raw_text=f"{headword} [H] vt Hold.",
                parser_output=parse_hannan_entry(f"{headword} [H] vt Hold."),
                confidence=0.95,
                review_state=ReviewState.APPROVED,
            )
        )
    request = RequestFactory().post("/admin/extraction/extractionunit/")
    request.user = staff_user
    model_admin = ExtractionUnitAdmin(ExtractionUnit, admin.site)
    model_admin.message_user = lambda *args, **kwargs: None
    model_admin.publish_selected_units(
        request,
        ExtractionUnit.objects.filter(pk__in=[unit.pk for unit in units]),
    )
    lemma_pks = list(
        ExtractionUnit.objects.filter(pk__in=[unit.pk for unit in units]).values_list(
            "canonical_record_object_id",
            flat=True,
        )
    )

    ExtractionUnit.objects.filter(pk__in=[unit.pk for unit in units]).delete()

    assert not ExtractionUnit.objects.filter(pk__in=[unit.pk for unit in units]).exists()
    assert not Lemma.objects.filter(pk__in=lemma_pks).exists()


@pytest.mark.django_db
def test_deleting_one_extraction_unit_keeps_shared_canonical_lemma(hannan_source):
    lemma = Lemma.objects.create(
        headword="-buda",
        headword_kind=Lemma.HeadwordKind.VERB_STEM,
        review_state=ReviewState.PUBLISHED,
    )
    content_type = ContentType.objects.get_for_model(Lemma)
    first = ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi Come out.",
        parser_output={"headword": "-buda"},
        parser_name="hannan-v1-fixture-parser",
        parser_status=ExtractionUnit.ParserStatus.PARSED,
        confidence=0.95,
        review_state=ReviewState.PUBLISHED,
        canonical_record_content_type=content_type,
        canonical_record_object_id=str(lemma.pk),
    )
    second = ExtractionUnit.objects.create(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.43:entry:-buda",
        raw_text="-buda [H] vi Come out.",
        parser_output={"headword": "-buda"},
        parser_name="hannan-v1-fixture-parser",
        parser_status=ExtractionUnit.ParserStatus.PARSED,
        confidence=0.95,
        review_state=ReviewState.PUBLISHED,
        canonical_record_content_type=content_type,
        canonical_record_object_id=str(lemma.pk),
    )

    first.delete()

    assert not ExtractionUnit.objects.filter(pk=first.pk).exists()
    assert ExtractionUnit.objects.filter(pk=second.pk).exists()
    assert Lemma.objects.filter(pk=lemma.pk).exists()


@pytest.mark.django_db
def test_extraction_unit_admin_action_repairs_legacy_published_unlinked_unit(
    hannan_source,
    staff_user,
):
    unit = ExtractionUnit.objects.create_from_parser_output(
        source=hannan_source,
        source_location_reference="hannan_dictionary.pdf:p.42:entry:-buda",
        raw_text="-buda [H] vi Come out.",
        parser_output=parse_hannan_entry("-buda [H] vi Come out."),
        confidence=0.95,
        review_state=ReviewState.PUBLISHED,
    )
    request = RequestFactory().post("/admin/extraction/extractionunit/")
    request.user = staff_user
    model_admin = ExtractionUnitAdmin(ExtractionUnit, admin.site)
    model_admin.message_user = lambda *args, **kwargs: None

    model_admin.publish_selected_units(request, ExtractionUnit.objects.filter(pk=unit.pk))
    unit.refresh_from_db()

    assert unit.review_state == ReviewState.PUBLISHED
    assert unit.canonical_record == Lemma.objects.get(headword="-buda")
