"""Land ox-sweep chunk files: merge boundary continuations, import, approve,
publish.

Continuation sidecars are written by chunk agents when an entry from the
PREVIOUS chunk continues onto their first page. The sidecar names the parent
book page, which always belongs to an earlier chunk file. This script:

  1. loads all chunk files and sidecars
  2. patches each sidecar's text into the correct parent row (last entry on
     the parent page in the chunk whose range contains that page), skipping
     sidecars whose text the parent row already contains (parent chunks often
     complete their last entry via the extra next-page image)
  3. imports + approves + publishes chunks in ascending order, asserting
     published == approved before declaring a chunk landed

Chunks whose "<BATCH-ID>: landed" line already appears in the run log are
skipped, so the script can be relaunched after a timeout and only processes
the remainder.

Usage:
  python local_batches/ox-sweep/land_wave.py <prefix>

Parser naming: prefix starting with "gpt" -> gpt-5.5-thinking, otherwise
ox-alpha-vision.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

OUT = Path("local_batches/ox-sweep/out")
CONT = OUT / "continuations"
LOG_DIR = OUT.parent


def chunk_range(path: Path) -> tuple[int, int] | None:
    m = re.search(r"_book_(\d+)-(\d+)\.jsonl$", path.name)
    return (int(m.group(1)), int(m.group(2))) if m else None


def batch_id_for(prefix: str, path: Path) -> str | None:
    rng = chunk_range(path)
    if rng is None:
        return None
    return f"{prefix.upper()}-{rng[0]:04d}-{rng[1]:04d}"


def patch_parent(chunk_path: Path, parent_page: int, text: str) -> bool:
    lines = [
        ln for ln in chunk_path.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]
    parent_idx = None
    parent_seq = -1
    for i, ln in enumerate(lines):
        m = re.search(r'"hannan:page_(\d+):entry_(\d+):', ln)
        if m and int(m.group(1)) == parent_page and int(m.group(2)) > parent_seq:
            parent_seq = int(m.group(2))
            parent_idx = i
    if parent_idx is None:
        return False

    row = json.loads(lines[parent_idx])
    po = row["parser_output"]
    cont = text.strip()
    row["raw_text"] = f"{row.get('raw_text', '').rstrip()} {cont}".strip()
    po["raw_entry_text"] = row["raw_text"]

    senses = po.get("senses") or []
    if senses:
        last = senses[-1]
        definition = (last.get("definition") or "").rstrip()
        if definition and cont.startswith(definition[: min(len(definition), 25)]):
            last["definition"] = cont
    lines[parent_idx] = json.dumps(row, ensure_ascii=False)
    chunk_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"patched {chunk_path.name} page_{parent_page:03d} entry_{parent_seq:03d} "
        f"with continuation ({len(cont)} chars)"
    )
    return True


def merge_sidecars(chunk_files: list[Path]) -> None:
    if not CONT.exists():
        return
    for sidecar in sorted(CONT.glob("*.json")):
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        parent_page = int(data["parent_book_page"])
        text = data["continuation_text"]
        target = None
        for cf in chunk_files:
            rng = chunk_range(cf)
            if rng and rng[0] <= parent_page <= rng[1]:
                target = cf
                break
        if target is None:
            print(f"WARNING: no chunk contains parent page {parent_page}; keeping sidecar")
            continue
        # Parent chunks often complete their last entry via the extra
        # next-page image, making a first-fragment sidecar redundant.
        probe = re.sub(r"\s+", " ", text.strip())[:30]
        already = any(
            probe in re.sub(r"\s+", " ", ln)
            for ln in target.read_text(encoding="utf-8").splitlines()
            if f"page_{parent_page:03d}" in ln
        )
        if already:
            sidecar.unlink()
            print(f"sidecar for parent page {parent_page}: parent already contains text; dropped")
            continue
        if patch_parent(target, parent_page, text):
            sidecar.unlink()


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    tail = "\n".join((result.stdout + result.stderr).splitlines()[-10:])
    print(tail)
    if result.returncode != 0:
        sys.exit(f"command failed: {' '.join(cmd)}")


def approve_batch(batch_id: str) -> tuple[int, int, int]:
    """Approve clean units of this batch; leave uncertain ones for editorial.

    Eligible: confidence == 1.0 and parse_metadata.completeness == 'parsed'.
    Returns (total, approved, left_in_review).
    """
    code = f"""
from shona_api.extraction.models import ExtractionUnit
from shona_api.editorial.models import ReviewState

qs = ExtractionUnit.objects.filter(batch_id={batch_id!r})
total = qs.count()
approved = 0
for u in qs.filter(review_state=ReviewState.NEEDS_REVIEW):
    po = u.parser_output or {{}}
    meta = po.get("parse_metadata") or {{}}
    if float(u.confidence or 0) >= 1.0 and meta.get("completeness", "parsed") == "parsed":
        u.review_state = ReviewState.APPROVED
        u.save(update_fields=["review_state", "updated_at"])
        approved += 1
left = qs.filter(review_state=ReviewState.NEEDS_REVIEW).count()
print("COUNTS", total, approved, left)
"""
    result = subprocess.run(
        [".venv/Scripts/python.exe", "manage.py", "shell", "-c", code],
        capture_output=True,
        text=True,
    )
    print(result.stdout.strip())
    if result.returncode != 0:
        sys.exit(result.stderr)
    counts = [
        ln.split()[1:]
        for ln in result.stdout.splitlines()
        if ln.startswith("COUNTS")
    ]
    total, approved, left = map(int, counts[0])
    return total, approved, left


def published_count(batch_id: str) -> int:
    code = f"""
from shona_api.extraction.models import ExtractionUnit
from shona_api.editorial.models import ReviewState
n = ExtractionUnit.objects.filter(
    batch_id={batch_id!r}, review_state=ReviewState.PUBLISHED
).count()
print("PUBLISHED", n)
"""
    result = subprocess.run(
        [".venv/Scripts/python.exe", "manage.py", "shell", "-c", code],
        capture_output=True,
        text=True,
    )
    for ln in result.stdout.splitlines():
        if ln.startswith("PUBLISHED"):
            return int(ln.split()[1])
    sys.exit(f"could not read published count for {batch_id}")


def main() -> None:
    prefix = sys.argv[1] if len(sys.argv) > 1 else "oxv1"
    log = LOG_DIR / f"land_{prefix}.log"
    landed: set[str] = set()
    if log.exists():
        for m in re.finditer(
            r"^((?:GPT55|OXV1)-\d+-\d+): landed",
            log.read_text(encoding="utf-8"),
            re.M,
        ):
            landed.add(m.group(1))

    search_dirs = [OUT / prefix, OUT]
    chunk_files = []
    for d in search_dirs:
        chunk_files = sorted(d.glob(f"{prefix}_book_*.jsonl"))
        if chunk_files:
            break
    if not chunk_files:
        sys.exit(f"no chunk files matching {prefix}")

    todo = [cf for cf in chunk_files if batch_id_for(prefix, cf) not in landed]
    if not todo:
        print(f"all {prefix} chunks already landed")
        return
    print(f"{len(todo)} of {len(chunk_files)} {prefix} chunks to land")
    merge_sidecars(todo)
    parser_name = (
        "gpt-5.5-thinking" if prefix.startswith("gpt") else "ox-alpha-vision"
    )
    for cf in todo:
        batch_id = batch_id_for(prefix, cf)
        run(
            [
                ".venv/Scripts/python.exe",
                "manage.py",
                "import_gpt_5_5_parsed",
                str(cf),
                "--batch-id",
                batch_id,
                "--parser-name",
                parser_name,
            ]
        )
        total, approved, left = approve_batch(batch_id)
        run(
            [
                ".venv/Scripts/python.exe",
                "manage.py",
                "publish_hannan_batch",
                "--batch-id",
                batch_id,
            ]
        )
        published = published_count(batch_id)
        if approved and published != approved:
            sys.exit(
                f"{batch_id}: approved {approved} but published {published}; aborting"
            )
        print(
            f"{batch_id}: landed. total={total} approved={approved} "
            f"published={published} needs_review={left}"
        )


if __name__ == "__main__":
    main()
