SEARCH_NORMALIZER_VERSION = "shona-orthography-normalizer-v1"


def normalize_search_query(value):
    normalized = " ".join(value.strip().split()).casefold()
    return normalized.removeprefix("-")
