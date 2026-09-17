from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
TIMEOUT = 30.0
DELAY_SECONDS = 1.2


@dataclass
class FetchedPage:
    url: str
    status_code: int
    html: str
    ok: bool


def fetch_url(url: str, client: httpx.Client | None = None) -> FetchedPage:
    own_client = client is None
    http = client or httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-US,en;q=0.9"},
        follow_redirects=True,
        timeout=TIMEOUT,
    )
    try:
        response = http.get(url)
        html = response.text if "text" in response.headers.get("content-type", "text/html") else ""
        return FetchedPage(
            url=str(response.url),
            status_code=response.status_code,
            html=html,
            ok=response.is_success and bool(html),
        )
    except httpx.HTTPError:
        return FetchedPage(url=url, status_code=0, html="", ok=False)
    finally:
        if own_client:
            http.close()


def polite_fetch(urls: list[str]) -> list[FetchedPage]:
    pages: list[FetchedPage] = []
    with httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-US,en;q=0.9"},
        follow_redirects=True,
        timeout=TIMEOUT,
    ) as client:
        for index, url in enumerate(urls):
            pages.append(fetch_url(url, client=client))
            if index < len(urls) - 1:
                time.sleep(DELAY_SECONDS)
    return pages
