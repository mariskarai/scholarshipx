from __future__ import annotations

import json
from pathlib import Path

from scholarshipx.models import Scholarship
from scholarshipx.paths import DATA_DIR, SCHOLARSHIPS_PATH


def load_scholarships(path: Path | None = None) -> list[Scholarship]:
    target = path or SCHOLARSHIPS_PATH
    if not target.exists():
        return []
    raw = json.loads(target.read_text(encoding="utf-8"))
    return [
        Scholarship.from_dict(item)
        for item in raw
        if isinstance(item, dict) and item.get("id") and item.get("name") and item.get("organization")
    ]


def save_scholarships(scholarships: list[Scholarship], path: Path | None = None) -> Path:
    target = path or SCHOLARSHIPS_PATH
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = [item.to_dict() for item in scholarships]
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
