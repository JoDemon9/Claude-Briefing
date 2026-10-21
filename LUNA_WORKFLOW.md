# Briefing with Luna

DEC-020 allows the user's selected ChatGPT model, including Luna. The producer uses ChatGPT tools and existing Python/GitHub helpers; it has no hardcoded LLM client, model ID or external AI bill. Five International/five Cyprus stories, actual source review, dated financial/weather/opportunity data, licensed photos, useful analysis and blocking release checks apply to every model.

## Six steps for every model

Follow the maintained task prompt: PREPARE, RESEARCH, WRITE, REVIEW ONCE, RUN ONE CHECK, PUBLISH AND FINISH. DEC-021 requires only content, preview and integrity for daily content. Maintenance adds unit checks; full archive browser audits are manual. Review the evidence and useful writing once, then consume the compact result and exact artifact. Do not add extra per-story essays/checklists or browser matrices.

## Preparation details

Read the applicable AGENTS files and fresh main capabilities once. Install requirements-v2.txt in the runtime. When main advertises `producer_handoff`, run:

```sh
python scripts/v2/prepare_run.py --date D --slot E --at ACTUAL_ISO_TIME --private-root ../Claude-Briefing-Private --wire-root ../oracle-briefing
```

Substitute the actual local date, morning/midday/evening slot and actual offset timestamp. This command composes research.py, collect.py and sports_news.py. It saves complete reports, capabilities, a handoff and every planning page under the private checkout. Each planning file is at most 12,000 UTF-8 bytes; continuation never silently drops a due or failed item. Read all returned pages. Full source passages and programme terms remain available at the linked private paths. Preparation does not approve evidence, quotes, images or publication.

Perform the broad independent news scan. For each new or changed material fact, keep a concise private note with its supporting passage/URL, source/event date and qualification. Write once from evidence. Add a supported comparison, mechanism or consequence where it improves understanding; keep a simple finding short when further analysis adds nothing. The single editorial pass checks factual support, numbers, chronology, source independence, omissions and clear Greek. No invented depth, mandatory opposing view or duplicated essay.

Scaffold a matching draft with research.py and copy stable structures mechanically. Apply the prepared sports report without fetching twice:

```sh
python scripts/v2/sports_news.py --apply-report PRIVATE_SPORTS_JSON --edition D-E
```

Review faithful Greek headlines; refresh sports checks if they exceed the 120-minute publication window. The four favourites show direct dated article links. Failures retain the original dated headlines with an explicit unavailable state. Up to two other-sports stories remain separate. Actual supporting reading is required for any substantive new sports claims.

Submit one source candidate to the existing GitHub Actions workflow. Consume its exact passing output and receipt. Verify source Pages before syncing/verifying the complete day in Oracle. Resume precise input corrections and preserve failed candidates and the last good release; preparation never bypasses a gate.

## Model selection and honest verification

Select Luna using the model control for the task/conversation where available. The exposed automation update API has no model field. These prompts cannot switch or attest to the actual runtime model. Preserve the three task titles/times/timezones/enabled states/destinations and the fourth historical task.

The regressions establish preparation, sports/UI and publication-contract behavior. They do not measure Luna's editorial quality or account quota. A genuine comparison requires completed Luna briefings assessed for coverage, factual support, meaningful depth, Greek clarity and exact served releases. Keep article targets, evidence standards and useful depth. The minimum three daily gates replace redundant automated suites, not editorial judgment.
