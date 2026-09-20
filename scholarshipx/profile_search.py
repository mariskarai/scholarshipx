from __future__ import annotations

from typing import Any

import yaml

from scholarshipx.paths import PROFILE_PATH

MAX_PROFILE_QUERIES = 32


def load_profile(path=PROFILE_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def generate_profile_queries(profile: dict[str, Any] | None = None) -> list[str]:
    profile = profile or load_profile()
    student = profile.get("student") or {}
    school = (student.get("school") or ["University of Kansas"])[0]
    major = (student.get("major") or ["computer science"])[0]
    fields = [str(value).lower() for value in (profile.get("include") or {}).get("fields", [])]
    identities = [str(value).lower() for value in (profile.get("include") or {}).get("identity_lanes", [])]
    locations = [str(value) for value in (profile.get("include") or {}).get("locations", [])]

    queries = [
        f"women in computing scholarship undergraduate deadline 2027",
        f"women in technology scholarship undergraduate {major}",
        f"first generation {major} scholarship undergraduate",
        "immigrant student scholarship undergraduate technology",
        f"{school} {major} scholarship current student",
        f"Kansas undergraduate {major} scholarship",
        "Kansas City women in technology scholarship",
        "software engineering scholarship women undergraduate",
        "fintech scholarship undergraduate computer science",
        "business technology scholarship undergraduate",
        "undergraduate AI scholarship computer science women",
        "undergraduate cybersecurity scholarship women technology",
    ]
    for field in fields:
        queries.append(f"{field} scholarship undergraduate deadline 2027")
    for identity in identities:
        queries.append(f"{identity} scholarship undergraduate technology")
    for location in locations:
        queries.append(f"{location} scholarship undergraduate computer science")

    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        normalized = " ".join(query.split()).strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            seen.add(key)
            deduped.append(normalized)
    return deduped[:MAX_PROFILE_QUERIES]
