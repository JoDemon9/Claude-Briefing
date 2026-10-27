# Maintenance operations

Read only the relevant section. Active editorial rules are in [the spec](../BRIEFING_SPEC.md), execution in [the task contract](../CHATGPT_TASK_INSTRUCTIONS.md). Historical incident reports under `history/` are not current deployment assertions.

## Cloud preparation and submission

The private `JoDemon9/Claude-Briefing-Private` host runs maintained public Python before the existing AI schedules. Reference workflows are in `deployment/`; changing them here does not change installed private workflows. Existing GitHub retry windows and Cloudflare watchdog must be preserved. Preparation is allowed 70 to more than 10 minutes before the AI task; submitted packs are immutable. GitHub cron delivery is best-effort. Missing/stale packs stop synthesis; maintenance may manually prepare a slot without adding an AI catch-up run.

`PUBLIC_BRIEFING_TOKEN` in the private repository needs Contents read/write for Claude-Briefing to submit source candidates; the private GITHUB_TOKEN only saves private packs. The existing watchdog uses its restricted private Actions-write/Contents-read credential. Never log secrets or export private caches as public artifacts. Check actual workflow/credential state separately from reference files.

```sh
python scripts/v2/pre_run.py --root <public> --private-root <private> --wire-root <portal> --slot morning
python scripts/v2/compose.py --input <private>/sources/synthesis/<edition>.md --research-pack <private>/research/runs/<edition>/research_pack.json
```

Compilation is offline and does not publish. `auto` is compiler acceptance after author review, never a synthetic source/quote/check time. Do not replace a pack during synthesis. New grammar is delivered by the Python digest; generated prompt files still need separate installation if saved task text is changed.

## Checks and publication

`python scripts/v2/backend.py` derives fresh capabilities from code/schema. `checks.py --base <sha>` chooses content or maintenance; `--profile full` explicitly includes historical browser audits. Daily publication has content, preview and integrity only; maintenance adds unit regressions. `quick_validate.py` is not a release gate replacement.

CI stores `.work/check-report.json`, detailed logs and the exact `docs/` artifact. Promotion reuses that artifact/receipt. `PORTAL_DEPLOY_TOKEN` in Claude-Briefing needs Contents read/write for oracle-briefing; the source workflow GITHUB_TOKEN cannot grant cross-repository access. Local role-specific `ORACLE_PUBLIC_PUSH_TOKEN` and `ORACLE_PORTAL_PUSH_TOKEN` are preflighted separately. Existing source Pages build requests use pages:write.

```sh
python scripts/v2/publish.py --portal-root <portal>
python scripts/v2/publish.py --status --date YYYY-MM-DD
# Only for an already authorized publication:
python scripts/v2/publish.py --portal-root <portal> --checks-receipt .work/check-report.json --publish
```

The journal `.work/publication-state.json` tracks generation, validation, build, checks, source push/verification, portal sync/push/verification. Resume the same inputs after resolving the recorded failure; don't delete the journal to hide it. Changed inputs invalidate relevant receipts. Fresh-main worktrees, allowlists and concurrency checks preserve independent Wire commits; no force push or automatic PR merge. Verify exact source Pages before portal sync, then exact portal bytes with bounded CDN retry. Source success with portal failure is reported as partial publication, never a distributed transaction or complete success.

## Targeted diagnostics

`backend.py --audit-identities` shows exact duplicate-ID/URL/headline review candidates. Resolve explicitly in `content/story-identity-reviews.json` or reviewed flat aliases, never fuzzy automatic merging. `backend.py --audit-freshness --at <ISO>` is read-only and cannot rewrite history or infer outcomes. `photo_library.py` and `prepare_images.py` verify exact licensed bytes; legacy aliases remain valid. Shared photo reuse adds no new duplicate binaries.

For a sparse edition inspect the digest's candidate inventory, visible per-desk evidence counts, omissions, actual source accessibility and selection reasons. Do not raise AI budgets or require invented shortage sources. For stale copy inspect baseline provenance and material deltas; explicitly retire irrelevant baseline stories. Full reporting and original times stay in the archive.

To change policy, update the owning canonical file, regenerate prompts if needed, update the digest/compiler/schema together, and add behavioral regressions. Run `checks.py` on the maintenance branch. Record actual checks and separate PR/main/Pages/task state in the PR; do not create another daily instruction override log.
