# DEC-027 — Real photographs for every article and a larger Sports desk

The user approved the quality implementation and explicitly requested a picture on every article, permitted reuse, and clarified **real photographs only**. They also requested a substantially larger, more useful Sports section while keeping AI usage low.

This supersedes DEC-023's image-unavailable publication exception for the new real-photos-v1 policy. Other partial-data rules remain. DEC-025/026 search, output, single-pass and carry limits remain unchanged. No image generation, AI image search, paid model or additional AI run is introduced.

## Implementation

- A reviewed registry contains 48 licensed real photographs, including 14 newly retrieved assets, 56 explicit story assignments and bounded subject rules. Python assigns a photograph when a new article omits photo fields. A matching subject photo is preferred; clearly labelled broad desk-context photographs cover unmatched subjects. The registry includes actual images of Earth, Nicosia and an Olympic stadium for those broad contexts. These are photographs, not generated illustrations. Reuse retains source, licence, author and retrieval metadata and verifies exact local bytes.
- Repair 86 image-less article records, including all three editions published today, and replace one old airport diagram. All 334 published article records now have photographs. Preserve every reporting field, source record and original publication/update time. Record image_revision_at separately. Rebase carry fingerprints chronologically and copy the repaired baseline image exactly. An image-only reporting fingerprint lets an older editorial contract remain valid only while its reporting is byte-equivalent after normalization; changes to facts, sources or timestamps do not receive that exception.
- A real-photos-v1 edition cannot publish a missing or invalid photograph. Missing remote assets no longer silently become image-less articles under that policy. Ordinary new compilation uses locally stored photographs, so routine publication needs no image download.
- The Python pre-run adds eight bounded RSS requests for favourite headlines, with date, relevance and URL checks. This adds zero AI data-collection calls. Headline-only feeds do not become article evidence and are not re-emitted by the model.
- Preserve structured UEFA data through hydration. Render recent scores, next confirmed fixtures and the top five available standings for Champions League, Europa League and Conference League. Keep source timestamps and unavailable states. Restore the 25 October evening and 26 October Morning/Midday/Evening editions’ previously dropped UEFA data from their exact sealed packs, recording sports_revision_at separately.
- Display F1 race results and driver standings already collected. Add club league statistics where returned. Larger team cards use licensed archive photographs, readable fixtures, sources and headline links. Render selected sports articles even when the optional major-story explanation was absent.
- Give a significant priority-team match or F1 championship development consideration for one analytical lead within existing caps. No invented tactics, xG, injuries or result-driven causal claims. This guidance is in the digest and repository prompts; actual saved task prompt settings remain separate.

## Preservation and verification

Keep all three scheduled times, existing collector/cloud-watchdog schedules, 38 market instruments, exact factual carries, privacy boundaries, article identities/URLs, archived reporting and source timestamps. User-facing image captions identify archive/context use; complete licensing remains on the credits page.

Targeted regressions cover automatic hash-preserving photo assignment, invalid explicit selections, every published article's local photo, reporting-fingerprint protection, bounded sports feeds, visible F1/UEFA tables and selected sports articles. Schema/build, maintenance CI and mobile/desktop rendering must pass before merge. Main deployment and exact live source/portal verification are separate from local checks; record their actual results in the delivery report.

Cloud reliability follow-through: the private collector actually ran at 18:20:21 Cyprus time on 25 October (Actions run 40211192299), succeeded and sealed the evening pack at 18:20:52. It had all 38 market rows and zero AI collection calls. The subsequent evening submission and source/portal publication succeeded. This is observed execution evidence, not a guarantee that every future provider or scheduler invocation will succeed.

## Subsequent coverage clarification, 26 October

The user explicitly clarified that Cyprus and international coverage had too few articles. Target 4–5 supported stories in each news desk. Raise the authored-story ceiling to 10 in Morning (including any sports lead) and 6 materially changed stories in later editions; retain exact carries for complete later coverage. This supersedes the earlier 6/4 story ceilings only. Search/open/tool caps, 6,500/4,000 output-token ceilings and one-pass synthesis remain unchanged. Do not hide or cut existing Cyprus/world coverage. Keep analytical desk leads and concise secondary reports; insufficient evidence never justifies padding.
