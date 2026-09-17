from __future__ import annotations

import re
import time
from urllib.parse import urljoin, urlparse

from scholarshipx.extract import _scholarship
from scholarshipx.fetch import DELAY_SECONDS, USER_AGENT
from scholarshipx.models import CHECK_SITE, UNKNOWN, Scholarship
from scholarshipx.sanitize import is_safe_http_url, prepare_html, sanitize_text
from scholarshipx.status import parse_amount_value

COS_HOST = "careeronestop.org"
CS_KEEP = (
    "computer",
    "software",
    "computing",
    "programming",
    "cyber",
    "information technology",
    "video game",
    "coding",
    "artificial intelligence",
    "data science",
)


def relevant_to_section(name: str, body: str, section: str) -> bool:
    blob = f"{name} {body}".lower()
    if section == "Computer Science & Software":
        return any(token in blob for token in CS_KEEP)
    return True


def is_careeronestop_url(url: str) -> bool:
    return COS_HOST in urlparse(url).netloc.lower()


def _first_line(text: str) -> str:
    return re.split(r"[\n\r]|<br", text, maxsplit=1)[0].strip(" :")


def extract_search_results(html: str, page_url: str, section: str) -> list[Scholarship]:
    soup = prepare_html(html)
    items: list[Scholarship] = []
    for row in soup.select("tr"):
        link = row.select_one("a[href*='find-scholarships-detail.aspx']")
        if not link:
            continue
        name = sanitize_text(link.get_text(" ", strip=True), limit=140)
        if not name:
            continue
        cells = row.find_all("td")
        org = "Unknown"
        purpose = ""
        if cells:
            org_block = cells[0].get_text("\n", strip=True)
            org_match = re.search(r"Organization:\s*(.+)", org_block)
            if org_match:
                org = sanitize_text(org_match.group(1).split("\n")[0], limit=80)
            purpose_match = re.search(r"Purposes?:\s*(.+)", org_block, flags=re.I | re.S)
            if purpose_match:
                purpose = sanitize_text(purpose_match.group(1), limit=400)
        level = cells[1].get_text(" ", strip=True) if len(cells) > 1 else ""
        award_type = cells[2].get_text(" ", strip=True) if len(cells) > 2 else ""
        raw_amount = cells[3].get_text(" ", strip=True) if len(cells) > 3 else ""
        amount = raw_amount if raw_amount and raw_amount.upper() != "N/A" else UNKNOWN
        deadline_text = cells[4].get_text(" ", strip=True) if len(cells) > 4 else CHECK_SITE
        if "loan" in award_type.lower():
            continue
        lowered_level = level.lower()
        if lowered_level and "bachelor" not in lowered_level and "associate" not in lowered_level:
            continue
        if not relevant_to_section(name, " ".join([purpose, org, award_type]), section):
            continue
        detail = urljoin(page_url, link["href"])
        body = " ".join(part for part in [purpose, level, award_type] if part)
        item = _scholarship(name, org, "", amount, deadline_text, body, section, "careeronestop.org")
        item.listing_url = detail
        item.academic_level = level or "Undergraduate"
        items.append(item)
        if len(items) >= 10:
            break
    return items


def parse_detail(html: str, detail_url: str) -> dict[str, str]:
    soup = prepare_html(html)
    data: dict[str, str] = {}
    title = soup.select_one("#detailTitle")
    if title:
        data["name"] = sanitize_text(title.get_text(" ", strip=True), limit=140)
    for row in soup.select("table.cos-table-detail tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        label = cells[0].get_text(" ", strip=True).rstrip(":").lower()
        value = sanitize_text(cells[1].get_text(" ", strip=True), limit=400)
        link = cells[1].find("a", href=True)
        if label == "organization":
            lines = [line.strip() for line in cells[1].get_text("\n", strip=True).split("\n") if line.strip()]
            data["organization"] = sanitize_text(lines[0] if lines else value, limit=80)
        elif label == "funds":
            data["amount"] = sanitize_text(value, limit=40)
        elif label == "deadline":
            data["deadline"] = sanitize_text(value, limit=80)
        elif label == "purpose":
            data["purpose"] = value
        elif label == "qualifications":
            data["qualifications"] = value
        elif label == "level of study":
            data["level"] = sanitize_text(value, limit=80)
        elif label == "for more information" and link:
            href = urljoin(detail_url, link["href"])
            if is_safe_http_url(href):
                data["website"] = href
    return data


def enrich_details(items: list[Scholarship], client, today=None) -> list[Scholarship]:
    enriched: list[Scholarship] = []
    for index, item in enumerate(items):
        if not item.listing_url:
            continue
        try:
            response = client.get(item.listing_url, headers={"User-Agent": USER_AGENT}, timeout=30.0)
            html = response.text if response.is_success else ""
        except Exception:
            html = ""
        if html:
            detail = parse_detail(html, item.listing_url)
            if detail.get("website"):
                item.official_url = detail["website"]
            if detail.get("organization") and (not item.organization or item.organization == "Unknown"):
                item.organization = sanitize_text(detail["organization"], limit=80)
            if detail.get("amount") and (not item.amount or item.amount == UNKNOWN):
                item.amount = sanitize_text(detail["amount"], limit=40) or UNKNOWN
                item.amount_value = parse_amount_value(detail["amount"])
            if detail.get("deadline"):
                item.deadline_display = detail["deadline"]
            extra = " ".join(part for part in [detail.get("purpose"), detail.get("qualifications"), detail.get("level")] if part)
            if extra:
                item.notes = sanitize_text(extra, limit=280)
                item.eligibility = (
                    [sanitize_text(detail["qualifications"], limit=180)] if detail.get("qualifications") else item.eligibility
                )
        if item.official_url:
            enriched.append(item)
        if index < len(items) - 1:
            time.sleep(DELAY_SECONDS)
    return enriched
