# Current editorial policy — DEC-004 / DEC-005

Effective from the user's request on 15 October 2026 (Asia/Nicosia). This policy supersedes the earlier mandatory 110–220-word preview, 450-word reader floor, counterargument checklist and always-expanded lead for reading review v2. Licensed images, honest sources, privacy, historical URLs and original publication/quote/source times remain required.

## Whole-day overview

Review all selected stories from the published participating editions before writing `edition.daily.summary_60s`. Write up to six points, at most 220 words in total, reflecting editorial importance across the day. Do not copy the latest slot's summary and call it the day. Supply parallel `edition.daily.summary_story_ids` arrays with the stable IDs supporting each point. Use the selected version of an evolving story and never refer to a draft or absent slot. The renderer stores the points/references in the day model and links to their cards.

`edition.summary_60s` remains the independent edition's own summary. Legacy data without reviewed cumulative points falls back to factual summaries of selected stories across the day, labeled “Επιλεγμένες ειδήσεις της ημέρας”; it is not presented as a reviewed 60-second synthesis. Reading review v2 requires the reviewed cumulative overview.

## Three reading levels

1. **The finding, about 30 seconds.** `article.summary` reports the original finding: who/what/when, material numbers and the qualification needed to understand them. Aim for 60–90 Greek words, at most 110. A genuinely simple item may be shorter. State allegations as allegations and forecasts as forecasts. Keep the entire summary visible, including on the lead.
2. **Useful expansion.** `article.newspaper_analysis` adds a specific comparison, context, mechanism, practical consequence or material evidence limit. Normally 80–140 words, at most 180; there is no minimum. Give `analysis_sources` containing URLs already recorded as readable and used for claims in `article.sources`. Omit the expansion (`[]`) when no supported added interpretation is useful. Lead and secondary analyses use the same optional native disclosure.
3. **Further reading when justified.** Set `reader_mode="full"` only when the dated reader adds further specific material beyond the first two levels. Record what it adds in `reader_value`; support it with reviewed sources. There is no minimum reader length. Otherwise use `reader_mode="source"`: retain a concise dated archival record for existing URLs/bookmarks/search and link from the card to a readable original source. Do not manufacture a long essay from a routine announcement.

## Intelligence, not padding

- The central question is “what will the reader understand here that the preceding level did not already explain?” If there is no answer, shorten or omit the extra level.
- For the most consequential or disputed stories, seek the primary document/data and an independent account where it would affect the interpretation. Syndicated copies count as one chain; an authoritative primary release does not need a second link merely to meet a quota.
- Prefer specific, sourced comparisons and correct arithmetic. Distinguish percentage points from percentage change, forecasts from measured outcomes, nominal values from quantities and an announcement from implementation.
- Explain the mechanism connecting facts to consequences. Mark editorial interpretation as such and identify the evidence supporting it. Do not invent causes, historical baselines, consensus forecasts, motives or confidence scores.
- Include a competing account only when there is a real, documented and relevant dispute or alternative explanation. Do not attach “the counterargument is…” or a generic hypothetical downside to every article. Legitimate denials, uncertainties and limits that change the finding's meaning remain.
- Do not expand by rephrasing the summary, repeating warnings or listing generic “what to watch” points. Further evidence should answer a concrete question raised by the facts.

## Review and compatibility

Set `edition.reading_review.version=2` and `completed_at` only after checking evidence and added value. New publications from 15 October require v2. Keep `image_review.version=2`; image/license/decode checks are unchanged.

The structural gates enforce concise summaries/expansions, readable supporting sources, explicit reader choice, non-duplicated material and valid daily references. They do not prove semantic quality; editorial review must inspect the actual substance. Earlier v1 editions remain valid under their original policy.

The 14 October newspaper was revised using only its stored public findings. Its 24 source articles were edited, genuine stakeholder disputes retained and formulaic opposing-view passages removed. The five retained separate full readers add distinct analysis; other cards lead to the original source. No new reporting, publication time, quote value or source retrieval time is implied by the editorial revision.

The existing three scheduled tasks receive only the corresponding cumulative-overview, reading-depth and review-version edits. Keep their schedules, titles, enabled state, destinations, sports/finance/weather rules and publication workflow unchanged.
