from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from scholarshipx.models import (
    CHECK_SITE,
    NONE_STATED,
    UNKNOWN,
    Scholarship,
    today_iso,
)
from scholarshipx.sanitize import is_safe_http_url, prepare_html, sanitize_text
from scholarshipx.status import (
    format_deadline,
    parse_amount_value,
    parse_deadline,
    slugify,
)

SKIP_TITLE_BITS = (
    "no-essay",
    "no essay",
    "sweepstakes",
    "giveaway",
    "one click apply",
    "find free scholarships",
    "college scholarships to apply",
    "what is a scholarship",
)

STEM_HINTS = (
    "computer science",
    "software",
    "stem",
    "engineering",
    "technology",
    "coding",
    "cyber",
    "data science",
    "ai ",
    "artificial intelligence",
)
WOMEN_HINTS = ("women", "woman", "female", "girls in")
FIRSTGEN_HINTS = ("first-generation", "first generation", "first in family", "immigrant", "daca", "undocumented")
BUSINESS_HINTS = ("business", "finance", "fintech", "accounting", "mba")
LOCAL_HINTS = ("kansas", "local", "community", "county", "city of")


def infer_section(name: str, text: str, fallback: str) -> str:
    blob = f"{name} {text}".lower()
    if any(hint in blob for hint in WOMEN_HINTS) and any(hint in blob for hint in STEM_HINTS):
        return "Women in STEM / Tech"
    if any(hint in blob for hint in FIRSTGEN_HINTS):
        return "First-generation & Immigrant"
    if "computer" in blob or "software" in blob or "coding" in blob or "cyber" in blob:
        return "Computer Science & Software"
    if any(hint in blob for hint in BUSINESS_HINTS):
        return "Business & FinTech"
    if any(hint in blob for hint in LOCAL_HINTS):
        return "Leadership & Community"
    if any(hint in blob for hint in STEM_HINTS):
        return "STEM & Engineering"
    return fallback or "General Undergraduate"


def infer_tags(name: str, text: str) -> list[str]:
    blob = f"{name} {text}".lower()
    tags: list[str] = ["Undergrad"]
    if "computer science" in blob or "software" in blob:
        tags.append("Computer Science")
    if "stem" in blob or "engineering" in blob:
        tags.append("STEM")
    if any(hint in blob for hint in WOMEN_HINTS):
        tags.append("Women in STEM")
    if "first-generation" in blob or "first generation" in blob:
        tags.append("First-gen")
    if "immigrant" in blob or "daca" in blob:
        tags.append("Immigrant")
    if "kansas" in blob:
        tags.append("Kansas")
    if "undergraduate" in blob:
        tags.append("Undergraduate")
    seen: set[str] = set()
    ordered: list[str] = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            ordered.append(tag)
    return ordered[:6]


def _clean_name(text: str) -> str:
    name = sanitize_text(text, limit=140).strip(" -:|")
    name = re.sub(r"^(top\s+\d+\s+)", "", name, flags=re.I)
    return name[:140]


def _looks_like_title(text: str) -> bool:
    name = _clean_name(text)
    if len(name) < 8 or len(name) > 140:
        return False
    lowered = name.lower()
    if any(bit in lowered for bit in SKIP_TITLE_BITS):
        return False
    if lowered in {"scholarships", "apply", "deadline", "amount"}:
        return False
    return bool(re.search(r"scholarship|fellowship|grant|award", lowered))


def extract_from_html(html: str, page_url: str, default_section: str = "General Undergraduate") -> list[Scholarship]:
    host = urlparse(page_url).netloc.lower()
    if "careeronestop.org" in host:
        from scholarshipx.careeronestop import extract_search_results

        found = extract_search_results(html, page_url, default_section)
        if found:
            return found
    return _extract_generic(html, page_url, default_section)


def _scholarship(
    name: str,
    organization: str,
    url: str,
    amount: str,
    deadline_text: str,
    body: str,
    section: str,
    source: str,
) -> Scholarship:
    parsed_deadline = parse_deadline(deadline_text)
    amount_text = amount or UNKNOWN
    return Scholarship(
        id=slugify(name),
        name=_clean_name(name),
        organization=sanitize_text(organization or source, limit=80) or source,
        official_url=url,
        amount=amount_text if amount_text != UNKNOWN else UNKNOWN,
        amount_value=parse_amount_value(amount_text),
        deadline=parsed_deadline.isoformat() if parsed_deadline else None,
        deadline_display=format_deadline(parsed_deadline, fallback=deadline_text or CHECK_SITE),
        section=infer_section(name, body, section),
        tags=infer_tags(name, body),
        eligibility=[sanitize_text(line, limit=180) for line in re.findall(r"^[-*]\s+(.+)$", body, flags=re.M)][:8],
        major_requirements=NONE_STATED,
        academic_level="Undergraduate",
        min_gpa=NONE_STATED,
        citizenship=NONE_STATED,
        essay_required=UNKNOWN,
        notes=sanitize_text(body, limit=280),
        date_found=today_iso(),
        source=source,
    )


def _extract_generic(html: str, page_url: str, section: str) -> list[Scholarship]:
    soup = prepare_html(html)
    items: list[Scholarship] = []
    for link in soup.find_all("a", href=True):
        raw_href = link.get("href")
        if isinstance(raw_href, (list, tuple)):
            raw_href = raw_href[0] if raw_href else ""
        href = urljoin(page_url, str(raw_href or ""))
        name = _clean_name(link.get_text(" ", strip=True))
        if not _looks_like_title(name):
            continue
        if not is_safe_http_url(href):
            continue
        parent_text = ""
        parent = link.find_parent(["article", "li", "div", "tr"])
        if parent:
            parent_text = sanitize_text(parent.get_text(" ", strip=True), limit=800)
        amount_match = re.search(r"\$[\d,]+", parent_text)
        deadline_match = re.search(
            r"(?:deadline[:\s]+)?((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+20\d{2})",
            parent_text,
            flags=re.I,
        )
        items.append(
            _scholarship(
                name,
                urlparse(href).netloc.replace("www.", ""),
                href,
                amount_match.group(0) if amount_match else UNKNOWN,
                deadline_match.group(1) if deadline_match else CHECK_SITE,
                parent_text,
                section,
                urlparse(page_url).netloc.replace("www.", ""),
            )
        )
    return _dedupe_extracted(items)


def _dedupe_extracted(items: list[Scholarship]) -> list[Scholarship]:
    seen: set[str] = set()
    unique: list[Scholarship] = []
    for item in items:
        key = item.id
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
