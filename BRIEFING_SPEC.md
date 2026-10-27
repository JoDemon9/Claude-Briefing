# Briefing specification

This is the canonical editorial and data contract. Execution budgets belong to [CHATGPT_TASK_INSTRUCTIONS.md](CHATGPT_TASK_INSTRUCTIONS.md); exact fields belong to [content.schema.json](templates/v2/content.schema.json). Historical records are rationale, not additional instructions.

## Product and selection

Publish clear Greek in independent morning_scan, midday_delta and evening_synthesis snapshots. The cumulative newspaper includes useful selected coverage from the whole available day, not merely the latest slot's summary. Its overview cites actual participating story IDs; preserve independent archived readers and original times.

Target **4–5 supported Cyprus and 4–5 international stories separately**. Count the lead in its actual geographic desk; Sports does not fill a news target. Broad evidence discovery happens in Python before synthesis. Read every visible candidate; prefer consequential distinct events over recency, repeated election reports, promotional shows or cartoon columns. Reserve news evidence before optional authored Sports or extra corroboration. No filler or fabricated shortage research.

The bounded profile permits 10 authored records in Morning and 6 changed records later, including any Sports article. Later same-day carries can preserve complete coverage. The current policy allows at most 5 Cyprus and 7 world stories; 6–7 world stories require an explicit editorial reason. Historical accepted editions retain their original contracts.

For new `selection_policy=balanced-v1` candidates, fewer than four stories in either news desk requires a specific `coverage_notes` reason for that desk. This is an explanation of actual evidence/selection limits, not a claim of extra research. A small supported edition may publish with that explanation; an unexplained coverage collapse fails validation. The threshold is four, the preferred range is four to five. CI reports actual counts, carried counts and shortfall reasons. New sealed packs select this policy; standalone compilation and direct current-contract editions from 2026-10-28 must use it too. Already sealed older packs retain their policy until that cutoff. Editions accepted before deployment retain their exact historical contracts/fingerprints even if deployment happens after the cutoff; edited or unaccepted records cannot claim that exception.

## Evidence and useful depth

Read evidence for every new/material claim. Record publisher, HTTPS URL, original publication time (null if unknown), actual retrieval time, reporting group, kind, access and claim use. Feed-only items, HTTP success and metadata are discovery, not proof of factual review. Independently corroborate consequential/disputed claims where needed within the budget, or narrow/omit them. Never invent sources, outcomes, licences or fresh checks.

Give each desk a substantive lead when evidence supports it: what changed, mechanism/incentive, who is affected, uncertainty and an observable next test. Aim for 120–170 Greek words across its analytical fields, not a quota. Analytical fields require `analysis_sources` drawn from read evidence. Scenarios are conditional paths, not facts or arbitrary probabilities. Secondary dispatches are normally two factual sentences and at most 70 words in the bounded profile. Extra depth is reserved for desk leads and supported market/tactical movers. No compulsory essay, counterargument or decorative scenario. A full reader must add distinct knowledge; otherwise link the readable source and retain the dated archive route.

Executive synthesis has 1–3 points, at most 160 words total (aim 90–120), connecting supported developments to implications and a next test. Cite selected/carried story IDs; unchanged risks are dated context, never fresh verification. Do not invent connections or event history.

## Identity, lead and continuity

Semantic ASCII slugs are valid filenames. No section prefix or separate `lead.json` is required. Author `section=cyprus|world|sports` independently of `is_lead`; canonical JSON represents the lead through `daily.lead_story_id` and the lead category. The selected lead ID must resolve to one of the edition's articles. If no explicit lead survives, the compiler selects the first supported article. A desk's first changed article is its analytical lead, independent of the edition lead.

Use stable `story_id` and `story_identity` for one evolving event. Explicit flat aliases reconcile reviewed identities only; an empty alias map is valid. Never infer identity or follow-ups from similar headlines. `daily.follow_ups` links genuinely related, different published stories; reject self, missing, future or conflicting references. Later-coverage links belong to the cumulative day, never earlier snapshots.

Name an exact earlier baseline edition and fingerprint. Later slots must account for each baseline story by a material update, an explicit exact carry, or an explicit omission with a reason. Carry only useful **same-day** records; never roll yesterday's unchanged copy into today's newspaper. An omission retires it from the later snapshot while preserving earlier coverage in the archive/day. Across days, reselect only with supported new reporting. Preserve original publication/source/image times; copies get no false novelty or fabricated events. UPDATED/REVERSAL/CORRECTION require a real factual delta; identical reporting cannot become an update by changing timestamps, status, headline or ID. UNKNOWN is never automatically UNCHANGED. Original baseline records and hashes remain immutable.

## Markets, opportunities and weather

Keep all 38 instrument identities exactly once, with absent quotes null/unavailable. Preserve actual quote/fixing/effective times, currency, unit and session status. Never infer a close, tenor or causal explanation from price movement. Explain supported transmission and practical Cyprus implications ahead of raw numbers; keep full data and one shared source/time disclosure. No trading advice, unsupported targets or confidence percentages.

Opportunities retain stable call IDs, official read sources, `verified_at`, eligibility, support, stage, opening/deadline type/date, budget constraints, application route and next action. Preserve date-only deadlines. Closed/proposed/unknown is not an active entitlement; infer no personal eligibility. Due records retain original verification, become `review_due=true` and lose active application promotion. The day selects the latest actual verification; show three actionable records first and disclose the rest/watchlist.

Python checks weather each slot; preserve real location, forecast validity and warning expiry. A forecast fetch is not an official warning check. Expired/unreviewed data is unavailable or clearly historical. A scheduled/started event does not establish an outcome. Never silently inherit market prices, forecasts, sports checks or opportunity verification from a baseline.

## Sports and photographs

Keep Omonoia, Manchester United, Real Madrid and F1 with authentic local logos and dated direct headlines, rich available team/fixture/statistics cards, UEFA scores/fixtures/standings and F1 results/standings. Logo ownership/source/hash records are separate from photo licences. Preserve full Python data even when the model digest is compact. Up to three selected Sports articles may cover the favourites or other sports, inside the overall authored budget. Tactics, injuries and xG require article evidence; scores alone cannot support them. Temporary provider failures affect individual fields with original check times and explicit unavailable/cached status.

`real-photos-v1` requires a decoded, licensed, relevant real photograph on every article. This intentionally supersedes the old partial-policy missing-photo exception, not other partial-data behavior. Python uses the reviewed registry and exact SHA-256 bytes: subject photographs first, clearly labelled broad archive/context photographs only under the reviewed fallback policy. Never imply a context photo depicts the reported event. No generated illustration or AI image search. Invalid explicit selections fail instead of silently substituting another photo.

New uses reference the existing reviewed library asset URL, retaining per-article caption/alt/relevance review and immutable source/author/licence/retrieval metadata. Do not create another slug-specific binary for the same photograph. Preserve existing published image URLs and their exact bytes; no history rewrite to recover disk space. Full rights and captions live on the shared credits page, with concise archive/context labels where needed.

## Availability, reading and release

`partial-v1` keeps a useful edition during item-level market, sports, weather or evidence outages. Omit unsupported claims/articles; explain shortfalls honestly. Block structural/schema/identity/security/integrity failures, invalid mandatory photos, zero supported articles and actual preview/publication failures. Never weaken a gate to label failure as success.

Standard shows complete facts; Full opens useful analysis; Executive uses supplied synthesis and compact market data. Native disclosures, tabs and filters enhance an accessible no-JS/print report. Keep compact mobile edition navigation, photo-first mobile lead, one-row meaningful actions with 44px targets, themes, search, bookmarks and the 3/2/1 grid. No repeated reading-duration labels, dummy actions or since-last-visit tracking.

JSON remains canonical; Markdown is a versioned input adapter into the same compiler. No producer-written HTML/CSS. Preserve `reading_review.version=2`, `image_review.version=2`, fresh capability/schema contracts, unchanged historical snapshots, original source/quote times and evidence provenance. Three daily gates: content (validate/build once), preview (selected edition and cumulative day at 390px with JS and 1440px without JS), integrity (unchanged exact receipt). Maintenance adds units; full archive browser audits are explicit manual work. Verify exact source Pages before portal sync and exact portal bytes afterward; no fake live-verification bypass.
