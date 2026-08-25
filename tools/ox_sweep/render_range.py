"""Render Hannan PDF pages to PNGs for vision extraction.

Usage: python local_batches/ox-sweep/render_range.py START END
Renders PDF pages START..END (1-based, inclusive) at 220 dpi into
local_batches/render_pages/hannan-pdf-page-XXXX.png
"""

import sys
from pathlib import Path

import fitz

PDF = Path(
    "shona_api/parsers/hannan_llm/source/Standard Shona Dictionary - Hannan.pdf"
)
OUT = Path("local_batches/render_pages")


def main(start: int, end: int) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(PDF)
    for p in range(start, end + 1):
        out = OUT / f"hannan-pdf-page-{p:04d}.png"
        if out.exists():
            continue
        pix = doc[p - 1].get_pixmap(dpi=220)
        pix.save(out)
        print(f"rendered {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]), int(sys.argv[2])))
