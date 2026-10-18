# DEC-016 — Separate section coverage and GitHub candidate checks

- User request (18 October 2026): review the briefing Markdown and changes intended to move checks to GitHub, apply them to the prompts and section creation, and fix International/Cyprus article shortages.
- Extends DEC-010/014/015. The working target is five International and five Cyprus articles in each edition, counting the lead once in its actual section. This replaces the later-slot instruction limiting both sections together to five. The user was offered the alternative of morning-only five/five while implementation continued; no answer was available when this record was prepared.
- Status: implementation on review branch. Main deployment, GitHub check outcome and actual task updates are distinct; final evidence is recorded below.

## Findings and changes

18 October morning has four International articles and one Cyprus article in its source inventory. The existing selection gate enforced only morning ceilings and allowed unexplained shortages. Later prompts requested up to five articles across both sections combined. Existing Structured briefing checks already performed deterministic validation/build/browser work, but its PR job required generated docs to be committed and returned only logs/report, leaving candidate assembly/build work with the producer. No separate Antigravity branch or identifiable new check implementation was found in accessible main/branches; the user was asked for its exact link. This implementation builds on the existing maintained workflow and does not claim to have inspected an unidentified change.

Selection/research packets/capabilities/prompts now carry separate world=5/cyprus=5 targets. From 18 October evening, all published slots require selection_review.version=2 with section_shortfalls normally empty. A real shortage requires a section-specific explanation and actually checked independent HTTPS sources after broader discovery. Domain checks are a mechanical minimum, not proof that sources were read or independent. Five Cyprus/seven International remain ceilings; six/seven International need a specific reason. Duplicate story IDs cannot fill targets. Earlier published snapshots retain inventory/contracts/times.

Later editions may retain useful earlier reporting as clearly dated context with original article/source times and stable identity, adding meaningful developments and missed major stories. This does not create new reporting or justify re-dating unchanged content. No filler, forced research of every tracked item, invented sources/photos or inferred outcomes is permitted.

The existing GitHub PR workflow now builds/tests source candidates and returns the exact public docs artifact plus a compact report with checked/source commit, workflow run, release/profile and section counts. Main still requires generated files committed. Publisher receipt consumption verifies the complete release manifest and required profile and skips a redundant build for an identical tested artifact. Changed files or insufficient proof block reuse. Detailed logs are read only for failures. CI does not perform editorial judgement or prove claims.

## Preservation and verification

No new scheduler, model/API, Telegram/email, private Pages, private artifact export, UI redesign, historical rewrite or Wire change. Three recurring task titles/schedules/timezones/enabled states/destinations and the historical fourth task are preserved. Code review/deployment remains separate from actual task edits; a pending PR does not grant supported capabilities to producers.

Focused checks cover separate section shortages in every slot, lead/duplicate counting, evidence requirements, stale exceptions, historical cutoff, packet targets and exact CI artifact reuse/rejection without rebuilding. Full unit and browser regression, deterministic build/release integrity and GitHub results are recorded after execution. Real ChatGPT quota savings are not measured or promised.

## Actual status

- Local implementation and focused section/efficiency/receipt tests: passed.
- Full regression/build/release and GitHub candidate checks: pending at record creation.
- Main/Pages: not deployed at record creation.
- Actual three task prompt updates/read-back: pending at record creation; schedules and historical task must remain unchanged.
