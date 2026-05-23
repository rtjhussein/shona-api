import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF is not installed. Please run: pip install pymupdf")
    sys.exit(1)

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: google-genai is not installed. Please run: pip install google-genai")
    sys.exit(1)


PARSER_DIR = Path(__file__).resolve().parent
DEFAULT_PDF_PATH = PARSER_DIR / "source" / "Standard Shona Dictionary - Hannan.pdf"
DEFAULT_OUTPUT_DIR = PARSER_DIR / "llm_extracted_batches"
DEFAULT_MODEL = "gemini-2.5-flash"


class CrossReference(BaseModel):
    type: str = Field(description="Type of cross reference, usually 'cp', 'see', 'cf', or 'qv'.")
    target: str = Field(description="The target headword being referenced.")
    dialects: List[str] = Field(default_factory=list)


class Example(BaseModel):
    shona: str = Field(description="The Shona example phrase/sentence as printed.")
    english: str = Field(description="The English translation.")


class SenseSchema(BaseModel):
    number: int = Field(description="Sequential sense number, starting from 1.")
    definition: str = Field(description="English definition/gloss.")
    dialects: List[str] = Field(default_factory=list)
    grammar: List[str] = Field(default_factory=list)
    examples: List[Example] = Field(default_factory=list)
    cross_references: List[CrossReference] = Field(default_factory=list)


class PartOfSpeech(BaseModel):
    code: str = Field(description="Short part-of-speech code.")
    label: str = Field(description="Human-readable part-of-speech label.")


class DerivedFormGroup(BaseModel):
    marker: Optional[str] = Field(
        default=None,
        description="Printed relation marker such as '>' or '<-'.",
    )
    forms: List[str] = Field(description="Derived forms belonging to this group.")
    source_note: Optional[str] = Field(
        default=None,
        description="Raw source note or phrase that introduced the forms.",
    )


class NounMetadata(BaseModel):
    classes: List[str] = Field(default_factory=list)
    plural_prefixes: List[str] = Field(default_factory=list)
    plural_classes: List[str] = Field(default_factory=list)


class ParsedHannanEntry(BaseModel):
    headword: str = Field(description="Headword, preserving initial hyphens for verb stems.")
    headword_kind: str = Field(description="'word', 'noun', 'verb_stem', 'ideophone', or 'unknown'.")
    part_of_speech: PartOfSpeech
    dialects: List[str] = Field(default_factory=list)
    comparative_bantu_marker: bool = False
    tone_pattern: Optional[str] = None
    noun: Optional[NounMetadata] = None
    senses: List[SenseSchema]
    derived_forms: List[DerivedFormGroup] = Field(default_factory=list)
    raw_entry_text: str


class PageExtraction(BaseModel):
    page_number: int
    entries: List[ParsedHannanEntry]


PROMPT = (
    "You are an expert lexicographer specializing in Southern African languages. "
    "Your task is to locate, transcribe, and parse every single dictionary entry on this scanned page "
    "from the Standard Shona Dictionary into the requested JSON schema. "
    "Apply these strict structural rules from the dictionary's front-matter introduction:\n\n"
    "1. NOUN CLASSES AND PLURAL PREFIXES:\n"
    "   - A noun entry is marked by 'n' (part of speech). The numbers/codes immediately following the 'n' "
    "     represent grammatical NOUN CLASSES, not sense numbers.\n"
    "   - Extract class numbers into `noun.classes`.\n"
    "   - Plural prefixes following 'pl:' represent plural formations. Extract plural prefixes into "
    "     `noun.plural_prefixes` and plural classes into `noun.plural_classes`.\n"
    "   - Do not treat noun class numbers as sense numbers or definitions.\n\n"
    "2. IMPLICIT FIRST SENSE:\n"
    "   - The first sense of a multi-sense entry is never numbered '1.' in the text. "
    "     The English gloss immediately following the part-of-speech and class markers belongs to Sense 1.\n"
    "   - Subsequent senses are numbered '2.', '3.', '4.', etc.\n\n"
    "3. EXAMPLES VS. DEFINITIONS:\n"
    "   - Phrase pairs formatted as 'Shona text : English translation.' are examples or proverbs, not definitions.\n"
    "   - Put them in the `examples` list of the corresponding sense.\n\n"
    "4. VERB DERIVED FORMS:\n"
    "   - Verb stems begin with a hyphen.\n"
    "   - Derived verb forms listed at the end of verb entries, marked by '>' or '<-', belong in `derived_forms`.\n"
    "   - Preserve the printed marker in `derived_forms[].marker` and the short raw source phrase in `derived_forms[].source_note`.\n\n"
    "Ensure all entries on the page are fully processed, correcting standard abbreviations and contextually "
    "repairing visual OCR character damage."
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract one or more Hannan dictionary PDF pages with Gemini."
    )
    parser.add_argument("--page", type=int, default=None, help="Single PDF page to extract.")
    parser.add_argument("--start-page", type=int, default=None, help="First PDF page to extract.")
    parser.add_argument("--end-page", type=int, default=None, help="Last PDF page to extract.")
    parser.add_argument("--pdf-path", type=Path, default=DEFAULT_PDF_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--initial-wait", type=int, default=5)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def page_range(args):
    if args.page is not None:
        return range(args.page, args.page + 1)
    if args.start_page is None:
        raise ValueError("Provide --page or --start-page.")
    end_page = args.end_page if args.end_page is not None else args.start_page
    if args.start_page < 1 or end_page < args.start_page:
        raise ValueError("Invalid page range.")
    return range(args.start_page, end_page + 1)


def render_page(pdf_path, page_number, dpi):
    doc = fitz.open(str(pdf_path))
    try:
        page = doc.load_page(page_number - 1)
        pix = page.get_pixmap(dpi=dpi)
        return pix.tobytes("png")
    finally:
        doc.close()


def extract_page(client, *, pdf_path, output_dir, page_number, model, dpi, retries, initial_wait, overwrite):
    output_file = output_dir / f"page_{page_number:03d}.json"
    if output_file.exists() and not overwrite:
        print(f"Skipping page {page_number}: {output_file} already exists.", flush=True)
        return output_file

    print(f"Rendering PDF page {page_number} as PNG...", flush=True)
    img_bytes = render_page(pdf_path, page_number, dpi)
    print(f"Page {page_number} rendered successfully ({len(img_bytes)} bytes).", flush=True)

    wait_time = initial_wait
    start_time = time.time()
    for attempt in range(1, retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                    PROMPT,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=PageExtraction,
                    temperature=0.1,
                ),
            )
            elapsed_time = time.time() - start_time
            print(
                f"Received page {page_number} response in {elapsed_time:.2f} seconds "
                f"on attempt {attempt}.",
                flush=True,
            )
            page_data = json.loads(response.text)
            page_data["page_number"] = page_number
            output_file.write_text(
                json.dumps(page_data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(
                f"Saved {len(page_data.get('entries', []))} entries for page {page_number} "
                f"to {output_file}.",
                flush=True,
            )
            return output_file
        except Exception as exc:
            print(f"Attempt {attempt} failed for page {page_number}: {exc}", flush=True)
            if attempt == retries:
                raise
            print(f"Waiting {wait_time} seconds before retrying...", flush=True)
            time.sleep(wait_time)
            wait_time *= 2


def main():
    args = parse_args()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.", flush=True)
        sys.exit(1)
    if not args.pdf_path.exists():
        print(f"Error: Could not find PDF at {args.pdf_path}", flush=True)
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pages = list(page_range(args))
    print(f"Extracting PDF pages {pages[0]} through {pages[-1]} with {args.model}.", flush=True)
    client = genai.Client(api_key=api_key)

    written = []
    for page_number in pages:
        written.append(
            extract_page(
                client,
                pdf_path=args.pdf_path,
                output_dir=args.output_dir,
                page_number=page_number,
                model=args.model,
                dpi=args.dpi,
                retries=args.retries,
                initial_wait=args.initial_wait,
                overwrite=args.overwrite,
            )
        )

    print("\n" + "=" * 60, flush=True)
    print(f"Finished Gemini extraction for {len(written)} page file(s).", flush=True)
    print("=" * 60 + "\n", flush=True)


if __name__ == "__main__":
    main()
