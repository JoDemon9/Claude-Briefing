# DEC-003 — Markets should explain, not merely list prices

- Date: 2026-10-14
- Status: User-requested; implementation validated locally; publication pending.
- Request source: This conversation. The user said the market section “doesn’t give any intelligence back” and only gives numbers they can already see live on TradingView.
- Related decision: [DEC-002](DEC-002-compact-market-evidence.md).

## Reason and prepared change

A static newspaper is useful when it explains relevant changes and their implications. Another price list adds little value to a reader who already has a live charting service.

The prepared brief leads with the market picture, practical implications for Cyprus and next events. Expandable drivers distinguish sourced observations from editorial interpretation and describe evidence that would strengthen or weaken the interpretation. Prices become supporting data. The current evening brief synthesizes already stored public evidence; it does not claim new research or live prices.

## Preserve during future work

- Keep interpretation and useful next questions ahead of raw prices.
- Give mechanisms and implications, not just “asset X moved Y%.”
- Distinguish a source's explanation from editorial judgment and from demonstrated causation.
- Require readable supporting sources and honest uncertainty. Do not infer causes, confidence percentages, price targets or trading recommendations from a price move.
- Explain relevant Cyprus channels such as energy imports, EUR/USD, financing and contractual Euribor. Do not imply a US release automatically changes ECB policy or a loan payment.
- Give a real reference time and sourced next milestones; preserve original publication and quote/source times.
- Research a fresh brief for future editions. Historical editions without a brief retain their stored summaries rather than receiving invented retrospective interpretation.

## Implementation and verification

Prepared implementation: typed `edition.market_brief` in `templates/v2/content.schema.json`; shared rendering in `compact_markets.py`; source/time validation in `build.py`; current evening edition brief; production guidance in `OPERATIONS.md`, `BRIEFING_SPEC.md` and `CHATGPT_TASK_INSTRUCTIONS.md`. The daily newspaper uses the latest participating edition's market brief.

Checks cover missing/inaccessible evidence, future reference times, original data preservation, matching daily/independent output and access to the full notes. See DEC-002 for the completed test counts and release status.

## Tradeoff and publication state

Interpretation requires editorial research, not a deterministic calculation from market numbers. The prepared UI cannot guarantee future editorial quality. The renderer/schema support the format; the production task must supply researched content. The actual external ChatGPT tasks have not been modified. This implementation remains staged pending publication approval.
