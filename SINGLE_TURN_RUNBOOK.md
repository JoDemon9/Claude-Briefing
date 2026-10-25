# Python pre-run → single analytical synthesis → existing publisher

This is DEC-025. Deployed and live-verified on 25 October 2026. Source PRs #33/#37, portal PR #21 and private PRs #10/#11/#12 are merged. Both PATs passed authenticated write checks; the portal push succeeded. The public publisher's run [40137964982, attempt 2](https://github.com/JoDemon9/Claude-Briefing/actions/runs/40137964982) verified 928 exact source files and 27 portal files. The separate served-release verification [40140163408](https://github.com/JoDemon9/Claude-Briefing/actions/runs/40140163408) also passed. All three live ChatGPT task prompts were subsequently saved and read-back verified through a full browser refresh on 25 October; the AI schedules and other settings were preserved.

The `.yml.example` files in `deployment/` are reference copies of the installed private workflows. Use maintained public main for Python execution. Preserve the three existing AI schedules and their settings.

## Cloud wiring

The live runner is ChatGPT cloud. Running `prepare_run.py` from an AI prompt would still start collection inside that run. The intended host is the existing **private** `JoDemon9/Claude-Briefing-Private` repository, with no Pages or public research artifacts.

The approved deployment installed `deployment/private-prepare-synthesis.yml.example` as private `.github/workflows/prepare-synthesis.yml`, `deployment/private-submit-synthesis.yml.example` as `.github/workflows/submit-synthesis.yml`, and `deployment/private-prefetch-window.py.example` as `.github/prefetch_window.py`. The clock is a private host helper; actual collection still uses maintained public `pre_run.py --slot`, never older copied private collectors. Before collection, the workflow tests PUBLIC_BRIEFING_TOKEN with an authenticated no-change push preflight. Missing/rejected credentials leave submission_ready=false.

The workflow provides four preparation attempts per edition in Europe/Athens: 06:22/06:37/06:52/07:07, 12:22/12:37/12:52/13:07 and 18:22/18:37/18:52/19:07. Its UTC cron covers both sides of DST. A cheap Python clock gate skips unused hours before heavy setup/provider calls, then rechecks after setup. Collection is allowed only 70 to more than 10 minutes before the AI task, preserving at least 20 minutes of the 90-minute pack life after the nominal start and leaving the eight-minute job timeout before synthesis. No automatic pack replacement during an AI run. GitHub cron can still be delayed or dropped; an absent/stale pack stops the AI briefly rather than triggering AI-side collection. Manual per-slot preparation remains available.

Prefetch uses only the private repository's GITHUB_TOKEN to save `research/runs/<edition>/research_pack.json` and `digest.md`. It checks out public source/portal repositories read-only, caches provider bodies privately and never invokes an AI/model API. Do not upload private caches as public artifacts. Refresh an expired pack with the manual workflow's slot input before retrying a task.

The configured **PUBLIC_BRIEFING_TOKEN** is stored under **Claude-Briefing-Private → Settings → Secrets and variables → Actions → Repository secrets**. Its fine-grained PAT owner is JoDemon9, selected repository **Claude-Briefing**, repository **Contents: Read and write**, Metadata read automatic. This is for the private submission workflow to write the composed public source candidate and trigger its existing CI. It needs no access to private research or the portal. Do not use the private repo's own GITHUB_TOKEN for a cross-repository push. Branch protection still applies; if it forbids direct publication, adapt the submission workflow to the established PR route before activation, without adding an AI polling loop.

Install the exact files `prompts/morning.md`, `prompts/midday.md`, `prompts/evening.md` into the three existing cloud tasks; keep titles/schedules/model/destination/enabled state and fourth task unchanged. They each fetch one digest, optionally fill tightly bounded evidence gaps and create one private `sources/synthesis/<edition>.md` file. That commit triggers the installed submit workflow. The task stops after submission. Existing public CI owns compilation validation/build/preview/integrity and publication. CI failure is maintenance, not another research run. Existing submissions are never silently overwritten.

## Local/manual host equivalent

```text
python scripts/v2/pre_run.py --root <public-checkout> --private-root <private-checkout> --wire-root <portal-checkout> --slot morning
python scripts/v2/compose.py --input <private-checkout>/sources/synthesis/<edition>.md --research-pack <private-checkout>/research/runs/<edition>/research_pack.json
```

The first command runs **before** the model is invoked. The second consumes its reviewed synthesis without network research. It produces canonical edition/articles for the existing publication route; it does not itself publish. Routine data must not be authored again. The digest contains the exact Markdown header/grammar, source aliases and baseline fingerprint. `auto` timestamps record compiler acceptance after the author's review; source, quote, fixture and original article timestamps are never synthesized from acceptance time.

## Limits and availability

| Edition | Searches | URL reads | All tool calls | Authored stories | Output reference tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| Morning | 5 | 2 | 10 | ≤6 | 6,500 |
| Midday | 3 | 1 | 7 | ≤4 deltas | 4,000 |
| Evening | 3 | 1 | 7 | ≤4 deltas | 4,000 |

The pack digest has a 48,000 UTF-8 byte ceiling; new excerpts are interleaved across desks and labelled. It is one read, not a paging loop. Model generation is one writing pass plus one review. The compiler actually enforces story counts, reference tokens, declared search/read budgets and exact carries. Prompt instructions govern live tool counts/turns; the cloud task interface here exposes no server-enforced tool/max-output parameter or run transcript. o200k_base is a reproducible reference tokenizer, not a claim about a chosen model's billable usage.

Every market identity is attempted, including ECB MLF. Yahoo prices are conservatively delayed; symbol/currency/time must match. ECB CSV observation dates and Euribor dates are kept; CSE uses a dated StockWatch fallback if the official page has no parseable observation. No quote is promoted to a cash close by inference. Weather uses Open-Meteo with a MET Norway fallback; failed TLS verification is never disabled. A forecast is not an official warning check. ESPN is an undocumented public endpoint and may change; jolpica is a community provider. Outages remain item-level unavailable states. Python never invents an alternative quote/result, and the AI never compensates with routine lookups.

## Portal HTTP 403

Update **PORTAL_DEPLOY_TOKEN** in **JoDemon9/Claude-Briefing → Settings → Secrets and variables → Actions → Repository secrets**. In GitHub **Settings → Developer settings → Personal access tokens → Fine-grained tokens**, create/regenerate the token with:

- Resource owner: **JoDemon9**.
- Repository access: **Only select repositories → oracle-briefing**.
- Repository permissions: **Contents → Read and write**. Metadata read is automatic.
- Valid expiration; any required owner/organization approval must be complete.

Replace the Actions secret's **value** with that token. The source repo's default GITHUB_TOKEN and workflow-level `contents: write` cannot grant access to another repository. Normal portal publishing does not edit workflow files, so it does not require Workflows permission. The updated token passed the role-specific write preflight and actual portal push on 25 October. Secret values were not displayed or changed by the verifier. The role-specific credential fix and dry-run preflights remain necessary. Both the portal push and exact live verification passed. Future token rotations should be verified through the same workflow.

Official settings: [fine-grained PATs](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens), [Actions secrets](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions).

## Audit and validation

`python scripts/v2/quota_audit.py` reconstructs saved full authoring payloads and counts reference tokens. It does not reconstruct actual searches/opens/retries/account quota. Legacy prompts had no finite ceiling. The old collector depended on previous Yahoo URLs, explicitly left manual quotes/weather and did not pull news article bodies. Sports.py rendered cards; sports_news.py collected headlines. Those were preparation aids, not a collection boundary before the AI. Run the new tests, maintenance build/browser/integrity gates and retain actual provider availability separately from successful parsing fixtures. A 90% reduction in collection work is the architecture target, not a measured reduction in the five-hour allowance.


## 25 October: Midday timer delivery failure and manual recovery

The four configured 12:22/12:37/12:52/13:07 Cyprus timer events produced no workflow runs. The workflow was active on default main; its latest scheduled run was 40179200485 at 11:05 local, before that window. No Python failure or rejected PAT was observed for Midday because Python never started. GitHub does not expose the internal reason for these absent events. Configured retry times and passing workflow CI are not proof of scheduled delivery.

Manual Python-only recovery [40190745480](https://github.com/JoDemon9/Claude-Briefing-Private/actions/runs/40190745480) passed credential preflight and saved both Midday files in commit 2ec4ff703be63af32c99f3c0ca427162ffb858cc. Prepared at 2026-10-25T11:53:48.429092Z (13:53:48 Cyprus), valid until 15:23:48 local: 38/38 market rows, 10 feeds, 13 article fetches, 90 HTTP requests, zero AI collection calls, submission_ready=true. The pack seal and matching digest header were independently verified. This recovered preparation, not an editorial submission or publication.

The user requires collection to stay fully in the cloud. An independent Cloudflare clock is prepared and locally tested (nine checks), but is NOT deployed: account setup/authorization and a dedicated private-repository Actions-write/Contents-read credential remain required. Existing GitHub retries and all three AI schedules/prompts remain unchanged. GitHub cron alone remains best-effort; do not report future delivery as fixed until actual scheduled events and fresh committed outputs are observed. Missing packs must still stop briefly without AI collection.


## Cloud-only timer backup (25 October)

The user created a Cloudflare account and approved restricted Wrangler authorization. The independent Worker and its regression tests are maintained in deployment/cloud-prefetch-watchdog/. Worker version 6aeca0c4-1d12-40df-863f-3227a9cc4dbd was uploaded at 12:18:25 UTC with no triggers or public routes. The dedicated encrypted GITHUB_PREFETCH_TOKEN, production cron activation and actual scheduled-output verification remain separate pending steps. Do not equate account login, uploaded code or declared secret names with a working schedule.

This is a host clock for the existing private Python workflow, with no AI task or PC dependency. The production manifest requires the secret; each due tick checks the real committed digest/files and its remaining lifetime, protects submitted packs, avoids recent duplicate collectors, and stops dispatch ten minutes before the unchanged 07:30/13:30/19:30 Cyprus tasks. An explicitly enabled deployment diagnostic performs two read-only GitHub checks outside those windows and must be removed after verification. Private source/pack bodies and token values are never logged. Eleven local tests passed; the provider accepted the 6.06 KiB upload with a 1 ms startup. This does not yet establish successful dispatch from a real scheduled event or a fresh resulting pack.
