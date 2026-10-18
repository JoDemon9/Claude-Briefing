# DEC-016 — Separate section coverage and GitHub candidate checks

- User request (18 October 2026): review the briefing Markdown and changes intended to move checks to GitHub, apply them to the prompts and section creation, and fix International/Cyprus article shortages.
- Extends DEC-010/014/015. The working target is five International and five Cyprus articles in each edition, counting the lead once in its actual section. This replaces the later-slot instruction limiting both sections together to five. The user was offered the alternative of morning-only five/five while implementation continued; no answer was available when this record was prepared.
- Status: implementation checked on PR #15; all three actual prompts updated and read-back verified. Main/Pages deployment is pending explicit merge approval after automatic approval review rejected the merge.

## Findings and changes

18 October morning has four International articles and one Cyprus article in its source inventory. The existing selection gate enforced only morning ceilings and allowed unexplained shortages. Later prompts requested up to five articles across both sections combined. Existing Structured briefing checks already performed deterministic validation/build/browser work, but its PR job required generated docs to be committed and returned only logs/report, leaving candidate assembly/build work with the producer. No separate Antigravity branch or identifiable new check implementation was found in accessible main/branches; the user was asked for its exact link. This implementation builds on the existing maintained workflow and does not claim to have inspected an unidentified change.

Selection/research packets/capabilities/prompts now carry separate world=5/cyprus=5 targets. From 18 October evening, all published slots require selection_review.version=2 with section_shortfalls normally empty. A real shortage requires a section-specific explanation and actually checked independent HTTPS sources after broader discovery. Domain checks are a mechanical minimum, not proof that sources were read or independent. Five Cyprus/seven International remain ceilings; six/seven International need a specific reason. Duplicate story IDs cannot fill targets. Earlier published snapshots retain inventory/contracts/times.

Later editions may retain useful earlier reporting as clearly dated context with original article/source times and stable identity, adding meaningful developments and missed major stories. This does not create new reporting or justify re-dating unchanged content. No filler, forced research of every tracked item, invented sources/photos or inferred outcomes is permitted.

The existing GitHub PR workflow now builds/tests source candidates and returns the exact public docs artifact plus a compact report with checked/source commit, workflow run, release/profile and section counts. Main still requires generated files committed. Publisher receipt consumption verifies the complete release manifest and required profile and skips a redundant build for an identical tested artifact. Changed files or insufficient proof block reuse. Detailed logs are read only for failures. CI does not perform editorial judgement or prove claims.

## Preservation and verification

No new scheduler, model/API, Telegram/email, private Pages, private artifact export, UI redesign, historical rewrite or Wire change. Three recurring task titles/schedules/timezones/enabled states/destinations and the historical fourth task are preserved. Code review/deployment remains separate from actual task edits; a pending PR does not grant supported capabilities to producers.

Focused checks cover separate section shortages in every slot, lead/duplicate counting, evidence requirements, stale exceptions, historical cutoff, packet targets and exact CI artifact reuse/rejection without rebuilding. Full unit and browser regression, deterministic build/release integrity and GitHub results are recorded after execution. Real ChatGPT quota savings are not measured or promised.

## Actual status — 18 October 2026

- Implementation: [PR #15](https://github.com/JoDemon9/Claude-Briefing/pull/15), checked code commit `1da61caf4c6405b85705880354b22a3d18c321ec`. Subsequent decision-record edits do not change release inputs or generated output.
- GitHub: [full-profile run 39124298421](https://github.com/JoDemon9/Claude-Briefing/actions/runs/39124298421) passed all ten stages. Its release ID is `a4c45f505b8581daf6083eb694921ed97164d30d0191db6bbbf2a822fd300ebf`, matching the local candidate exactly. Both `briefing-built-candidate` (artifact 12135294502) and `briefing-candidate-checks` (12136041202) were produced for that exact implementation head.
- Local: 132 unit tests passed; 576 browser checks, 16 frontend checks and 14 editorial browser checks across 22 articles passed. Build/release integrity passed for 19 editions and 152 articles. All 174 historical content files are byte-identical to the starting commit.
- Earlier verification attempts: one full run was invalidated by concurrent implementation edits and restarted against fixed inputs. A local browser attempt hit the sandbox socket restriction; the complete browser suites passed after granting preview-server network permission. No test/gate was weakened.
- Actual task prompts: morning/midday/evening updated and independently read back exactly at 5,398 / 5,497 / 5,488 characters. Titles, schedules (07:30 / 13:30 / 19:30 Europe/Athens), timezones, enabled states and destinations are preserved; the disabled historical fourth task is unchanged. No run-now was invoked. New fields/artifacts are conditional on actual main capabilities until deployment.
- Main/Pages: implementation is not merged or deployed. Automatic approval review rejected the exact merge of PR #15 into main because the user's implementation/review request did not explicitly authorize that protected-branch merge. No indirect main update or workaround was attempted. The concrete checked PR is ready for explicit user approval.
- Real quota savings and the exact unidentified Antigravity change: not measured/verified; no unsupported claim is made.
