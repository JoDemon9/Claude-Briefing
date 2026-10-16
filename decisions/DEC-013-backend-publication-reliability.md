# DEC-013 — Reliable publication and versioned producers

- User request: implement all six approved backend recommendations: resumable publishing, per-slot/site status, prompt/schema capabilities, shared story identity checks, structured freshness, and incremental builds/verification.
- Date: 15 October 2026.
- Extends DEC-008–012 without changing sports/UI choices, content, historical times/URLs, privacy, image/reading gates, schedules or Wire's editorial role.
- Status: implementation and failure/retry checks on existing review branches; main/Pages publication remains pending. See release notes for actual final checks and task state.

The existing source builder already protected local publication. The missing boundary was the multi-step/two-site operation: a push could be mistaken for live publication, portal metadata could be partially saved, compatibility relied on prose, and every archive reader was rendered/re-fetched each run.

`BACKEND_OPERATIONS.md` defines the concrete stages, private durable journal, process locks, retry/output invalidation, safe allowlists, atomic local candidates, exact live checks and separate two-site failure states. The Git adapter uses fresh-main worktrees to preserve concurrent independent Wire updates; tests use local bare repositories, never production pushes. Default preparation performs no remote mutation. Existing review branches are not automatically merged or published.

The generated capability contract binds producer protocol oracle-briefing/3 to the actual schema hash. Source fingerprints preserve unchanged historical contracts. A shared registry flags review candidates without fuzzy merging and requires stable editorial event identity on future articles. Typed source-backed freshness records use edition time for archives and an independent explicit time for current audits. Legacy prose remains honestly unstructured. Future gates start 16 October to preserve existing published inventories.

Conservative dependency caching skips unchanged historical rendering; an invalid/altered cache or code/templates/assets force full rendering. Changed/current verification uses bounded parallel requests and retains the last good receipt on failure; full archive audit remains explicit. Companion portal changes add bounded retries, durable receipts and a local shared Wire/promotion lock, preserving the existing RSS schedule and data.

Affected: scripts/v2/{atomic,backend,incremental,publish,build,daily,release,sync_portal}.py, content schema, identity reviews, generated data contracts/reports, deployment checks, tests, shared instructions and the companion portal release/Wire entrypoint. No existing article source is rewritten.

Verified locally: 104-test full newspaper run, final 14-case backend run and the additional portal-promotion rollback case; 11 portal unit tests; 388 newspaper browser checks; 29 central browser cases. Full/incremental output equivalence, unchanged-input zero rendering, failure/retry/concurrency, contract/history, identity/freshness and last-good receipt behavior pass. All 112 original article files and five Wire data/cache/health files are unchanged. Three internal prompts were updated/read back exactly, settings/schedules unchanged and the historical fourth task untouched. Main and Pages remain pending.
