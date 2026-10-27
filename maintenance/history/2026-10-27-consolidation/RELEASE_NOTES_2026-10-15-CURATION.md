# Sports, daily composition and morning balance — 15 October 2026

User request implemented as [DEC-008](decisions/DEC-008-compact-sports.md), [DEC-009](decisions/DEC-009-curated-daily-newspaper.md), [DEC-010](decisions/DEC-010-morning-news-balance.md) and [DEC-011](decisions/DEC-011-real-sports-logos.md).

- Four favourite sports display one small official latest-news link each; small authentic local club/F1 logo images replace the emojis; no per-interest paragraphs or disclosures.
- Separate sports selection excludes all four interests, including F1 management reports. Up to two other stories are selected; the current 15 October inventory has one eligible other story (Six Kings Slam), so an unsupported second story is not invented.
- The day has one lead, linked global/Cyprus highlights, unique global then Cyprus cards and a collapsed chronology below the news. Source provenance and every dated reader remain available. Older selections no longer carry the latest slot's new/updated badge.
- From 16 October, morning publication requires selection_review.version=1: at most five Cyprus stories, normally five globals, up to seven only with a specific reason. The lead counts in its actual section. Existing inventories are preserved; the cumulative day is not capped at one morning's count.

## Checks

82 newspaper unit tests and 9 central portal unit tests pass. Focused frontend checks pass in 16 scenarios, and editorial browser checks pass in 14 viewport/JavaScript scenarios across all 22 selected stories of the 14 October edition. Mobile/desktop screenshots were inspected. The four official news destinations returned HTTP 200. Every source article was compared with the prior main: only explicit sports_interest classification was added; all 112 findings, sources, image metadata and timestamps are unchanged. All edition inventories and market quotes remain unchanged. 388 general browser checks and 29 central snapshot browser checks passed before the logo follow-up. After the real-logo follow-up, all 82 newspaper unit tests, 9 portal unit tests and 16 focused frontend scenarios pass again, including local logo decoding at 320/375/390/1440px with JavaScript enabled/disabled. Logo screenshots were inspected in light/dark themes. The final central refresh/browser run also passes all 29 cases after the SVG decoder fix. Live publication is pending.

## Publication state

Validated local implementation. Automatic approval review rejected direct default-branch publication because the fixes did not include explicit publication approval. The changes are prepared on review branches instead. Both main merges and Pages publication remain pending. The user separately authorized the three internal ChatGPT prompt edits; they were updated and read back exactly, with unchanged schedules/settings and a schema-compatibility guard until the reviewed website changes reach main. These states are verified separately. Schedules, enabled states, the unrelated fourth historical task, Wire and private notes are outside this change.

Reviewable results: [newspaper PR #7](https://github.com/JoDemon9/Claude-Briefing/pull/7) and [central portal PR #9](https://github.com/JoDemon9/oracle-briefing/pull/9). Local previews and prepared exact task-prompt changes remain in .work (not published). Main/Pages remain unchanged pending publication approval. The three internal prompts are updated; the unrelated historical task remains unchanged.

## Latest UI follow-up — DEC-012

The user approved recommendations 1–3, requested complete removal of the repeated reading labels, and deferred since-last-visit tracking. The existing PRs now include:

- A compact mobile date/update row and native edition dropdown, preserving edition identity, missing slots, home/archive links and distinct scheduled/publication times. The mobile publication bar measures 57px at 390px.
- An explicit reviewed link from the stored morning markets/TSMC preview to the selected midday results, with earlier coverage marked as background. The renderer supports valid participating follow_ups and rejects absent/draft/future/self references and conflicting targets; obsolete pointers never lead backwards in edition chronology. No fuzzy headline/entity matching is used.
- Mobile lead order: headline, licensed photograph, full factual summary, existing one-row actions.
- Removal of repeated 30-second labels and per-article duration estimates, with no once-per-page replacement. The named cumulative overview and internal concise-summary gates remain.

All 112 article source files are byte-for-byte unchanged from the preceding review branch. Edition data only gains the explicit cumulative relationship; all findings, publication/quote/source times, images, original article URLs and story IDs remain preserved. Since-last-visit tracking was not added.

The three internal ChatGPT prompts now also contain DEC-012, including explicit reviewed follow-ups and a guard against unsupported public fields before main is updated. Exact prompt read-back and preservation of titles, schedules, enabled states and timezone were verified; the fourth historical task is unchanged. Private local receipts remain in .work.

Validation: 90 newspaper unit tests, 9 portal unit tests, 16 focused frontend scenarios, 14 editorial browser scenarios and 29 central refresh/browser cases pass locally. All 388 broad historical/browser checks also pass. The focused checks cover 320/375/390/1440px, keyboard/no-JavaScript dropdowns, lead image order, action alignment, explicit later-coverage navigation, hidden labels, logo decoding and light/dark themes. Main merges, CI and live Pages publication remain separate pending states.

## DEC-013 backend follow-up

All six backend recommendations are implemented on these same review branches. See [backend operations](BACKEND_OPERATIONS.md) and [DEC-013](decisions/DEC-013-backend-publication-reliability.md). The coordinator prepares safely by default; actual two-site publication remains a separately verified operation on reviewed main. Prompt contract/recovery instructions are active in the same three internal tasks, read back exactly, with all schedules/settings and the historical fourth task preserved.

Local checks so far: the 104-test complete newspaper suite passed, the final 14-test backend suite passed after retry/Git changes, and an additional portal-promotion rollback case passed. All 11 portal tests and 29 central browser cases passed. All 112 article files and all five Wire/cache/health files are byte-identical to the preceding branch. The only edition-data additions are exact existing weather-validity metadata with next-slot editorial recheck deadlines.

Final backend regression: all 388 newspaper browser checks pass, as do the 29 central browser cases. A no-change incremental rebuild renders zero edition/readers and preserves the exact manifest. Source/central manifests match their files; current per-slot status truthfully remains prepared with both sites pending publication. These are local results; no new main push, CI completion or live Pages verification is claimed.

## DEC-014 approved efficiency implementation

The active instructions and three internal task prompts are consolidated. Prompt readback proves 79.1–79.3% fewer characters, with all settings and the historical fourth task unchanged. Private research/due-check/checkpoint/scaffold/collection/usage helpers, explicit licensed photo reuse and a blocking change-aware check stage are implemented on the review branch. Prior instructions are archived; the latest evening and Wire publication is integrated.

See EFFICIENCY_REPORT_2026-10-15.md for measured payload proxies, scope and actual checks. The full local candidate profile passed 123 source unit tests and all browser profiles; portal units/browser checks and a separate routine-content replay pass. Real scheduled usage savings remain unmeasured and the live pilot awaits main deployment. No new scheduler/model/paid API/private export or direct main publication is introduced.
