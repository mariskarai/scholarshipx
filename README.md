<div align="center">

# Scholarshipx

### Undergraduate scholarships you can actually apply to — CS, STEM, first-gen, immigrant, and local awards in one table.

[![Last Updated](https://img.shields.io/github/last-commit/mariskarai/scholarshipx?style=for-the-badge&label=Last%20Updated&color=00C853&labelColor=000000)](https://github.com/mariskarai/scholarshipx/commits/main)

</div>



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

## Computer Science & Software

| Status | Scholarship | Organization | Amount | Tags | Apply | Deadline |
| ------ | ----------- | ------------ | ------ | ---- | ----- | -------- |
| ✅ **[OPEN]** | Oracle Scholarship for Excellence in Computer Science | National Federation of the Blind | Unknown | Undergrad · Computer Science | <a href="https://nfb.org"><img src="https://img.shields.io/badge/Apply-blue?style=for-the-badge" alt="Apply"></a> | Mar 31, 2027 |
| ✅ **[OPEN]** | ESA Foundation Computer and Video Game Arts and Sciences Scholarship | Entertainment Software Association | $3,000 | Undergrad · Computer Science · Women in STEM | <a href="https://www.theesa.com"><img src="https://img.shields.io/badge/Apply-blue?style=for-the-badge" alt="Apply"></a> | Apr 30, 2027 |

## STEM & Engineering

| Status | Scholarship | Organization | Amount | Tags | Apply | Deadline |
| ------ | ----------- | ------------ | ------ | ---- | ----- | -------- |
| 🔥 **[CLOSING SOON]** | Johnson & Johnson Access-Ability Lime Connect Scholarship | Lime Connect / Johnson & Johnson | $10,000 | Undergrad · STEM · Disability | <a href="https://limeconnect.com/opportunities/scholarships-awards/"><img src="https://img.shields.io/badge/Apply-blue?style=for-the-badge" alt="Apply"></a> | Sep 22, 2026 |
| ✅ **[OPEN]** | BOC Sciences Chemistry Scholarship Program | BOC Sciences | $1,000 | Undergrad · STEM | <a href="https://www.bocsci.com/chemistry-scholarship-program.html"><img src="https://img.shields.io/badge/Apply-blue?style=for-the-badge" alt="Apply"></a> | Oct 31, 2026 |
| ✅ **[OPEN]** | Golen Engine Scholarship | Golen Engine Service | $500 | Undergrad · STEM | <a href="http://golenengineservice.com"><img src="https://img.shields.io/badge/Apply-blue?style=for-the-badge" alt="Apply"></a> | November 30. |
| ✅ **[OPEN]** | ASHARE Undergraduate Engineering Scholarships | American Society of Heating, Refrigerating and Air-Conditioning | $3,000 $10,000 | Undergrad · STEM · Undergraduate | <a href="http://www.ashrae.org"><img src="https://img.shields.io/badge/Apply-blue?style=for-the-badge" alt="Apply"></a> | December 1. |
| ✅ **[OPEN]** | Decommissioning and Environmental Science Division Scholarship | American Nuclear Society | $2,000 $3,000 | Undergrad | <a href="http://www.ans.org"><img src="https://img.shields.io/badge/Apply-blue?style=for-the-badge" alt="Apply"></a> | February 1. |

## Women in STEM / Tech

| Status | Scholarship | Organization | Amount | Tags | Apply | Deadline |
| ------ | ----------- | ------------ | ------ | ---- | ----- | -------- |
| ✅ **[OPEN]** | Dotcom-Monitor Women in Computing Scholarship | Dotcom-Monitor, Inc. | $1,000 | Undergrad · Computer Science · Women in STEM | <a href="https://www.dotcom-monitor.com"><img src="https://img.shields.io/badge/Apply-blue?style=for-the-badge" alt="Apply"></a> | Apr 1, 2027 |

## First-generation & Immigrant

| Status | Scholarship | Organization | Amount | Tags | Apply | Deadline |
| ------ | ----------- | ------------ | ------ | ---- | ----- | -------- |
| — | None yet | — | — | — | — | — |

## Business & FinTech

| Status | Scholarship | Organization | Amount | Tags | Apply | Deadline |
| ------ | ----------- | ------------ | ------ | ---- | ----- | -------- |
| — | None yet | — | — | — | — | — |

## Leadership & Community

| Status | Scholarship | Organization | Amount | Tags | Apply | Deadline |
| ------ | ----------- | ------------ | ------ | ---- | ----- | -------- |
| ✅ **[OPEN]** | H.G. Hardbarger Science - Mathematics Award | Parkersburg Area Community Foundation | Unknown | Undergrad · STEM | <a href="https://pacfwv.com"><img src="https://img.shields.io/badge/Apply-blue?style=for-the-badge" alt="Apply"></a> | Mar 1, 2027 |
| ✅ **[OPEN]** | Ronald Phillips Memorial Science Scholarship | Community Foundation for Southwest Washington | $2,500 | Undergrad | <a href="http://www.cfsww.org"><img src="https://img.shields.io/badge/Apply-blue?style=for-the-badge" alt="Apply"></a> | Check site |

## General Undergraduate

| Status | Scholarship | Organization | Amount | Tags | Apply | Deadline |
| ------ | ----------- | ------------ | ------ | ---- | ----- | -------- |
| — | None yet | — | — | — | — | — |


---

## How to update this list

The tables above are built from JSON so columns stay aligned.

```bash
py -3 -m venv .venv
.venv\Scripts\activate
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
