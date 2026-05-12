from .graphemes import DEFAULT_GRAPHEME_INVENTORY, GraphemeInventory, segment_graphemes


VOWELS = frozenset({"a", "e", "i", "o", "u"})


def syllabify_word(
    word: str, inventory: GraphemeInventory = DEFAULT_GRAPHEME_INVENTORY
) -> list[str]:
    syllables = []
    current = []

    for grapheme in segment_graphemes(word, inventory=inventory):
        current.append(grapheme)
        if grapheme in VOWELS:
            syllables.append("".join(current))
            current = []

    if current:
        if syllables:
            syllables[-1] = f"{syllables[-1]}{''.join(current)}"
        else:
            syllables.append("".join(current))

    return syllables
