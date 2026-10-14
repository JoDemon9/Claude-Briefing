# DEC-002 — Compact market evidence on mobile

- Date: 2026-10-14
- Status: User-requested; implementation validated locally; publication pending.
- Request source: This conversation and the supplied mobile screenshot. The user said the section where “τεκμηριωση happens with the links takes too much space,” making scrolling harder.
- Related decision: [DEC-003](DEC-003-market-interpretation.md).

## Reason and prepared change

Every company explanation had its own large documentation row. Repeated evidence controls consumed vertical space even when closed. The fix groups note evidence into one native “Πηγές και χρόνοι” disclosure, with numbered references. Full quotes and the original summaries/company notes remain available on demand.

## Preserve during future work

- Keep one shared market-note evidence panel. Do not reintroduce a tall documentation row under every mover as an incidental styling or data fix.
- Preserve every underlying source, reporting chain, source time, quote value, status and quote time.
- Keep keyboard operation and a usable no-JavaScript path. With JavaScript, a reference opens the panel; without it, the link leads to its visible heading.
- Use the shared renderer for daily and independent editions. Preserve historical pages, search, images and reading controls.
- Keep the initial mobile reading flow compact. Extra raw data belongs in the full-data disclosure.

## Implementation and evidence

Prepared files: `scripts/v2/compact_markets.py`, `templates/v2/newspaper-ui.css`, `docs/assets/reading.js`, rebuilt public pages and portal snapshots. Focused checks: `tests/test_market_brief.py`, `tests/market_browser_checks.py`, and `tests/fixtures/market-baseline.json`.

Before/after measurements for the complete market redesign, including DEC-003: at 375px width, 2,729px to 1,243px (54.4% less initial height); at 390px, 2,640px to 1,194px (54.8%). These measure the collapsed section, not the height after opening all evidence/data. The source baseline was Claude-Briefing commit `86ee50695a886803b2c9ce3caaff163dc619577c`, daily page 2026-10-14, Chromium, 950px viewport height.

Prepared release verification: 68 newspaper unit tests, 300 general browser checks, 16 frontend browser checks, 10 focused market cases and 9 portal tests passed. The existing edition JSON is unchanged except for the added `market_brief`; original quotes, sources and publication times were compared with the published source.

## Publication state and tradeoff

The earlier GitHub commit attempt was rejected by automatic approval review because explicit approval of the publication destination/payload was required. The prepared market changes remain local; this record does not describe them as live. Full raw data now takes an extra expansion, in exchange for substantially easier initial scrolling.
