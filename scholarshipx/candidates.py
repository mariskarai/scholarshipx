from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from scholarshipx.models import Scholarship
from scholarshipx.notion import _deadline, is_specific_scholarship_url
from scholarshipx.paths import CANDIDATE_SCHOLARSHIPS_PATH
from scholarshipx.scoring import ScoredCandidate

STATUS_ORDER = {"likely_match": 0, "possible_match": 1}


def _evidence(item: Scholarship) -> str:
    evidence = " ".join(item.eligibility or [])
    if not evidence:
        evidence = item.notes
    return " ".join(evidence.split())[:320]


def candidate_row(scored: ScoredCandidate) -> dict[str, Any]:
    item = scored.item
    deadline = _deadline(item.to_dict())
    return {
        "name": item.name,
        "amount": item.amount_value,
        "amount_display": item.amount,
        "website": item.official_url,
        "deadline": deadline,
        "source_url": item.listing_url or item.official_url,
        "source_name": item.source or item.organization,
        "match_status": scored.match_status,
        "fit_score": scored.fit_score,
        "match_lanes": scored.match_lanes,
        "evidence_snippet": _evidence(item),
        "eligibility_summary": " ".join(item.eligibility)[:500],
        "uncertainties": scored.uncertainties,
        "official_page_verified": is_specific_scholarship_url(item.official_url),
        "deadline_verified": bool(deadline),
        "amount_verified": item.amount_value is not None,
        "eligibility_verified": bool(
            item.eligibility
            or item.major_requirements.lower() not in {"", "none stated", "unknown", "n/a"}
        ),
        "rejection_reason": scored.rejection_reason,
    }


def build_candidate_rows(
    scored: list[ScoredCandidate],
    limit: int = 25,
) -> list[dict[str, Any]]:
    rows = [
        candidate_row(candidate)
        for candidate in scored
        if candidate.match_status in {"likely_match", "possible_match"}
    ]
    rows.sort(
        key=lambda row: (
            STATUS_ORDER[row["match_status"]],
            -row["fit_score"],
            row["deadline"] or "9999-12-31",
            row["name"].casefold(),
        )
    )
    return rows[:limit]


def save_candidate_rows(
    rows: list[dict[str, Any]],
    path: Path = CANDIDATE_SCHOLARSHIPS_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def build_profile_exports(
    items: list[Scholarship],
    today=None,
) -> dict[str, Any]:
    from scholarshipx.notion import export_notion_scholarships
    from scholarshipx.scoring import score_candidate
    from scholarshipx.store import save_notion_scholarships

    scored = [score_candidate(item, today=today) for item in items]
    rows = build_candidate_rows(scored)
    candidate_path = save_candidate_rows(rows)
    likely_items = [candidate.item for candidate in scored if candidate.match_status == "likely_match"]
    notion = export_notion_scholarships(likely_items, today=today)
    save_notion_scholarships(notion["rows"])
    return {
        "scored": scored,
        "candidate_rows": rows,
        "candidate_path": str(candidate_path),
        "rejection_reasons": dict(
            Counter(
                candidate.rejection_reason
                for candidate in scored
                if candidate.rejection_reason
            )
        ),
        "notion": notion,
    }
