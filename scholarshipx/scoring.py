from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from scholarshipx.models import Scholarship, STATUS_EXPIRED
from scholarshipx.notion import (
    _deadline,
    has_disqualifying_requirement,
    has_relevant_lane,
    is_specific_scholarship_url,
)


@dataclass(frozen=True)
class ScoredCandidate:
    item: Scholarship
    fit_score: float
    match_status: str
    match_lanes: list[str]
    uncertainties: list[str]
    rejection_reason: str | None
    candidate_type: str = "individual_scholarship"


def _text(item: Scholarship) -> str:
    return " ".join(
        [
            item.name,
            item.organization,
            item.section,
            " ".join(item.tags),
            " ".join(item.eligibility),
            item.major_requirements,
            item.academic_level,
            item.notes,
            " ".join(item.other_requirements),
        ]
    ).lower()


def _lanes(item: Scholarship) -> list[str]:
    text = _text(item)
    checks = (
        ("computer science", ("computer science", "computing")),
        ("software engineering", ("software",)),
        ("technology", ("technology", "technolog", "cyber", "artificial intelligence", "data science")),
        ("business / fintech", ("business", "fintech", "finance")),
        ("women in tech / STEM", ("women in", "woman", "female", "girls in")),
        ("first-generation / immigrant", ("first-generation", "first generation", "immigrant")),
        ("Kansas / KU / Kansas City", ("kansas", "ku", "lawrence", "kansas city")),
        ("engineering", ("engineering",)),
        ("leadership / community", ("leadership", "community")),
        ("undergraduate", ("undergraduate", "bachelor", "college student")),
    )
    return [label for label, signals in checks if any(signal in text for signal in signals)]


GENERIC_PORTAL_PATTERNS = (
    re.compile(r"award\s*(?:&|and)\s*scholarships?\s*hub"),
    re.compile(r"financial aid\s*(?:&|and)\s*scholarships?"),
    re.compile(r"community foundation scholarships?"),
    re.compile(r"scholarship portal"),
    re.compile(r"scholarships? hub"),
    re.compile(r"search and apply for scholarships"),
    re.compile(r"award hub"),
)


def is_generic_portal(item: Scholarship) -> bool:
    text = _text(item)
    path = item.official_url.lower().rstrip("/")
    return any(pattern.search(text) for pattern in GENERIC_PORTAL_PATTERNS) or (
        path.endswith("academicworks.com") and "/opportunities/" not in path
    )


def _profile_terms(profile: dict[str, Any]) -> list[str]:
    include = profile.get("include") or {}
    values: list[str] = []
    for key in ("fields", "identity_lanes", "locations", "priorities"):
        values.extend(str(value).lower() for value in include.get(key, []) or [])
    student = profile.get("student") or {}
    for key in ("major", "school", "level"):
        raw = student.get(key, [])
        values.extend(str(value).lower() for value in (raw if isinstance(raw, list) else [raw]))
    return values


def _profile_exclusion(text: str, profile: dict[str, Any]) -> str | None:
    exclusions = (profile.get("exclude") or []) if profile else []
    for exclusion in exclusions:
        normalized = str(exclusion).lower().replace("-", " ")
        if normalized and normalized in text:
            return str(exclusion)
    return None


def _strong_profile_fit(item: Scholarship, profile: dict[str, Any]) -> bool:
    text = _text(item)
    configured = " ".join(_profile_terms(profile)) or (
        "computer science software computing technology women in stem "
        "first-generation immigrant business fintech"
    )
    strong_groups = (
        ("computer science", "software", "computing", "technology", "technolog"),
        ("women in tech", "women in stem", "women in", "female", "woman"),
        ("first-generation", "first generation", "first-gen", "immigrant"),
        ("business", "fintech", "finance", "entrepreneur"),
    )
    if any(
        any(signal in text for signal in group)
        and any(signal in configured for signal in group)
        for group in strong_groups
    ):
        return True
    has_local = any(signal in text for signal in ("university of kansas", "kansas city", "lawrence", "ku"))
    has_individual_evidence = bool(
        item.eligibility
        or (
            item.notes
            and any(signal in text for signal in ("student", "undergraduate", "ku"))
        )
    )
    return has_local and has_individual_evidence and not is_generic_portal(item)


def score_candidate(
    item: Scholarship,
    profile: dict[str, Any] | None = None,
    today: date | None = None,
) -> ScoredCandidate:
    profile = profile or {}
    text = _text(item)
    lanes = _lanes(item)
    uncertainties: list[str] = []
    score = 0.25
    rejection_reason: str | None = None
    now = today or date.today()
    candidate_type = "generic_portal" if is_generic_portal(item) else "individual_scholarship"
    minimum_amount = int(profile.get("minimum_amount", 500) or 500)

    if item.status == STATUS_EXPIRED or (item.deadline and item.deadline < now.isoformat()):
        return ScoredCandidate(item, 0.0, "reject", lanes, [], "expired", candidate_type)
    profile_exclusion = _profile_exclusion(text, profile)
    if profile_exclusion:
        return ScoredCandidate(
            item,
            0.0,
            "reject",
            lanes,
            [],
            f"profile_exclusion:{profile_exclusion}",
            candidate_type,
        )
    if has_disqualifying_requirement(item):
        return ScoredCandidate(item, 0.0, "reject", lanes, [], "unsupported_requirement", candidate_type)
    if item.amount_value is not None:
        if item.amount_value < minimum_amount:
            return ScoredCandidate(item, 0.1, "reject", lanes, [], "below_minimum_amount", candidate_type)
        score += 0.08
    else:
        if "varies" in item.amount.lower():
            score += 0.02
        else:
            uncertainties.append("amount should be confirmed on the official page")

    strong_signals = (
        ("computer science", 0.25),
        ("software", 0.20),
        ("technology", 0.15),
        ("business", 0.12),
        ("fintech", 0.15),
        ("women in", 0.15),
        ("first-generation", 0.15),
        ("immigrant", 0.15),
        ("kansas", 0.12),
        ("university of kansas", 0.15),
        ("leadership", 0.05),
        ("community", 0.05),
        ("undergraduate", 0.10),
    )
    for signal, weight in strong_signals:
        if signal in text:
            score += weight

    resolved_deadline = _deadline(item.to_dict(), today=today)
    if not resolved_deadline:
        uncertainties.append("deadline should be confirmed on the official page")
    if not item.eligibility and item.major_requirements.lower() in {"", "none stated", "unknown", "n/a"}:
        uncertainties.append("eligibility details are sparse")
    if not is_specific_scholarship_url(item.official_url):
        score -= 0.20
        uncertainties.append("official application page not found")
    else:
        score += 0.12
    if not _strong_profile_fit(item, profile):
        score -= 0.20
        rejection_reason = "weak_profile_match"
    if candidate_type == "generic_portal":
        score = min(score, 0.49)
        uncertainties.append("generic portal, not an individual scholarship")

    score = max(0.0, min(1.0, round(score, 2)))
    strict_quality = (
        candidate_type == "individual_scholarship"
        and bool(resolved_deadline)
        and ("official application page not found" not in uncertainties)
        and (item.amount_value is not None or "varies" in item.amount.lower())
        and _strong_profile_fit(item, profile)
        and "eligibility details are sparse" not in uncertainties
    )
    if score >= 0.80 and strict_quality and rejection_reason is None:
        status = "likely_match"
    elif score >= 0.50 or (score >= 0.30 and _strong_profile_fit(item, profile)):
        status = "possible_match"
    elif score >= 0.30:
        status = "weak_match"
    else:
        status = "reject"
        rejection_reason = rejection_reason or "weak_profile_match"
    return ScoredCandidate(item, score, status, lanes, uncertainties, rejection_reason, candidate_type)
