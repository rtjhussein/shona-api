"""Coverage ledger: per-page extraction state across the whole dictionary.

Usage: python local_batches/ox-sweep/coverage.py

Prints covered page ranges (from ExtractionUnit source locators), gaps within
the Shona-English scope (book 1-757 + addendum 997-1014), and unit counts by
review state.
"""

import re
from collections import defaultdict

import django

django.setup()

from shona_api.extraction.models import ExtractionUnit  # noqa: E402

SCOPE = set(range(1, 758)) | set(range(997, 1015))


def main() -> None:
    pages = set()
    state_by_page = defaultdict(lambda: defaultdict(int))
    for loc, state in ExtractionUnit.objects.values_list(
        "source_location_reference", "review_state"
    ):
        m = re.search(r"hannan:page_(\d+):", str(loc or ""))
        if not m:
            continue
        page = int(m.group(1))
        pages.add(page)
        state_by_page[page][state] += 1

    print(f"pages touched: {len(pages)} / {len(SCOPE)} scope pages")
    gaps = sorted(SCOPE - pages)
    print(f"gaps: {len(gaps)}")
    if gaps:
        ranges = []
        start = prev = gaps[0]
        for p in gaps[1:]:
            if p != prev + 1:
                ranges.append((start, prev))
                start = p
            prev = p
        ranges.append((start, prev))
        print(
            "gap ranges:",
            ", ".join(f"{a}-{b}" if a != b else str(a) for a, b in ranges),
        )
    extra = sorted(pages - SCOPE)
    if extra:
        print("pages outside scope (index/back matter?):", extra[:20])
    states = defaultdict(int)
    for page_states in state_by_page.values():
        for s, n in page_states.items():
            states[s] += n
    print("units by state:", dict(states))


if __name__ == "__main__":
    main()
