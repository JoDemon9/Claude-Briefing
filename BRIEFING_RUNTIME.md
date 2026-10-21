# Oracle Sovereign Briefing: Runtime & Production Architecture (v3.0 Sovereign)

Canonical reference for all agent workflows (ChatGPT, Luna, Antigravity). Follow the single-payload protocol. Internal LLM generation containers produce a single clean, validated JSON payload (`/tmp/payload.json`); deterministic compilation, WebP image processing, multi-file decomposition, Playwright tests, and GitHub Pages sync are handled autonomously by `scripts/v2/compose.py` and GitHub Actions CI upon Git push.

---

## 1. SINGLE-PAYLOAD COMPOSITION WORKFLOW
Rather than orchestrating 12 separate JSON files, manual SHA-256 calculation, and image manipulation, agent workflows execute a streamlined 2-step process:

1. **Write Lean Payload**: The LLM outputs a single high-signal file to `/tmp/payload.json` containing:
   - `edition_id`: Target slot (e.g. `YYYY-MM-DD-morning`, `YYYY-MM-DD-midday`, or `YYYY-MM-DD-evening`).
   - `edition_mode`: `morning_scan`, `midday_delta`, or `evening_synthesis`.
   - `executive_scan`: 3-Pillar scan (`geopolitics_macro`, `cyprus_institutions`, `markets_tech`) + `day_catalysts`.
   - `delta_log`: Delta shift log for midday editions.
   - `articles`: Array of structured analytical articles (1 lead, Cyprus, World, Sports) with 4-layer analytical depth.
   - `fast_wire`: Rapid single-line ticker developments.
   - `sports_highlights`: Real-time match data and analysis for `omonoia`, `manutd`, `realmadrid`, and `formula1`.

2. **Execute Smart Compiler**:
   ```bash
   python scripts/v2/compose.py --input /tmp/payload.json --publish
   ```
   The compiler dynamically computes SHA-256 hashes, copies WebP assets, clones 38 market instruments, decomposes articles into `content/articles/<edition_id>/*.json`, compiles static HTML, and pushes to Git.

---

## 2. RESEARCH & ASYMMETRIC WRITING MODES

### 2.1. Asymmetric Slot Modes
- **Morning Scan (`edition_mode: "morning_scan"`)**:
  - `executive_scan`: 3-Pillar high-level overview:
    - `geopolitics_macro`: Global and European macro developments.
    - `cyprus_institutions`: National regulatory, political, and institutional agenda.
    - `markets_tech`: Market sentiment and key technology/AI developments.
    - `day_catalysts`: 3–5 bullet points of scheduled events, speeches, earnings, or data releases to watch today.
  - Comprehensive analytical reporting across Cyprus, World, and morning sports.
- **Midday Delta Mode (`edition_mode: "midday_delta"`)**:
  - `delta_log`: 3–6 concise bullet points explaining strictly **«Τι Άλλαξε από τις 07:30»** (breaking shifts, official announcements, mid-session market reactions).
  - Articles updating earlier morning stories include `delta_update` callouts at the top.
  - `fast_wire`: 3–6 fast single-line ticker developments (`category`, `summary`, `source_name`, `source_url`) for breaking wire items that do not require full long-form articles.
  - **No copy-pasting**: Never duplicate static morning text; focus strictly on newly emerged facts and delta shifts.
- **Evening Synthesis (`edition_mode: "evening_synthesis"`)**:
  - Full daily synthesis, final closing market analysis with economic transmission mechanisms (`transmission_mechanism`), final match and score analysis, and tomorrow's watchpoints.

### 2.2. 4-Layer Analytical Realism on Articles
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
- **Full Sports Articles**: Dedicated sports articles (`sport-*.json`) in `content/articles/<edition-id>/` linked in `sports.major_stories`. Articles for Omonoia, Man Utd, Real Madrid, F1, and other sports are fully supported and rendered on both the edition and homepage.

### 2.4. Causal Markets & Cyprus Real Economy Radar
- **Markets**: Track S&P 500, Nasdaq, STOXX Europe 600, CSE (ΧΑΚ), EUR/USD, Brent, ECB Deposit Rate, and Euribor.
  - For major movers, provide `transmission_mechanism` explaining how the market movement transmits into the Cyprus/EU real economy (borrowing costs, inflation, energy bills).
- **Real Economy & Regulatory Radar (`opportunities`)**: Track active Cyprus and EU grant schemes, corporate incentives, and regulatory rights.

---

## 3. POLICY & BOUNDARIES
- **private Pages**: private Pages stays disabled; original source/quote times are preserved verbatim from original publishers without artificial shifts.
- **morning, midday, evening**: Every morning, midday, and evening edition preserves image_review.version=2 and reading_review.
- **Integrity**: No fuzzy automatic matching of headlines; keep unchanged historical editions, schemas, and contracts intact.
- **Constraints**: No arbitrary quota/time limit inside generation; No PR merge operations in automated tasks.
