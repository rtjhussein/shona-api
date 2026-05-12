import json
from pathlib import Path
from typing import Any


HANNAN_FIXTURE_PATH = Path(__file__).with_name("entries.json")


def load_hannan_fixtures(path: Path = HANNAN_FIXTURE_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def iter_hannan_fixture_entries(path: Path = HANNAN_FIXTURE_PATH):
    yield from load_hannan_fixtures(path)["entries"]
