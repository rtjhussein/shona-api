from dataclasses import dataclass


@dataclass(frozen=True)
class GraphemeInventory:
    version: str
    graphemes: tuple[str, ...]

    @property
    def longest_first(self) -> tuple[str, ...]:
        return tuple(sorted(self.graphemes, key=len, reverse=True))


SHONA_CORE_V1_GRAPHEMES = (
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
)

# shona-core-v2 adds the consonant clusters that shona-core-v1 split into
# separate graphemes. Every addition below is either named in the product
# grapheme list (key_documents/prd_v5.md section 9.1) or attested in the
# published lexicon, recorded here with its headword count at the time of the
# change so a later editor can re-check the ones with no current witness:
#   ngw (518), ndw (68), nzw (63), dzw (73), mbw (308), ty (309), vw (5)
#   nkw (0), ndv (0), zvw (0), tshw (0), tsh (0), ph (0), nk (1)
# The pre-reform clusters (tsh, tshw) and the zero-witness clusters are carried
# because segmentation must handle query input and future sources, not only the
# currently published headwords. `mbw` covers core vocabulary such as "mbwa"
# (dog), which shona-core-v1 counted as four graphemes.
SHONA_CORE_V2_GRAPHEMES = SHONA_CORE_V1_GRAPHEMES + (
    "ngw",
    "ndw",
    "nkw",
    "nzw",
    "dzw",
    "ndv",
    "zvw",
    "tshw",
    "tsh",
    "mbw",
    "vw",
    "ty",
    "ph",
    "nk",
)

SHONA_CORE_V1_INVENTORY = GraphemeInventory(
    version="shona-core-v1",
    graphemes=SHONA_CORE_V1_GRAPHEMES,
)

# The inventory applied to new and recomputed records. Bumping this constant
# changes every stored `phonology_inventory_version`, `graphemes`,
# `grapheme_count`, `syllables`, and `syllable_count`; run
# `manage.py recompute_phonology` afterwards to bring stored records onto the
# new inventory.
DEFAULT_GRAPHEME_INVENTORY = GraphemeInventory(
    version="shona-core-v2",
    graphemes=SHONA_CORE_V2_GRAPHEMES,
)

GRAPHEME_INVENTORIES = {
    SHONA_CORE_V1_INVENTORY.version: SHONA_CORE_V1_INVENTORY,
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
