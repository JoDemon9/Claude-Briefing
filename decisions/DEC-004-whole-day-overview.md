# DEC-004 — The day overview must cover the selected whole day

- Date: 2026-10-15, Asia/Nicosia.
- Status: Implemented; publication and task-prompt verification recorded in the change's completion report.
- Request source: The user accepted recommendation 1 from NEWSPAPER_REVIEW.md and asked to implement it in GitHub and the existing ChatGPT scheduled prompts.
- Related: [DEC-001](DEC-001-decision-history.md), [DEC-005](DEC-005-reading-value.md).

## Reason

The previous daily renderer could label the latest edition's summary as “the day,” losing important earlier coverage even though those stories remained in the full newspaper. The user wants an intelligent short reading route through the findings, not a recap whose coverage depends only on the latest slot.

## Change and preservation requirements

The day model now stores a reviewed overview and supporting story IDs. The current morning, midday and evening edition data have distinct cumulative summaries covering their actually available selected stories. Points link to the correct cards. An explicit legacy fallback selects factual summaries across the day and labels them as selected stories, rather than pretending the latest slot's summary is cumulative.

Preserve separate independent summaries, stable story IDs, correct selected versions, original publication times and genuine missing slots. Future additions must not silently restore `latest.summary_60s` as the day's editorial overview. New v2 editions require reviewed cumulative points and matching published story references.

## Implementation and verification

See `scripts/v2/editorial.py`, `daily.py`, `newspaper_ui.py`, the content/day schemas, the 14 October edition data and `tests/test_editorial_value.py`. Tests cover important morning stories surviving into the evening overview, working card links, honest legacy fallback and rejected unknown/missing/mismatched references. The three existing task prompts are changed only in the relevant cumulative-overview instruction plus DEC-005's reading/review rules; schedules and unrelated instructions are preserved.

The renderer does not generate new analytical prose. The production task must review the day's evidence and supply the overview.

## Completed local checks

71 newspaper unit tests, 300 general browser checks, 16 frontend browser checks, 8 focused editorial cases covering all 22 selected day stories with and without JavaScript, and 9 portal unit tests passed. Source/quote/image data, stable identities and original publication times were compared with main and preserved. Git diff whitespace and changed Markdown links were checked. Served release and actual task-prompt verification are recorded after publication.
