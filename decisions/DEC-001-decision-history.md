# DEC-001 — Preserve the reasons behind fixes

- Date: 2026-10-14
- Status: Accepted; repository documentation implemented in this change.
- Request source: This conversation. The user asked to track what was fixed and why in GitHub, based on the chat and their needs, because tomorrow's unrelated fix might otherwise reverse a previous improvement.

## Reason and outcome

Commit history alone describes code changes without reliably retaining the user's purpose. Existing operational files contain useful requirements, but also successive revisions that are difficult to scan. Stable decision records make the intent explicit and discoverable before the next edit.

The repository now has a canonical index, individual rationale records, a template, startup instructions in both repositories and a PR review template. Accepted requirements, prepared implementations, live releases and recommendations are labeled separately.

## Preserve during future work

- Keep the reason, the user need, affected behavior and actual verification together.
- Read the relevant records before an unrelated change. Do not erase the rationale to make a new implementation appear consistent.
- Record intentional changes with a superseding decision and explicit user-request context. New user instructions still take precedence.
- Distinguish a recommendation from an approved requirement and a staged implementation from a published fix.
- Publish only concise product requirements. Full transcripts and private details stay out of public repositories.

## Files and verification

`DECISIONS.md`, `decisions/`, `NEWSPAPER_REVIEW.md`, `AGENTS.md`, `README.md` and `.github/pull_request_template.md` in Claude-Briefing; a canonical link and corresponding startup/review instructions in Oracle.

Verification: Markdown links and decision IDs checked in the changed documentation; candidate Git tree checked against the intended documentation-only file set. No product behavior, scheduler, data or live layout changes are part of this documentation commit. Publication is reported separately in the conversation and Git history.

## Tradeoff

This is durable guidance and a review discipline, not a guarantee that no future regression can occur. Relevant automated behavior checks should accompany implementation changes. Avoid a second independently edited copy of the canonical history.
