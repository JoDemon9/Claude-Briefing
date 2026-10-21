# Oracle Sovereign Briefing: Runtime & Production Architecture (v3.0 Sovereign)

Canonical reference for all agent workflows (ChatGPT, Luna, Antigravity). Follow the 4-step streamlined protocol. Internal LLM generation containers produce clean, validated JSON content; deterministic compilation, WebP image processing, Playwright tests, and GitHub Pages sync are handled autonomously by GitHub Actions CI upon Git push.

---

## 1. PREPARE (30 Seconds)
1. Determine the target slot and local date (`Europe/Athens` / `Asia/Nicosia` timezone):
   - **Morning**: `YYYY-MM-DD-morning` (07:30 EEST)
   - **Midday**: `YYYY-MM-DD-midday` (13:30 EEST)
   - **Evening**: `YYYY-MM-DD-evening` (19:30 / 20:30 EEST)
2. Run planning helper:
   ```bash
   python scripts/v2/prepare_run.py
   ```
   Inspect current capabilities, sports headlines, and existing coverage to avoid duplicate stories.

---

## 2. RESEARCH & ASYMMETRIC WRITING

### 2.1. Asymmetric Slot Modes
- **Morning Scan (`edition_mode: "morning_scan"`)**:
  - `executive_scan`: 3-Pillar high-level overview:
    - `geopolitics_macro`: Global and European macro developments.
    - `cyprus_institutions`: National regulatory, political, and institutional agenda.
    - `markets_tech`: Market sentiment and key technology/AI developments.
    - `day_catalysts`: 3–5 bullet points of scheduled events, speeches, earnings, or data releases to watch today.
  - Comprehensive analytical reporting across Cyprus and World.
- **Midday Delta Mode (`edition_mode: "midday_delta"`)**:
  - `delta_log`: 3–6 concise bullet points explaining strictly **«Τι Άλλαξε από τις 07:30»** (breaking shifts, official announcements, mid-session market reactions).
  - Articles updating earlier morning stories include `delta_update` callouts at the top.
  - `fast_wire`: 3–6 fast single-line ticker developments (`category`, `summary`, `source_name`, `source_url`) for breaking wire items that do not require full long-form articles.
  - **No copy-pasting**: Never duplicate static morning text; focus strictly on newly emerged facts and delta shifts.
- **Evening Synthesis (`edition_mode: "evening_synthesis"`)**:
  - Full daily synthesis, final closing market analysis with economic transmission mechanisms (`transmission_mechanism`), final match and score analysis, and tomorrow's watchpoints.

### 2.2. 4-Layer Analytical Realism on Articles (`content/articles/<edition-id>/*.json`)
For high-impact stories, write structured articles with 4-layer analytical depth:
- **Layer 1: Delta & Core Facts**: Clear headline, verified sources, and `summary` (with optional `delta_update` for developing stories).
- **Layer 2: Mechanics & Incentives (`mechanics_and_incentives`)**: The economic forces, institutional incentives, and underlying motives driving actors.
- **Layer 3: Second-Order Effects (`second_order_effects`)**: Ripple effects, unintended consequences, and sector-wide impacts.
- **Layer 4: Sovereign Scenarios (`scenarios`)**:
  - `base_case`: Most probable medium-term outcome.
  - `tail_risk`: Low-probability, high-consequence risk scenario.
  - `watch_next`: Observable trigger points to monitor.

### 2.3. Sports Renaissance
- **Four Permanent Pillars**: Permanent structured reporting for **Omonoia**, **Manchester United**, **Real Madrid**, and **Formula 1**.
- Under `sports.coverage`, populate for each team:
  - `status_badge`: Position / points, championship standing, or Grand Prix status.
  - `last_match`: Final score, opponent, scorers, and date.
  - `next_fixture`: Next match date, kickoff time, opponent, and venue.
  - `analysis`: 2–3 sentences of tactical breakdown, injuries, or strategic stakes.
  - `verified_links`: 1–2 official headline links.
- **Full Sports Articles**: Write 1–2 dedicated sports articles (`sport-*.json`) in `content/articles/<edition-id>/` whenever there are match reviews, previews, or major sports news, and link them in `sports.major_stories`. Articles for Omonoia, Man Utd, Real Madrid, F1, and other sports are fully supported and rendered on both the edition and homepage.

### 2.4. Causal Markets & Cyprus Real Economy Radar
- **Markets**: Track S&P 500, Nasdaq, STOXX Europe 600, CSE (ΧΑΚ), EUR/USD, Brent, ECB Deposit Rate, and Euribor.
  - For major movers, provide `transmission_mechanism` explaining how the market movement transmits into the Cyprus/EU real economy (borrowing costs, inflation, energy bills).
- **Real Economy & Regulatory Radar (`opportunities`)**: Track active Cyprus and EU grant schemes, corporate incentives, and regulatory rights.

---

## 3. QUICK VALIDATE (0.5s)
Before pushing, run the lightweight offline validator:
```bash
python scripts/v2/quick_validate.py <edition-id>
```
Confirms JSON syntax, required keys, and article path references.

---

## 4. COMMIT & PUSH
Push directly to the `main` branch:
```bash
git add content/editions/<edition-id>.json content/articles/<edition-id>/
git commit -m "feat(edition): publish <edition-id>"
git pull --rebase origin main
git push origin main
```
**Publication Complete!**
GitHub Actions CI autonomously:
1. Prepares and optimizes images with soft-fail fallback placeholders.
2. Compiles static HTML for the edition, articles, Daily Hub, and archive (`build.py`).
3. Runs deterministic integrity gates (`checks.py`).
4. Commits and deploys built assets to GitHub Pages.
5. Synchronizes the portal release to `JoDemon9/oracle-briefing`.

---

## 5. POLICY & BOUNDARIES
- **private Pages**: private Pages stays disabled; original source/quote times are preserved verbatim from original publishers without artificial shifts.
- **morning, midday, evening**: Every morning, midday, and evening edition preserves image_review.version=2 and reading_review.
- **Integrity**: No fuzzy automatic matching of headlines; keep unchanged historical editions, schemas, and contracts intact.
- **Constraints**: No arbitrary quota/time limit inside generation; No PR merge operations in automated tasks.

