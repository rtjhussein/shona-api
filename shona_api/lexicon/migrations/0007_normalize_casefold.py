"""Recompute normalized fields with casefold + annotation stripping.

Stored ``normalized_headword`` / ``normalized_form`` previously stripped only
leading annotation markers (dagger/asterisk/hyphen) without casefolding or
whitespace collapsing. Search queries via ``normalize_search_query`` casefold,
so capitalized Hannan headwords (proper nouns like ``Bhaibheri``, ``Agasiti``)
were unsearchable and flagged by ``qa_published_corpus`` as
``lemma_unsearchable`` (103 cases).

This migration recomputes both fields with the canonical
``shona_api.phonology.orthography.normalize_orthography`` helper, which is the
same logic ``Lemma.save`` / ``Form.save`` and ``normalize_search_query`` now
share.
"""

from django.db import migrations

from shona_api.phonology.orthography import normalize_orthography


def recompute_normalized_fields(apps, schema_editor):
    lemma_model = apps.get_model("lexicon", "Lemma")
    form_model = apps.get_model("lexicon", "Form")

    for lemma in lemma_model.objects.iterator():
        normalized = normalize_orthography(lemma.headword)
        if normalized != lemma.normalized_headword:
            lemma.normalized_headword = normalized
            lemma.save(update_fields=["normalized_headword"])

    for form in form_model.objects.iterator():
        normalized = normalize_orthography(form.form_text)
        if normalized != form.normalized_form:
            form.normalized_form = normalized
            form.save(update_fields=["normalized_form"])


class Migration(migrations.Migration):
    dependencies = [
        ("lexicon", "0006_strip_annotation_markers"),
    ]

    operations = [
        migrations.RunPython(
            recompute_normalized_fields,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
