from __future__ import annotations

import argparse

from scholarshipx.notion import format_notion_cli_summary, run_notion_export
from scholarshipx.status import refresh_conference_status, refresh_status
from scholarshipx.store import load_conferences, load_scholarships, save_conferences, save_scholarships


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scholarshipx",
        description="Discover scholarships from listing sites and render GitHub tables.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    discover_parser = sub.add_parser("discover", help="Scrape listing sites and merge new scholarships")
    discover_parser.add_argument("--max-new", type=int, default=15, help="Cap on newly added verified rows")
    discover_parser.add_argument(
        "--no-search",
        action="store_true",
        help="Only fetch configured listing pages, skip DuckDuckGo",
    )

    sub.add_parser("status", help="Recompute OPEN / CLOSING SOON / OPENS SOON from deadlines")
    sub.add_parser("render", help="Rebuild README.md and ARCHIVE.md from JSON")
    sub.add_parser("notion-export", help="Write data/notion_scholarships.json from filtered scholarships")

    args = parser.parse_args(argv)

    if args.command == "discover":
        from scholarshipx.discover import discover
        from scholarshipx.render import render

        report = discover(max_new=args.max_new, use_search=not args.no_search)
        rendered = render()
        print(
            "Scholarshipx discovery complete\n"
            f"Profile queries: {report['profile_queries']}; "
            f"queries used: {report['queries_used']}; "
            f"search results considered: {report['search_results_considered']}\n"
            f"Pages fetched: {report['pages_fetched']}; "
            f"candidates extracted: {report['discovered']}; "
            f"{report['verified']} verified, "
            f"{report['rejected']} rejected, "
            f"{report['added']} added, "
            f"{report['total']} total.\n"
            f"Likely matches: {report['likely_matches']}; "
            f"possible matches: {report['possible_matches']}\n"
            f"Wrote: {report['candidate_path']}\n"
            "Top rejection reasons: "
            + ", ".join(
                f"{reason}={count}"
                for reason, count in sorted(
                    report["rejection_reasons"].items(),
                    key=lambda item: (-item[1], item[0]),
                )[:5]
            )
        )
        print(format_notion_cli_summary(rendered["notion_path"], rendered["notion_summary"]))
        return 0

    if args.command == "status":
        items = refresh_status(load_scholarships())
        save_scholarships(items)
        conferences = refresh_conference_status(load_conferences())
        save_conferences(conferences)
        open_count = sum(1 for item in items if item.status == "OPEN")
        closing = sum(1 for item in items if item.status == "CLOSING_SOON")
        soon = sum(1 for item in items if item.status == "OPENS_SOON")
        expired = sum(1 for item in items if item.status == "EXPIRED")
        grant_open = sum(1 for item in conferences if item.status in {"OPEN", "CLOSING_SOON"})
        print(
            f"Status updated: {open_count} open, {closing} closing soon, "
            f"{soon} opens soon, {expired} expired scholarships; "
            f"{grant_open} conference grants still in window."
        )
        return 0

    if args.command == "render":
        from scholarshipx.render import render

        report = render()
        print(
            f"Rendered {report['active']} scholarships and {report['conferences']} conferences to README.md "
            f"({report['archived']} + {report['archived_conferences']} archived); "
            f"{report['candidate']} candidate rows written to {report['candidate_path']}."
        )
        print(format_notion_cli_summary(report["notion_path"], report["notion_summary"]))
        return 0

    if args.command == "notion-export":
        export = run_notion_export()
        print(format_notion_cli_summary(export["path"], export))
        return 0

    parser.error("unknown command")
    return 2
