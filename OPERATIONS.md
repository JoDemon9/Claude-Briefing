# Newspaper operations

Routine production uses [BRIEFING_RUNTIME.md](BRIEFING_RUNTIME.md), the compact packet and fresh main capabilities. This consolidated policy supersedes the former repeated startup document list (DEC-014). Detailed recovery contracts remain in [BACKEND_OPERATIONS.md](BACKEND_OPERATIONS.md); the original instructions are preserved under maintenance/history/2026-10-15.

The existing ChatGPT tasks at 07:30 / 13:30 / 19:30 Europe/Athens select, research, write and review. No second scheduler is introduced. The public repo holds reviewed structured content and deterministic static output; Private holds source notes and persistent research state; Oracle holds the saved full daily newspaper and independent RSS Wire.

## Routine commands

1. research.py --date D --slot E --at <offset time> --private-root <private checkout> --wire-root <portal checkout>
2. collect.py --packet <returned packet> --private-root <private checkout>; read attention items and relevant evidence only. No automatic verified_at changes.
3. photo_library.py --story-id <stable ID>; explicitly review relevance/date before --reuse. prepare_images.py --edition D-E verifies every selected asset.
4. publish.py --portal-root <portal checkout> prepares and validates one candidate. For an already authorised publication use the same command with --publish. Inspect --status and .work/check-report.json; resume after the recorded failure rather than regenerating unrelated material.
5. usage.py --packet <packet> --checks .work/check-report.json --private-root <private checkout> records work and outcome. Real Pro usage is optional manually observed data, never a token/time estimate.

All commands are under scripts/v2; run from a checked-out maintained main with requirements-v2.txt installed. A producer without local runtime uses a validated candidate/CI and verifies its exact release receipt; it must not write substitute HTML or claim missing checks ran. Until these helpers exist on actual main, follow the active editorial policy with the maintained main workflow and supported fields, storing unsupported metadata privately.

## Publication contracts

build.py produces independent editions/readers/archive/search, the cumulative daily/YYYY-MM-DD.html, today.html/day-latest.json, and public indexes. latest.html/latest.json remains the latest independent snapshot. sync_portal.py saves the complete day, descriptors and required assets in Oracle, preserving archive/Wire. Keep original times and existing URLs on corrections.

release.py records the public allowlist and verifies exact served bytes; daily_release.py does the same for the central snapshot. Source Pages must verify before central promotion. The private durable journal distinguishes generated/validated/built/checked, pushed and served/verified stages on each site. Retain last good receipts/snapshots and accurately report partial publication.

Routine content CI validates source constraints and changed edition/day/readers at mobile/desktop with and without JavaScript. Code/schema/template/test/workflow changes trigger full unit/browser regression; archive audits remain separately available. A failure blocks publication and produces a concise report plus logs. Routine tasks do not debug or weaken tests.

Wire collection remains its own existing :15/:45 UTC workflow; provider health older than 90 minutes is stale discovery, never verified reporting. No private Pages, personal messages, additional task or changes to task schedules. Git commits alone never update the actual ChatGPT prompts. Track code/main/Pages and actual task updates separately.
