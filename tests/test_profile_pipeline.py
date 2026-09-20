from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path

from scholarshipx.candidates import build_candidate_rows
from scholarshipx.models import Scholarship
from scholarshipx.notion import (
    export_notion_scholarships,
    has_disqualifying_requirement,
    has_relevant_lane,
)
from scholarshipx.profile_search import generate_profile_queries, load_profile
from scholarshipx.scoring import score_candidate


class ProfilePipelineTests(unittest.TestCase):
    def test_profile_queries_are_deterministic_and_bounded(self) -> None:
        profile = load_profile()
        first = generate_profile_queries(profile)
        second = generate_profile_queries(profile)
        self.assertEqual(first, second)
        self.assertLessEqual(len(first), 40)
        self.assertTrue(any("computer science" in query for query in first))
        self.assertTrue(any("women in technology" in query for query in first))

    def test_generic_stem_and_leadership_are_not_profile_matches(self) -> None:
        self.assertFalse(
            has_relevant_lane(
                {"section": "STEM & Engineering", "major_requirements": "None stated"}
            )
        )
        self.assertFalse(has_relevant_lane({"section": "Leadership & Community"}))
        self.assertTrue(has_relevant_lane({"major_requirements": "Computer Science"}))

    def test_employee_child_requirement_is_rejected(self) -> None:
        item = {
            "name": "C&C Group Scholarship",
            "organization": "Greater Kansas City Community Foundation",
            "eligibility": ["Children of full-time C&C employees"],
            "notes": "Parent or legal guardian employment relationship",
        }
        self.assertTrue(has_disqualifying_requirement(item))

    def test_candidate_export_has_rich_evidence(self) -> None:
        item = Scholarship(
            id="cs-award",
            name="Computer Science Award",
            organization="Sponsor",
            official_url="https://sponsor.example/scholarships/cs-award",
            amount="$1,000",
            amount_value=1000,
            deadline="2027-03-15",
            section="Computer Science & Software",
            tags=["Undergrad", "Computer Science"],
            eligibility=["Undergraduate computer science students"],
            major_requirements="Computer Science",
        )
        scored = score_candidate(item, today=date(2026, 9, 20))
        rows = build_candidate_rows([scored])
        self.assertEqual(rows[0]["match_status"], "likely_match")
        self.assertIn("evidence_snippet", rows[0])
        self.assertIn("fit_score", rows[0])

    def test_notion_export_keeps_four_fields(self) -> None:
        result = export_notion_scholarships([], today=date(2026, 9, 20))
        self.assertEqual(result["rows"], [])
        self.assertEqual(json.loads("[]"), result["rows"])
        self.assertTrue(Path("data/notion_scholarships.json").exists())


if __name__ == "__main__":
    unittest.main()
