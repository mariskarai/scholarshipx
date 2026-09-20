from __future__ import annotations

import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from scholarshipx.models import STATUS_EXPIRED, Scholarship

ISO_DATE = re.compile(r"^20\d{2}-\d{2}-\d{2}$")
MINIMUM_AMOUNT = 500
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
BLOCKED_APPLY_DOMAINS = (
    "bold.org",
    "scholarships360.org",
    "unigo.com",
    "scholarships.com",
    "fastweb.com",
    "niche.com",
    "goingmerry.com",
    "scholarshipowl.com",
    "sallie.com",
    "localscholarships.org",
    "scholarshipsthatwork.com",
    "chegg.com",
    "cappex.com",
    "careeronestop.org",
)

SEARCH_FIELDS = (
    "name",
    "section",
    "tags",
    "eligibility",
    "major_requirements",
    "academic_level",
    "notes",
    "other_requirements",
    "organization",
)

LANE_PATTERNS = (
    re.compile(r"computer science"),
    re.compile(r"\bcomputing\b"),
    re.compile(r"\bsoftware\b"),
    re.compile(r"technolog"),
    re.compile(r"\btech\b"),
    re.compile(r"\bstem\b"),
    re.compile(r"engineer"),
    re.compile(r"women in (stem|tech|computing|engineering|science)"),
    re.compile(r"women in stem"),
    re.compile(r"women in tech"),
    re.compile(r"first[- ]gen"),
    re.compile(r"\bimmigrant"),
    re.compile(r"kansas city"),
    re.compile(r"\bkansas\b"),
    re.compile(r"\bku\b"),
    re.compile(r"university of kansas"),
    re.compile(r"\bfintech\b"),
    re.compile(r"financial technology"),
    re.compile(r"\bbusiness\b"),
    re.compile(r"leadership"),
    re.compile(r"community"),
)

KEEP_GEO = re.compile(
    r"kansas city|\bkansas\b|\bku\b|lawrence|topeka|johnson county|"
    r"wyandotte|overland park|olathe|university of kansas|jackson county|"
    r"clay county|platte county"
)

DISQUALIFY_PATTERNS = (
    re.compile(r"\bblind"),
    re.compile(r"blindness"),
    re.compile(r"visually impaired"),
    re.compile(r"federation of the blind"),
    re.compile(r"\bdeaf\b"),
    re.compile(r"hard of hearing"),
    re.compile(r"disabilit"),
    re.compile(r"\bdisabled\b"),
    re.compile(r"lime connect"),
    re.compile(r"access-ability"),
    re.compile(r"\bveteran"),
    re.compile(r"\bmilitary\b"),
    re.compile(r"armed forces"),
    re.compile(r"\brotc\b"),
    re.compile(r"active duty"),
    re.compile(r"dependent of"),
    re.compile(r"\bdependents\b"),
    re.compile(r"child[\s-]?care"),
    re.compile(r"children of employees"),
    re.compile(r"employee'?s? child"),
    re.compile(r"parent (is |must be )?(employed|works)"),
    re.compile(r"parent works"),
    re.compile(r"must be (an? )?employee"),
    re.compile(r"(?:from|at|attend(?:ing)?)\s+[a-z][a-z .'-]{1,40} high school"),
    re.compile(r"incoming[, ]+(first[- ]year|freshman)"),
    re.compile(r"first[- ]year (ku |students )?only"),
    re.compile(r"freshman only"),
    re.compile(r"incoming freshman"),
    re.compile(r"transfer students? only"),
    re.compile(r"graduate students only"),
    re.compile(r"graduate-only"),
    re.compile(r"master'?s only"),
    re.compile(r"phd only"),
    re.compile(r"doctoral only"),
    re.compile(r"high school students only"),
    re.compile(r"accepted paper"),
    re.compile(r"abstract submission"),
    re.compile(r"conference presenter"),
    re.compile(r"must present (a |an )?(paper|abstract)"),
    re.compile(r"\bhvac\b"),
    re.compile(r"heating, refrigerat"),
    re.compile(r"air-conditioning"),
    re.compile(r"\bashrae\b"),
    re.compile(r"must be (a )?(christian|catholic|muslim|jewish)"),
    re.compile(r"church membership"),
    re.compile(r"religious affiliation required"),
    re.compile(r"sweepstakes"),
    re.compile(r"random drawing"),
    re.compile(r"\bgiveaway\b"),
    re.compile(r"no[- ]essay"),
    re.compile(r"transitional housing"),
)

EXCLUSIVE_MAJOR_TOKENS = {
    "chemistry": ("chemistry", "chemical"),
    "nursing": ("nursing", "nurse"),
    "medical": ("medical-only", "pre-med", "premed", "medicine", "nursing"),
    "hvac": ("hvac", "heating", "refrigerat", "air-conditioning", "air conditioning"),
}

BROAD_KEEP_IN_MAJOR = (
    "computer",
    "software",
    "computing",
    "engineer",
    "stem",
    "technolog",
    "math",
)

OTHER_GEO = (
    re.compile(r"parkersburg"),
    re.compile(r"washougal"),
    re.compile(r"southwest washington"),
    re.compile(r"west virginia"),
    re.compile(r"\bwv\b"),
    re.compile(r"must (be|live|reside) in"),
)

AGGREGATOR_HINTS = (
    "bold.org",
    "scholarships360",
    "no essay scholarship by sallie",
    "scholarshipowl",
    "one click apply",
)


def _is_safe_http_url(url: str) -> bool:
    parsed = urlparse(url or "")
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.username or parsed.password:
        return False
    host = (parsed.hostname or "").lower().removeprefix("www.")
    if not host or host in LOCAL_HOSTS:
        return False
    if host.endswith(".local") or host.endswith(".internal"):
        return False
    return True


def _is_blocked_apply_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return any(host == domain or host.endswith("." + domain) for domain in BLOCKED_APPLY_DOMAINS)


def _record(item: Scholarship | dict[str, Any]) -> dict[str, Any]:
    if isinstance(item, Scholarship):
        return item.to_dict()
    return item if isinstance(item, dict) else {}


def _as_text(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, (list, tuple)):
        return " ".join(_as_text(part) for part in raw)
    return str(raw)


def searchable_text(item: Scholarship | dict[str, Any]) -> str:
    record = _record(item)
    parts = [_as_text(record.get(field)) for field in SEARCH_FIELDS]
    return " ".join(parts).lower()


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
        if isinstance(url, str) and _is_safe_http_url(url.strip()):
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


def _amount_meets_minimum(record: dict[str, Any]) -> bool:
    amount = _amount(record.get("amount_value"))
    return amount is None or amount >= MINIMUM_AMOUNT


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def _is_aggregator(record: dict[str, Any], website: str | None) -> bool:
    if website and _is_blocked_apply_url(website):
        return True
    official = record.get("official_url")
    if isinstance(official, str) and official.strip() and _is_blocked_apply_url(official.strip()):
        return True
    blob = searchable_text(record)
    source = _as_text(record.get("source")).lower()
    haystack = f"{blob} {source}"
    if any(hint in haystack for hint in AGGREGATOR_HINTS):
        return True
    host = _host(website or "")
    return host in {"bold.org"} or host.endswith(".bold.org")


def _exclusive_field_mismatch(record: dict[str, Any]) -> bool:
    major = _as_text(record.get("major_requirements")).strip().lower()
    name = _as_text(record.get("name")).lower()
    notes = _as_text(record.get("notes")).lower()
    blob = f"{major} {name} {notes}"
    if any(keep in major for keep in BROAD_KEEP_IN_MAJOR):
        return False
    for tokens in EXCLUSIVE_MAJOR_TOKENS.values():
        if any(token in blob for token in tokens):
            if major in {"", "none stated", "unknown", "n/a"}:
                if any(token in name or token in notes for token in tokens):
                    return True
            elif any(token in major for token in tokens):
                return True
    return False


def _outside_local_geography(text: str) -> bool:
    if KEEP_GEO.search(text):
        return False
    return any(pattern.search(text) for pattern in OTHER_GEO)


def _graduate_only(record: dict[str, Any], text: str) -> bool:
    level = _as_text(record.get("academic_level")).lower()
    undergrad = any(token in level for token in ("undergrad", "bachelor", "college"))
    grad = any(token in level for token in ("graduate", "master", "phd", "doctoral"))
    if grad and not undergrad and "high school" not in level:
        return "undergraduate" not in text
    return bool(re.search(r"graduate students only|master'?s only|phd only|doctoral only", text)) and "undergraduate" not in text


def _high_school_only(record: dict[str, Any], text: str) -> bool:
    level = _as_text(record.get("academic_level")).lower()
    college = any(token in f"{level} {text}" for token in ("undergraduate", "bachelor", "college", "university"))
    if "high school" in level and not any(token in level for token in ("bachelor", "undergrad", "graduate")):
        return not college
    if re.search(r"high school students only", text):
        return True
    if re.search(r"high school senior", text) and not college:
        return True
    return False


def _no_essay(record: dict[str, Any], text: str) -> bool:
    essay = _as_text(record.get("essay_required")).strip().lower()
    if essay in {"no", "false", "none", "not required"}:
        return True
    return bool(re.search(r"no[- ]essay", text))


def has_relevant_lane(item: Scholarship | dict[str, Any]) -> bool:
    text = searchable_text(item)
    if not text.strip():
        return False
    return any(pattern.search(text) for pattern in LANE_PATTERNS)


def has_disqualifying_requirement(item: Scholarship | dict[str, Any]) -> bool:
    record = _record(item)
    text = searchable_text(record)
    if any(pattern.search(text) for pattern in DISQUALIFY_PATTERNS):
        return True
    if _exclusive_field_mismatch(record):
        return True
    if _outside_local_geography(text):
        return True
    if _graduate_only(record, text):
        return True
    if _high_school_only(record, text):
        return True
    if _no_essay(record, text):
        return True
    name = (_name(record.get("name")) or "").lower()
    if name.startswith("transfer scholarship") or name == "transfer scholarships":
        return True
    return False


def is_valid_notion_candidate(item: Scholarship | dict[str, Any], today: date | None = None) -> bool:
    record = _record(item)
    name = _name(record.get("name"))
    website = _website(record)
    deadline = _deadline(record.get("deadline"))
    if not name or not website or not deadline:
        return False
    if _is_expired(record, deadline, today=today):
        return False
    if not _amount_meets_minimum(record):
        return False
    return True


def _skip_reason(record: dict[str, Any], today: date | None) -> str | None:
    if not _name(record.get("name")):
        return "missing_name"
    website = _website(record)
    if not website:
        return "missing_website"
    deadline = _deadline(record.get("deadline"))
    if not deadline:
        return "missing_deadline"
    if _is_expired(record, deadline, today=today):
        return "expired"
    if not _amount_meets_minimum(record):
        return "below_minimum_amount"
    if not is_valid_notion_candidate(record, today=today):
        return "missing_website"
    if _is_aggregator(record, website):
        return "aggregator"
    if has_disqualifying_requirement(record):
        return "unsupported_requirement"
    if not has_relevant_lane(record):
        return "not_relevant_lane"
    return None


def _row(record: dict[str, Any]) -> dict[str, Any]:
    name = _name(record.get("name"))
    website = _website(record)
    deadline = _deadline(record.get("deadline"))
    assert name and website and deadline
    return {
        "Name": name,
        "Amount": _amount(record.get("amount_value")),
        "Website": website,
        "Deadline": deadline,
    }


def build_notion_scholarships(
    raw_items: list[Scholarship] | list[dict[str, Any]],
    today: date | None = None,
) -> list[dict[str, Any]]:
    return export_notion_scholarships(raw_items, today=today)["rows"]


def export_notion_scholarships(
    raw_items: list[Scholarship] | list[dict[str, Any]],
    today: date | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    skip_reasons: Counter[str] = Counter()
    seen: set[tuple[str, str, str]] = set()
    for item in raw_items:
        record = _record(item)
        reason = _skip_reason(record, today)
        if reason:
            skip_reasons[reason] += 1
            continue
        row = _row(record)
        key = (row["Name"].casefold(), row["Website"], row["Deadline"])
        if key in seen:
            skip_reasons["duplicate"] += 1
            continue
        seen.add(key)
        rows.append(row)
    rows.sort(key=lambda row: (row["Deadline"], row["Name"].casefold()))
    return {
        "rows": rows,
        "raw_count": len(raw_items),
        "exported": len(rows),
        "skipped": len(raw_items) - len(rows),
        "skip_reasons": dict(skip_reasons),
    }


def format_notion_cli_summary(path: str, export: dict[str, Any]) -> str:
    display = "data/notion_scholarships.json"
    try:
        from scholarshipx.paths import ROOT

        display = str(Path(path).resolve().relative_to(ROOT))
    except Exception:
        if path:
            display = path
    lines = [
        f"Wrote {export['exported']} Notion records to {display}; skipped {export['skipped']} records.",
        f"Raw scholarships: {export['raw_count']}.",
    ]
    reasons = sorted(export["skip_reasons"].items(), key=lambda item: (-item[1], item[0]))
    if reasons:
        lines.append("Top skip reasons:")
        for reason, count in reasons:
            lines.append(f"- {reason}: {count}")
    return "\n".join(lines)
