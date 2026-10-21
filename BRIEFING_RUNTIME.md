# Daily briefing: Four steps and autonomous CI publishing (DEC-022)

Use the existing morning/midday/evening tasks and their unchanged schedules (07:30, 13:30, 19:30 Europe/Athens).

Produce the Greek Oracle briefing using the user's selected model (ChatGPT / Luna). JoDemon9/Claude-Briefing is the public content and build engine; oracle-briefing is the central public portal and Wire.

## 1. PREPARE
Use fresh main, the actual local date/time in Europe/Athens and this task's slot. Read current capabilities once. Run `python scripts/v2/prepare_run.py` to get current planning context, sports headlines, and already published coverage for today to avoid duplicate stories.

## 2. RESEARCH & WRITE
- **Cyprus (4–6 stories)**: Major national, political, economic, legal, infrastructure, and community news.
- **World & Greece (4–5 stories)**: Consequential international developments, European policy, geopolitics, markets/tech.
- **Sports (High Value)**:
  - Permanent coverage for **Omonoia**, **Manchester United**, **Real Madrid**, and **Formula 1**.
  - In `sports.coverage`: provide `status_badge` (league position/points), `last_match` (score & scorers), `next_fixture` (time & opponent), and `analysis` (tactics, key developments, stakes).
  - Write 1 to 2 full sports articles (`sport-*.json`) in `content/articles/<edition-id>/` whenever there are match reviews, previews, or major sports news. Include them in `sports.major_stories` (full articles for Omonoia, Man Utd, Real Madrid, F1, and other sports are fully supported and encouraged).
- **Markets & Desks**: Keep ECB/Euribor, Brent, Gold, S&P, Nasdaq, CSE with accurate quote timestamps. Check Limassol weather.
- **Writing**: Clear, informative Greek. 60–90 word findings; optional evidence-backed analysis up to 180 words. Include real, relevant licensed image attribution.

## 3. QUICK VALIDATE (0.5s)
Run:
```bash
python scripts/v2/quick_validate.py <edition-id>
```
Confirms that the edition JSON and all referenced article JSON files exist and have valid structure. No heavy image processing, Playwright browser suites, or live polling required inside the generation container.

## 4. COMMIT & PUSH
Commit the content files directly:
```bash
git add content/editions/<edition-id>.json content/articles/<edition-id>/
git commit -m "feat(edition): publish <edition-id>"
git pull --rebase origin main
git push origin main
```
**Done!** Once pushed to `main`, GitHub Actions CI autonomously:
- Refreshes sports cache and validates assets.
- Prepares and optimizes images with soft placeholder fallbacks.
- Compiles the static HTML newspaper and Daily Hub (`build.py`).
- Runs deterministic integrity checks (`checks.py`).
- Commits and pushes compiled `docs/` and synchronizes to `oracle-briefing`.
