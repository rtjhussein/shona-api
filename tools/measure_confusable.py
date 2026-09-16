"""Measure a disputed headword character from the page itself, and print the
measurement beside the verdict.

The misread queue (`evaluation/scan_audit/headword-misread-candidates.tsv`) holds
published headwords one character away from the dictionary text's spelling, where
the characters are a confusable pair. Neither derived reading is the page, so this
tool reads the page: it renders the entry from its locator, calibrates on glyphs
of the same page whose identity is not in question, measures the disputed
character, and prints the measurement next to a verdict.

Two tests, both independent of either derived reading:

* **b against h** -- a printed ``b`` encloses a counter (a hole in the glyph),
  ``h`` never does. Count enclosures in the rendered glyph, and cross-check the
  count against the rest of the headword, whose letters both readings agree on.
* **v against w** -- the ink of a printed ``w`` is roughly half again as wide as
  a ``v``. Measure the disputed glyph's ink extent in points.

Neither threshold is hardcoded: both are re-derived on every run from a
calibration pool of the page's own bold glyphs of the two letters (topped up from
surrounding pages when the page is short of one of them), and the pool is scored
against its own derived boundary -- a calibration that cannot separate its own
letters is reported rather than used. Widths are normalised by type size because
the size varies page to page (8.94-9.68 pt over the 45 pages of the queue).

Both readings are compared with the page, never with each other: which spelling
the entry prints is read from the located entry's own headword, and a pixel
reading that contradicts it is reported as a failure rather than believed.

Usage::

    # one row, by page and spellings
    python tools/measure_confusable.py -p 104 -a chubvi -b chubwi

    # one row with its extraction unit, so the entry is located by its own line
    python tools/measure_confusable.py -p 151 -a dzomba -b dzomha \
        --locator hannan:page_151:entry_033:dzomba

    # every row of the misread queue
    python tools/measure_confusable.py --table evaluation/scan_audit/headword-misread-candidates.tsv

    # the 38 rows the earlier headword sample already settled, as a check on the tool
    python tools/measure_confusable.py --settled
"""

from __future__ import annotations

import argparse
import collections
import csv
import difflib
import json
import re
import sqlite3
import sys
import tempfile
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

TOOLS_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))
sys.path.insert(0, str(REPOSITORY_ROOT))

# The renderer is reused, not reimplemented: it owns the crop geometry and the
# headword-followed-by-a-bracket rule that keeps a crop on the intended entry.
from render_dictionary_entry import DEFAULT_PDF, PAGE_OFFSET, render_entry  # noqa: E402

DATABASE = "db/shona.sqlite3"
DEFAULT_TABLE = REPOSITORY_ROOT / "evaluation" / "scan_audit" / "headword-misread-candidates.tsv"

#: Zoom for the pixel measurement. A 9.6 pt glyph is ~230 px tall here: enough for
#: a counter about 0.9 pt across to clear MIN_HOLE_PX by an order of magnitude.
ZOOM = 24
#: Grey level below which a pixel counts as ink. The type is #111111 on white.
INK_LEVEL = 160
#: A hole smaller than this many pixels at ZOOM is speckle, not a counter.
MIN_HOLE_PX = 8
#: Glyphs of each letter wanted from the page itself before the pool is topped up.
MIN_CALIBRATION = 5
#: Pages searched either side of the disputed page for the other spelling.
NEAR_PAGES = 3
#: Pages searched when the near window does not carry the other spelling.
FAR_PAGES = 60
#: What the print puts before a headword: the verb marker, and the dagger that
#: flags an archaic form (`†mhemba`).
MARKERS = "-\u2020*"
#: How far apart the two calibrated medians must be, as a fraction of the wider
#: one, before ink width is allowed to choose between them. The v/w pair separates
#: by about half; b/h separate by about a twentieth in this typeface and are never
#: decided on width, only on counters.
MIN_WIDTH_SEPARATION = 0.15


@dataclass(frozen=True)
class Glyph:
    """One printed character, with the box the PDF gives it."""

    char: str
    rect: fitz.Rect
    line: int
    font: str
    size: float


@dataclass(frozen=True)
class Token:
    """A whitespace-delimited run of glyphs on one printed line."""

    start: int
    end: int
    text: str
    line: int

    @property
    def stripped(self) -> str:
        return self.text.lstrip(MARKERS).lower()

    @property
    def marker_len(self) -> int:
        return len(self.text) - len(self.text.lstrip(MARKERS))


@dataclass
class Ink:
    """What the pixels of one glyph box measure."""

    width_pt: float
    height_pt: float
    holes: int
    pixels: tuple[int, int]


@dataclass
class Calibration:
    """The pool the disputed glyph is judged against, and how well it separates."""

    widths: dict[str, list[float]] = field(default_factory=dict)  # letter -> ink width / type size
    holes: dict[str, list[int]] = field(default_factory=dict)  # letter -> counters per glyph
    pages: dict[str, list[int]] = field(default_factory=dict)  # letter -> page each sample came from

    def distinct(self, letter: str) -> list[float]:
        return sorted(set(round(value, 4) for value in self.widths.get(letter, [])))


@dataclass
class Row:
    published: str
    text: str
    page: int
    locator: str | None = None


@dataclass
class Finding:
    row: Row
    verdict: str
    measurement: str
    printed: str = ""
    note: str = ""
    calibration: str = ""


# --------------------------------------------------------------------- the page


def open_document(pdf: Path = DEFAULT_PDF) -> fitz.Document:
    if not pdf.exists():
        raise SystemExit(f"scan not found: {pdf}")
    return fitz.open(pdf)


def page_of(document: fitz.Document, dict_page: int) -> fitz.Page:
    """The PDF page a printed dictionary page sits on (PDF page = printed + 24)."""
    index = dict_page + PAGE_OFFSET - 1
    if not 0 <= index < document.page_count:
        raise SystemExit(f"page {dict_page} is outside the document")
    return document[index]


def page_glyphs(page: fitz.Page) -> list[Glyph]:
    """Every printed character on the page, in reading order, tagged with its line.

    The line tag matters: PyMuPDF's character stream carries no line break, so a
    tokeniser that ignores it runs the last word of one line into the first of the
    next and reports ``Z.dzomha`` as a headword, then measures the wrong glyph.
    """
    glyphs: list[Glyph] = []
    line = 0
    for block in page.get_text("rawdict")["blocks"]:
        if block["type"] != 0:
            continue
        for line_dict in block["lines"]:
            line += 1
            for span in line_dict["spans"]:
                for char in span["chars"]:
                    glyphs.append(
                        Glyph(
                            char=char["c"],
                            rect=fitz.Rect(char["bbox"]),
                            line=line,
                            font=span["font"],
                            size=span["size"],
                        )
                    )
    return glyphs


def tokens_of(glyphs: list[Glyph]) -> list[Token]:
    """Whitespace-delimited runs, never crossing a line break."""
    out: list[Token] = []
    index = 0
    while index < len(glyphs):
        if glyphs[index].char.isspace():
            index += 1
            continue
        end = index
        while end < len(glyphs) and not glyphs[end].char.isspace() and glyphs[end].line == glyphs[index].line:
            end += 1
        out.append(Token(start=index, end=end, text="".join(g.char for g in glyphs[index:end]), line=glyphs[index].line))
        index = end
    return out


def headword_tokens(glyphs: list[Glyph]) -> list[Token]:
    """Tokens a tone bracket follows on the same line -- printed headwords."""
    out = []
    for token in tokens_of(glyphs):
        tail = "".join(g.char for g in glyphs[token.end : token.end + 3] if g.line == token.line).lstrip()
        if tail.startswith("[") and any(ch.isalpha() for ch in token.text):
            out.append(token)
    return out


def window_text(glyphs: list[Glyph], start: int, end: int) -> str:
    """Page text from one headword to the next, line breaks kept apart."""
    parts: list[str] = []
    line = glyphs[start].line
    for glyph in glyphs[start:end]:
        if glyph.line != line:
            parts.append(" ")
            line = glyph.line
        parts.append(glyph.char)
    return "".join(parts)


def words(text: str) -> list[str]:
    cleaned = text.lower().replace("\u2010", "-").replace("\u2011", "-")
    return re.sub(r"[^a-z0-9' -]", " ", cleaned).split()


def entry_windows(glyphs: list[Glyph]) -> list[tuple[Token, str]]:
    """Each printed headword with the text of its entry (up to the next headword)."""
    heads = headword_tokens(glyphs)
    out = []
    for index, head in enumerate(heads):
        end = heads[index + 1].start if index + 1 < len(heads) else min(head.start + 400, len(glyphs))
        out.append((head, window_text(glyphs, head.start, end)))
    return out


def locate_entry(glyphs: list[Glyph], raw_text: str) -> tuple[Token | None, float, float]:
    """The printed entry an extraction unit read, by word-level match on its text.

    The headword itself may be the misread one, so the match is scored over the
    whole entry -- bracket, gloss and all -- and the runner-up score comes back
    with it: two windows that score alike mean the entry was not identified, and
    the caller gets to say so instead of measuring the wrong line.
    """
    target = words(raw_text)
    if not target:
        return None, 0.0, 0.0
    scored = [(difflib.SequenceMatcher(None, target, words(text)).ratio(), head) for head, text in entry_windows(glyphs)]
    if not scored:
        return None, 0.0, 0.0
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[0][1], scored[0][0], (scored[1][0] if len(scored) > 1 else 0.0)


# -------------------------------------------------------------------- measuring


def measure(page: fitz.Page, rect: fitz.Rect, zoom: int = ZOOM) -> Ink | None:
    """Ink extent and enclosed counters of one glyph box, from the rendered page."""
    if rect.is_empty:
        return None
    pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=rect)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples).convert("L")
    width, height = image.size
    pixels = image.load()
    ink = [[pixels[x, y] < INK_LEVEL for x in range(width)] for y in range(height)]
    columns = [x for x in range(width) if any(ink[y][x] for y in range(height))]
    rows = [y for y in range(height) if any(ink[y])]
    if not columns or not rows:
        return None
    holes: list[int] = []
    seen = [[False] * width for _ in range(height)]
    for y0 in range(height):
        for x0 in range(width):
            if ink[y0][x0] or seen[y0][x0]:
                continue
            queue = deque([(x0, y0)])
            seen[y0][x0] = True
            area = 0
            touches_border = False
            while queue:
                x, y = queue.popleft()
                area += 1
                if x in (0, width - 1) or y in (0, height - 1):
                    touches_border = True
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < width and 0 <= ny < height and not ink[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        queue.append((nx, ny))
            if not touches_border and area >= MIN_HOLE_PX:
                holes.append(area)
    return Ink(
        width_pt=(max(columns) - min(columns) + 1) / zoom,
        height_pt=(max(rows) - min(rows) + 1) / zoom,
        holes=len(holes),
        pixels=(width, height),
    )


def median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


# ------------------------------------------------------------------ calibrating


def calibrate(
    document: fitz.Document,
    page: fitz.Page,
    glyphs: list[Glyph],
    letters: tuple[str, str],
    font: str,
    size: float,
    skip: int | None,
) -> Calibration:
    """Measure the two letters on this page, topping up from surrounding pages.

    The pool is bold glyphs of the two letters -- the headword type, which is the
    type the disputed glyph is set in. A Hannan page can be short of one of them
    (page 82 carries no bold ``v`` and no bold ``h``), so a thin pool is topped up
    from the surrounding pages and the split is reported with the measurement.
    """
    calibration = Calibration()
    wanted = set(letters)
    seen_glyphs: set[tuple[int, float]] = set()

    def collect(source: fitz.Page, source_glyphs: list[Glyph], on_page: bool) -> None:
        for index, glyph in enumerate(source_glyphs):
            letter = glyph.char.lower()
            if letter not in wanted or glyph.font != font or abs(glyph.size - size) > 0.3:
                continue
            if source is page and index == skip:
                continue
            measured = measure(page if source is page else source, glyph.rect)
            if measured is None:
                continue
            calibration.widths.setdefault(letter, []).append(measured.width_pt / glyph.size)
            calibration.holes.setdefault(letter, []).append(measured.holes)
            if on_page:
                calibration.pages.setdefault(letter, []).append(source.number + 1 - PAGE_OFFSET)

    collect(page, glyphs, True)
    if any(len(calibration.widths.get(letter, [])) < MIN_CALIBRATION for letter in wanted):
        for offset in range(1, 6):
            for number in (page.number + offset, page.number - offset):
                if not 0 <= number < document.page_count:
                    continue
                other = document[number]
                collect(other, page_glyphs(other), False)
            if all(len(calibration.widths.get(letter, [])) >= MIN_CALIBRATION for letter in wanted):
                break
    return calibration


def calibration_line(calibration: Calibration, letters: tuple[str, str]) -> str:
    """The pool, its split, and whether the derived boundary separates it."""
    parts = []
    for letter in sorted(letters, key=lambda c: median(calibration.widths.get(c, [0.0]))):
        widths = calibration.widths.get(letter, [])
        if not widths:
            parts.append(f"{letter}: no glyphs")
            continue
        on_page = len(calibration.pages.get(letter, []))
        origin = f"{on_page} on page" + (f", {len(widths) - on_page} nearby" if len(widths) > on_page else "")
        parts.append(
            f"{letter} median {median(widths):.3f} em (range {min(widths):.3f}-{max(widths):.3f}), "
            f"counters {sorted(set(calibration.holes.get(letter, [])))}, n={len(widths)} [{origin}]"
        )
    return "calibration: " + "; ".join(parts) + " | " + score_pool(calibration, letters)


def score_pool(calibration: Calibration, letters: tuple[str, str]) -> str:
    narrow, wide = sorted(letters, key=lambda c: median(calibration.widths.get(c, [0.0])))
    if not calibration.widths.get(narrow) or not calibration.widths.get(wide):
        return "pool incomplete"
    boundary = (median(calibration.widths[narrow]) + median(calibration.widths[wide])) / 2
    right = total = 0
    for letter, values in calibration.widths.items():
        for value in values:
            total += 1
            right += (value > boundary) == (letter == wide)
    return f"boundary {boundary:.3f} em, pool scored {right}/{total} on its own letters"


# ---------------------------------------------------------------------- verdict


def decide(
    ink: Ink,
    size: float,
    published_letter: str,
    text_letter: str,
    calibration: Calibration,
    counters_rest: int,
    rest_note: str,
) -> tuple[str | None, str]:
    """Which of the two letters the disputed glyph is, from the calibrated tests.

    Counters decide when the two calibrations separate on them (the b/h case);
    ink width decides otherwise (the v/w case), and only if the calibrated ranges
    are disjoint. Anything else is returned as no decision, with the reason.
    """
    width = {letter: calibration.widths.get(letter, []) for letter in (published_letter, text_letter)}
    holes = {letter: calibration.holes.get(letter, []) for letter in (published_letter, text_letter)}
    counter_test = all(holes.values()) and not set(holes[published_letter]) & set(holes[text_letter])

    if counter_test:
        line = (
            f"counters: disputed glyph has {ink.holes}, calibrated "
            + ", ".join(f"{letter}={sorted(set(holes[letter]))} (n={len(holes[letter])})" for letter in (published_letter, text_letter))
            + f"; rest of headword {counters_rest} counters ({rest_note})"
        )
        for letter in (published_letter, text_letter):
            if ink.holes in set(holes[letter]):
                return letter, line + f" -> disputed letter is {letter!r}"
        return None, line + f" -> {ink.holes} counters is neither {published_letter!r} nor {text_letter!r}"

    if not all(width.values()):
        return None, f"no calibration pool for {published_letter}/{text_letter} on this page"

    narrow, wide = sorted((published_letter, text_letter), key=lambda c: median(width[c]))
    boundary = (median(width[narrow]) + median(width[wide])) / 2
    line = (
        f"ink width: disputed glyph {ink.width_pt:.2f} pt = {ink.width_pt / size:.3f} em; calibrated "
        f"{published_letter} {median(width[published_letter]):.3f} em, {text_letter} {median(width[text_letter]):.3f} em, "
        f"boundary {boundary:.3f} em = {boundary * size:.2f} pt; counters {ink.holes} (uninformative here)"
    )
    separation = (median(width[wide]) - median(width[narrow])) / median(width[wide])
    if separation < MIN_WIDTH_SEPARATION:
        return None, line + f" -> the two calibrated widths are only {separation:.1%} apart, too close to choose"
    if min(width[wide]) <= max(width[narrow]):
        return None, line + f" -> calibrated ranges overlap ({narrow} up to {max(width[narrow]):.3f} em, {wide} from {min(width[wide]):.3f} em)"
    return (wide if ink.width_pt / size > boundary else narrow), line


def printed_headword_pages(
    document: fitz.Document, spelling: str, first: int, last: int, cache: dict[int, set[str]]
) -> list[int]:
    """Printed pages in range whose headwords include ``spelling``."""
    found = []
    limit = document.page_count - PAGE_OFFSET
    for number in range(max(first, 1), min(last, limit) + 1):
        if number not in cache:
            page = page_of(document, number)
            cache[number] = {token.stripped for token in headword_tokens(page_glyphs(page))}
        if spelling in cache[number]:
            found.append(number)
    return found


def disputed_index(published: str, text: str) -> int | None:
    """Where the two spellings differ, or None when they are not one pair apart."""
    left, right = published.lstrip(MARKERS), text.lstrip(MARKERS)
    if len(left) != len(right):
        return None
    differing = [index for index, (a, b) in enumerate(zip(left, right)) if a != b]
    return differing[0] if len(differing) == 1 else None


def matching_occurrences(glyphs: list[Glyph], spelling: str) -> list[Token]:
    """Printed headword tokens that spell ``spelling`` (marker and case aside)."""
    return [token for token in headword_tokens(glyphs) if token.stripped == spelling.lstrip(MARKERS).lower()]


def measure_printed_spelling(
    page: fitz.Page, glyphs: list[Glyph], spelling: str, index: int
) -> tuple[str, float | None, int | None] | None:
    """Measure the disputed glyph as printed in an occurrence of ``spelling``."""
    hits = matching_occurrences(glyphs, spelling)
    if not hits:
        return None
    token = hits[0]
    position = token.start + token.marker_len + index
    if position >= token.end:
        return None
    ink = measure(page, glyphs[position].rect)
    if ink is None:
        return None
    return token.text, ink.width_pt, ink.holes


# ------------------------------------------------------------------ one row


def page_glyph_cache(document: fitz.Document, number: int, cache: dict[int, list[Glyph]]) -> list[Glyph]:
    if number not in cache:
        cache[number] = page_glyphs(page_of(document, number))
    return cache[number]


def run_row(
    document: fitz.Document,
    conn: sqlite3.Connection,
    row: Row,
    *,
    crops: Path | None,
    headword_cache: dict[int, set[str]],
    glyph_cache: dict[int, list[Glyph]],
    calibration_cache: dict[tuple[int, str, str], Calibration],
) -> Finding:
    page = page_of(document, row.page)
    glyphs = page_glyph_cache(document, row.page, glyph_cache)

    raw_text = unit_raw_text(conn, row.locator) if row.locator else None
    located: Token | None = None
    ratio = second = float("nan")
    if raw_text:
        located, ratio, second = locate_entry(glyphs, raw_text)
    if located is None:
        candidates = matching_occurrences(glyphs, row.published) + matching_occurrences(glyphs, row.text)
        if not candidates:
            return Finding(row, "unreadable", "no printed headword matches either spelling", note="not located")
        located = candidates[0]

    index = disputed_index(row.published, row.text)
    if index is None:
        return Finding(row, "unreadable", "the two spellings differ in more than one character", printed=located.text)

    published_stripped = row.published.lstrip(MARKERS).lower()
    text_stripped = row.text.lstrip(MARKERS).lower()
    body = located.stripped
    if body != published_stripped and body != text_stripped:
        return Finding(
            row,
            "unreadable",
            f"located {located.text!r} at score {ratio:.2f}, which is not either spelling",
            printed=located.text,
        )
    if body[:index] != published_stripped[:index] or body[index + 1 :] != published_stripped[index + 1 :]:
        return Finding(
            row,
            "unreadable",
            f"located {located.text!r}, which differs from the pair somewhere other than the disputed character",
            printed=located.text,
        )

    published_letter = published_stripped[index]
    text_letter = text_stripped[index]
    glyph = glyphs[located.start + located.marker_len + index]
    ink = measure(page, glyph.rect)
    if ink is None:
        return Finding(row, "unreadable", "the disputed glyph rendered no ink", printed=located.text)

    key = (row.page, published_letter, text_letter)
    if key not in calibration_cache:
        calibration_cache[key] = calibrate(
            document,
            page,
            glyphs,
            (published_letter, text_letter),
            glyph.font,
            glyph.size,
            located.start + located.marker_len + index,
        )
    calibration = calibration_cache[key]

    # The headword's other glyphs: both readings agree on every one of them, so
    # their counters are not in question and carry into each spelling's prediction.
    rest = 0
    rest_glyphs = 0
    for offset in range(located.start, located.end):
        if offset == located.start + located.marker_len + index:
            continue
        measured = measure(page, glyphs[offset].rect)
        if measured is not None:
            rest += measured.holes
            rest_glyphs += 1

    chosen, line = decide(
        ink,
        glyph.size,
        published_letter,
        text_letter,
        calibration,
        rest,
        f"{rest_glyphs} of {located.end - located.start - 1} printed, both readings agree on them",
    )

    where = (
        f"page {row.page} "
        + (f"raster ({len(page.get_images(full=True))} images)" if page.get_images(full=True) else "digital (0 raster images)")
    )
    located_note = (
        f"located {located.text!r} score {ratio:.2f} (next {second:.2f}, {'match' if ratio >= 0.55 else 'WEAK MATCH'})"
        if raw_text
        else f"no locator; located by spelling ({located.text!r})"
    )
    detail = f"{line} | {where} | {located_note}"

    if chosen is None:
        return Finding(row, "unreadable", detail, printed=located.text, calibration=calibration_line(calibration, (published_letter, text_letter)))
    if body[index] != chosen:
        return Finding(
            row,
            "unreadable",
            detail + f" | pixels read {chosen!r} where the located token spells {body[index]!r}",
            printed=located.text,
            calibration=calibration_line(calibration, (published_letter, text_letter)),
        )

    other = text_stripped if chosen == published_letter else published_stripped
    if body == text_stripped:
        verdict = "published wrong"
        note = f"the entry prints {located.text!r}"
        twins = printed_headword_pages(
            document, published_stripped, row.page - NEAR_PAGES, row.page + NEAR_PAGES, headword_cache
        )
        if twins:
            note += f"; the published spelling is also printed as a headword on {_pages(twins)}"
    else:
        near = printed_headword_pages(document, other, row.page - NEAR_PAGES, row.page + NEAR_PAGES, headword_cache)
        far = near or printed_headword_pages(document, other, row.page - FAR_PAGES, row.page + FAR_PAGES, headword_cache)
        if near:
            verdict = "both legible, distinct words"
            note = f"{other!r} is printed as a headword on {_pages(near)}"
        elif far:
            verdict = "both legible, distinct words"
            note = f"{other!r} is printed as a headword on {_pages(far)}, outside the {NEAR_PAGES}-page window"
        else:
            verdict = "text wrong"
            note = f"{other!r} is printed as a headword on none of pages {max(row.page - FAR_PAGES, 1)}-{row.page + FAR_PAGES}"

    paired = measure_printed_spelling(page, glyphs, other, index)
    if paired:
        note += f"; the printed {paired[0]!r} on this page measures {paired[1]:.2f} pt/{paired[2]} counters"

    if crops is not None:
        written = render_entry(
            dict_page=row.page, headword=located.text, out_path=crops / f"p{row.page:04d}_{located.stripped}.png"
        )
        note += f"; crop {written.name}" if written else "; crop not written"

    return Finding(
        row,
        verdict,
        detail,
        printed=located.text,
        note=note,
        calibration=calibration_line(calibration, (published_letter, text_letter)),
    )


def unit_raw_text(conn: sqlite3.Connection, locator: str) -> str | None:
    row = conn.execute(
        "select raw_text from extraction_extractionunit where source_location_reference = ?", (locator,)
    ).fetchone()
    return row[0] if row else None


def _pages(numbers: list[int]) -> str:
    if not numbers:
        return "no page"
    if len(numbers) == 1:
        return f"p{numbers[0]}"
    return "pp" + ", ".join(str(number) for number in numbers[:6]) + ("..." if len(numbers) > 6 else "")


# ----------------------------------------------------------------------- inputs


def read_table(path: Path) -> list[Row]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for record in csv.DictReader(handle, delimiter="\t"):
            rows.append(
                Row(
                    published=record["published_headword"],
                    text=record["text_spelling"],
                    page=int(record["source_locator"].split(":")[1].split("_")[1]),
                    locator=record["source_locator"],
                )
            )
    return rows


#: The 38 rows the earlier headword sample settled against the page (2026-09-16),
#: with the verdict it recorded. 35 are `both legible, distinct words` -- the
#: negative controls, run here so the tool is checked against a known answer
#: before its output on the 60-row queue is believed -- and 3 are `published
#: wrong`, the positive controls.
SETTLED: tuple[tuple[str, str, int, str], ...] = (
    ("bumba", "bumha", 28, "both legible, distinct words"),
    ("bumha", "bumba", 29, "both legible, distinct words"),
    ("bwabwa", "bwahwa", 43, "both legible, distinct words"),
    ("bwahwa", "bwabwa", 43, "both legible, distinct words"),
    ("chimbu", "chimhu", 76, "both legible, distinct words"),
    ("chimhu", "chimbu", 77, "both legible, distinct words"),
    ("demhe", "dembe", 116, "both legible, distinct words"),
    ("gumhi", "gumbi", 199, "both legible, distinct words"),
    ("kumbi", "kumhi", 289, "both legible, distinct words"),
    ("kumhi", "kumbi", 289, "both legible, distinct words"),
    ("mhomho", "mhombo", 355, "both legible, distinct words"),
    ("mushumha", "mushumba", 408, "both legible, distinct words"),
    ("-nyemha", "nyemba", 486, "both legible, distinct words"),
    ("umhombo", "umbombo", 701, "both legible, distinct words"),
    ("dzimbahwe", "dzimbabwe", 148, "published wrong"),
    ("shakahuni", "shakabuni", 599, "published wrong"),
    ("fombo", "fomho", 168, "both legible, distinct words"),
    ("hungurubwe", "hunguruhwe", 229, "both legible, distinct words"),
    ("bvubvuva", "bvubvuwa", 38, "both legible, distinct words"),
    ("bvubvuwa", "bvubvuva", 38, "both legible, distinct words"),
    ("chava", "chawa", 53, "both legible, distinct words"),
    ("chawa", "chava", 53, "both legible, distinct words"),
    ("chubvi", "chubwi", 104, "both legible, distinct words"),
    ("dzva", "dzwa", 154, "both legible, distinct words"),
    ("hava", "hawa", 220, "both legible, distinct words"),
    ("kiva", "kiwa", 274, "both legible, distinct words"),
    ("ndowe", "ndove", 443, "both legible, distinct words"),
    ("nzwa", "nzva", 498, "published wrong"),
    ("tosve", "toswe", 657, "both legible, distinct words"),
    ("tsva", "tswa", 677, "both legible, distinct words"),
    ("zereva", "zerewa", 743, "both legible, distinct words"),
    ("bava", "bawa", 9, "both legible, distinct words"),
    ("buva", "buwa", 32, "both legible, distinct words"),
    ("chipfuva", "chipfuwa", 86, "both legible, distinct words"),
    ("chivi", "chiwi", 100, "both legible, distinct words"),
    ("kuve", "kuwe", 296, "both legible, distinct words"),
    ("puva", "puwa", 547, "both legible, distinct words"),
    ("tuvi", "tuwi", 691, "both legible, distinct words"),
)

#: Ink widths in points the earlier sample recorded for pages that print both
#: spellings, with the position of the disputed letter: the tool's numbers are
#: compared against these, letter by letter.
SETTLED_WIDTHS: dict[tuple[int, str], tuple[float, int]] = {
    (104, "chubvi"): (5.00, 4),
    (104, "chubwi"): (7.58, 4),
    (443, "ndove"): (4.96, 3),
    (443, "ndowe"): (7.50, 3),
    (86, "chipfuva"): (5.08, 6),
    (86, "chipfuwa"): (7.71, 6),
}


# ------------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--table", type=Path, help="Run every row of a queue TSV.")
    parser.add_argument("--settled", action="store_true", help="Run the 38 rows the earlier sample settled.")
    parser.add_argument("--limit", type=int, help="Stop after this many rows.")
    parser.add_argument("-p", "--page", type=int, help="Printed dictionary page.")
    parser.add_argument("-a", "--published", help="Published headword.")
    parser.add_argument("-b", "--text", help="The dictionary text's spelling.")
    parser.add_argument("--locator", help="Extraction unit locator, so the entry is located by its own line.")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--crops", type=Path, default=Path(tempfile.gettempdir()) / "confusable_crops")
    parser.add_argument("--no-crops", action="store_true", help="Do not render entry crops.")
    parser.add_argument("--verify-width", action="store_true", help="Compare against the widths the earlier sample recorded.")
    parser.add_argument("--json", type=Path, help="Also write the findings as JSON.")
    args = parser.parse_args()

    if not args.table and not args.settled and not (args.page and args.published and args.text):
        parser.error("give --table, --settled, or --page with --published and --text")

    rows: list[Row] = []
    if args.table:
        rows.extend(read_table(args.table))
    if args.settled:
        rows.extend(Row(published=p, text=t, page=page) for p, t, page, _verdict in SETTLED)
    if args.page and args.published and args.text:
        rows.append(Row(published=args.published, text=args.text, page=args.page, locator=args.locator))
    if args.limit:
        rows = rows[: args.limit]

    crops = None if args.no_crops else args.crops
    if crops:
        crops.mkdir(parents=True, exist_ok=True)

    document = open_document(args.pdf)
    conn = sqlite3.connect(f"file:{REPOSITORY_ROOT / DATABASE}?mode=ro", uri=True)
    headword_cache: dict[int, set[str]] = {}
    glyph_cache: dict[int, list[Glyph]] = {}
    calibration_cache: dict[tuple[int, str, str], Calibration] = {}

    findings: list[Finding] = []
    for row in rows:
        finding = run_row(
            document,
            conn,
            row,
            crops=crops,
            headword_cache=headword_cache,
            glyph_cache=glyph_cache,
            calibration_cache=calibration_cache,
        )
        findings.append(finding)
        print(
            f"{finding.row.published}\t{finding.row.text}\tpage {finding.row.page}\tprinted {finding.printed!r}\t"
            f"{finding.verdict}\t{finding.measurement}\t{finding.calibration}\t{finding.note}"
        )

    counts: collections.Counter[str] = collections.Counter(finding.verdict for finding in findings)
    print("\nverdicts:", ", ".join(f"{verdict} {count}" for verdict, count in sorted(counts.items())))
    wrong = [finding for finding in findings if finding.verdict == "published wrong"]
    if wrong:
        print(f"published wrong ({len(wrong)}):")
        for finding in wrong:
            print(f"  {finding.row.published} -> {finding.row.text} (page {finding.row.page}): {finding.note}")

    if args.settled:
        print("\nsettled rows -- verdict recorded by the earlier sample against this tool:")
        agreed = 0
        for finding, (_p, _t, _page, verdict) in zip(findings, SETTLED):
            match = "agree" if finding.verdict == verdict else "DISAGREE"
            agreed += finding.verdict == verdict
            print(f"  {finding.row.published:>17}/{finding.row.text:<17} recorded {verdict:<28} tool {finding.verdict:<28} {match}")
        print(f"  {agreed}/{len(findings)} rows agree")

    if args.verify_width:
        print("\nrecorded ink widths against this tool's (points, at each page's type size):")
        worst = 0.0
        for (page_number, spelling), (recorded, index) in sorted(SETTLED_WIDTHS.items()):
            glyphs = page_glyph_cache(document, page_number, glyph_cache)
            measured = measure_printed_spelling(page_of(document, page_number), glyphs, spelling, index)
            if not measured:
                print(f"  p{page_number} {spelling:<10} recorded {recorded:.2f} pt, tool did not find it")
                continue
            delta = measured[1] - recorded
            worst = max(worst, abs(delta))
            print(f"  p{page_number} {spelling:<10} recorded {recorded:.2f} pt, tool {measured[1]:.2f} pt (delta {delta:+.2f})")
        print(f"  largest disagreement {worst:.2f} pt")

    if args.json:
        args.json.write_text(
            json.dumps(
                [
                    {
                        "published": f.row.published,
                        "text": f.row.text,
                        "page": f.row.page,
                        "printed": f.printed,
                        "verdict": f.verdict,
                        "measurement": f.measurement,
                        "calibration": f.calibration,
                        "note": f.note,
                    }
                    for f in findings
                ],
                indent=1,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
