# Product decisions and reasons

This is the canonical record of user needs that future changes must respect. Read it before changing the newspaper, its content workflow or the Oracle portal. A changelog says what changed; these records also explain why, what should remain true, and how the result was checked.

## Recorded decisions

| ID | User need | Current status | Record |
| --- | --- | --- | --- |
| DEC-001 | Remember what was fixed and why, so unrelated work does not accidentally reverse it. | Accepted; repository documentation implemented. | [Decision history](decisions/DEC-001-decision-history.md) |
| DEC-002 | Source links take too much mobile space and make scrolling harder. | Requested; market implementation validated locally; publication pending. | [Compact market evidence](decisions/DEC-002-compact-market-evidence.md) |
| DEC-003 | Markets should return intelligence beyond numbers already available on TradingView. | Requested; market implementation validated locally; publication pending. | [Market interpretation](decisions/DEC-003-market-interpretation.md) |

The statuses above distinguish intent, implementation and publication. DEC-002/003 are user requirements, but their prepared code is not yet on main or live. The prior attempt to create the publication commit was rejected by automatic approval review. This documentation does not approve that pending release.

## How to use this record

1. Identify the relevant decision IDs before editing. Read their rationale and preservation requirements, then consult the current operational rules.
2. For each meaningful fix, add or update a record with the user's request or a faithful short paraphrase, the reason, affected files, tradeoffs, preservation requirements, actual checks and implementation/publication status. Never invent earlier chat history or claim checks that were not run.
3. Reference the IDs in the commit or PR description. Verify relevant behavior, not just that the new code runs.
4. When a later user request intentionally changes a decision, implement the request and create a superseding record linking both ways. Preserve the old reason and mark its status superseded. An unrelated fix is not authorization to reverse an earlier choice. If a request has an actual unresolved conflict, clarify that conflict and continue unaffected work.
5. Update status when code reaches main and again when live publication is verified. Code, CI, Pages and external ChatGPT actions are distinct states.

New user instructions take precedence over older records. This process does not add a blanket permission requirement to normal fixes.

## Existing requirements from repository instructions

These are existing documented rules, not reconstructed statements from unseen conversations. Their authority remains [AGENTS.md](AGENTS.md), [OPERATIONS.md](OPERATIONS.md), [BRIEFING_SPEC.md](BRIEFING_SPEC.md) and [CHATGPT_TASK_INSTRUCTIONS.md](CHATGPT_TASK_INSTRUCTIONS.md).

- Keep the central daily newspaper, independent edition snapshots and dated readers distinct; preserve historical URLs and original publication times.
- Preserve the full factual summaries, always-visible lead analysis, optional secondary-card analysis and separate full readers. The current reviewed word-count and image requirements remain active.
- Keep licensed, relevant photographs and complete credits, with honest archive captions and readable failure states.
- Preserve source chains, unknown data, quote/source times and the distinction between reporting, editorial interpretation and verified events.
- Preserve mobile navigation, the 3/2/1 article grid, themes, search, bookmarks and reading controls.
- Keep ChatGPT production tasks separate from repository CI and the RSS Wire. Do not silently restore removed generators or change task schedules.
- Keep private notes out of public repositories and Pages.

Any proposed change to these rules must state the exact rule it revises and the user need supporting that revision.

## Proposals are not decisions

[The newspaper review](NEWSPAPER_REVIEW.md) contains recommendations, not approved work or a list of completed fixes. Add a decision record when a recommendation becomes an actual requested change.

Use [the record template](decisions/TEMPLATE.md). The Oracle repository links here rather than maintaining a second conflicting decision history. Only short, publishable product requirements belong here; do not copy private conversations or personal information.
