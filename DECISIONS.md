# Product decisions and reasons

This is the canonical record of user needs that future changes must respect. Read it before changing the newspaper, its content workflow or the Oracle portal. A changelog says what changed; these records also explain why, what should remain true, and how the result was checked.

## Recorded decisions

| ID | User need | Current status | Record |
| --- | --- | --- | --- |
| DEC-026 | Better analytical quality while retaining low usage. | Implementation and bounded-input regression checks; deployment and future editorial results tracked separately. | [Quality within synthesis budget](decisions/DEC-026-quality-within-synthesis-budget.md) |
| DEC-025 | Stop five-hour quota exhaustion: Python collection before the AI, hard budgets and later delta-only output. | Deployed; live prompts, PATs and exact site releases verified; Python preparation has bounded retry windows before each AI task. | [Deterministic prefetch and single-turn synthesis](decisions/DEC-025-deterministic-prefetch-and-single-turn.md) |
| DEC-023 | Audit the v3 compiler/rendering/runtime and deliver three prompts; ordinary missing items must not stop an edition. | Implementation and regression checks in audit branch; main, CI, Pages and actual task settings tracked separately. | [Compiler audit and partial availability](decisions/DEC-023-compiler-audit-and-partial-availability.md) |
| DEC-022 | Sports section renaissance (rich team cards, restore favorite major stories), and autonomous CI publishing with zero-friction LLM push. | Implemented: sports_news, sports renderer, relaxed schema, quick_validate, and GitHub Actions autonomous pipeline. | [Sports renaissance & autonomous CI](decisions/DEC-022-sports-renaissance-and-autonomous-ci.md) |
| DEC-021 | Reduce daily checks to the minimum and make instructions clear for lower models, preserving good quality. | Three-gate implementation and six-step prompts under review; code/main/Pages/tasks tracked separately. | [Minimum daily checks](decisions/DEC-021-minimum-daily-checks.md) |
| DEC-020 | Restore sports output, support user-selected Luna with intact quality, and make findings collapsible. | Review branch prepared; checks, prompts, model selection and publication tracked separately. | [Luna, sports and findings](decisions/DEC-020-luna-sports-and-collapsible-findings.md) |
| DEC-019 | Further restrict mechanical quota use and restore visible news for the four favourite sports interests. | Three live prompts updated/read-back verified; bounded helpers and visible headline layout under review. Full CI pending. | [Visible favourite news and bounded work](decisions/DEC-019-favourite-news-and-bounded-work.md) |
| DEC-018 | Reduce remaining ChatGPT work through explicit mechanical delegation, compact inputs and targeted evidence review with unchanged quality. | Approved PR #17 merged; full candidate CI and 511 exact live file checks passed; three live prompts verified. Actual quota comparison pending. | [Further delegation with intact quality](decisions/DEC-018-further-delegation-with-quality.md) |
| DEC-016 | Move compilation, schema validation, image preparation and browser checks from ChatGPT to GitHub Actions. | Implemented by merged PR #15/DEC-017; full CI and live release verified. | [Decoupled content and CI](decisions/DEC-016-decoupled-content-and-ci.md) |
| DEC-017 | Move deterministic checks/builds to GitHub and meet separate International/Cyprus article targets in every slot. | Merged PR #15; full CI and 511 live file checks passed; actual prompts verified. | [Section coverage and GitHub checks](decisions/DEC-017-section-coverage-and-github-checks.md) |
| DEC-015 | Recover failed publication, improve news selection and clear writing, and keep schedules running. | Published and live verified on 16 October; deployment/task evidence in the recovery report. | [Production recovery](decisions/DEC-015-production-recovery-and-editorial-quality.md) |
| DEC-014 | Reduce Pro usage and improve editorial quality through compact inputs, reuse and automated routine work. | Published and live verified; compact tasks active; real usage pilot pending. | [Efficient editorial production](decisions/DEC-014-efficient-editorial-production.md) |
| DEC-013 | Reliable resumable publishing, status, versioned producers, identity, freshness and incremental work. | Published and live verified on 16 October; deployment/task evidence in the recovery report. | [Backend reliability](decisions/DEC-013-backend-publication-reliability.md) |
| DEC-012 | Compact mobile header, clear later developments, photo-first lead and no reading labels. | Published and live verified on 16 October; deployment/task evidence in the recovery report. | [Reading UI and follow-ups](decisions/DEC-012-reading-ui-and-followups.md) |
| DEC-011 | Authentic small sports logos replace emojis. | Published and live verified on 16 October; deployment/task evidence in the recovery report. | [Sports logos](decisions/DEC-011-real-sports-logos.md) |
| DEC-008 | Four small sports links and two distinct other sports stories. | Published and live verified on 16 October; deployment/task evidence in the recovery report. | [Compact sports](decisions/DEC-008-compact-sports.md) |
| DEC-009 | Compose the day as one curated newspaper. | Published and live verified on 16 October; deployment/task evidence in the recovery report. | [Daily composition](decisions/DEC-009-curated-daily-newspaper.md) |
| DEC-010 | At most five local stories; five globals, up to seven when justified. | Published and live verified on 16 October; deployment/task evidence in the recovery report. | [Morning balance](decisions/DEC-010-morning-news-balance.md) |
| DEC-006 | Keep three article actions on one row and remove per-photo prose. | Published and live verified; tasks updated. | [Compact article actions](decisions/DEC-006-compact-article-actions.md) |
| DEC-007 | Track actionable grants, benefits and rights with eligibility and application deadlines. | Published and live verified; tasks maintain the tracker. | [Opportunities and rights](decisions/DEC-007-opportunities-and-rights.md) |
| DEC-004 | The daily overview must include important selected stories from the whole available day. | Published and live verified; tasks updated. | [Whole-day overview](decisions/DEC-004-whole-day-overview.md) |
| DEC-005 | 30-second findings, useful expansion and further reading only when it adds knowledge; no forced counterarguments. | Published and live verified; tasks updated. | [Reading value](decisions/DEC-005-reading-value.md) |
| DEC-001 | Remember what was fixed and why, so unrelated work does not accidentally reverse it. | Accepted; repository documentation implemented. | [Decision history](decisions/DEC-001-decision-history.md) |
| DEC-002 | Source links take too much mobile space and make scrolling harder. | Published and live verified on 16 October; deployment/task evidence in the recovery report. | [Compact market evidence](decisions/DEC-002-compact-market-evidence.md) |
| DEC-003 | Markets should return intelligence beyond numbers already available on TradingView. | Published and live verified on 16 October; deployment/task evidence in the recovery report. | [Market interpretation](decisions/DEC-003-market-interpretation.md) |

The statuses distinguish implementation, CI, Pages and actual task settings. Earlier publication attempts were rejected by automatic approval review before explicit deployment approval. The user approved the concrete DEC-015 recovery on 16 October; both sites are now live verified and the three daily tasks resumed. See REPAIR_REPORT_2026-10-16.md for exact evidence.

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
- Preserve full factual summaries and historical readers. DEC-005 intentionally supersedes the earlier always-visible lead, preview/reader minimum lengths and universal counterargument checklist. The current layered reading policy and licensed-image requirements remain active.
- Keep licensed, relevant photographs and complete credits, with honest archive captions and readable failure states.
- Preserve source chains, unknown data, quote/source times and the distinction between reporting, editorial interpretation and verified events.
- Preserve mobile navigation, the 3/2/1 article grid, themes, search, bookmarks and reading controls.
- Keep ChatGPT production tasks separate from repository CI and the RSS Wire. Do not silently restore removed generators or change task schedules.
- Keep private notes out of public repositories and Pages.

Any proposed change to these rules must state the exact rule it revises and the user need supporting that revision.

## Proposals are not decisions

[The newspaper review](NEWSPAPER_REVIEW.md) contains recommendations, not approved work or a list of completed fixes. Add a decision record when a recommendation becomes an actual requested change.

Use [the record template](decisions/TEMPLATE.md). The Oracle repository links here rather than maintaining a second conflicting decision history. Only short, publishable product requirements belong here; do not copy private conversations or personal information.

[DEC-024 — Intelligence authoring and reading](decisions/DEC-024-intelligence-authoring-and-reading.md): user-approved implementation; source/portal review branches, checks and deployment tracked separately.
