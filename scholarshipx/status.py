from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

from scholarshipx.models import (
    STATUS_CLOSING_SOON,
    STATUS_EXPIRED,
    STATUS_OPEN,
    STATUS_OPENS_SOON,
    Scholarship,
)

CLOSING_SOON_DAYS = 14
MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def slugify(value: str) -> str:
    text = (
        value.lower()
        .replace("'", "")
        .replace("'", "")
        .replace("'", "")
        .replace("'", "")
        .replace("&", " and ")
    )
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return slug or "scholarship"


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", slugify(value))


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    key = f"{host}{path}".lower()
    if parsed.query:
        key = f"{key}?{parsed.query.lower()}"
    return key


def parse_amount_value(text: str | None) -> int | None:
    if not text:
        return None
    match = re.search(r"\$?\s*([\d,]+)", text)
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


def parse_deadline(text: str | None, today: date | None = None) -> date | None:
    if not text:
        return None
    cleaned = text.strip()
    lowered = cleaned.lower()
    if lowered in {"unknown", "check site", "rolling", "varies", "n/a"}:
        return None
    if lowered.startswith("opens "):
        return None

    iso = re.search(r"(20\d{2})-(\d{2})-(\d{2})", cleaned)
    if iso:
        return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))

    days_left = re.search(r"only\s+(\d+)\s+days?\s+left", lowered)
    if days_left:
        return (today or date.today()) + timedelta(days=int(days_left.group(1)))

    month_day_year = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
        r"dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?\.?,?\s*(20\d{2})\b",
        lowered,
    )
    if month_day_year:
        month = MONTHS[month_day_year.group(1)]
        return date(int(month_day_year.group(3)), month, int(month_day_year.group(2)))

    month_day = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
        r"dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?\.?\b",
        lowered,
    )
    if month_day:
        now = today or date.today()
        month = MONTHS[month_day.group(1)]
        day = int(month_day.group(2))
        try:
            candidate = date(now.year, month, day)
        except ValueError:
            return None
        if candidate < now:
            candidate = date(now.year + 1, month, day)
        return candidate

    month_year = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
        r"dec(?:ember)?)\s+(20\d{2})\b",
        lowered,
    )
    if month_year:
        month = MONTHS[month_year.group(1)]
        return date(int(month_year.group(2)), month, 1)

    return None


def format_deadline(value: date | None, fallback: str = "Check site") -> str:
    if value is None:
        return fallback
    return value.strftime("%b %d, %Y")


def compute_status(item: Scholarship, today: date | None = None) -> str:
    now = today or date.today()
    if item.expected_open:
        opens = parse_deadline(item.expected_open, today=now)
        if opens and opens > now:
            return STATUS_OPENS_SOON
    deadline = parse_deadline(item.deadline, today=now)
    if deadline is None and item.deadline_display and not (item.deadline_display or "").lower().startswith("opens "):
        deadline = parse_deadline(item.deadline_display, today=now)
    if deadline is None:
        display = (item.deadline_display or "").lower()
        if display.startswith("opens ") or item.status == STATUS_OPENS_SOON:
            opens = parse_deadline(item.expected_open or item.deadline_display, today=now)
            if opens and opens > now:
                return STATUS_OPENS_SOON
            if opens and opens <= now:
                return STATUS_OPEN
        if "open" in display or display in {"rolling", "check site", "unknown"}:
            return STATUS_OPEN
        return item.status or STATUS_OPEN
    if deadline < now:
        return STATUS_EXPIRED
    if deadline <= now + timedelta(days=CLOSING_SOON_DAYS):
        return STATUS_CLOSING_SOON
    return STATUS_OPEN


def refresh_status(items: list[Scholarship], today: date | None = None) -> list[Scholarship]:
    for item in items:
        display = (item.deadline_display or "").lower()
        source = item.deadline
        if not source and display and not display.startswith("opens "):
            source = item.deadline_display
        parsed = parse_deadline(source, today=today)
        item.status = compute_status(item, today=today)
        if parsed and (not item.deadline or not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", item.deadline)):
            item.deadline = parsed.isoformat()
        if parsed and item.deadline_display in {"Unknown", "Check site", ""}:
            item.deadline_display = format_deadline(parsed)
    return items
