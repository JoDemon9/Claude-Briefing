# DEC-019 — Visible favourite news and bounded mechanical work

The user asks for larger quota savings with more restrictions and reports that news for their sports interests is missing. Earlier permission covered merging PR #17; this subsequent implementation is prepared separately for review. Quality and International/Cyprus targets remain required.

## Problem and intentional revision

DEC-008 intentionally replaced favourite updates with four generic latest-news links. The renderer ignored all existing coverage.updates, and DEC-014/018 prompts explicitly avoided further favourite reporting. That reduced effort but hid the news the user now requests. This instruction supersedes the links-only part of DEC-008 while preserving DEC-011's small authentic logos and two separate other-sports stories.

Each of Omonoia, Manchester United, Real Madrid football and F1 now gets up to two visible real article links with source headlines, publication date or explicit unknown, and source-check time. Optional faithful Greek headline_el retains original wording. Official all-news links remain. Old sourced updates are revealed with their original dates/archive labels; archived facts, source files, IDs and times are not rewritten. Headline links are attributed metadata, not new results/fixture reporting or independent verification. Any substantive new summary/result still needs actual supporting evidence. Favourites do not count towards the five International/five Cyprus targets or displace the separate other-sports selection.

## Enforceable resource limits

- sports_news.py uses four official providers, at most ten HTTP attempts, no automatic redirects/retries, 12-second per-request timeout, 2 MB maximum response, two items per interest and a 45-minute cache. Omonoia uses RSS, United its men's news listing, Madrid first-team metadata with canonical/article validation, and F1 its official listing/articles. Redirects/unsafe hosts and future metadata are rejected. There is no paid AI/API or new scheduler.
- Reused metadata keeps original check/retrieval dates. Failure preserves last successful items with their real dates and explicit unavailable status, or shows no available headline. It does not invent dates, results, eligibility or successful verification. Only a draft may receive metadata; unchanged URL/headline pairs retain reviewed translations. Current-contract publications from 19 October require all four source statuses checked within 120 minutes of completion. Previously accepted historical contracts remain accepted.
- context_view.py projects private planning metadata with a hard 12,000-byte UTF-8 page ceiling. Fingerprints, record indexes, paths, kind filters and next_page preserve all projected records. Oversized records fail explicitly; no hidden truncation. Full opportunities/quotes/evidence stay on disk and are copied mechanically. Evidence reading, broad discovery and editorial judgment remain mandatory.
- Preflight known infrastructure blockers before expensive research. Prepare/collect once, draft/review once, one external candidate and one precise input correction/recheck; further failures preserve the checkpoint for maintenance. No development/research regeneration loop, repeated passing suite, busy polling or duplicate journals.

These are enforceable tool/work limits, not a hard percentage limit on the ChatGPT account window. No such account control is available here. A synthetic saved-edition replay reduced a 44,283-byte packet to 15,155 bytes in 10,775/4,380-byte planning pages, retaining all 16 projected records; this is not measured quota saving or a fresh-reporting quality trial. Actual usage observations remain private.

## Verification and deployment status

Focused sports/context regressions cover request/response budgets, safe URLs/redirects, cache and failed-source dates, unknown/future metadata, required fresh source statuses, immutable published editions, visible escaped headlines and complete bounded pagination. Existing selection/source-only/structured-content gates remain intact. Source content files remain unchanged; generated layout/metadata changes require full CI.

The live official-source probe returned two headlines per interest. The first Omonoia attempt exposed leading whitespace before its XML declaration; normalising that whitespace repaired parsing. A subsequent pass used the cache for the other three sources and needed one Omonoia request. No probe data or private report is published.

Mobile/desktop checks with JavaScript enabled and disabled pass, including eight visible links, keyboard targets, no overflow, unknown dates and retained-source-failure states (24 frontend checks).

All three actual task prompts were updated and read back exactly: morning 5,416, midday 5,404 and evening 5,414 characters. Titles, schedules/timezones, enabled states, destinations and the entire fourth historical task are unchanged. The prompts explicitly use new helpers/fields only when actual main supports them; otherwise existing sourced update fields apply. Implementation, generated layout and new capabilities remain under review until separately merged/deployed. Final full CI, release/PR and deployment status are recorded in the review. This change does not publish an overdue briefing or claim quota savings.
