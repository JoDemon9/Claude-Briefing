# DAILY_HUB_HANDOFF — The Oracle Sovereign

Η εφημερίδα ημέρας υλοποιείται στον κοινό renderer v2. Το ChatGPT εξακολουθεί να ερευνά και να γράφει τις ανεξάρτητες εκδόσεις. Κώδικας και GitHub workflows κάνουν validation, rendering, synchronization και verification· δεν παράγουν ειδήσεις.

## Πραγματική κατάσταση

- Κεντρική εφημερίδα: https://jodemon9.github.io/oracle-briefing/
- Μόνιμη ημέρα: https://jodemon9.github.io/Claude-Briefing/daily/2026-10-13.html
- Φορητή νεότερη πραγματική ημέρα: https://jodemon9.github.io/Claude-Briefing/today.html
- Αρχείο ημερών: https://jodemon9.github.io/Claude-Briefing/daily/index.html
- Συμβατό τελευταίο ανεξάρτητο briefing: https://jodemon9.github.io/Claude-Briefing/latest.html και data/latest.json.
- Ανεξάρτητα URLs της 13/10: morning/2026-10-13.html, midday/2026-10-13.html, evening/2026-10-13.html στο Claude-Briefing. Οι readers παραμένουν στο articles/<edition-id>/<article-id>.html. Τα παλιότερα dated reader routes δεν αλλάζουν.
- Πηγή αρχικής ημέρας: ήδη δημοσιευμένες και ελεγμένες εκδόσεις 13/10· δεν έγινε νέα δημοσιογραφική έρευνα. Τα αρχικά Pages bytes των latest.json, editions.json και evening/2026-10-13.html συγκρίθηκαν με το πραγματικό αρχικό main και ταίριαξαν.
- Αρχικά main: δημόσιο e3d0fe1dfba6172ffaf3377a73519eea69af3318, Oracle 3a70b20f34f5a662ed4868b6ab41ec674d1aab92, private b380f33ec57bbba8e205c60de99b36ef3227cf56. Οι πρόσφατες merged PR 4/3/2 (public), 3/2/1 (Oracle), 9/8/7 (private) επιθεωρήθηκαν. Δεν υπήρχε νεότερη ανοιχτή υλοποίηση ημέρας σε αυτές τις αναφορές.
- Οι ακριβείς implementation commits, επιτυχημένα deployment αποτελέσματα και receipt IDs καταγράφονται στην ενότητα «Επαληθευμένη δημοσίευση».

## Paths και ροή

`content/editions/*.json` → έλεγχο schema και σημασιολογικών gates στο `scripts/v2/build.py` → ανεξάρτητα HTML/readers → `scripts/v2/daily.py` → επικύρωση `templates/v2/day.schema.json` → ολόκληρο υποψήφιο docs με rollback → `scripts/v2/release.py` → δημόσιο main/Pages → exact-byte verification → `scripts/v2/sync_portal.py` → Oracle index/assets/registry/descriptor → `scripts/daily_release.py` στο Oracle → Oracle Pages/exact-byte verification.

Παραγόμενα δημόσια αρχεία:

| Path | Ρόλος |
| --- | --- |
| docs/daily/YYYY-MM-DD.html | Πλήρης εφημερίδα συγκεκριμένης ημέρας· ανανεώνεται στην ίδια διεύθυνση |
| docs/today.html | Φορητή πλήρης νεότερη πραγματική ημέρα με absolute δημόσιους συνδέσμους |
| docs/data/day-latest.json | day_id, updated_at, day_url, html_url, HTML/asset hashes, version |
| docs/data/days/YYYY-MM-DD.json | Επικυρωμένες αναφορές ιστοριών/εκδόσεων και update history |
| docs/data/days.json, docs/daily/index.html | Αρχείο ημερών |
| docs/latest.html, docs/data/latest.json | Τελευταία ανεξάρτητη έκδοση· διατηρημένη συμβατότητα |
| Oracle docs/index.html | Πλήρες τοπικό αποθηκευμένο ημερήσιο fallback |
| Oracle docs/assets/latest-snapshot/<version>/assets/* | Μόνο τα αναφερόμενα ελεγμένα δημόσια assets |
| Oracle docs/data/day-snapshot.html | Αντίγραφο φορητής ημέρας, hash-identical με public today.html |
| Oracle docs/assets/latest-briefing.js | Έλεγχος ημέρας, HTML/asset hashes και image decoding πριν από αντικατάσταση |
| Oracle docs/data/release.json | Receipt της κεντρικής εφημερίδας, χωρίς σύνδεση με μεταβολές Wire |

Εντολές στο δημόσιο:

```sh
python scripts/v2/prepare_images.py --edition YYYY-MM-DD-type --verify-only
python scripts/v2/build.py
python -m compileall -q scripts tests
python -m unittest discover -s tests -v
python tests/browser_checks.py --screenshots .work/preview
python scripts/v2/release.py
python scripts/v2/release.py --stage .work/public-package
# Commit πλήρων reviewed sources + παραγόμενων docs, non-force update του fresh main.
python scripts/v2/release.py --verify-live
python scripts/v2/sync_portal.py --portal-root ../oracle-briefing
```

Στο Oracle:

```sh
python -m unittest discover -s tests -v
python tests/latest_browser_checks.py --screenshots .work/daily-preview
python tests/browser_checks.py --screenshots .work/portal-preview
python scripts/daily_release.py
# Commit μόνο τα σχετικά ελεγμένα αρχεία, preserving concurrent Wire updates.
python scripts/daily_release.py --verify-live
```

Το private έχει τον ίδιο renderer/schema και το δικό του preview από τα δικά του content. Το preview του main είχε δεδομένα μόνο ως 12/10, ενώ οι νεότερες πρωτογενείς πηγές ήταν σε χωριστά ιδιωτικά αρχεία. Δεν αντιγράφηκαν αυτά στο δημόσιο και δεν κατασκευάστηκε ψευδής ιδιωτική έκδοση 13/10. Το ιδιωτικό `docs/PROMPTS_PROPOSAL.md` μετακινήθηκε στο ιδιωτικό root `PROMPTS_PROPOSAL.md`, ώστε να μη συμπεριληφθεί ποτέ σε allowlisted public package. Δεν ενεργοποιήθηκε private Pages.

## Ακριβές optional input schema

Το `templates/v2/content.schema.json` απορρίπτει άγνωστα πεδία. Όλα τα παρακάτω είναι προαιρετικά· δεν απαιτούνται αλλαγές των ενεργών prompts για να λειτουργήσει η σύνθεση.

- `edition.daily`: object, additionalProperties=false. `lead_story_id`: string. `summary_60s`: 1–6 strings, κάθε string τουλάχιστον 20 χαρακτήρες.
- `article.daily`: object, additionalProperties=false. `section`: cyprus/world/sports. `priority`: integer 0–10000, μικρότερο πρώτα. `events`: array από objects με additionalProperties=false.
- Κάθε event απαιτεί `id` (μη κενό μοναδικό αμετάβλητο string), `kind` (new/substantive_update/correction/enrichment/provenance), `at` (ISO date-time με offset), `summary` (τουλάχιστον 10 χαρακτήρες), `source_urls` (μοναδικά HTTPS URLs από τις προσβάσιμες ελεγμένες πηγές του άρθρου).
- `market_core`: έως έξι μοναδικά instrument keys, δεν περικόπτει το πλήρες markets dataset.
- `market_summary`: έως τρία αντικείμενα `text`, `sources` με τουλάχιστον μία πηγή.
- `market_movers`: array των ίδιων sourced objects, πρώτη προβολή έως τρία.
- `market_next_event`: ένα sourced object για το επόμενο market ορόσημο στο fallback overview.
- `timezone`: Europe/Athens ή Asia/Nicosia, με ZoneInfo/IANA DST. date και type δηλώνονται ρητά.

Παράδειγμα μορφής για άρθρο με ήδη ελεγμένο source URL (εκδοτικό template, όχι νέο δημοσιευμένο γεγονός):

```json
{
  "daily": {
    "section": "cyprus",
    "priority": 10,
    "events": [
      {
        "id": "leaders-result-confirmed-v1",
        "kind": "substantive_update",
        "at": "2026-10-13T18:20:00+03:00",
        "summary": "Περιγράψτε εδώ μόνο το συγκεκριμένο νέο τεκμηριωμένο στοιχείο.",
        "source_urls": ["https://example.org/the-reviewed-article-source"]
      }
    ]
  }
}
```

Το example.org πρέπει να αντικατασταθεί από URL που ήδη υπάρχει στα article.sources και έχει ελεγχθεί. Η εκδοτική ώρα πρέπει να είναι η πραγματική ώρα του documented update, όχι η ώρα build.

Για αλλαγή κεντρικού θέματος στην έκδοση:

```json
{
  "daily": {
    "lead_story_id": "stable-story-id-from-a-participating-edition",
    "summary_60s": ["Σύντομη συνολική εικόνα από όλες τις πραγματικά διαθέσιμες εκδόσεις."]
  },
  "market_core": ["^GSPC", "^IXIC", "^STOXX", "cse", "eurusd", "brent"]
}
```

## Παραγόμενο day schema και σημασιολογία

Το ακριβές JSON Schema είναι `templates/v2/day.schema.json`, χωρίς extra properties. Απαιτεί schema_version=1, status=published, date, timezone, url, created_at, updated_at, input_sha256, lead_story_id, missing_slots, editions, stories και updates.

- editions: 1–3 αναφορές id/type/url/published_at, μόνο σε συμμετέχουσες υπαρκτές δημοσιευμένες εκδόσεις της ίδιας ημερομηνίας.
- stories: μία ανά canonical story_id, first_seen_at, last_substantive_at (nullable), section, priority, selected και references. Κάθε article reference έχει edition_id/article_id/source_story_id/url. Δεν περιέχει αντίγραφα των sections ή ιδιωτικές σημειώσεις.
- updates: id, kind, at, summary, source_urls, story_id (nullable μόνο για enrichment έκδοσης) και origin reference.
- created_at είναι η πραγματική πρώτη δημιουργία του ημερήσιου αρχείου. updated_at είναι η τελευταία πραγματική αλλαγή ημερήσιων inputs, όχι χρόνος πηγής/quote. Διατηρούνται σε byte-identical rerun. CSS αλλαγές αλλάζουν το publication hash/version, χωρίς να βαφτίζονται ειδησεογραφική εξέλιξη.

`new`: τεκμηριωμένη νέα προσθήκη. `substantive_update`: συγκεκριμένο νέο γεγονός με πηγές. `correction`: διόρθωση συντακτικής/πραγματολογικής διατύπωσης χωρίς ισχυρισμό νέου γεγονότος. `enrichment`: φωτογραφία/ανάλυση. `provenance`: απλή συμμετοχή/αναφορά χωρίς απόδειξη novelty. Χωρίς πηγές, new/substantive_update γίνεται provenance. Το schema/validator δεν υποκαθιστά πραγματολογική διασταύρωση.

Τα υπάρχοντα changes με συγκεκριμένο story_id μεταφράζονται: Προσθήκη→new, Εξέλιξη→substantive_update, Διόρθωση→correction, Πλαίσιο→provenance, με τα ελεγμένα sources του άρθρου και ώρα έκδοσης. Changes με null story_id δεν παράγουν ψευδή article badges. Τα image_revision_at/analysis_revision_at δίνουν χωριστό enrichment history. Σε correction badge η «Συντακτική διόρθωση» προηγείται του badge εξέλιξης. Το last_substantive_at δεν αλλάζει από correction/enrichment/hash.

## Τι κάνουν τα actions στην επόμενη συνομιλία

Πρωινό: φρέσκια έρευνα, ρητή σημερινή τοπική date/type=morning, stable IDs, publication gates και υπάρχον build. Δημιουργείται η νέα ημέρα με μόνο πρωινό. Δεν μεταφέρεται σιωπηρά χθεσινή ύλη.

Μεσημεριανό: φρέσκια έρευνα, type=midday, ίδιο story_id όταν πρόκειται για την ίδια ιστορία, explicit documented events μόνο για όσα άλλαξαν. Το build συνθέτει πρωί+μεσημέρι, κρατά διαφορετικές χρήσιμες πρωινές ιστορίες και επιλέγει τον νεότερο published reader για κοινά IDs.

Βραδινό: type=evening, πραγματικοί χρόνοι πηγών/quotes, διαθέσιμα κλεισίματα ξεχωριστά από συνεχιζόμενη US session. Το build συνθέτει όλες τις διαθέσιμες εκδόσεις. Προαιρετικά daily.summary_60s καλύπτει συνολικά την ημέρα και daily.lead_story_id αλλάζει το πρώτο θέμα.

Και τα τρία διατηρούν δημοσιογραφική έρευνα/αθλητικά/εικόνες/αναγνωστικό βάθος. Αγορές και συμπαγείς πίνακες δεν χρειάζονται padding άρθρου. Επαναλαμβάνουν την ίδια διαδρομή build/tests/release/Pages verification/sync, χωρίς δεύτερο scheduler ή AI generator. Μόνο ελεγμένα δημόσια JSON και assets μεταφέρονται από private προς public. Οι νέες οδηγίες σε Markdown δεν εφαρμόζονται αυτόματα σε αποθηκευμένα tasks.

## Migration και όρια

- Ιστορίες επιλέγονται ανά explicit stable ID, όχι fuzzy title matching. Ρητό alias migration ενοποιεί τις δύο ήδη δημοσιευμένες ονομασίες του Ριάντ και την παλιά changes αναφορά στους ηγέτες· historical source IDs και URLs μένουν σταθερά.
- Default priority = 1000 + αρχική συντακτική θέση στην πρώτη έκδοση όπου εμφανίστηκε η ιστορία (πρώτο θέμα στη θέση 0), με ισοπαλίες βάσει stable story_id. Έτσι τα προηγούμενα κεντρικά θέματα διατηρούνται ψηλά. Explicit priority/section επιτρέπει συντακτική αλλαγή. Χωρίς lead πεδίο επιλέγεται το νεότερο πρώτο θέμα, αλλιώς η πρώτη ταξινομημένη ιστορία. Δεν αξιολογεί AI τη σημασία.
- Διατηρούνται όλα τα διαφορετικά θέματα. Η ημέρα 13/10 έχει 26 μοναδικές ιστορίες από 28 άρθρα, με το κοινό κυπριακό πρώτο θέμα και το Ριάντ ενωμένα μόνο ως references.
- Ημερήσια quotes επιλέγονται ανά instrument με τον πραγματικό χρόνο αναφοράς. Cash/futures και διαφορετικά rate tenors δεν συγχωνεύονται. Όταν μία ακριβής ώρα είναι άγνωστη και οι πραγματικές ημερομηνίες quote είναι ίδιες, επιλέγεται η νεότερη συμμετέχουσα έκδοση χωρίς να κατασκευάζεται ώρα. Οι παλιότερες τιμές EUR/USD/Brent παραμένουν με εμφανή πρωινό quote timestamp, χωρίς προσποίηση βραδινής live τιμής.
- Legacy HTML με άγνωστο αρχικό published_at δεν κατασκευάζει ψευδές day model. Όλα τα ιστορικά URLs διατηρούνται. Ημέρες με δομημένα γνωστά timestamps αρχειοθετούνται από τα δικά τους δεδομένα.
- Μερική ημέρα δηλώνει missing_slots· δεν υπάρχει αυτόματη συμπλήρωση.
- Νέα δημοσίευση χωρίς νόμιμη φωτογραφία/depth/reviews αποτυγχάνει. Οι παλιότερες εκδόσεις κρατούν την τεκμηριωμένη legacy compatibility. Δεν παρακάμφθηκαν gates.
- Το build συγκρίνει αποθηκευμένα published_at και απορρίπτει αλλαγή τους σε correction. Δεν αντικαθιστά source/quote timestamps με runtime ώρα.
- Ο loader διατηρεί saved fallback αν δεν είναι διαθέσιμη η νέα HTML, εικόνα ή σωστό hash. Χωρίς JavaScript διαβάζεται ολόκληρη η αποθηκευμένη ημέρα και λειτουργούν native expansions· απαιτείται νέο sync για αλλαγή της saved έκδοσης.
- Το Oracle snapshot συντηρείται με ρητό sync. Δεν προστέθηκε scheduler για sync. Το ήδη υπάρχον browser refresh μπορεί να δείξει νέο public day ακόμη πριν από επόμενο sync.
- Search/bookmarks παραμένουν indexed ανά edition/article, ώστε να μην αλλάζουν τα αποθηκευμένα dated readers.

**Ρητή επιβεβαίωση: τα τρία πραγματικά ChatGPT automations δεν δημιουργήθηκαν, δεν ενημερώθηκαν, δεν απενεργοποιήθηκαν και δεν άλλαξαν. Δεν στάλθηκε Telegram, email ή προσωπικό μήνυμα. Το Wire παραμένει χωριστό και τα ιδιωτικά Markdown/notes δεν δημοσιεύτηκαν.**

## Επαληθευμένη δημοσίευση

Ολοκληρώθηκε πραγματική δημοσίευση και έλεγχος στις 13/10/2026. Όλα τα παρακάτω αποτελέσματα παρατηρήθηκαν, δεν αποτελούν πρόβλεψη CI.

| Repository | Implementation commit | Deployment / CI |
| --- | --- | --- |
| Claude-Briefing | [b04f9183ef004aca85d1d699b8e740bd48db9dee](https://github.com/JoDemon9/Claude-Briefing/commit/b04f9183ef004aca85d1d699b8e740bd48db9dee) | [Pages success](https://github.com/JoDemon9/Claude-Briefing/actions/runs/38451033483), [structured checks success](https://github.com/JoDemon9/Claude-Briefing/actions/runs/38451034201), [served release verification success](https://github.com/JoDemon9/Claude-Briefing/actions/runs/38451133421) |
| oracle-briefing | [0b929ada45b77f24ed4e0d6a908cad127a87593c](https://github.com/JoDemon9/oracle-briefing/commit/0b929ada45b77f24ed4e0d6a908cad127a87593c) | [Pages success](https://github.com/JoDemon9/oracle-briefing/actions/runs/38451366469), [reading checks success](https://github.com/JoDemon9/oracle-briefing/actions/runs/38451368099), [served daily verification success](https://github.com/JoDemon9/oracle-briefing/actions/runs/38451518333) |
| Claude-Briefing-Private | [342eaaabcffc9d8b39b58ebc0d697e1f69bc70ae](https://github.com/JoDemon9/Claude-Briefing-Private/commit/342eaaabcffc9d8b39b58ebc0d697e1f69bc70ae) | [CI success](https://github.com/JoDemon9/Claude-Briefing-Private/actions/runs/38451076161), ιδιωτικό preview μόνο |

Οι ενημερώσεις έγιναν ως πλήρη Git commits με fresh main heads και non-force pushes. Δεν απορρίφθηκε παράλληλη αλλαγή και δεν τροποποιήθηκε το Wire. Ακολουθεί ξεχωριστή τεκμηριωτική ενημέρωση αυτού του handoff, χωρίς μεταβολή των δημοσιευμένων bytes.

- Public release ID: `14f6ca20aa3f6cd75d7edacae2ec060c29cda13cb095d77f6771b7bf1b0bab5b`. Το `release.py --verify-live` επιβεβαίωσε **126 πραγματικά σερβιρισμένα αρχεία**, περιλαμβάνοντας ημερήσιο URL, today/descriptor, όλες τις δημοσιευμένες ανεξάρτητες εκδόσεις, αναλυτικά άρθρα και assets.
- Oracle release ID: `526291edcd3daf5a74c25962f0f3af4d29d2ca75da54640c725a6ddb82cdc1a7`. Το `daily_release.py --verify-live` επιβεβαίωσε **38 πραγματικά σερβιρισμένα αρχεία**, κεντρική πλήρη ημέρα, descriptor, compatibility endpoints και όλα τα αναφερόμενα τοπικά assets.
- Τοπικά unit tests: **57 public + 38 private + 9 Oracle = 104**, όλα επιτυχή. Περιλαμβάνουν τρία slots, ουσιαστική εξέλιξη/ουδέτερη προέλευση, correction/enrichment, idempotence, distinct stories, missing morning/new day/DST, immutable publication times, original quote timestamps, failed image/build/promotion/hash και πλήρες διατηρημένο dataset.
- Τοπικά browser checks: **188 δημόσιας εφημερίδας/readers + 17 κεντρικής ημέρας + 9 ιστορικής πύλης = 214**, όλα επιτυχή. Πλάτη **320/375/390/1440 px**, overflow, πραγματικό decode/naturalWidth/naturalHeight, keyboard/native disclosures, independent active slot, daily participating slots, bookmarks/progress/search/TOC/font/theme, blocked storage, χωρίς JavaScript και fetch/hash/asset failures.
- Πρόσθετα **28 live browser checks** πέρασαν με **85 πραγματικές HTTPS ανακτήσεις** από τα δημόσια Pages. Ελέγχθηκαν και οι δύο ιστοσελίδες, ημερήσια σελίδα, οι τρεις εκδόσεις και reader σε όλα τα πλάτη, τα παλιά pinned reader routes, αναζήτηση/bookmark/font/TOC και live Oracle fallback χωρίς JavaScript και με blocked storage. Οι πραγματικές αποκρίσεις μεταφέρθηκαν μέσω του runtime proxy και της CA trust, χωρίς συνθετικές αποκρίσεις δημοσίευσης.
- Επιθεωρήθηκαν mobile/desktop screenshots του κεντρικού θέματος, μεγάλων καρτών, συμπαγών αγορών και expanded Tech watch. Οι χρόνοι/καταστάσεις είναι ορατοί. Η αρχική οικονομική όψη έχει έως έξι βασικές τιμές και έως τρεις movers· η πλήρης κάλυψη παραμένει στις σαφείς native αναπτύξεις. Τα CI runs παραπάνω διατηρούν τα αντίστοιχα browser artifacts· οι πρόσθετες live εικόνες είναι στο `.work/live-preview/` της τρέχουσας εργασίας.
- Πέρασαν compilation, allowlisted public packaging, reproducible πλήρες rebuild/release και diff whitespace checks. Receipts: public `.work/publication-check.json`, Oracle `.work/daily-publication-check.json`, πρόσθετο `.work/live-browser-check.json` (τοπικά, δεν δημοσιεύουν private στοιχεία).

**Δεν παραμένει εμπόδιο υλοποίησης ή δημοσίευσης. Τα πραγματικά automations παρέμειναν αμετάβλητα.**

## Ενοποιημένη εμφάνιση — 14/10/2026

Η βελτίωση εφαρμόζεται στον κοινό renderer και στο νέο `templates/v2/newspaper-ui.css`, που αντιγράφεται ως `docs/assets/newspaper-ui.css` και συμμετέχει στα versioned asset hashes. Το public build και το `sync_portal.py` μεταφέρουν ολόκληρη την ίδια εμφάνιση στις ανεξάρτητες εκδόσεις, στην εφημερίδα ημέρας και στο αποθηκευμένο Oracle fallback. Το private κρατά τον ίδιο κώδικα και ιδιωτικό preview, χωρίς Pages.

- Κύπρος και διεθνή: τρία άρθρα ανά σειρά από 1100 px, δύο από 700–1099 px, ένα σε κινητό. Οι κάρτες διατηρούν πλήρη περίληψη/ανάλυση, χωρίς line-clamp.
- Συμπαγές πρώτο θέμα: φωτογραφία και λειτουργίες στην ίδια διάταξη, κουμπί χωριστού reader με σωστή αντίθεση και native ανάπτυξη της σύντομης ανάλυσης. Σε κινητό η φωτογραφία ακολουθεί την περίληψη.
- «Τι άλλαξε»: ομοιόμορφες κάρτες με τίτλο αναφοράς, πραγματική ώρα, τύπο ενημέρωσης και πηγές με τα ονόματα των publishers.
- Τεχνολογία, Λεμεσός και ημερολόγιο: κοινά πλαίσια, σαφείς τίτλοι και προσβάσιμες αναπτύξεις πηγών. Χωρίζονται μόνο οι ρητές ημερομηνίες/ώρες που υπάρχουν ήδη στο κείμενο· άγνωστη μορφή παραμένει ακέραιη.
- Οπτικά σημεία αναφοράς: 🇨🇾 Κύπρος, 🌍 διεθνή, 🏆 αθλητικά, 📈 αγορές, 💻 τεχνολογία, 🌦️ καιρός, 📅 ημερολόγιο και ⚡ περίληψη. Τα διακοσμητικά emoji έχουν `aria-hidden=true` και συνοδεύονται πάντα από λεκτικές ετικέτες. Διακριτικά παστέλ χρώματα/επιφάνειες, ημερολογιακές ετικέτες και badges ενισχύουν την οπτική σάρωση σε light/dark, χωρίς να αλλάζουν την τεκμηριωμένη σημασία ενημερώσεων.
- Αγορές, movers και ΕΚΤ/Euribor: συνεπείς μικρές κάρτες και αναπτύξεις. Παραμένουν αρχικά έως έξι βασικές τιμές και έως τρεις movers, με όλα τα υπόλοιπα στοιχεία και metadata διαθέσιμα. Τα fixing/ημερομηνίες ισχύος δεν αντικαθίστανται από ώρα σελίδας.

Η UI δημοσίευση χρησιμοποιεί την πραγματική εφημερίδα **14/10/2026**, με τη διαθέσιμη δημοσιευμένη πρωινή έκδοση και ειλικρινώς μη διαθέσιμα τα υπόλοιπα slots. Δεν μεταβλήθηκαν content JSON, timestamps, εικόνες, άρθρα ή ιστορικά URLs. Δεν έγινε νέα δημοσιογραφική έρευνα. Τα πραγματικά ChatGPT automations και το Wire παρέμειναν αμετάβλητα.

Τοπική επικύρωση: **60 public + 38 private + 9 Oracle unit tests** και **248 public + 25 central + 9 portal browser checks**, όλα επιτυχή. Περιλαμβάνονται πλάτη 320/375/390/1440 px, πραγματικό decode εικόνων, τρεις desktop στήλες, overflow, native/keyboard αναπτύξεις, ορατοί χρόνοι/καταστάσεις, blocked storage, χωρίς JavaScript και διατήρηση πλήρους fallback σε fetch/hash/asset failures. Επιθεωρήθηκαν light/dark mobile/desktop screenshots του lead, των ενημερώσεων, των καρτών, αγορών, επιτοκίων, τεχνολογίας, καιρού και ημερολογίου. Πρόσθετα tests αποδεικνύουν ότι κάθε αρχική παράγραφος, URL πηγής και χρόνος διατηρούνται και ότι αδόμητο ημερολόγιο δεν αποκτά επινοημένη ώρα.

### Πραγματικά αποτελέσματα UI deployment

Η δημοσίευση και οι παρακάτω έλεγχοι ολοκληρώθηκαν στις 14/10/2026:

| Repository | Τελικό UI commit / head | Παρατηρημένο αποτέλεσμα |
| --- | --- | --- |
| Claude-Briefing | [1eddda4a2033c3cdd44ee10dffadf4d999401633](https://github.com/JoDemon9/Claude-Briefing/commit/1eddda4a2033c3cdd44ee10dffadf4d999401633), μετά το κοινό UI [eb3ec26](https://github.com/JoDemon9/Claude-Briefing/commit/eb3ec26b29fdc451e43bf647ac2ebe7ce178e096) | [Pages success](https://github.com/JoDemon9/Claude-Briefing/actions/runs/38533891106), [structured checks success](https://github.com/JoDemon9/Claude-Briefing/actions/runs/38533892156), [served release success](https://github.com/JoDemon9/Claude-Briefing/actions/runs/38533996043) |
| oracle-briefing | [0942e79da41a63eb812c0c26376e77a1dafca881](https://github.com/JoDemon9/oracle-briefing/commit/0942e79da41a63eb812c0c26376e77a1dafca881), περιλαμβάνει το UI [4691308](https://github.com/JoDemon9/oracle-briefing/commit/4691308) | [Pages success](https://github.com/JoDemon9/oracle-briefing/actions/runs/38534173896), [reading checks success](https://github.com/JoDemon9/oracle-briefing/actions/runs/38534174388), [served daily success](https://github.com/JoDemon9/oracle-briefing/actions/runs/38534267535) |
| Claude-Briefing-Private | [b87407b1da5742ac4afb0281bbb85db3a1a849a8](https://github.com/JoDemon9/Claude-Briefing-Private/commit/b87407b1da5742ac4afb0281bbb85db3a1a849a8) | [CI success](https://github.com/JoDemon9/Claude-Briefing-Private/actions/runs/38533831143), private preview χωρίς Pages |

- Public `release.py --verify-live`: **156 πραγματικά σερβιρισμένα αρχεία**, release `a90951adbe657b663da0c8e7956c22db087941d67fe7b7aae46fd7cbf160d12e`.
- Oracle `daily_release.py --verify-live`: **26 πραγματικά σερβιρισμένα αρχεία**, release `4abfc2e637f6ae5ea5da9866a383e0e4b06100082e29828bb82f5ab0762a8c24`.
- Πρόσθετα **39 live browser checks** πέρασαν με **71 πραγματικές HTTPS ανακτήσεις**. Κεντρική Oracle, πραγματική ημερήσια 14/10, today/latest, η νεότερη πραγματική ανεξάρτητη έκδοση κάθε slot και ο επιλεγμένος reader ελέγχθηκαν στα 320/375/390/1440 px. Επιβεβαιώθηκαν τρεις desktop στήλες, εικόνες που αποκωδικοποιούνται, σαφή slots/χρόνοι, keyboard αναπτύξεις, theme, bookmark/font/περιεχόμενα/search, native πλήρες fallback χωρίς JavaScript και blocked storage. Οι αποκρίσεις προήλθαν από πραγματικά Pages μέσω runtime proxy/CA trust, χωρίς συνθετικές δημοσιευμένες αποκρίσεις.
- Επιθεωρήθηκαν τα **live** screenshots στο `.work/ui-live-preview/`, με light/dark κεντρική, τρεις κάρτες, ενημερώσεις, αγορές, καιρό και ημερολόγιο. Receipts: `.work/publication-check.json`, `.work/ui-live-browser-check.json` και Oracle `.work/daily-publication-check.json`.
- Πέρασαν compilation, δημόσια allowlisted εξαγωγή και reproducible build στο CI. Όλες οι ενημερώσεις ήταν non-force. Διατηρήθηκε η παράλληλη διόρθωση UTF-8 [fcb65c2](https://github.com/JoDemon9/oracle-briefing/commit/fcb65c2dda877586a88e323698e497da503e2bfb) με merge και εκ νέου επιτυχή Oracle unit tests. Δεν άλλαξαν content JSON, quote/source timestamps, Wire ή πραγματικά automations.

Κεντρικό live URL: https://jodemon9.github.io/oracle-briefing/ · ημερήσιο URL: https://jodemon9.github.io/Claude-Briefing/daily/2026-10-14.html. Δεν παραμένει εμπόδιο UI υλοποίησης ή δημοσίευσης.

## Frontend με προτεραιότητα στην ανάγνωση — 14/10/2026

Εφαρμόστηκαν οι οκτώ βελτιώσεις της frontend αξιολόγησης στον κοινό renderer: μικρότερη κορυφή/publication bar, lead με μεγαλύτερη φωτογραφία δίπλα στον τίτλο, χαμηλότερες κάρτες με native πλήρη ανάλυση, λιγότερα επαναλαμβανόμενα πλαίσια, συμπαγές χρονολόγιο, καθαρές λεζάντες και συγκεντρωμένο provenance, πλήρες μενού ενοτήτων στο κινητό, σταθερά emoji στις επικεφαλίδες και σαφέστερες αγορές.

Νέο κοινό path: `scripts/v2/newspaper_ui.py`. Καλείται από `build.py` στις ανεξάρτητες εκδόσεις και από `daily.render()` στην ημέρα. Η επανεφαρμογή του είναι idempotent και διατηρεί τη σειρά/ταυτότητα ιστοριών και όλα τα URLs. Το `templates/v2/newspaper-ui.css` αποδίδει τις 3/2/1 στήλες και native disclosures. Το `image()` διατηρεί την πλήρη αρχική λεζάντα, τους συνδέσμους δικαιωμάτων και όλα τα στοιχεία φωτογραφίας. Το `reading.js` κλείνει μενού με Escape/κλικ και ανοίγει το περιεχόμενο για εκτύπωση, επαναφέροντας μετά τις προηγούμενες αναπτύξεις.

Δεν άλλαξε schema, content JSON, μοντέλο σύνθεσης ημέρας, χρόνος δημοσίευσης/πηγής/quote, εικόνα, ιστορικό URL ή εκδοτικό gate. Τα πλήρη newspaper_analysis και οι readers εξακολουθούν να απαιτούν 110–220 και ≥450 λέξεις αντίστοιχα. Η factual περίληψη παραμένει ολόκληρη ορατή. Οι αναπτύξεις λειτουργούν χωρίς JavaScript και δεν χρησιμοποιείται line-clamp. Η ελληνική ημερομηνία και τα time/datetime προέρχονται από τα ρητά editorial inputs. Ο προγραμματισμός παραμένει χωριστός από την πραγματική δημοσίευση.

Τοπικά αποτελέσματα: **62 public + 38 private + 9 Oracle unit tests**, **248 public + 29 central + 9 portal browser checks**, όλα επιτυχή. Τα νέα tests ελέγχουν ακριβή διατήρηση κάθε paragraph/summary/λεζάντας/άδειας, την ταυτότητα των ιστοριών, idempotence, τα πραγματικά publication datetimes, native μενού/πηγές/ανάλυση/credits, μικρή κορυφή, τρεις desktop στήλες και χαμηλότερες κάρτες. Επιθεωρήθηκαν mobile/desktop, light/dark screenshots, μαζί με expanded πηγές/επιτόκια. Πέρασαν compilation, allowlisted package export και whitespace checks.

Τα τρία πραγματικά automations παρέμειναν αμετάβλητα. Οι οδηγίες στα repositories εξηγούν μόνο την παρουσίαση του renderer. Δεν προστέθηκε scheduler/AI backend, δεν στάλθηκαν μηνύματα, δεν άλλαξε η χωριστή λειτουργία Wire και το private παραμένει χωρίς Pages.

### Επαληθευμένο frontend deployment

| Repository | Commit | Πραγματικό αποτέλεσμα |
| --- | --- | --- |
| Claude-Briefing | [26e2ac64a8b75882ea2089975fc6e2d158e22be4](https://github.com/JoDemon9/Claude-Briefing/commit/26e2ac64a8b75882ea2089975fc6e2d158e22be4) | [Pages success](https://github.com/JoDemon9/Claude-Briefing/actions/runs/38540970341), [structured checks success](https://github.com/JoDemon9/Claude-Briefing/actions/runs/38540971247), [served release success](https://github.com/JoDemon9/Claude-Briefing/actions/runs/38541075214) |
| oracle-briefing | [eae07a9c8f4577d397960c728e213e200dd79b6d](https://github.com/JoDemon9/oracle-briefing/commit/eae07a9c8f4577d397960c728e213e200dd79b6d) | [Pages success](https://github.com/JoDemon9/oracle-briefing/actions/runs/38541492927), [reading checks success](https://github.com/JoDemon9/oracle-briefing/actions/runs/38541493284), [served daily success](https://github.com/JoDemon9/oracle-briefing/actions/runs/38541596767) |
| Claude-Briefing-Private | [5f76196fe3773a05e18cd361324eabb920dd7093](https://github.com/JoDemon9/Claude-Briefing-Private/commit/5f76196fe3773a05e18cd361324eabb920dd7093) | [CI success](https://github.com/JoDemon9/Claude-Briefing-Private/actions/runs/38540985326), ιδιωτικό preview χωρίς Pages |

Η πραγματική δημοσίευση χρησιμοποιεί τη διαθέσιμη εφημερίδα 14/10/2026 και την πρωινή συμμετέχουσα έκδοση. Τα midday/evening compatibility URLs οδηγούν στις πραγματικές νεότερες ανεξάρτητες εκδόσεις τους, με τη δική τους ημερομηνία.

- Public live hashes: **156 αρχεία**, release `a542150a13eaa3940fcc66b1a6f684b428f8a02e7554ded8d4f8d28b983e239a`.
- Oracle live hashes: **26 αρχεία**, release `a46cf2b8d86e32fef07dec934bac746e0e668ca6b64e4b7589f3b8f068483620`.
- **43 επιπλέον live browser checks** πέρασαν, με **71 πραγματικές HTTPS ανακτήσεις** μέσω runtime proxy/CA trust, χωρίς συνθετικές δημοσιευμένες αποκρίσεις. Ελέγχθηκαν Oracle, ημερήσιο URL, today/latest, νεότερη πραγματική ανεξάρτητη έκδοση κάθε slot και ο επιλεγμένος reader στα 320/375/390/1440 px. Περιλαμβάνονται native μενού, πλήρης ανάλυση/πηγές/credits, quote times/status, πραγματικό decode, print expansion/restoration, themes, search/bookmark/font/TOC, χωρίς JavaScript και blocked storage.
- Επιθεωρήθηκαν τα live screenshots στο `.work/layout-live-preview/`. Receipt: public `.work/layout-live-browser-check.json`, μαζί με `.work/publication-check.json` και Oracle `.work/daily-publication-check.json`.

Μετρήσεις της ίδιας ύλης και κλειστών αναπτύξεων, πριν/μετά:

| Μέτρηση | Πριν | Μετά |
| --- | --- | --- |
| Θέση πρώτου τίτλου, 375 px | 747 px | 382 px |
| Ύψος πρώτης κάρτας Κύπρου, 375 px | 1682 px | 810 px |
| Ύψος πρώτης κάρτας Κύπρου, 1440 px | 1410 px | 768 px |
| Συνολικό ύψος ημέρας, 375 px | 31830 px | 18608 px |
| Συνολικό ύψος ημέρας, 1440 px | 13099 px | 8820 px |

Η μείωση προήλθε από τη διάταξη/native disclosures και τη συγκέντρωση controls, με μηδενικό diff σε content JSON και αποθηκευμένα μοντέλα ημέρας. Όλο το αρχικό κείμενο/πηγές/metadata παραμένει διαθέσιμο. Οι ενημερώσεις ήταν non-force, με fresh heads, χωρίς αλλαγές Wire ή automations. Δεν παραμένει εμπόδιο υλοποίησης ή δημοσίευσης.
