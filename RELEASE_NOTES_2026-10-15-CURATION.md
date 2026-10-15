# Sports, daily composition and morning balance — 15 October 2026

User request implemented as [DEC-008](decisions/DEC-008-compact-sports.md), [DEC-009](decisions/DEC-009-curated-daily-newspaper.md) [DEC-010](decisions/DEC-010-morning-news-balance.md) and [DEC-011](decisions/DEC-011-real-sports-logos.md).

- Four favourite sports display one small official latest-news link each; small authentic local club/F1 logo images replace the emojis; no per-interest paragraphs or disclosures.
- Separate sports selection excludes all four interests, including F1 management reports. Up to two other stories are selected; the current 15 October inventory has one eligible other story (Six Kings Slam), so an unsupported second story is not invented.
- The day has one lead, linked global/Cyprus highlights, unique global then Cyprus cards and a collapsed chronology below the news. Source provenance and every dated reader remain available. Older selections no longer carry the latest slot's new/updated badge.
- From 16 October, morning publication requires selection_review.version=1: at most five Cyprus stories, normally five globals, up to seven only with a specific reason. The lead counts in its actual section. Existing inventories are preserved; the cumulative day is not capped at one morning's count.

## Checks

82 newspaper unit tests and 9 central portal unit tests pass. Focused frontend checks pass in 16 scenarios, and editorial browser checks pass in 14 viewport/JavaScript scenarios across all 22 selected stories of the 14 October edition. Mobile/desktop screenshots were inspected. The four official news destinations returned HTTP 200. Every source article was compared with the prior main: only explicit sports_interest classification was added; all 112 findings, sources, image metadata and timestamps are unchanged. All edition inventories and market quotes remain unchanged. 388 general browser checks and 29 central snapshot browser checks passed before the logo follow-up. After the real-logo follow-up, all 82 newspaper unit tests, 9 portal unit tests and 16 focused frontend scenarios pass again, including local logo decoding at 320/375/390/1440px with JavaScript enabled/disabled. Logo screenshots were inspected in light/dark themes. Live publication is pending.

## Publication state

Validated local implementation. Automatic approval review rejected direct default-branch publication because the fixes did not include explicit publication approval. The changes are prepared on review branches instead. Both main merges, Pages publication and the three existing task prompt updates remain pending; task edits depend on the new schema/renderer reaching main. These states must be verified separately. Schedules, enabled states, the unrelated fourth historical task, Wire and private notes are outside this change.
