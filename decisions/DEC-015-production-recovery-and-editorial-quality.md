# DEC-015 — Recover production and improve news judgment

The user reported the 16 October evening failure (`Every article must have a photograph`) and poor morning/noon editions, then clarified that story selection and writing were the primary problems. Fix the failure, recover the preserved evening research and improve both the actual editions and future production. Extends DEC-004–014; quality gates, privacy and factual/source provenance remain mandatory.

## Findings and changes

The old sports renderer emitted the ordinary article card only when `newspaper_analysis` was nonempty. A correctly reviewed source-only sports article therefore lost its existing licensed photograph in the edition, although its asset and reader were sound. Keep optional analysis optional; always render an eligible other-sports article through the same photographed card. The approved compact sports renderer supplies that behavior. Add a regression for empty analysis and per-article browser assertions checking the exact image, without reducing photo coverage.

The approved source implementation had not reached main. Integrate it with the current morning/noon and the preserved PR #11 evening research; keep the original source/quote/previously published times and URLs. Add supported producer/identity/selection/weather metadata from existing dated evidence. Actual source retrievals, full opportunity terms and unavailable application endpoints are reviewed separately; no cache/hash or date rollover implies verification. The evening's failed proposed publication time is not a successful publication: use its actual repaired finalisation time, retaining the researched facts and evidence times.

Rewrite the 11 morning/noon cards in natural Greek around the event, its concrete consequence and the useful next step. Retain material uncertainty and attribution, reported details and genuine source limits; remove repeated process narration and generic caution. Preserve prior reporting in Git history and mark the actual copy-edit time. Prioritise the Oregon school attack as the noon lead; this is editorial ranking, not a new event time. Enrich the repaired evening with separately read AP and primary UN civilian-harm reporting on Ukraine, using a licensed archive image with explicit reuse review rather than presenting it as a current photograph.

Future tasks rank a bounded private shortlist from two independent broad world-news desks before deep research. Compare scale, human impact, urgency and changed facts; check for major omissions beyond tracked/market/Cyprus stories. Avoid quota padding, routine local announcements displacing major world news, forced Cyprus angles and analyses that add no knowledge. This improves selection while retaining the compact/reuse workflow.

All three recurring tasks had become paused after failures. A failed candidate blocks that release and preserves the previous good site; it does not authorise disabling future scheduled runs. Update the existing prompts and restore the same three schedules after the repaired implementation is verified. Keep the historical fourth task disabled. No catch-up automation, run-now, replacement generator or additional delivery is introduced.

The portal implementation was still on its review branch: SVG/JPG logo support, atomic receipt/retry handling, the shared Wire lock, compact instructions and corresponding assertions had not reached main. Integrate those reviewed files with all subsequent Wire updates, and sync the complete repaired day only after exact source Pages verification. A generation task must never export cached infrastructure/instructions onto a newer main.

## Verification and release state

See REPAIR_REPORT_2026-10-16.md for actual local/remote checks, publication identities and task readback. Record statuses separately; a prepared candidate, a push, green CI and exact live Pages verification are different evidence. Real account-usage savings remain unmeasured; no quota percentage is inferred from these repairs.
