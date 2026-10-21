# DEC-017 — Separate section coverage and the DEC-016 CI handoff

DEC-021 supersedes automatic full regression, repeated validation and broad current-reader browser matrices for routine completion. Daily content uses three gates; maintenance adds units; archive browser audits are explicit. Evidence, coverage and presentation requirements below remain. See [DEC-021](DEC-021-minimum-daily-checks.md).

- User request: read the briefing instructions and latest changes entry, apply the GitHub check handoff to the prompts and section creation, and fix International/Cyprus article shortages.
- Implements the existing [Oracle DEC-016 entry](https://github.com/JoDemon9/oracle-briefing/blob/main/DECISIONS.md), corroborated by Oracle AGENTS.md. The original decision ID is preserved; this coverage extension is DEC-017. Extends DEC-010/014/015/016.
- Status: PR #15 explicitly approved, merged and live verified on 18 October 2026. All three actual task prompts updated and independently read back.

## Reason and resulting behavior

18 October morning contains four International stories and one Cyprus story. The earlier gate enforced morning ceilings but accepted unexplained shortages; later prompts limited both sections together to five. Every slot now targets five distinct International and five Cyprus articles, counting the lead once in its actual geographic section. Five Cyprus/seven International remain ceilings, and six/seven International require a specific editorial reason. Duplicate story IDs cannot fill targets.

From 18 October evening, published slots require selection_review.version=2 with section_shortfalls normally empty. Broaden discovery before accepting a shortage. A genuine shortage needs a section-specific reason and actually checked independent HTTPS sources. Domain checks are a mechanical minimum, not proof of reading or independence. No padding, invented sources/photos, relabelling or false novelty. Completed snapshots retain their inventories and times.

Later editions add meaningful developments and missed major stories while retaining useful earlier coverage as dated context with stable identities and original article/source times. The cumulative day keeps one selected version per story; unchanged reporting is never called new.

## Original Antigravity handoff

ChatGPT selects/researches stories, reads supporting sources, verifies factual meaning and image relevance/rights, reviews the copy, and delivers structured edition/article JSON plus selected image metadata. GitHub Actions prepares/optimizes those images, validates the schema and source/reading/section/opportunity gates, builds the site, and runs the required browser checks. Private notes, packets, caches and usage metrics stay private.

The existing PR workflow returns briefing-built-candidate and briefing-candidate-checks, including exact checked/source commits, workflow run, release/profile and section counts. Main still requires the exact generated files committed. The publisher binds a genuine passing report to the complete current release manifest and required profile, then reuses the tested artifact without rebuilding. Changed bytes or insufficient proof block reuse. Detailed logs are inspected for failures. CI does not establish editorial truth or live publication.

Image preparation runs before validation. Editions without image_review retain legacy illustrations; ordinary validation still rejects new publications lacking required reviews. Prebuilt candidates only verify assets and cannot download or mutate them. The first amended CI attempt exposed the archived 12 October SVG; this compatibility fix and its regression preserve historical data without weakening gates.

## Final verification and publication

- Approved [PR #15](https://github.com/JoDemon9/Claude-Briefing/pull/15) merged into main at `f537f8dad3812d084f7af270d7600ba3aece57fa` from final implementation head `6b60bf73512395de28490d028ed3d213464e7178`. The earlier automatic approval rejection was resolved by explicit user approval of this exact PR.
- [Full candidate CI 39126194022](https://github.com/JoDemon9/Claude-Briefing/actions/runs/39126194022) passed all eleven stages: image preparation, section coverage, validation, build, release record/integrity, units, three browser suites and unchanged-candidate verification.
- Actual downloaded CI logs confirm 133 unit tests, 576 browser checks, 16 frontend checks and 14 editorial browser checks across 22 articles passed. Focused regressions cover shortages in every slot, lead/duplicate counting, evidence/stale exceptions, historical compatibility, missing-image preparation and prebuilt no-download behavior.
- Release ID: `1de88dec723be1cecf5bb10ebf6eeeecb4a1c614730ccdfeab47371896cf2aef`. Built artifact 12136152701 and check artifact 12135733969 belong to the exact final implementation head. The downloaded report was accepted by publish.accept_checks against matching local release inputs/output without rebuilding.
- [Pages deployment 39127092797](https://github.com/JoDemon9/Claude-Briefing/actions/runs/39127092797) passed. [Served-release verification 39127146619](https://github.com/JoDemon9/Claude-Briefing/actions/runs/39127146619) passed in full mode: 511 exact published files verified at 12:24:41 UTC on 18 October.
- Independent direct HTTPS checks also match served data/release.json and data/capabilities.json byte-for-byte to the tested candidate. Live capabilities expose world=5/cyprus=5, selection_review_version=2 and the 2026-10-18-evening cutoff. An earlier probe before deployment still saw the prior release; it was not counted as successful activation.
- All three actual prompts match their maintained templates exactly (morning 5,385; midday 5,484; evening 5,475 characters). Titles, schedules (07:30/13:30/19:30 Europe/Athens), timezones, enabled states and destinations are preserved. The disabled historical fourth task is unchanged; no run-now was invoked.
- All 174 historical content files remain byte-identical to the starting commit. Generated changes are capabilities/release metadata only; no historical news, article/source/quote time, UI, private data, Wire or central snapshot was rewritten. No new scheduler, model or paid API was introduced.
- Main CI may repeat the same source checks after merge; the candidate CI and completed live verification above are the evidence for this release. Decision-record-only follow-ups do not change release inputs or generated output.

The original DEC-016 entry reports approximately 50% token savings. No supporting account observation was available here, so that remains the original claim rather than a measured result of this work. Actual usage requires observation of scheduled editions.
