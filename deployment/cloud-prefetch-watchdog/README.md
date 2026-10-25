# Independent cloud prefetch backup — Worker uploaded, activation pending

25 October 2026. The GitHub timer created no collector runs in today's 12:22–13:07 Cyprus window. Its workflow is active on main and its actor is active. The exact reason GitHub omitted those events is not exposed. The Python-only manual recovery [40190745480](https://github.com/JoDemon9/Claude-Briefing-Private/actions/runs/40190745480) passed and saved a ready Midday pack at 13:53:48 Cyprus time, valid until 15:23:48.

This optional Cloudflare Worker supplies an independent clock. It does not create an AI automation, change the three ChatGPT schedules, or gather briefing data. It checks the private committed digest/files and dispatches the existing private Python workflow only when needed. Existing GitHub cron remains a first path. GitHub runner/API availability is still required; no provider is an absolute delivery guarantee.

The user created a Cloudflare account and approved restricted Wrangler authorization on 25 October. Worker version 6aeca0c4-1d12-40df-863f-3227a9cc4dbd was uploaded at 12:18:25 UTC with no cron triggers or public route. Eleven control/timing tests passed; the provider accepted the 6.06 KiB bundle with a 1 ms startup. The dedicated GitHub secret, activation and actual scheduled validation are still pending. No credentials are included here or copied from the user's existing Git/Actions tokens.

## Behavior

- The UTC cron covers Cyprus summer/winter offsets. The Worker uses the real Asia/Nicosia clock and skips unused hours without GitHub requests.
- Check every five minutes from 70 to more than 10 minutes before 07:30, 13:30 and 19:30. Require enough pack life to last until at least 20 minutes after the AI starts. At 10 and 5 minutes before start, verify only and fail visibly in Worker logs if the pack is absent/stale; do not collect then.
- Do not replace a pack after a synthesis submission exists. Avoid another dispatch while a recent collector is queued/running. The existing private workflow serializes collectors.
- Both digest.md and research_pack.json must exist. The digest must have the correct protocol, edition, SHA header, prepared time and ready flags. The Python compiler still performs authoritative sealed-pack integrity/baseline checks; the Worker does not label a header check as cryptographic verification.
- One dispatch is only `dispatch_accepted`, never `ready`. The following timer checks the actual committed files. No AI, polling loop, outbound person-directed messages, public briefing data or public mutation endpoint.
- Errors contain HTTP status, not token values or source bodies. HTTP requests to the Worker return 404. Its runtime secret is server-side only.
- An explicit temporary VERIFY_GITHUB_ACCESS=true deployment diagnostic makes two read-only private GitHub requests outside the preparation windows. It cannot dispatch a collector. Remove this flag after verification; production outside-window ticks make no GitHub requests.
- The production manifest declares GITHUB_PREFETCH_TOKEN as required, so Wrangler rejects activation if the secret has not been installed. Secret presence alone is not proof of valid permissions.

## Dedicated credential

Create a separate fine-grained GitHub PAT with resource owner **JoDemon9**, selected repository **Claude-Briefing-Private**, **Contents: Read-only**, **Actions: Read and write**, Metadata automatic. Do not broaden or replace PORTAL_DEPLOY_TOKEN or PUBLIC_BRIEFING_TOKEN. Store the new token only as the Cloudflare Worker encrypted secret **GITHUB_PREFETCH_TOKEN**; never paste it into chat or commit it. The Worker uses Contents to inspect readiness and Actions to call workflow_dispatch.

## Deployment after account authorization

From this directory with the official Wrangler CLI:

```text
npx wrangler login
npx wrangler secret put GITHUB_PREFETCH_TOKEN
npx wrangler deploy
```

The secret command takes its value interactively, not as a shell argument. Select Workers Free; this design does not require upgrading to a paid plan or paid AI. Confirm any free-plan runtime limits in the actual account before declaring production ready. Cron changes can take up to 15 minutes to propagate. Deploy well before the next preparation window.

Validation must include a real scheduled event, correct slot selection, a missing-pack dispatch (when due and safe), the successful Python job and the actual fresh committed pack. A successful deployment or dispatch alone does not prove readiness. Do not start an additional AI task for the test.

Local regression checks (no credentials/network):

```text
node --test worker.test.mjs
```

Primary references: [GitHub timer limitations](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows#scheduled-workflows-running-at-unexpected-times), [workflow dispatch permissions](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event), [Cloudflare Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/), [Workers pricing and limits](https://developers.cloudflare.com/workers/platform/pricing/).
