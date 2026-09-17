from __future__ import annotations

from datetime import date
from urllib.parse import urlparse

import yaml

from scholarshipx.careeronestop import enrich_details, is_careeronestop_url
from scholarshipx.extract import extract_from_html
from scholarshipx.fetch import USER_AGENT, polite_fetch
from scholarshipx.models import Scholarship
from scholarshipx.paths import SOURCES_PATH
from scholarshipx.status import normalize_name, normalize_url, refresh_status, slugify
from scholarshipx.store import load_scholarships, save_scholarships
from scholarshipx.verify import has_external_apply_link, verify

DEFAULT_MAX_NEW = 15
DEFAULT_SEARCH_RESULTS = 8


def load_sources() -> dict:
    return yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8"))


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _is_preferred(url: str, sources: dict) -> bool:
    host = _domain(url)
    allowed = [item.removeprefix("www.") for item in sources.get("prefer_domains", [])]
    return any(host == item or host.endswith("." + item) for item in allowed)


def search_listing_sites(queries: list[str], sources: dict, limit: int = DEFAULT_SEARCH_RESULTS) -> list[str]:
    urls: list[str] = []
    try:
        from ddgs import DDGS
    except ImportError:
        return urls
    with DDGS() as ddgs:
        for query in queries:
            try:
                results = ddgs.text(query, max_results=limit)
            except Exception:
                continue
            for row in results or []:
                href = row.get("href") or row.get("url")
                if href and _is_preferred(href, sources):
                    urls.append(href)
    return urls


def merge_scholarships(existing: list[Scholarship], incoming: list[Scholarship]) -> tuple[list[Scholarship], int]:
    by_url = {normalize_url(item.official_url): item for item in existing if item.official_url}
    by_id = {item.id: item for item in existing}
    by_name = {normalize_name(item.name): item for item in existing}
    added = 0
    for item in incoming:
        item.id = slugify(item.name)
        url_key = normalize_url(item.official_url)
        name_key = normalize_name(item.name)
        if url_key in by_url or item.id in by_id or name_key in by_name:
            continue
        by_url[url_key] = item
        by_id[item.id] = item
        by_name[name_key] = item
        existing.append(item)
        added += 1
    return existing, added


def prune_internal_apply_links(items: list[Scholarship]) -> list[Scholarship]:
    return [item for item in items if has_external_apply_link(item)]


def discover(
    max_new: int = DEFAULT_MAX_NEW,
    use_search: bool = True,
    today: date | None = None,
) -> dict:
    import httpx

    sources = load_sources()
    existing = prune_internal_apply_links(load_scholarships())
    listing_urls = [site["url"] for site in sources.get("listing_sites", [])]
    search_urls: list[str] = []
    if use_search:
        search_urls = search_listing_sites(sources.get("search_queries", []), sources)

    seen_urls: set[str] = set()
    ordered_urls: list[str] = []
    for url in listing_urls + search_urls:
        key = normalize_url(url)
        if key in seen_urls:
            continue
        seen_urls.add(key)
        ordered_urls.append(url)

    discovered: list[Scholarship] = []
    rejected = 0
    pages = polite_fetch(ordered_urls)
    section_by_url = {
        normalize_url(site["url"]): site.get("section", "General Undergraduate")
        for site in sources.get("listing_sites", [])
    }

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=30.0) as client:
        for page in pages:
            if not page.ok:
                rejected += 1
                continue
            section = section_by_url.get(normalize_url(page.url), "General Undergraduate")
            extracted = extract_from_html(page.html, page.url, default_section=section)
            if extracted and is_careeronestop_url(page.url):
                extracted = enrich_details(extracted[: max_new * 2], client, today=today)
            for item in extracted:
                ok, _reason = verify(item, today=today)
                if not ok:
                    rejected += 1
                    continue
                discovered.append(item)

    unique: list[Scholarship] = []
    seen: set[str] = set()
    for item in discovered:
        key = f"{item.id}|{normalize_url(item.official_url)}"
        if key in seen:
            continue
        seen.add(key)
        if not item.id:
            item.id = slugify(item.name)
        unique.append(item)
        if len(unique) >= max_new:
            break

    merged, added = merge_scholarships(existing, unique)
    merged = prune_internal_apply_links(merged)
    refresh_status(merged, today=today)
    save_scholarships(merged)
    return {
        "pages_fetched": len(pages),
        "discovered": len(discovered),
        "verified": len(unique),
        "rejected": rejected,
        "added": added,
        "total": len(merged),
    }
