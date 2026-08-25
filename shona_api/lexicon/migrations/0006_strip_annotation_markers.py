"""Recompute normalized headword/form fields with annotation-marker stripping.

Dagger (†) and asterisk (*) glyphs from Hannan source annotations leaked into
normalized_headword / normalized_form because the save path only removed the
leading hyphen. Marker glyphs break morphology lookups (ku†-kura) and
exact-match search. This migration recomputes both fields from their source
text using shona_api.phonology.orthography.strip_annotation_markers, which is
the same logic Lemma.save / Form.save now apply.
"""

from django.db import migrations

from shona_api.phonology.orthography import strip_annotation_markers


def recompute_normalized_fields(apps, schema_editor):
    lemma_model = apps.get_model("lexicon", "Lemma")
    form_model = apps.get_model("lexicon", "Form")

    for lemma in lemma_model.objects.iterator():
        normalized = strip_annotation_markers(lemma.headword)
        if normalized != lemma.normalized_headword:
            lemma.normalized_headword = normalized
            lemma.save(update_fields=["normalized_headword"])

    for form in form_model.objects.iterator():
        normalized = strip_annotation_markers(form.form_text)
        if normalized != form.normalized_form:
            form.normalized_form = normalized
            form.save(update_fields=["normalized_form"])


class Migration(migrations.Migration):
    dependencies = [
        ("lexicon", "0005_form_form_text_trgm_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(
            recompute_normalized_fields,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
