# Daily newspaper handoff

Read BRIEFING_RUNTIME.md for the active editorial/production contract and OPERATIONS.md for commands. Full pre-consolidation architecture notes remain in maintenance/history/2026-10-15/DAILY_HUB_HANDOFF.md; routine tasks do not reread that history.

Claude-Briefing stores reviewed public structured articles, independent editions, stable dated readers and deterministic daily composition. daily/YYYY-MM-DD.html is the permanent cumulative day; today.html/day-latest.json selects the latest published day. latest.html/latest.json remains the latest independent edition. Draft/absent slots stay absent. The day selects the latest actual version of each stable story without paragraph concatenation or fuzzy merging, retaining important earlier stories and provenance.

Oracle saves the complete day and referenced hash-versioned assets in index.html, with day-snapshot.html and compatibility descriptors. Refresh verifies identity/HTML/asset hashes and decoded images before replacement; failure keeps the saved newspaper. Wire remains independent. Private contains source research, memory/cache/packets and metrics and never has Pages enabled.

Use explicit daily lead/section/priority, reviewed cumulative overview/story references, immutable supported editorial events, flat aliases and genuine later follow-ups. Preserve published/source/quote times, historical URLs, privacy, image/reading gates, optional native panels and current sports/mobile choices. No site development during routine edition creation.
