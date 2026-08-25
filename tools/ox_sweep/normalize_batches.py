"""Normalize GPT-5.5 batch files for import.

- Repairs locator convention: rows whose locator page != payload actual book
  page get the locator page rebuilt from the payload (entry_NNN and slug kept).
- Re-sequences entry numbers to per-page 001..N for pages NOT already in the
  DB (the June files use file-global sequencing; the DB convention restarts
  per page). DB-covered pages keep byte-identical locators so import dedupe
  matches.
- Resolves multi-covered pages by file supersession: for each page covered by
  multiple files, only the file with the most rows on that page keeps its
  rows; other files drop that page entirely. NO headword-level dedupe (Hannan
  legitimately repeats headwords on one page).
- Emits one normalized file per source file:
  out/gpt55/gpt55_book_<min>-<max>.jsonl
"""

import json
import re
from collections import defaultdict
from pathlib import Path

SRC = Path("shona_api/parsers/hannan_llm/llm_extracted_batches")
OUT = Path("local_batches/ox-sweep/out/gpt55")

LOC = re.compile(r"^hannan:page_(\d+):entry_(\d+):(.*)$")

# Pages already represented in the DB (locators must stay byte-identical for
# import dedupe). Everything else gets re-sequenced to per-page 001..N.
DB_PAGES = set(range(1, 20)) | set(range(21, 57)) | {390}


def actual_page(row: dict) -> int | None:
    page = row.get("primary_source_page")
    if page is None:
        page = row.get("provenance", {}).get("actual_page_number")
    return int(page) if page is not None else None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    page_files: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    parsed: dict[str, list[dict]] = {}
    for f in sorted(SRC.glob("*.jsonl")):
        rows = []
        for ln in f.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                row = json.loads(ln)
            except json.JSONDecodeError:
                continue
            rows.append(row)
            page = actual_page(row)
            if page is not None:
                page_files[page][f.name] += 1
        parsed[f.name] = rows

    # page -> winning file (most rows; ties -> lexicographically latest name)
    winner: dict[int, str] = {}
    for page, counts in page_files.items():
        if len(counts) > 1:
            winner[page] = max(counts, key=lambda n: (counts[n], n))

    dropped = 0
    repaired = 0
    for f in sorted(SRC.glob("*.jsonl")):
        kept = []
        pages = set()
        seq_by_page: dict[int, int] = {}
        for row in parsed[f.name]:
            page = actual_page(row)
            if page is None:
                print(f"{f.name}: row without actual page; skipping: {row.get('source_locator')}")
                continue
            if page in winner and winner[page] != f.name:
                dropped += 1
                continue
            m = LOC.match(str(row.get("source_locator", "")))
            if m and int(m.group(1)) != page:
                row["source_locator"] = f"hannan:page_{page:03d}:entry_{m.group(2)}:{m.group(3)}"
                repaired += 1
            if page not in DB_PAGES:
                seq_by_page[page] = seq_by_page.get(page, 0) + 1
                m2 = LOC.match(str(row["source_locator"]))
                if m2:
                    row["source_locator"] = (
                        f"hannan:page_{page:03d}:entry_{seq_by_page[page]:03d}:{m2.group(3)}"
                    )
            kept.append(row)
            pages.add(page)
        if not kept:
            continue
        out = OUT / f"gpt55_book_{min(pages):04d}-{max(pages):04d}.jsonl"
        out.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in kept) + "\n",
            encoding="utf-8",
        )
        print(f"{f.name}: {len(kept)} rows -> {out.name}")

    print(f"total: repaired locators={repaired}, dropped superseded rows={dropped}")


if __name__ == "__main__":
    main()
