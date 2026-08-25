"""Orthography helpers shared by lexicon storage and search normalisation.

Hannan source text annotates headwords with marker glyphs that are
typographic annotations, not part of the word:

- ``†`` marks Comparative Bantu reconstruction (captured separately in
  ``Lemma.comparative_bantu_marker``).
- ``*`` marks unattested/reconstructed forms in the same style.

These glyphs must never reach ``normalized_headword`` / ``normalized_form``
or search queries: they break morphology lookups (``ku†-kura`` analyses as
nothing) and exact-match search.
"""

ANNOTATION_MARKER_CHARS = "†*-"


def strip_annotation_markers(value: str) -> str:
    """Strip annotation glyphs and hyphens from the start of a headword/form.

    ``†-kura`` -> ``kura``; ``*-tubwaira`` -> ``tubwaira``; ``-buda`` ->
    ``buda``. Only leading glyphs are removed: Hannan places markers at the
    start of a headword, and mid-word hyphens are meaningful.
    """
    return value.strip().lstrip(ANNOTATION_MARKER_CHARS)
