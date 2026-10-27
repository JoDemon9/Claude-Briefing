# The Oracle Sovereign — Claude-Briefing

Public Greek newspaper, independent editions, cumulative daily coverage and archived readers. Python collects routine evidence before one bounded ChatGPT synthesis; the compiler produces canonical JSON and existing CI validates and publishes it.

Start with [AGENTS.md](AGENTS.md), the [editorial specification](BRIEFING_SPEC.md) and [execution contract](CHATGPT_TASK_INSTRUCTIONS.md). [Maintenance operations](maintenance/OPERATIONS.md) and [historical rationale](DECISIONS.md) are references only.

- [Newspaper](https://jodemon9.github.io/Claude-Briefing/)
- [Central portal](https://jodemon9.github.io/oracle-briefing/)

Private research stays private. Existing task schedules and the independent RSS Wire are preserved. Changes in this repository do not install task prompts or establish live publication.

```sh
python -m pip install -r requirements-v2.txt
python -m playwright install chromium
python scripts/v2/task_prompts.py --check
python scripts/v2/checks.py --base origin/main
```
