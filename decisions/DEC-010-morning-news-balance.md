# DEC-010 — Five Cyprus stories and a stronger world briefing

- Date: 15 October 2026, Asia/Nicosia.
- User need: The user wants at most five local stories, normally five global stories and up to seven global stories only when necessary.
- Status: Implemented locally; publication and actual task-prompt verification pending.

## Change and rationale

scripts/v2/selection.py, build.py, selection_review schema, shared editorial instructions and the existing morning task prompt.

The lead counts in its actual daily.section. Five locals and seven globals are absolute ceilings for new mornings; six/seven globals need an explicit editorial reason. No quota padding or relabelling. Earlier snapshots keep their historical inventory. Midday/evening scope and schedules are preserved.

## Verification and publication

See tests/test_selection.py, relevant UI/browser checks and RELEASE_NOTES_2026-10-15-CURATION.md for actual checks, main commits, Pages and task status. Do not equate a local build with a live release. New selection gates begin with the 16 October morning; the rendered layout applies to maintained existing pages immediately.


## Extension on 18 October 2026

[DEC-017](DEC-017-section-coverage-and-github-checks.md) adds explicit five-per-section targets for every slot, evidence-backed section shortfalls, and GitHub-built candidate/receipt reuse. It revises the later-slot combined five-story scope while preserving no filler, source/editorial review, original times and historical snapshots. Actual task prompts are updated; the checked implementation in PR #15 has explicit user merge approval and awaits amended candidate verification.
