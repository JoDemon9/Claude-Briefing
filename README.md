# THE ORACLE SOVEREIGN — published website

Website: https://jodemon9.github.io/Claude-Briefing/

This repository serves reviewed static artifacts. Development, generation, source Markdown, financial checks, configuration and credentials belong in the private development repository `JoDemon9/Claude-Briefing-Private`.

The private build produces `docs/index.html` (archive), permanent `docs/briefings/YYYY-MM-DD.html` editions, dated article JSON, reader and markets pages, search data and shared assets. All September published HTML is preserved exactly. October uses compact cards, dated readers, detailed sports and cacheable editorial illustrations with AI disclosure.

Only the private pipeline's allowlisted release package should be copied here. Never mirror the private working tree. New editions require matching content/HTML/article-data validation receipts before export. Merge/deployment and Telegram delivery are separate steps; the review branch does not publish.

```bash
python tools/validate-site.py
```

The check verifies archive membership, article data, asset paths and links. The historical September pages retain their original widgets; internal repairs to those pages are outside the October scope. Browser and pipeline regression tests run in the private development repository.

TradingView currently embeds Bitcoin, TSMC ADR and NVIDIA. SPX, Nasdaq Composite and the LSE VUAA/EQQQ listings use explicit external links because the provider restricts embedding. Instruments are never silently replaced by ETFs or CFDs. Provider availability may change.

Obsolete public generator scripts, duplicate Markdown and the automatic Telegram notifier are removed in this review. Their source/history remains in the private repository and Git history. Active publishing instructions remain in CLAUDE.md. Duplicate development instructions, the public environment example and design-plan copy are removed; their authoritative versions and Git history remain private.
