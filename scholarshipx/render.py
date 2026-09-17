from __future__ import annotations

from datetime import date
from html import escape

from scholarshipx.models import (
    SECTIONS,
    STATUS_CLOSING_SOON,
    STATUS_EXPIRED,
    STATUS_OPEN,
    STATUS_OPENS_SOON,
    Scholarship,
)
from scholarshipx.paths import ARCHIVE_PATH, README_PATH
from scholarshipx.sanitize import is_safe_http_url, markdown_cell
from scholarshipx.status import refresh_status
from scholarshipx.store import load_scholarships, save_scholarships
from scholarshipx.verify import has_external_apply_link

STATUS_LABELS = {
    STATUS_OPEN: "✅ **[OPEN]**",
    STATUS_CLOSING_SOON: "🔥 **[CLOSING SOON]**",
    STATUS_OPENS_SOON: "⏳ **[OPENS SOON]**",
}

STATUS_ORDER = {
    STATUS_CLOSING_SOON: 0,
    STATUS_OPEN: 1,
    STATUS_OPENS_SOON: 2,
}

README_INTRO = """<div align="center">

# Scholarshipx

### Undergraduate scholarships you can actually apply to — CS, STEM, first-gen, immigrant, and local awards in one table.

[![Last Updated](https://img.shields.io/github/last-commit/mariskarai/scholarshipx?style=for-the-badge&label=Last%20Updated&color=00C853&labelColor=000000)](https://github.com/mariskarai/scholarshipx/commits/main)

</div>

> [!IMPORTANT]
> A living list of **currently open** undergraduate scholarships, with extra attention to computer science, software, STEM, women in tech, first-generation students, immigrant students, and local awards. Discovery uses [CareerOneStop Scholarship Finder](https://www.careeronestop.org/Toolkit/Training/find-scholarships.aspx) and keeps only awards that have a **sponsor apply link** (not Bold.org-style on-site applications). Deadlines move. Always confirm amount, eligibility, and dates on the **apply page** before you submit.

This list is generated from [`data/scholarships.json`](data/scholarships.json). Do not hand-edit the tables below — run the Python script instead.

---

## How to Read This List

**Status** — where the scholarship is in its cycle:

| Badge | Meaning |
| ----- | ------- |
| ✅ **[OPEN]** | Applications are open right now |
| 🔥 **[CLOSING SOON]** | Deadline is within about 2 weeks |
| ⏳ **[OPENS SOON]** | Next cycle is not open yet — watch the date |

**Apply** — the blue button goes to the **sponsor's own page**, not an aggregator. Awards that only apply on Bold.org or similar boards are skipped.

---

## Table of Contents

- [Computer Science & Software](#computer-science--software)
- [STEM & Engineering](#stem--engineering)
- [Women in STEM / Tech](#women-in-stem--tech)
- [First-generation & Immigrant](#first-generation--immigrant)
- [Business & FinTech](#business--fintech)
- [Leadership & Community](#leadership--community)
- [General Undergraduate](#general-undergraduate)
- [How to update this list](#how-to-update-this-list)

---
"""

README_FOOTER = """
---

## How to update this list

The tables above are built from JSON so columns stay aligned.

```bash
py -3 -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
py -3 -m scholarshipx discover
py -3 -m scholarshipx status
py -3 -m scholarshipx render
```

- `discover` searches [CareerOneStop Scholarship Finder](https://www.careeronestop.org/Toolkit/Training/find-scholarships.aspx), opens each award's detail page, and keeps the **sponsor website** as the apply link. It skips sweepstakes, expired awards, and boards with no external apply URL.
- `status` recalculates OPEN / CLOSING SOON / OPENS SOON from deadlines.
- `render` rewrites this README and moves expired awards to [`ARCHIVE.md`](ARCHIVE.md).

Quality over quantity: a run that adds a handful of verified listings is better than dumping every aggregator card.

Closed cycles live in [`ARCHIVE.md`](ARCHIVE.md).
"""

ARCHIVE_INTRO = """# Archive

Scholarships whose deadlines have passed. When a new cycle opens, `discover` / `status` can bring them back to the README.

| Scholarship | Organization | Amount | Apply | Deadline |
| ----------- | ------------ | ------ | ----- | -------- |
"""


def _apply_button(url: str) -> str:
    if not is_safe_http_url(url):
        return "—"
    safe = escape(url, quote=True)
    return (
        f'<a href="{safe}">'
        f'<img src="https://img.shields.io/badge/Apply-blue?style=for-the-badge" alt="Apply">'
        f"</a>"
    )


def _tags(item: Scholarship) -> str:
    return " · ".join(markdown_cell(tag) for tag in item.tags) if item.tags else "Undergrad"


def _row(item: Scholarship) -> str:
    badge = STATUS_LABELS.get(item.status, STATUS_LABELS[STATUS_OPEN])
    deadline = markdown_cell(item.deadline_display or item.deadline or "Check site")
    return (
        f"| {badge} | {markdown_cell(item.name)} | {markdown_cell(item.organization)} | "
        f"{markdown_cell(item.amount)} | {_tags(item)} | {_apply_button(item.official_url)} | {deadline} |"
    )


def _sort_key(item: Scholarship) -> tuple:
    return (
        STATUS_ORDER.get(item.status, 9),
        item.deadline or "9999-12-31",
        item.name.lower(),
    )


def _table(items: list[Scholarship]) -> str:
    header = (
        "| Status | Scholarship | Organization | Amount | Tags | Apply | Deadline |\n"
        "| ------ | ----------- | ------------ | ------ | ---- | ----- | -------- |"
    )
    rows = [_row(item) for item in sorted(items, key=_sort_key)]
    return "\n".join([header, *rows]) if rows else header + "\n| — | None yet | — | — | — | — | — |"


def render_readme(active: list[Scholarship]) -> str:
    parts = [README_INTRO]
    for section in SECTIONS:
        rows = [item for item in active if item.section == section]
        parts.append(f"## {section}\n")
        parts.append(_table(rows))
        parts.append("")
    parts.append(README_FOOTER)
    return "\n".join(parts).rstrip() + "\n"


def render_archive(expired: list[Scholarship]) -> str:
    rows = []
    for item in sorted(expired, key=lambda s: s.deadline or "", reverse=True):
        deadline = markdown_cell(item.deadline_display or item.deadline or "Unknown")
        rows.append(
            f"| {markdown_cell(item.name)} | {markdown_cell(item.organization)} | "
            f"{markdown_cell(item.amount)} | {_apply_button(item.official_url)} | {deadline} |"
        )
    body = "\n".join(rows) if rows else "| — | — | — | — | — |"
    return ARCHIVE_INTRO + body + "\n"


def render(today: date | None = None) -> dict:
    items = [item for item in refresh_status(load_scholarships(), today=today) if has_external_apply_link(item)]
    save_scholarships(items)
    expired = [item for item in items if item.status == STATUS_EXPIRED]
    active = [item for item in items if item.status != STATUS_EXPIRED]
    README_PATH.write_text(render_readme(active), encoding="utf-8")
    ARCHIVE_PATH.write_text(render_archive(expired), encoding="utf-8")
    return {
        "active": len(active),
        "archived": len(expired),
        "readme": str(README_PATH),
        "archive": str(ARCHIVE_PATH),
    }
