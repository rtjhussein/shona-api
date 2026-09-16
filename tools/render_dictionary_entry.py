"""Render one Hannan entry from the scan, so a disputed reading can be read.

Extraction pipelines misread this scan -- `dikanwa [HHH]KZ n 5, pl: mad-` was
recorded as `madh-`, and `dimba`'s door entry the same way -- so where two
readings disagree the page itself decides. This renders the region around a
headword at 6x zoom, which is legible enough to settle it by eye.

PDF page = dictionary page + 24, verified against a unit whose provenance
records both (actual page 5, pdf page 29).

Usage::

    python tools/render_dictionary_entry.py 128 dikanwa /tmp/dikanwa.png

Then read the image, or ask a vision model about it:

    read("/tmp/dikanwa.png?q=What plural prefix does the dikanwa entry give?")
"""

from __future__ import annotations

import argparse
from pathlib import Path

import fitz

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PDF = REPOSITORY_ROOT / "key_documents" / "hannan_dictionary.pdf"
PAGE_OFFSET = 24


def render_entry(
    *,
    dict_page: int,
    headword: str,
    out_path: Path,
    pdf_path: Path = DEFAULT_PDF,
    zoom: float = 6.0,
) -> Path | None:
    """Write the region around ``headword`` and return the path, or None if absent."""
    if not pdf_path.exists():
        raise SystemExit(f"scan not found: {pdf_path}")

    document = fitz.open(pdf_path)
    page = document[dict_page + PAGE_OFFSET - 1]
    hits = page.search_for(headword)
    if not hits:
        return None

    box = hits[0]
    clip = fitz.Rect(
        max(box.x0 - 180, 0),
        max(box.y0 - 40, 0),
        min(box.x0 + 420, page.rect.x1),
        min(box.y0 + 130, page.rect.y1),
    )
    page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip).save(out_path)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dict_page", type=int, help="Dictionary page number.")
    parser.add_argument("headword")
    parser.add_argument("out", type=Path)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    args = parser.parse_args()

    written = render_entry(
        dict_page=args.dict_page, headword=args.headword, out_path=args.out, pdf_path=args.pdf
    )
    if written is None:
        print(f"no text hit for {args.headword!r} on pdf page {args.dict_page + PAGE_OFFSET}")
        return 1
    print(f"wrote {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
