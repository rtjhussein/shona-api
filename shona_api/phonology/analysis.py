from .graphemes import DEFAULT_GRAPHEME_INVENTORY, GraphemeInventory, segment_graphemes
from .syllables import syllabify_word


def compute_phonology_fields(
    text: str, inventory: GraphemeInventory = DEFAULT_GRAPHEME_INVENTORY
) -> dict[str, object]:
    graphemes = segment_graphemes(text, inventory=inventory)
    syllables = syllabify_word(text, inventory=inventory)

    return {
        "phonology_inventory_version": inventory.version,
        "graphemes": graphemes,
        "grapheme_count": len(graphemes),
        "syllables": syllables,
        "syllable_count": len(syllables),
    }
