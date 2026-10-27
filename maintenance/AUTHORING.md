# Manual authoring reference

Daily synthesis uses only the grammar printed in its digest and the [task contract](../CHATGPT_TASK_INSTRUCTIONS.md). This reference covers the optional standalone adapter, not a second production workflow. Current policy is [BRIEFING_SPEC.md](../BRIEFING_SPEC.md).

New compact directives: `@Coverage section=cyprus reason="Specific evidence limitation"` (or world) explains a desk below four stories. `@Omit id=story-id reason="No longer useful in this snapshot"` accounts for a baseline story without carrying stale copy. Same-day-only carries preserve exact records; omitted earlier stories remain in the cumulative day/archive. A sixth/seventh world story uses `@WorldException reason="Specific editorial reason"`.

# Oracle Markdown authoring v1

This optional prose authoring adapter feeds the existing compose/build/validation pipeline. JSON remains the public contract. Supply one .md to `python -X utf8 scripts/v2/compose.py --input work/briefing.md`. Do not commit private authoring files. Both formats remain supported while real usage is measured.

The following 15 lines are a grammar example, not researched news. Replace placeholders with genuine inputs; a baseline is `edition-id@edition-article-fingerprint` from the private context view, or `none`. Quoted attribute values use JSON string escaping; unique key=value fields and ` | ` separators are required.

```markdown
@Edition v=1 id=2026-10-23-midday published=<ISO> completed=<ISO> baseline=none
@Review version=2 completed=<ISO>
## world
### energy-corridor | story=energy-corridor | identity=energy-corridor-2026 | status=UPDATED | lead=true
@Headline Energy corridor: what changed
@Fact [s1] Verified development and factual delta.
@Mechanism [s1] Incentive and causal transmission.
@Effects [s1] Cost bearer and second-order consequence.
@Scenarios base="..." alternative="..." tail="..."
@Watch Specific date, indicator and threshold.
@Tags EastMed,Energy
@Data instrument=brent value=null status=unavailable quoted_at=null
@Source s1 | publisher="Name" | url=https://example.org/report | published=null | retrieved=<ISO> | group=primary-chain | kind=primary | access=read | claims=true
@AnalysisSources s1
@Image photo=<library-sha> reviewed=<ISO> relevance_checked=true caption="Archive context" alt="Relevant archive photograph"
```

Repeat ## world/cyprus/sports and ### article headers. Sports headers add interest=omonoia/manutd/realmadrid/formula1/other. One article may be lead=true. @Delta supplies a shorter change statement; if omitted for an explicit changed status, @Fact itself is the declared delta. @Fact maps to summary. Optional analysis directives require @AnalysisSources. The old unavailable-image directive is legacy-only; current real-photos-v1 compilation requires a real photograph. A reviewed image instead uses @Image photo=<library-sha> reviewed=<ISO> relevance_checked=true caption="..." alt="...". All source fields are explicit; inaccessible sources cannot support claims.

@Carry story-one,story-two selects exact unchanged baseline records. Do not write the same story again. Sources, article publication/update times, images and original image reviews are preserved; copied output receives its own edition reader URL and baseline origin. No quotes or weather are copied implicitly.

Optional existing typed contracts use @Block <name>, followed by a fenced json value. Names: executive_scan, daily, markets, market_summary, market_movers, market_next_event, market_core, market_notes, sports, panels, freshness, opportunities, fast_wire, selection_review. This preserves rich structured sports, weather, eligibility and evidence metadata instead of inventing a second schema. @Block article inside an article preserves optional paragraphs/sections/newspaper_analysis/reader_mode/reader_value/related_story_ids/daily/freshness/revision_note/published_at/updated_at/why_it_matters. Duplicate fields and undeclared private fields are rejected.

@Data supports maintained instrument IDs, value, status, quoted_at, optional change_pct and sources=s1,s2. Declare quote aliases before @Data. Local inventory supplies only static descriptions, never prices. @Scenarios supports base/alternative/tail/label; Watch is separate. No compulsory padding, numeric probabilities or invented source review.

Additional typed edition blocks preserve image_review, changes, delta_log and calculator. The article block also preserves evidence_note and list-valued mechanics_and_incentives/second_order_effects. Quoted attributes preserve JSON escapes and literal separators.

Unknown directives/versions, duplicate fields, raw HTML, unresolved aliases and unsafe/mismatched baselines fail with an input error. The adapter never renders arbitrary Markdown or executes expressions. Export/replay helpers do not establish fresh editorial review. Measure equivalent saved inputs with authoring_pilot.py; byte counts are not tokens or Pro quota. Live model usage requires a subsequent real production pilot.
