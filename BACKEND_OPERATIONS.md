# Publishing contract and recovery — DEC-013

This is the maintained producer/publisher path after the review branches reach main. Existing ChatGPT tasks remain the only edition producers. No new scheduler or delivery is introduced. Keep source Markdown and research notes private.

## Prepare, publish, resume, inspect

Start with fresh public and portal main checkouts and the maintained Python dependencies. Keep unrelated work in separate checkouts. Preparation does not perform a remote write:

```sh
python scripts/v2/publish.py --portal-root ../oracle-briefing
python scripts/v2/publish.py --status --date 2026-10-16
```

The coordinator records generated → validated → built → checked → public_published → public_verified → portal_synced → portal_published → portal_verified in `.work/publication-state.json`. The status command reports all three slots, including missing/draft content, the exact failed stage, release IDs and whether current inputs still match the record. `published` means the Git push was accepted; `verified` means exact live Pages bytes passed. No generation or deployment time is inferred from a scheduled slot.

For an already authorized daily publication on reviewed main:

```sh
python scripts/v2/publish.py --portal-root ../oracle-briefing --publish
```

Retry the same command after resolving the recorded failure. Completed preparation/check/publication steps are retained for the same inputs; each retry rechecks live state before advancing the portal. Changed inputs archive the prior journal and start a new run. Changed/missing local outputs invalidate build/sync completion. A killed process releases the OS lock; a `running` step is retried. Never delete the journal merely to hide a failed step.

The Git adapter accepts only the configured repositories and main, rejects unrelated staged/untracked work, and publishes allowlisted public files through a temporary worktree based on fresh remote main. Concurrent unrelated Wire commits survive. Incoming publisher-code drift or conflicting editorial files stop publication. No force push, automatic PR merge or private export occurs. A successful push does not reset the operator's checkout; the private Git baseline permits retries and subsequent publications without discarding local work. Use a fresh checkout when updating publisher code.

Local source builds and portal sync prepare complete candidates and restore the preceding directory if promotion fails. Portal sync and local Wire collection share a process lock. Live source verification must succeed before portal sync/publication. A source or central live mismatch leaves the last successful verification receipt intact. These are two separate Pages deployments: a source publication can succeed while central publication is pending. The journal reports that state; it does not claim a distributed transaction or silently roll back another publisher's commit. Prior good public releases remain in Git history and the portal's saved snapshot remains available.

## Producer/renderer compatibility

Fetch actual main first. `python scripts/v2/backend.py` derives the contract from the checked-out schema. A build exposes the same machine-readable contract at `docs/data/capabilities.json`. Compare its schema SHA-256 with `templates/v2/content.schema.json`; do not trust a stale deployed capability file over fresh main.

The producer protocol is `oracle-briefing/3`; content schema version remains 2. For new published editions from local date 2026-10-16, copy the exact `producer_protocol` and `content_schema_sha256` into `edition.producer_contract`. Use only declared fields/features, reading review 2 and image review 2. A mismatch stops publication. Unchanged historical editions retain accepted contracts through source fingerprints in `data/edition-contracts.json`; editing one requires the current contract. This avoids invalidating history merely because an additive schema changes its hash.

Until this implementation reaches main, keep using the actual maintained main workflow and supported fields. Keep unsupported review/identity/freshness data privately. An open PR or updated ChatGPT prompt is not a deployment.

## Story identity and review

`docs/data/story-registry.json` covers all structured published editions, stable IDs, aliases and dated references. From 16 October new articles require a stable `story_identity` key describing the subject/event/date. Reuse it across actual updates. Different identities under one stable ID, duplicate canonical IDs within an edition, alias cycles/chains/missing targets and invalid/future follow-ups fail validation. Existing day-composer chronology checks remain active.

Identical normalized headlines, explicit identity keys or reporting URLs under different IDs produce review candidates. Similar wording never automatically merges stories. Record a justified `distinct_stories` decision keyed by the issue hash in `content/story-identity-reviews.json`, or deliberately reconcile stable IDs with a flat alias map. Candidates involving new publications from 16 October block until resolved; older unresolved candidates remain visible as historical warnings. Reviewed seed decisions preserve the broad market/TSMC distinction and separate UEFA matches based on existing source records, without changing article facts or IDs.

Run `python scripts/v2/backend.py --audit-identities` to see the complete candidate IDs/evidence before resolving a blocked publication. This read-only audit does not bypass publication validation.

## Freshness

Edition/article `freshness` arrays use typed records: `weather`, `warning`, `event`, `recheck`. All require an ID, label, checked_at and HTTPS source URLs. Forecasts/warnings require valid_from, valid_until and recheck_at. Events require starts_at and recheck_at; ends_at is optional. Recheck records require recheck_at. Use explicit timezone offsets and real evidence; never guess expiry or an outcome.

The schema and backend reject reversed intervals, duplicate records, checks later than edition completion and rechecks before the source check. From 16 October a weather panel requires structured forecast validity. Expired/due/started-or-ended records block a new publication unless explicitly retained as historical_context and described as such in the editorial text. A started event is an outcome requiring research, not an inferred result.

`docs/data/freshness.json` is evaluated at each edition's actual editorial/publication timestamp. Legacy unstructured prose remains marked `legacy_unstructured`, not falsely verified. For a separate current audit:

```sh
python scripts/v2/backend.py --audit-freshness --at 2026-10-16T13:00:00+03:00
```

The audit does not rewrite archives. Existing structured sports fixture and opportunity times and their validation remain intact.

The two 15 October weather records are seeded from the exact forecast validity and retrieval times already stored in their panels. Their recheck_at values are editorial deadlines at the next existing briefing slot, not invented meteorological expiry times. No forecast wording, original publication/source time or article file is changed.

## Incremental work and archive audit

`build.py --incremental` validates all inputs, then renders changed days/editions/readers and shared indexes/descriptors. Same-day navigation and related readers form a conservative dependency group. Unchanged historical days/readers skip rendering. A first run, code/template/alias/asset change, corrupt cache or any altered/missing output forces a full build. The private cache is saved only after successful promotion. Plain `build.py` remains the full reference build; tests compare byte-for-byte results after a content change.

`release.py --verify-live` checks the release pointer first, then changed files and essential current editions/readers/assets with at most six concurrent downloads, each with a bounded timeout and retry budget. The first run checks every file. Only a completely successful run advances the private verified-file cache. CI restores that last successful cache and keeps full archive verification separately available:

```sh
python scripts/v2/release.py --verify-live --full
```

The existing deployment-verification workflow exposes the same manual full_archive input. Central verification checks its small complete current snapshot with the same bounded network retries. Wire files stay outside the daily release receipt.

## Efficient editorial production — DEC-014

BRIEFING_RUNTIME.md is the compact active contract. Routine tasks read that and applicable AGENTS files once, then prepare a private research.py packet instead of rereading full manuals/schemas/renderer/earlier bodies. Public research-index.json/photo-library.json contain only published context and approved image provenance. Private editorial memory, drafts, full collection evidence, packets and metrics never enter public docs or CI artifacts.

research.py --scaffold <packet> --title <Greek title> --articles <new article paths> mechanically creates a new draft from stable data. It copies all dated quote records and unchanged opportunities, clears old reviews/overviews/weather/movers/reader aliases, and never invents news or replaces an existing edition. After research, --remember D-E --at <actual time> --private-root <checkout> saves a checkpoint; --notes <JSON> accepts explicit unresolved questions/next_check_at by stable story ID. Resume is offered only when the source hash still matches and evidence predates the checkpoint.

collect.py caches bounded public-source fetches, normalises changed text and proposes conservative parsed quote snapshots. Unsupported providers, changed/new/failed documents and official close/fixing ambiguities require review. HTTP 304 preserves original retrieval provenance; neither collection nor unchanged hashes advances verified_at. --apply-report <collection.json> --edition D-E --approve <instruments> --at <actual review> copies only explicitly reviewed, non-older, matching-unit candidates into the matching draft and validates its schema. No article text or catalyst is generated.

photo_library.py suggests already licensed/decoded assets by exact story identity. --reuse requires explicit factual caption/alt, relevance and original date/archive review; checksums bind source and target and original rights/retrieval metadata stays unchanged. prepare_images.py validates cached/reused bytes and only paces actual network downloads. Logos are excluded.

The blocking checked stage runs checks.py or consumes an exact release/profile receipt from a completed local/CI check. DEC-021 defines three routine gates:

1. content: prepare selected images and validate/build once. Source/schema, evidence metadata, reading, image rights, section coverage, identity, freshness and opportunity rules remain blocking. An already built candidate receives validation once.
2. preview: selected edition and cumulative day only, at 390px JS-on and 1440px JS-off. Verify the full finding/toggle, headline, lead image, local links/assets, overflow and JS errors. Generated reader references are validated without a browser sweep of readers/history.
3. integrity: confirm the source/output fingerprint did not change, then record the exact release receipt.

Code/schema/template/test/workflow/runtime changes require maintenance: the same three gates plus unit regressions. They cannot be downgraded to content. The old archive browser suites are available only through explicit --profile full or the workflow's manual full_regression input. They are not a daily completion requirement. This supersedes DEC-014/017/018's automatic full-suite wording, not their evidence standards. Detailed logs stay in .work/check-logs; read .work/check-report.json and its named failing input. QA inputs remain fingerprinted. Genuine matching passing CI receipts are reused without rebuilding or repeating validation. Preserve failed candidates and the last good publication.

Central CI verifies the exact saved daily receipt and previews the current portal at the same two configurations. Its code changes add units; historical portal/Wire suites are explicit full audits only. Source live verification still precedes central promotion, with bounded current-release hash verification on both sites. Wire remains independent; no new scheduler is added.

usage.py writes private work/gate metrics and optional explicitly observed Pro-window percentages. It never estimates account quota from bytes/calls/time. research.py --replay <3–5 saved IDs> measures input/due-check proxies, not fresh editorial quality or real Pro savings. Historical maintenance can make earlier evidence unavailable at a replay cutoff; the packet withholds it rather than guessing the old version. The real 3–5-edition pilot starts when the helpers are on maintained main; compact prompt policy can apply meanwhile using supported main fields.
