# Python pre-run → single analytical synthesis → existing publisher

This is DEC-025. Merge the source implementation and portal compatibility changes before installing its prompts. The source PR incorporates DEC-024; do not run the new syntax against older main. The files in `deployment/` are inactive review templates. No live task or schedule has been changed.

## Cloud wiring

The live runner is ChatGPT cloud. Running `prepare_run.py` from an AI prompt would still start collection inside that run. The intended host is the existing **private** `JoDemon9/Claude-Briefing-Private` repository, with no Pages or public research artifacts.

After approval, install `deployment/private-prepare-synthesis.yml.example` as `.github/workflows/prepare-synthesis.yml` there, and `deployment/private-submit-synthesis.yml.example` as `.github/workflows/submit-synthesis.yml`. Use the public source code on maintained main, not the private repository's older copied scripts. The pre-run cron covers Athens summer/winter UTC offsets, with a Python local-time guard: 07:10/13:10/19:10. Delayed runs after :30 skip; Actions cron is not a guaranteed delivery SLA. An absent or stale pack stops the AI run with a short status; it never triggers AI collection.

Prefetch uses only the private repository's GITHUB_TOKEN to save `research/runs/<edition>/research_pack.json` and `digest.md`. It checks out public source/portal repositories read-only, caches provider bodies privately and never invokes an AI/model API. Do not upload private caches as public artifacts. Refresh an expired pack with the manual workflow's slot input before retrying a task.

Set **PUBLIC_BRIEFING_TOKEN** under **Claude-Briefing-Private → Settings → Secrets and variables → Actions → Repository secrets**. Its fine-grained PAT owner is JoDemon9, selected repository **Claude-Briefing**, repository **Contents: Read and write**, Metadata read automatic. This is for the private submission workflow to write the composed public source candidate and trigger its existing CI. It needs no access to private research or the portal. Do not use the private repo's own GITHUB_TOKEN for a cross-repository push. Branch protection still applies; if it forbids direct publication, adapt the submission workflow to the established PR route before activation, without adding an AI polling loop.

Install the exact files `prompts/morning.md`, `prompts/midday.md`, `prompts/evening.md` into the three existing cloud tasks; keep titles/schedules/model/destination/enabled state and fourth task unchanged. They each fetch one digest, optionally fill tightly bounded evidence gaps and create one private `sources/synthesis/<edition>.md` file. That commit triggers the proposed submit workflow. The task stops after submission. Existing public CI owns compilation validation/build/preview/integrity and publication. CI failure is maintenance, not another research run. Existing submissions are never silently overwritten.

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

Replace the Actions secret's **value** with that token. The source repo's default GITHUB_TOKEN and workflow-level `contents: write` cannot grant access to another repository. Normal portal publishing does not edit workflow files, so it does not require Workflows permission. The historical 403 establishes a rejected push, not which secret value/scope was used; this session cannot inspect or repair the secret. The role-specific credential fix and dry-run preflights remain necessary. Confirm repair only with a successful portal push and exact live verification.

Official settings: [fine-grained PATs](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens), [Actions secrets](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions).

## Audit and validation

`python scripts/v2/quota_audit.py` reconstructs saved full authoring payloads and counts reference tokens. It does not reconstruct actual searches/opens/retries/account quota. Legacy prompts had no finite ceiling. The old collector depended on previous Yahoo URLs, explicitly left manual quotes/weather and did not pull news article bodies. Sports.py rendered cards; sports_news.py collected headlines. Those were preparation aids, not a collection boundary before the AI. Run the new tests, maintenance build/browser/integrity gates and retain actual provider availability separately from successful parsing fixtures. A 90% reduction in collection work is the architecture target, not a measured reduction in the five-hour allowance.
