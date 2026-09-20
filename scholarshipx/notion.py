from __future__ import annotations

import re
from datetime import date
from typing import Any

from scholarshipx.models import STATUS_EXPIRED, Scholarship
from scholarshipx.sanitize import is_safe_http_url

ISO_DATE = re.compile(r"^20\d{2}-\d{2}-\d{2}$")


def _record(item: Scholarship | dict[str, Any]) -> dict[str, Any]:
    if isinstance(item, Scholarship):
        return item.to_dict()
    return item


def _name(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    name = raw.strip()
    return name or None


def _amount(raw: Any) -> int | None:
    if isinstance(raw, bool) or raw is None:
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    return None


def _website(record: dict[str, Any]) -> str | None:
    for key in ("official_url", "listing_url"):
        url = record.get(key)
        if isinstance(url, str) and is_safe_http_url(url.strip()):
            return url.strip()
    return None


def _deadline(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not ISO_DATE.fullmatch(value):
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _is_expired(record: dict[str, Any], deadline: str, today: date | None = None) -> bool:
    if str(record.get("status") or "").upper() == STATUS_EXPIRED:
        return True
    now = today or date.today()
    return date.fromisoformat(deadline) < now


def build_notion_scholarships(
    scholarships: list[Scholarship] | list[dict[str, Any]],
    today: date | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in scholarships:
        record = _record(item)
        name = _name(record.get("name"))
        website = _website(record)
        deadline = _deadline(record.get("deadline"))
        if not name or not website or not deadline:
            continue
        if _is_expired(record, deadline, today=today):
            continue
        key = (name.casefold(), website, deadline)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "Name": name,
                "Amount": _amount(record.get("amount_value")),
                "Website": website,
                "Deadline": deadline,
            }
        )
    rows.sort(key=lambda row: (row["Deadline"], row["Name"].casefold()))
    return rows
