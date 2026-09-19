from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

# Scraped listing text is untrusted. Strip markup and reject jailbreak-style payloads
# before they land in JSON, README, or a later agent prompt.
INJECTION_PATTERNS = (
    r"ignore (all |any )?(previous|prior|above) (instructions|prompts|rules)",
    r"disregard (all )?(previous|prior|above) (instructions|prompts|rules)",
    r"you are (now )?(chatgpt|an? ai|a language model)",
    r"system prompt",
    r"\[INST\]",
    r"<\|im_start\|>",
    r"<\|endofprompt\|>",
    r"```(?:system|assistant|tool)",
    r"do not follow (the )?(user|developer)",
    r"override (your )?(safety|guardrails|instructions)",
)

_INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.I)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]+\)")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
UNSAFE_TAGS = ("script", "style", "noscript", "iframe", "object", "embed", "template")
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def looks_like_injection(text: str) -> bool:
    return bool(text and _INJECTION_RE.search(text))


def sanitize_text(text: str, limit: int = 280) -> str:
    cleaned = html.unescape(text or "")
    cleaned = _HTML_TAG_RE.sub(" ", cleaned)
    cleaned = _MD_LINK_RE.sub(r"\1", cleaned)
    cleaned = _CONTROL_RE.sub("", cleaned)
    cleaned = cleaned.replace("|", "/").replace("`", "'")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:limit]


def markdown_cell(text: str) -> str:
    return sanitize_text(text, limit=160) or "—"


def html_text(text: str, limit: int = 160) -> str:
    return html.escape(sanitize_text(text, limit=limit) or "—")


def prepare_html(html_text: str) -> BeautifulSoup:
    soup = BeautifulSoup(html_text or "", "lxml")
    for tag in soup(UNSAFE_TAGS):
        tag.decompose()
    return soup


def is_safe_http_url(url: str) -> bool:
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
