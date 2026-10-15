# DEC-008 — Compact favourite links and distinct other sports

- Date: 15 October 2026, Asia/Nicosia.
- User need: The user could not understand the expanded sports sections and requested one small latest-news link per favourite, with two additional sports stories outside those interests.
- Status: Implemented locally; publication and actual task-prompt verification pending.

## Change and rationale

scripts/v2/sports.py, selection.py, build.py/daily.py, article sports_interest metadata, content schema, shared CSS and browser/unit checks. Existing result/fixture evidence and all dated readers remain archived.

Supersedes the old expandable favourite layout and 2–3 sports target. Keep exactly four official latest-news links, no per-favourite prose/disclosure and at most two other stories. Never move F1 news into the other-sports desk.

## Verification and publication

See tests/test_selection.py, relevant UI/browser checks and RELEASE_NOTES_2026-10-15-CURATION.md for actual checks, main commits, Pages and task status. Do not equate a local build with a live release. New selection gates begin with the 16 October morning; the rendered layout applies to maintained existing pages immediately.

Follow-up [DEC-011](DEC-011-real-sports-logos.md) supersedes the emoji markers with small authentic logo images; the four-link layout is preserved.
