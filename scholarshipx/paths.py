from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SCHOLARSHIPS_PATH = DATA_DIR / "scholarships.json"
CONFERENCES_PATH = DATA_DIR / "conferences.json"
NOTION_SCHOLARSHIPS_PATH = DATA_DIR / "notion_scholarships.json"
SOURCES_PATH = DATA_DIR / "sources.yaml"
README_PATH = ROOT / "README.md"
ARCHIVE_PATH = ROOT / "ARCHIVE.md"
