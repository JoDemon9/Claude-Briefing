# DEC-006 — One-row article actions and quieter photographs

- Date: 15 October 2026 (Asia/Nicosia).
- User request: the three article buttons should stay on the same line on both web and mobile; remove photograph/rights sections and text explaining the photos from every article.
- Reason: repeated controls and photo explanations consume scrolling space in a personal briefing.
- Supersedes: earlier presentation instructions requiring per-photo visible captions/rights disclosures. Image truth, metadata, licensing and decode gates remain required.

The shared frontend groups Ανάλυση / Άρθρο / Πηγές in one row with 44px targets and full accessible labels. Native details remain usable with keyboard and JavaScript disabled; expanded content flows underneath at full width. No useful analysis means two meaningful actions, never a dummy third control. The layout applies to the day, independent editions and central portal snapshot. Dated readers keep their original routes.

`build.image` renders the image, accurate alt and failure state without captions or rights panels. One generated `docs/photo-credits.html` page preserves reviewed full captions, authorship, original source and license links; it is linked from the footer, not under every image. Source JSON is unchanged. Do not reintroduce per-photo prose during unrelated image or styling work.

Affected sources: build.py, newspaper_ui.py, newspaper-ui.css, UI/image/browser tests, generated public pages and portal snapshot. Verification/publication is recorded in RELEASE_NOTES_2026-10-15.md after actual checks. This change is authorized for the repositories and the relevant scheduled-prompt instructions.

Code is on main, both Pages releases passed live verification, and the three task prompts were updated/read back exactly. Evidence is maintained in [RELEASE_NOTES_2026-10-15.md](../RELEASE_NOTES_2026-10-15.md).

## Evening validation reliability, 15 October

The evening candidate's general and frontend checks passed, but the historical 14 October editorial check sampled expanded action controls with separate browser protocol calls. Native-disclosure scrolling and lazy-image layout shifts can move the whole row between those samples. The existing central-portal check already uses one `getBoundingClientRect` snapshot for this reason. The editorial check now applies that same atomic measurement to collapsed and expanded controls, retaining the strict under-2px alignment and 44px target requirements, and adds an expanded-state failure screenshot. No UI CSS, source time, reading policy, image gate, scheduler or Wire changes are involved. Actual candidate/main/Pages outcomes are recorded separately with the evening publication evidence; this note is not a publication claim.
