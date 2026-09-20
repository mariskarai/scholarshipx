from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from scholarshipx.models import Scholarship, STATUS_EXPIRED
from scholarshipx.notion import (
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


def score_candidate(
    item: Scholarship,
    profile: dict[str, Any] | None = None,
    today: date | None = None,
) -> ScoredCandidate:
    del profile
    text = _text(item)
    lanes = _lanes(item)
    uncertainties: list[str] = []
    score = 0.25
    rejection_reason: str | None = None
    now = today or date.today()

    if item.status == STATUS_EXPIRED or (item.deadline and item.deadline < now.isoformat()):
        return ScoredCandidate(item, 0.0, "reject", lanes, [], "expired")
    if has_disqualifying_requirement(item):
        return ScoredCandidate(item, 0.0, "reject", lanes, [], "unsupported_requirement")
    if item.amount_value is not None:
        if item.amount_value < 500:
            return ScoredCandidate(item, 0.1, "reject", lanes, [], "below_minimum_amount")
        score += 0.08
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

    if not item.deadline:
        uncertainties.append("deadline should be confirmed on the official page")
    if not item.eligibility and not item.major_requirements:
        uncertainties.append("eligibility details are sparse")
    if not is_specific_scholarship_url(item.official_url):
        score -= 0.15
        uncertainties.append("official URL may be a homepage rather than the application page")
    else:
        score += 0.12
    if not has_relevant_lane(item):
        score -= 0.20
        rejection_reason = "weak_profile_match"

    score = max(0.0, min(1.0, round(score, 2)))
    if score >= 0.80 and rejection_reason is None:
        status = "likely_match"
    elif score >= 0.55:
        status = "possible_match"
    elif score >= 0.30:
        status = "weak_match"
    else:
        status = "reject"
        rejection_reason = rejection_reason or "weak_profile_match"
    return ScoredCandidate(item, score, status, lanes, uncertainties, rejection_reason)
