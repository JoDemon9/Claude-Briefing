# DEC-009 — A coherent daily reading route

- Date: 15 October 2026, Asia/Nicosia.
- User need: The user disliked the way separate editions and sections were combined in the main newspaper and asked for a more beautiful, intelligent composition.
- Status: Implemented locally; publication and actual task-prompt verification pending.

## Change and rationale

scripts/v2/daily.py and newspaper-ui.css; unique stable story selections, linked highlights from world/Cyprus, global coverage first and a collapsed chronology after news.

Extends DEC-004/005. Preserve one selected version per story, every participating slot, reviewed cumulative overview, factual summaries, optional analysis, readers, provenance and timestamps. No fuzzy merging or text concatenation. Favourite stories retain overview anchors on their compact rows.

## Verification and publication

See tests/test_selection.py, relevant UI/browser checks and RELEASE_NOTES_2026-10-15-CURATION.md for actual checks, main commits, Pages and task status. Do not equate a local build with a live release. New selection gates begin with the 16 October morning; the rendered layout applies to maintained existing pages immediately.

Follow-up [DEC-012](DEC-012-reading-ui-and-followups.md) removes visible duration labels while preserving concise findings, and adds explicit later-coverage links and a compact mobile reading layout.
