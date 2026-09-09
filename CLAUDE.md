# THE ORACLE SOVEREIGN — repo guide

A daily Greek-language briefing for a reader in Limassol. An edition is a
hand-authored markdown file; the scripts turn it into the published page,
check it, and notify. **The scripts never invent content.**

There is a second clone of this repo at `..\..\Antigravity\Daily Brief`.
It is not this one. Check `git rev-parse --show-toplevel` before assuming
edits here reach anything.

## Pipeline

Editions are authored, not generated. The unattended morning loop
(`daily-run.py`, `morning-runner.py`, `run-morning.bat`) was removed in
0e82c39 because it published unreviewed output. Run the stages yourself:

```bash
python scripts/build-html.py briefings/oracle-briefing-YYYY-MM-DD.md
python scripts/check-links.py briefings/oracle-briefing-YYYY-MM-DD.md
python scripts/validate-edition.py briefings/oracle-briefing-YYYY-MM-DD.md
git add -A && git commit && git push        # only if both checks passed
python scripts/send-briefing.py briefings/oracle-briefing-YYYY-MM-DD.md
```

Run `check-links.py` **before** `build-html.py` if you want the link footnote
to reflect this run — the build reads the report the checker leaves behind.

`.github/workflows/notify.yml` runs the same sequence on push and only sends
to Telegram if the link check and the validator both pass.

| Script | Does |
| --- | --- |
| `scripts/build-html.py` | markdown → `docs/`. Parses the edition, resolves images, builds the cross-edition search index, fills the template. |
| `scripts/templates/edition.html` | the whole page: markup, CSS, JS. `string.Template` — a literal `$` is written `$$`. |
| `scripts/check-links.py` | requests every URL in the edition; non-zero exit on any dead one; writes `briefings/.link-check-DATE.json`. |
| `scripts/validate-edition.py` | the pre-publish gate — see Invariants. Non-zero exit blocks the push. |
| `scripts/send-briefing.py` | formats and dispatches the Telegram summary. The only sender; the `.mjs` twin is gone. |
| `scripts/env_loader.py` | the only `.env` parser. Real environment variables win over the file. |
| `scripts/generate-briefing.py` | optional draft collector (RSS + Gemini). Needs `GEMINI_API_KEY`; fails loudly without it. Output is a **draft** — verify every number and URL. |

## Layout

```
briefings/oracle-briefing-DATE.md    the source edition — the only hand-written file
briefings/.link-check-DATE.json      link-check report (gitignored)
docs/                                the single published tree (GitHub Pages)
  index.html                           latest edition
  briefings/DATE.html + DATE.md        permanent archive
  search-index.json, house-search/
scripts/                             pipeline
.antigravity/rules/oracle-briefing.md  the editorial house rules
```

`docs/` is the only build output. Root `index.html`, `search-index.json`,
`house-search/` and `briefings/*.html` were identical copies of it and are
gitignored — do not reintroduce them.

## Invariants

**Never publish a number, fact or URL that nothing produced.**

1. **No stale defaults.** `parse_markdown()` seeds nothing. Every rate comes
   from the ΕΠΙΤΟΚΙΑ section; a missing value renders `—` and raises a build
   warning. It used to default to ECB 3,75% / ΚΤΚ 3,78% / €1.032 — values a
   parse failure would have passed through as live data.
2. **The instalment is computed, not copied.** `annuity_payment()` derives it
   from the parsed amount/term/rate, so the figure can never disagree with the
   rate printed beside it.
3. **Only `check-links.py` may claim the links were checked.** The build drops
   any authored sentence asserting verification and appends the checker's own
   report; `validate-edition.py` rejects an edition that carries such a claim.
   Editions used to assert «όλοι οι σύνδεσμοι ελέγχθηκαν (200 OK)» with
   nothing having opened a socket.
4. **Structure**, enforced by `validate-edition.py` (see
   `.antigravity/rules/oracle-briefing.md`):
   - ΚΥΠΡΟΣ exactly 6 items, ΔΙΕΘΝΗ 5, ΑΓΟΡΕΣ 5
   - ΚΥΠΡΟΣ item 6 tagged `[Ο Φάκελός μου]`, and no other item
   - at most 2 items per outlet across the whole edition
   - no URL cited by two items
   - a card's `<details>` must add context, not repeat its visible text
5. **`generate-briefing.py` fails rather than fabricates.** Its RSS fallback
   used to write invented dashboards, Euribor rows, sports fixtures, portfolio
   notes and deadlines as fact. No key or no model output is now an error.
6. **Tailwind is pinned** (`cdn.tailwindcss.com/3.4.16`). It previously loaded
   from an unversioned `gstatic.com/antigravity/web/dev/` host.

## Editing the page

Markup, CSS and JS belong in `scripts/templates/edition.html`.
`render_html()` is data prep only: it builds a context dict and calls
`render_template()`. Adding a placeholder means adding a key — a missing one
raises `KeyError` at build time, naming the placeholder.
