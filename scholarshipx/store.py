from __future__ import annotations

import json
from pathlib import Path

from scholarshipx.models import Conference, Scholarship
from scholarshipx.paths import CONFERENCES_PATH, DATA_DIR, SCHOLARSHIPS_PATH


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


def load_conferences(path: Path | None = None) -> list[Conference]:
    target = path or CONFERENCES_PATH
    if not target.exists():
        return []
    raw = json.loads(target.read_text(encoding="utf-8"))
    return [
        Conference.from_dict(item)
        for item in raw
        if isinstance(item, dict) and item.get("id") and item.get("name") and item.get("grant_url")
    ]


def save_conferences(conferences: list[Conference], path: Path | None = None) -> Path:
    target = path or CONFERENCES_PATH
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = [item.to_dict() for item in conferences]
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
