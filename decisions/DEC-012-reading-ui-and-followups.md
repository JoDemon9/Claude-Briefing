# DEC-012 — A compact mobile opening and clear later coverage

- User request: implement UI recommendations 1–3; remove the repeated reading labels entirely; leave since-last-visit tracking for later.
- Date: 15 October 2026, Asia/Nicosia.
- Status: implemented and locally validated on the existing review branch; main and Pages remain unchanged. Three internal briefing prompts were updated and read back exactly.
- Extends DEC-009 daily composition and DEC-004/005/006 reading/navigation. Supersedes the visible per-card duration labels; the internal concise-summary policy remains.

## Why and behavior

The repeated mobile introduction and full edition desk delayed the first headline. A compact date/update row and closed native edition dropdown retain all editions, missing-slot status, current edition, home/archive links and scheduled/publication distinctions. Desktop navigation is preserved. The measured mobile publication bar is 57px at 390px width before opening its dropdown.

The lead now orders headline, licensed photo, complete factual summary and existing actions on mobile. Remove “Η είδηση · 30 δευτερόλεπτα” entirely instead of moving it into an introductory explanation. Remove per-article duration estimates from buttons/readers as well. Keep the named cumulative overview, original times, full summaries, optional analyses, image research/credits and the one-row action layout.

The daily model stores explicit follow_ups declared by participating edition editors. Only genuine later published outcomes receive a link from an earlier card, which is marked as earlier coverage. Alias resolution and chronological checks prevent broken/draft/future/self/backwards links. No fuzzy title/entity matching merges unrelated stories. The earlier finding remains readable and archived; independent snapshots/readers remain faithful to their publication.

The seed connects the existing 15 October morning markets/TSMC preview to the midday results. No facts, source/quote times or publication identity were changed. Story IDs are preserved, including the results story's original stable ID ending in preview.

## Maintenance and verification

Affected: newspaper_ui.py, newspaper-ui.css, build.py, daily.py, edition/day schemas, one explicit cumulative relationship, unit/browser checks, maintained policy, generated public pages and portal snapshot. Future tasks should supply reviewed relationships when the fresh main schema supports them; otherwise record them privately without unsupported JSON. Schedules and unrelated task instructions remain unchanged. Since-last-visit tracking was not implemented.

See tests/test_follow_ups.py and the focused frontend browser checks for actual behavior, and RELEASE_NOTES_2026-10-15-CURATION.md for final validation and the separate PR/main/Pages/task state.

Local checks: 90 newspaper unit tests, 9 portal unit tests, 16 focused frontend scenarios, 14 editorial scenarios and 29 central refresh/browser cases pass. All 388 broad historical/browser checks also pass. All article JSON and original timestamps were compared with the preceding branch and preserved; only the explicit cumulative relationship was added to edition data.
