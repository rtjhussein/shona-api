from .graphemes import DEFAULT_GRAPHEME_INVENTORY, GraphemeInventory, segment_graphemes
from .syllables import syllabify_word


def compute_phonology_fields(
    text: str, inventory: GraphemeInventory = DEFAULT_GRAPHEME_INVENTORY
) -> dict[str, object]:
    # A headword can hold more than one word (`bye bye`, `kwakwara kwakwara`).
    # Segmenting the whole string treated the space as a grapheme, so it inflated
    # grapheme_count and attached itself to the start of the next syllable
    # (`['bye', ' bye']`). A space separates words; it is not a segment of either
    # one, so each word is segmented on its own and the results are concatenated
    # into the flat lists the records already hold.
    words = text.split()
    graphemes = [
        grapheme for word in words for grapheme in segment_graphemes(word, inventory=inventory)
    ]
    syllables = [
        syllable for word in words for syllable in syllabify_word(word, inventory=inventory)
    ]

    return {
        "phonology_inventory_version": inventory.version,
        "graphemes": graphemes,
        "grapheme_count": len(graphemes),
        "syllables": syllables,
        "syllable_count": len(syllables),
    }
