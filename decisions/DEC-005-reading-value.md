# DEC-005 — Each reading level must add useful knowledge

- Date: 2026-10-15, Asia/Nicosia.
- Status: Implemented; publication and task-prompt verification recorded in the change's completion report.
- Request source: The user accepted recommendation 2, said articles currently “add words but not intelligence,” objected to an opposing view attached to every article, and requested a 30-second findings summary, useful expansion and full reading where needed.
- Supersedes: The 13/14 October mandatory 110–220-word preview, 450-word reader floor, universal counterargument checklist and always-visible lead analysis, as documented in AGENTS.md and the former specification. These were existing repository rules, not a reconstructed claim about an unseen chat.

## Reason

Mandatory length and a uniform argument/counterargument structure encouraged generic prose even for announcements with little disputed substance. The user's current instruction explicitly favors useful evidence and appropriate depth over filling every section.

## Change

[EDITORIAL_POLICY.md](../EDITORIAL_POLICY.md) defines reading review v2: a factual summary of about 30 seconds, optional sourced expansion and a separate full reader only when it adds specific material. Short items may link directly to their original readable source. Both lead and secondary analysis open on demand. Actual denials, disputes and material uncertainty remain; hypothetical opposing views are not compulsory.

The current 14 October newspaper's 24 underlying articles are revised from stored evidence. Examples of added intelligence include the reversal in direction of the IMF/ministry forecast gaps, slower inflation versus falling prices, and CPI component weighting versus headline growth. Five separate full readers retain distinct additional analysis. Original story IDs, images, source/quote data, published_at/updated_at and historical reader URLs remain intact; editorial revision time is separately visible.

## Preserve during unrelated work

- Never restore minimum article length or mandatory “opposite view” boilerplate merely to make a validator pass.
- Keep all factual summary text visible. Keep expanded analysis concise and optional, including on the lead.
- Require actual reviewed evidence; do not mistake a populated metadata field for proof of intelligence.
- A full reader must add beyond the summary/expansion. Otherwise link to the original source, while retaining dated archival routes.
- Prioritize primary findings, meaningful comparisons and mechanisms. Do not invent a number, cause, counterargument or source to create depth.
- The earlier market DEC-002/003 changes remain separately staged; this request does not silently incorporate that pending release.

## Verification and prompt scope

Relevant checks are in `tests/test_editorial_value.py`, updated UI tests and the mobile/no-JavaScript browser checks. Existing image/license, archive, source-chain and publication integrity gates remain. The current newspaper revision does not claim fresh reporting or additional independently retrieved sources.

For the initial reading request, three passages of each active daily task prompt are replaced: the cumulative-day overview instruction, the reading-depth instruction and the reading-review version. Task titles, enabled state, timing/timezone and all other prompt text are retained. The completed one-off task is untouched. Verification checks those unchanged fields and exact prompt text after updating.

## Completed local checks

71 newspaper unit tests, 300 general browser checks, 16 frontend browser checks, 8 focused editorial cases covering all 22 selected day stories with and without JavaScript, and 9 portal unit tests passed. Source/quote/image data, stable identities and original publication times were compared with main and preserved. Git diff whitespace and changed Markdown links were checked. Served release and actual task-prompt verification are recorded after publication.

The subsequent user request adds only the DEC-006 photo/action presentation instructions and the DEC-007 opportunity-tracking block. The three actual task prompts were updated and read back exactly; their title, schedule, timezone and enabled state were preserved. See [the final verification record](../RELEASE_NOTES_2026-10-15.md).

Code is on main, both Pages releases passed live verification, and the three task prompts were updated/read back exactly. Evidence is maintained in [RELEASE_NOTES_2026-10-15.md](../RELEASE_NOTES_2026-10-15.md).
