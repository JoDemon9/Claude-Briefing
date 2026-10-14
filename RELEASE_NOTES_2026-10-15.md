# Release verification — 15 October 2026

User-requested work: DEC-004/005 layered reading and whole-day overview, DEC-006 compact controls/photo presentation, DEC-007 verified opportunities.

The first editorial commit is on main: Claude-Briefing 1a3ca41425280d445d3fd6f21599af8340cea601; Oracle cefb2efa0d0826d5c9942caf72298a737800bb51. The follow-up release and actual live/task verification are recorded below after execution.

## Scheduled prompt scope

Only the three active existing daily tasks receive changes: cumulative-day overview, useful reading layers, reading-review v2, inline controls/photo presentation and the new opportunities block. Original schedules/timezones, titles and enabled state are preserved; the completed one-off is untouched. Unrelated research, sports, finance, weather, privacy and publication instructions remain byte-for-byte unchanged.

| Task | Original prompt SHA-256 | Revised prompt SHA-256 |
| --- | --- | --- |
| Oracle Απογευματινό Briefing | 5405ccea1d762c981b679e2724d46b05e14e0050223229277bd237f7a85a5553 | e0fe7247a1c1e0ce0c3561ae0288a190e2cef7b358852f839699c70d1061e499 |
| Oracle Μεσημεριανό Briefing | d264fa43f19b4afb20be13f6b898da2273356e71e219bb4a9a95edf95e8928e5 | df8f85b564c10e5564523dac60e26392d952d614ec5120b5c36e5d5d8cef8824 |
| Oracle Πρωινό Briefing | 91b4c48ab8fa04e3b0bb32d1cb999ff9bea3b07b98051a18e5ffb3587eb504d3 | 08698d927080c52657c2b2423e2b4c883c8aa7db5465a642ce13aca0a7bd2c02 |

## Local checks

76 newspaper unit tests and 10 focused browser cases passed (320/375/390/768/1440px, JavaScript enabled/disabled; all 22 selected stories). These cover same-row controls, 44px touch targets, full-width expansion, visible factual summaries, linked overview, source readers, no per-photo captions, centralized credits, funding-stage deadlines and expired-call rejection. Broader browser/portal verification is recorded after completion.

## Publication state

Follow-up code is prepared locally. Actual Pages and external-task verification remain pending until recorded after execution.
