"""Canonical part-of-speech codes for lexical records.

Source parsers emit Hannan's abbreviations as written, so the same category
arrives spelled several ways (``vt`` / ``v t`` / ``vt&i`` / ``v t & i``). That
makes ``part_of_speech_code`` useless as a filter key: a client filtering on
``vt`` silently misses every entry the parser spelled ``v t``.

This module maps only *re-spellings of the same category* -- whitespace, case,
separators, and the source's own abbreviation variants. It deliberately does
not merge distinct categories: ``adj, pron`` (adjective or pronoun),
``interrog adv`` (interrogative adverb), ``enum`` (enumerative), and similar
compound labels keep their own codes, because collapsing them would discard a
grammatical distinction no source here authorises us to drop.
"""

# Alias -> canonical code. Every alias is a different spelling of the canonical
# category, never a different category.
CANONICAL_POS_ALIASES = {
    # Verb transitivity. Hannan writes the same word class as "vt", "v t",
    # "v t & i", "vt&i", "vt & i", "vt_i", "vi&t", "v i & t", "vt & vi",
    # "vt_vi", and "vit".
    "v t": "vt",
    "v i": "vi",
    "v t & i": "vti",
    "vt&i": "vti",
    "vt & i": "vti",
    "vt_i": "vti",
    "vi&t": "vti",
    "v i & t": "vti",
    "vt & vi": "vti",
    "vt_vi": "vti",
    "vit": "vti",
    # Defective verb, written out, abbreviated, and compounded.
    "defective v": "defective_v",
    "def v": "defective_v",
    "compound defective v": "defective_v",
    # Affix names.
    "sfx": "suffix",
    "v sfx": "suffix",
    "infx": "infix",
    # Editorial note kinds, and entries the parser could not classify.
    "orthographic_note": "note",
    "tense sign": "tense_sign",
    "": "unknown",
    "none": "unknown",
}

# Canonical codes in use. `POS_FILTERS` in the lexicon views accepts these, so
# the public filter stays in step with what records actually store.
CANONICAL_POS_CODES = frozenset(
    {
        "n",
        "vt",
        "vi",
        "vti",
        "v",
        "defective_v",
        "ideo",
        "adj",
        "adv",
        "pron",
        "conj",
        "inter",
        "cop",
        "poss",
        "quant",
        "demons",
        "sc",
        "oc",
        "suffix",
        "infix",
        "prefix",
        "stem",
        "note",
        "tense_sign",
        "unknown",
    }
)


def canonical_pos_code(value: object) -> str:
    """Return the canonical code for a parser-supplied part-of-speech code.

    Unknown values are returned stripped and case-folded rather than rewritten:
    an unrecognised code must stay visible in the data instead of being
    silently relabelled as something it may not be.
    """
    if not isinstance(value, str):
        return ""
    candidate = " ".join(value.split()).casefold()
    alias = CANONICAL_POS_ALIASES.get(candidate)
    if alias is not None:
        return alias
    return candidate
