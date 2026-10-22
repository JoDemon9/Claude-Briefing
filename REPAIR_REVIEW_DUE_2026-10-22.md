# Opportunity contract repair — 22 October 2026

The user requested a permanent correction of the `review_due` publication failure and continuation of the saved morning edition (PR #26).

## Cause and correction

DEC-023 made due opportunities archival through an optional boolean `review_due`. The content schema accepted it, but the duplicated opportunity definition in `day.schema.json` omitted it. The compiler therefore validated the independent edition and failed when the full daily newspaper was composed.

The day schema now accepts the same boolean. No gate is disabled and no verification time is renewed. Unknown properties and non-boolean values remain rejected. Historical content is unchanged.

## Regression

The compiler regression now composes and validates the complete daily model with an actually due fixture, checks preservation of `verified_at`, and verifies the archival label and absence of the application link. It also rejects a string-valued flag. A second regression requires equality of the entire opportunity definitions so future field drift fails maintenance CI.

Local verification: `python -m unittest discover -s tests -p test_compose.py -q` — 24 tests passed. GitHub maintenance checks and Pages publication are recorded separately in the PR/run; this file does not claim them complete.

Scope: DEC-023 compatibility repair, preserving DEC-007 eligibility/provenance, the current daily content gates, archived routes/times, private boundaries, Wire and all task settings.
