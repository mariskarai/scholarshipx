from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any


SECTIONS = [
    "Computer Science & Software",
    "STEM & Engineering",
    "Women in STEM / Tech",
    "First-generation & Immigrant",
    "Business & FinTech",
    "Leadership & Community",
    "General Undergraduate",
]

STATUS_OPEN = "OPEN"
STATUS_CLOSING_SOON = "CLOSING_SOON"
STATUS_OPENS_SOON = "OPENS_SOON"
STATUS_EXPIRED = "EXPIRED"

UNKNOWN = "Unknown"
CHECK_SITE = "Check site"
NONE_STATED = "None stated"


@dataclass
class Scholarship:
    id: str
    name: str
    organization: str
    official_url: str
    amount: str = UNKNOWN
    amount_value: int | None = None
    deadline: str | None = None
    deadline_display: str = UNKNOWN
    section: str = "General Undergraduate"
    status: str = STATUS_OPEN
    tags: list[str] = field(default_factory=list)
    eligibility: list[str] = field(default_factory=list)
    major_requirements: str = NONE_STATED
    academic_level: str = "Undergraduate"
    min_gpa: str = NONE_STATED
    citizenship: str = NONE_STATED
    essay_required: str = UNKNOWN
    other_requirements: list[str] = field(default_factory=list)
    notes: str = ""
    date_found: str = ""
    source: str = ""
    expected_open: str | None = None
    listing_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scholarship:
        known = {key: data[key] for key in cls.__dataclass_fields__ if key in data}
        return cls(**known)


def today_iso() -> str:
    return date.today().isoformat()
