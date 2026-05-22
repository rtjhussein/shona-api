import argparse
import json
import re
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel


PARSER_DIR = Path(__file__).resolve().parent
DEFAULT_BATCHES_DIR = PARSER_DIR / "llm_extracted_batches"
DEFAULT_OUTPUT_JSONL = DEFAULT_BATCHES_DIR / "hannan_gemini_batch.jsonl"
DEFAULT_SOURCE_FILENAME = "Standard Shona Dictionary - Hannan.pdf"


class CrossReference(BaseModel):
    type: str
    target: str
    dialects: List[str] = []


class Example(BaseModel):
    shona: str
    english: str


class SenseSchema(BaseModel):
    number: int
    definition: str
    dialects: List[str] = []
    grammar: List[str] = []
    examples: List[Example] = []
    cross_references: List[CrossReference] = []


class PartOfSpeech(BaseModel):
    code: str
    label: str


class DerivedFormGroup(BaseModel):
    forms: List[str]


class NounMetadata(BaseModel):
    classes: List[str] = []
    plural_prefixes: List[str] = []
    plural_classes: List[str] = []


class ParsedHannanEntry(BaseModel):
    headword: str
    headword_kind: str
    part_of_speech: PartOfSpeech
    dialects: List[str] = []
    comparative_bantu_marker: bool = False
    tone_pattern: Optional[str] = None
    noun: Optional[NounMetadata] = None
    senses: List[SenseSchema]
    derived_forms: List[DerivedFormGroup] = []
    raw_entry_text: str


class PageExtraction(BaseModel):
    page_number: int
    entries: List[ParsedHannanEntry]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compile Gemini page JSON files into shona-api JSONL."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_BATCHES_DIR)
    parser.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUTPUT_JSONL)
    parser.add_argument("--start-page", type=int, default=None)
    parser.add_argument("--end-page", type=int, default=None)
    parser.add_argument("--source-filename", default=DEFAULT_SOURCE_FILENAME)
    parser.add_argument("--model-name", default="gemini-2.5-flash")
    return parser.parse_args()


def selected_page_files(input_dir, start_page, end_page):
    json_files = sorted(input_dir.glob("page_*.json"))
    selected = []
    for file_path in json_files:
        page_number = page_number_from_name(file_path.name)
        if page_number is None:
            print(f"Skipping file with unrecognized name format: {file_path.name}", flush=True)
            continue
        if start_page is not None and page_number < start_page:
            continue
        if end_page is not None and page_number > end_page:
            continue
        selected.append((page_number, file_path))
    return selected


def page_number_from_name(filename):
    filename_match = re.match(r"page_(\d+)\.json", filename)
    if not filename_match:
        return None
    return int(filename_match.group(1))


def safe_headword_slug(headword):
    return re.sub(r"[^A-Za-z0-9-]+", "-", headword).strip("-") or "entry"


def compile_pages(*, input_dir, output_jsonl, start_page=None, end_page=None, source_filename, model_name):
    print(f"Scanning directory: {input_dir}...", flush=True)
    page_files = selected_page_files(input_dir, start_page, end_page)
    if not page_files:
        raise SystemExit("No extracted page JSON files found for the selected range.")

    print(f"Found {len(page_files)} page files to compile.", flush=True)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    compiled_entries_count = 0
    with output_jsonl.open("w", encoding="utf-8") as out_f:
        for pdf_page, file_path in page_files:
            actual_page = pdf_page - 24
            print(
                f"Processing {file_path.name} "
                f"(PDF Page: {pdf_page} -> Actual Book Page: {actual_page})...",
                flush=True,
            )

            try:
                raw_data = json.loads(file_path.read_text(encoding="utf-8"))
                extraction = PageExtraction.model_validate(raw_data)
            except Exception as exc:
                print(f"Error compiling {file_path.name}: {exc}", flush=True)
                continue

            for entry_idx, entry in enumerate(extraction.entries, start=1):
                entry_dict = entry.model_dump()
                entry_dict["parse_metadata"] = {
                    "parser": "gemini-2.5-flash-v1",
                    "completeness": "parsed",
                }
                entry_dict["normalized_headword"] = entry.headword.removeprefix("-").strip()
                locator = (
                    f"hannan:page_{actual_page:03d}:entry_{entry_idx:03d}:"
                    f"{safe_headword_slug(entry.headword)}"
                )
                jsonl_record = {
                    "source_locator": locator,
                    "raw_text": entry.raw_entry_text,
                    "confidence": 1.0,
                    "primary_source_page": actual_page,
                    "source_pages": [actual_page],
                    "parser_output": entry_dict,
                    "provenance": {
                        "source_filename": source_filename,
                        "pdf_page_number": pdf_page,
                        "actual_page_number": actual_page,
                        "model_name": model_name,
                        "compiler": "compile_llm_batches.py",
                    },
                }
                out_f.write(json.dumps(jsonl_record, ensure_ascii=False) + "\n")
                compiled_entries_count += 1

    print("\n" + "=" * 60, flush=True)
    print(f"SUCCESS! Consolidated {compiled_entries_count} entries into JSONL:", flush=True)
    print(f"  {output_jsonl}", flush=True)
    print("=" * 60 + "\n", flush=True)
    return compiled_entries_count


def main():
    args = parse_args()
    compile_pages(
        input_dir=args.input_dir,
        output_jsonl=args.output_jsonl,
        start_page=args.start_page,
        end_page=args.end_page,
        source_filename=args.source_filename,
        model_name=args.model_name,
    )


if __name__ == "__main__":
    main()
