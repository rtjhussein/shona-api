from dataclasses import dataclass


@dataclass(frozen=True)
class GraphemeInventory:
    version: str
    graphemes: tuple[str, ...]

    @property
    def longest_first(self) -> tuple[str, ...]:
        return tuple(sorted(self.graphemes, key=len, reverse=True))


DEFAULT_GRAPHEME_INVENTORY = GraphemeInventory(
    version="shona-core-v1",
    graphemes=(
        "dzv",
        "nzv",
        "tsv",
        "bv",
        "bw",
        "dy",
        "dz",
        "gw",
        "hw",
        "kw",
        "mb",
        "mh",
        "mw",
        "mv",
        "nd",
        "ng",
        "nh",
        "nj",
        "ny",
        "pf",
        "pw",
        "sh",
        "sv",
        "sw",
        "ts",
        "tw",
        "vh",
        "zh",
        "zv",
        "ch",
        "a",
        "e",
        "i",
        "o",
        "u",
        "b",
        "d",
        "f",
        "g",
        "h",
        "j",
        "k",
        "m",
        "n",
        "p",
        "r",
        "s",
        "t",
        "v",
        "w",
        "y",
        "z",
    ),
)

GRAPHEME_INVENTORIES = {
    DEFAULT_GRAPHEME_INVENTORY.version: DEFAULT_GRAPHEME_INVENTORY,
}


def get_grapheme_inventory(version: str) -> GraphemeInventory:
    try:
        return GRAPHEME_INVENTORIES[version]
    except KeyError as exc:
        raise ValueError(f"Unknown grapheme inventory version: {version}") from exc


def segment_graphemes(
    text: str, inventory: GraphemeInventory = DEFAULT_GRAPHEME_INVENTORY
) -> list[str]:
    normalized = text.casefold()
    segments = []
    index = 0

    while index < len(normalized):
        for grapheme in inventory.longest_first:
            if normalized.startswith(grapheme, index):
                segments.append(normalized[index : index + len(grapheme)])
                index += len(grapheme)
                break
        else:
            segments.append(normalized[index])
            index += 1

    return segments
