# DEC-026 — Restore analytical value within the existing quota budget

25 October 2026. The user reported that the noon briefing was much worse and asked for better quality while retaining low usage. This refines DEC-025; it does not raise any search, tool, story or output limit, invoke another AI producer, or rewrite the published noon edition.

## Observed causes

The private noon submission authored three stories but only one short Mechanism paragraph; it had no Effects, Scenarios or Watch directives. The Executive mostly repeated facts. The prompt restricted where analysis could appear without clearly allocating prose or specifying what useful analysis must answer. The original Python digest clipped every evidence excerpt at 1,000 UTF-8 bytes: the Greek example retained only 552 characters. Routine sports context occupied 15,964 bytes. Candidate selection was primarily recency within publisher-assigned desks, which could place a foreign story from a Cyprus publisher in Cyprus.

## Changes

- Rank discovery using transparent heuristic hints for likely baseline follow-ups, policy/security/economic consequences, priority sports and multiple publishers. These hints are not evidence of significance, independent reporting or a matching story identity; the author makes the editorial choice.
- Honor explicit RSS geographic categories. Unknown categories retain the feed's desk as a provisional hint; the author must check geography.
- Bound article downloads to fourteen: one per selected cluster first, then a remaining different-publisher candidate. Separate publishers still require reporting-chain review before claiming corroboration.
- Extract up to 3,200 Unicode characters per article. The model digest shows up to 2,400 for the first candidate in a desk and 1,600 for others, preferring sentence boundaries. This removes the Greek byte penalty. Source bodies remain private, labelled excerpts; feed-only evidence remains discovery.
- Deduplicate repeated routine source references and show three recent/next UEFA events plus any priority-club event in the collected list. Label omitted counts; retain complete provider records in the sealed pack. All 38 market rows and the four priority cards remain in the digest.
- Give analytical leads about 120–170 Greek words for fact, change, mechanism, affected parties and an observable next test. Use conditional scenarios only when supported; never invent depth for routine news. The Executive connects developments to implications and uncertainty, instead of repeating headlines. Allocate roughly 60% of prose to leads, 20% to the Executive and 20% to secondary dispatches.

The editorial guidance is part of the deterministic digest as well as all three maintained prompt files. Existing installed tasks already read that digest once, so next fresh packs carry the guidance without another tool call. Replacing the saved live task prompts is a separate external setting; do not claim installation from repository edits. The previously used Windows task-edit helper was blocked by Windows security on this maintenance run; no security setting was disabled.

## Preservation and validation

Keep Morning 5 searches/2 opens/10 tools/6 stories/6,500 reference output tokens; Midday and Evening 3 searches/1 open/7 tools/4 deltas/4,000 tokens. Keep one analytical pass and one review, exact fingerprinted carry records, all original evidence/publication times, partial availability, the existing three publication gates and source-then-portal verification. History and all AI schedules/models remain unchanged.

Regression coverage includes Greek excerpt retention, foreign RSS category routing, significant follow-up ranking, the article-request ceiling, all-desk candidates, provenance-preserving digest compaction and priority-club retention. Replay the same sealed noon pack to compare input size and visible evidence; this is not an account-usage measurement or proof of future editorial quality. Local checks, PR CI, deployed main, future fresh packs and actual AI output remain distinct evidence.

Offline replay of the same sealed noon pack: 47,175 → 46,567 UTF-8 bytes; 14,004 → 12,345 o200k_base input reference tokens; visible article evidence 8,812 → 14,397 characters; the Greek e1 excerpt 552 → 1,600 characters. All eleven candidate clusters still fit. These are digest measurements only, not actual ChatGPT account savings. Six targeted quality tests, twenty-two existing synthesis tests and two preparation tests passed locally (Windows sandbox filesystem restrictions required an authorized unsandboxed rerun for the file/symlink tests). Full maintenance CI remains required.
