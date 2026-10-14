# Release verification — 15 October 2026

User-requested work: DEC-004/005 layered reading and whole-day overview, DEC-006 compact controls/photo presentation, DEC-007 verified opportunities.

The first editorial commit is on main: Claude-Briefing 1a3ca41425280d445d3fd6f21599af8340cea601; Oracle cefb2efa0d0826d5c9942caf72298a737800bb51. The follow-up release, live pages and actual task prompts are verified below.

## Scheduled prompt scope

Only the three active existing daily tasks receive changes: cumulative-day overview, useful reading layers, reading-review v2, inline controls/photo presentation and the new opportunities block. Original schedules/timezones, titles and enabled state are preserved; the completed one-off is untouched. Unrelated research, sports, finance, weather, privacy and publication instructions remain byte-for-byte unchanged.

| Task | Original prompt SHA-256 | Revised prompt SHA-256 |
| --- | --- | --- |
| Oracle Απογευματινό Briefing | 5405ccea1d762c981b679e2724d46b05e14e0050223229277bd237f7a85a5553 | e0fe7247a1c1e0ce0c3561ae0288a190e2cef7b358852f839699c70d1061e499 |
| Oracle Μεσημεριανό Briefing | d264fa43f19b4afb20be13f6b898da2273356e71e219bb4a9a95edf95e8928e5 | df8f85b564c10e5564523dac60e26392d952d614ec5120b5c36e5d5d8cef8824 |
| Oracle Πρωινό Briefing | 91b4c48ab8fa04e3b0bb32d1cb999ff9bea3b07b98051a18e5ffb3587eb504d3 | 08698d927080c52657c2b2423e2b4c883c8aa7db5465a642ce13aca0a7bd2c02 |

## Checks

- 76 newspaper unit tests; 300 general browser checks; 16 frontend browser cases passed.
- 14 final focused cases covered 320/375/390/768/1100/1200/1440px, JavaScript enabled/disabled, all 22 selected day stories, same-row controls, full-width expansion, keyboard use, funding stages and deadlines, and mobile/desktop navigation. Six UI unit checks were rerun after the final navigation correction.
- 9 portal unit tests, 9 portal browser checks and 29 central newspaper browser checks passed.
- Actual funding cards and the centralized image-credits page were visually checked. Required source/license links remain available; article photo captions/rights panels are absent.
- All 24 revised article source records were compared with the first editorial commit and unchanged by the presentation/funding follow-up. The evening edition changed only by adding opportunities; news/quote/publication timestamps are preserved. The opportunity records have their own honest verification time.
- Git trees were compared with the reviewed working trees before non-force publication. Wire and private reporting files were preserved.

## Repository publication

- Public renderer/content: [885d1ec](https://github.com/JoDemon9/Claude-Briefing/commit/885d1ec9d5cfc48081f1706d215b5e3f2ab2f9d8).
- Complete central snapshot: [72bd8fb](https://github.com/JoDemon9/oracle-briefing/commit/72bd8fb3ea457423a7d1d5ee21aec4e3c9ca3da9).
- Private repository: agent guidance only, commit c950f0ff38fb541eb96e12b2fb9c7017133d00f2. No private reporting data was exported.

The three active daily ChatGPT task prompts were updated and read back exactly. Their titles, schedules, timezones, timing modes, enabled states and conversation destinations were compared before/after and unchanged. The completed one-off task is unchanged. The prompt hashes above identify the exact reviewed versions without copying private task contents into a public repository.

## Served release verification

Verified from the actual Pages origins at 2026-10-15T01:13:21+03:00:

- Public briefing: `e5baeaeaac80142377105ca8a0368d1efd409d3919f689d53028038c807067f1`; **181 exact file checks passed**, including dated editions, readers, images, CSS/JS, day/latest descriptors and centralized photo credits.
- Central Oracle: `34c8791a705551b2f838c2c37614ffc5a0d3daad1dc830c73b7a93cb4ad6e846`; **35 exact file checks passed**, including the complete day, portable assets and compatibility descriptors.
- [Public served-release workflow](https://github.com/JoDemon9/Claude-Briefing/actions/runs/38645858726): success.
- [Central served-release workflow](https://github.com/JoDemon9/oracle-briefing/actions/runs/38645902670): success.
- [Portal reading CI](https://github.com/JoDemon9/oracle-briefing/actions/runs/38645796638): success. [Public reading CI](https://github.com/JoDemon9/Claude-Briefing/actions/runs/38645771872) was still running at this verification; local checks above passed. A workflow link is provided so current status can be checked independently.

Live newspaper: https://jodemon9.github.io/oracle-briefing/ . Funding/rights: https://jodemon9.github.io/oracle-briefing/#opportunities .

The earlier market redesign (DEC-002/003) remains separately staged as recorded; this release does not silently incorporate it.
