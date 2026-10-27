# DEC-022: Sports Renaissance and Autonomous CI Publishing

- **Date**: 21 October 2026
- **User Request**: Restore the quality and richness of the sports section; eliminate the excessive verification checks and token bloat that caused task timeouts and failed publications.

## Cause and Resulting Behavior

1. **Sports Renaissance**:
   - Eliminated brittle club-site HTML scraping in `sports_news.py`. Added resilient RSS/Google News collection, browser User-Agent, and increased check staleness threshold from 120 minutes to 720 minutes to prevent fatal build crashes.
   - Removed the restrictive filter `interest(lookup[r['article_id']]) == 'other'` in `sports.py` for editions from 21 October onwards. Full analytical sports articles (`sport-*.json`) covering Omonoia, Manchester United, Real Madrid, and Formula 1 are now rendered in `major_stories`.
   - Rendered rich team cards in `sports.py`: scores, upcoming fixtures, league position/status badge, and editorial analysis from `coverage[team]` are now directly visible to readers instead of being discarded.
   - Refactored `$defs/sports_team` in `templates/v2/content.schema.json` to require only essential fields while supporting both legacy structured objects and concise strings.

2. **Autonomous CI Publishing & Pure Decoupling**:
   - Transferred image conversion, HTML compilation (`build.py`), deterministic checks (`checks.py`), and two-site Git synchronization to GitHub Actions CI (`content-checks.yml`).
   - Added `quick_validate.py` (0.5s check) for the LLM container.
   - Added `ORACLE_SKIP_LIVE_POLL=1` in `publish.py` to prevent Fastly CDN propagation delays from causing live verification deadlocks.
   - Streamlined `BRIEFING_RUNTIME.md` and `CHATGPT_TASK_INSTRUCTIONS.md` into an efficient 4-step workflow (Prepare, Research/Write, Quick Validate, Commit & Push).
