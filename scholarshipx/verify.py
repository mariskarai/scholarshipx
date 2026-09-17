from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlparse

from scholarshipx.models import STATUS_EXPIRED, Scholarship
from scholarshipx.paths import SOURCES_PATH
from scholarshipx.sanitize import is_safe_http_url, looks_like_injection
from scholarshipx.status import parse_deadline

DEFAULT_BLOCKED_APPLY_DOMAINS = (
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

PAY_TO_APPLY = (
    "application fee",
    "pay to apply",
    "processing fee required",
    "fee to apply",
)
SWEEPSTAKES = (
    "sweepstakes",
    "giveaway",
    "random drawing",
    "no essay scholarship by sallie",
    "scholarshipowl",
    "100 bold points",
    "one click apply",
)
HIGH_SCHOOL_ONLY = (
    "high school senior",
    "high school students",
    "grade level high school senior",
)
GRAD_ONLY = (
    "graduate-only",
    "master's only",
    "phd only",
    "doctoral only",
)


def is_undergrad_eligible(item: Scholarship) -> bool:
    blob = " ".join(
        [
            item.name,
            item.academic_level,
            item.notes,
            " ".join(item.tags),
            " ".join(item.eligibility),
        ]
    ).lower()
    if any(token in blob for token in GRAD_ONLY) and "undergraduate" not in blob:
        return False
    hs_only = any(token in blob for token in HIGH_SCHOOL_ONLY)
    college = any(
        token in blob
        for token in ("undergraduate", "college", "all grade levels", "all students", "university")
    )
    if hs_only and not college:
        return False
    return True


def is_sweepstakes(item: Scholarship) -> bool:
    blob = f"{item.name} {item.notes} {item.organization}".lower()
    return any(token in blob for token in SWEEPSTAKES)


def requires_payment(item: Scholarship) -> bool:
    blob = f"{item.notes} {' '.join(item.other_requirements)}".lower()
    return any(token in blob for token in PAY_TO_APPLY)


def apply_host(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def blocked_apply_domains() -> list[str]:
    try:
        import yaml

        sources = yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8")) or {}
        configured = sources.get("blocked_apply_domains") or []
        if configured:
            return [item.removeprefix("www.") for item in configured]
    except Exception:
        pass
    return list(DEFAULT_BLOCKED_APPLY_DOMAINS)


def is_blocked_apply_url(url: str, blocked: list[str] | None = None) -> bool:
    host = apply_host(url)
    blocked = blocked or blocked_apply_domains()
    return any(host == domain or host.endswith("." + domain) for domain in blocked)


def has_external_apply_link(item: Scholarship) -> bool:
    if not item.official_url:
        return False
    if not is_safe_http_url(item.official_url):
        return False
    return not is_blocked_apply_url(item.official_url)


def has_prompt_injection(item: Scholarship) -> bool:
    blob = " ".join(
        [
            item.name,
            item.organization,
            item.notes,
            item.amount,
            item.deadline_display,
            " ".join(item.eligibility),
            " ".join(item.other_requirements),
        ]
    )
    return looks_like_injection(blob)


def verify(item: Scholarship, today: date | None = None) -> tuple[bool, str]:
    if not item.name or not item.official_url:
        return False, "missing name or url"
    if not is_safe_http_url(item.official_url):
        return False, "invalid url"
    if has_prompt_injection(item):
        return False, "prompt injection in scraped text"
    if is_sweepstakes(item):
        return False, "sweepstakes or giveaway"
    if requires_payment(item):
        return False, "pay to apply"
    if not is_undergrad_eligible(item):
        return False, "not undergraduate-eligible"
    if not has_external_apply_link(item):
        return False, "missing external apply link"
    if len(item.organization) > 80:
        return False, "organization field looks scraped incorrectly"
    deadline = parse_deadline(item.deadline, today=today)
    if deadline is None and item.deadline_display and not (item.deadline_display or "").lower().startswith("opens "):
        deadline = parse_deadline(item.deadline_display, today=today)
    if deadline and deadline < (today or date.today()):
        return False, "expired"
    if item.status == STATUS_EXPIRED:
        return False, "expired"
    if re.search(r"graduate only|high-school-only|high school only", item.notes, flags=re.I):
        return False, "wrong academic level"
    return True, "ok"
