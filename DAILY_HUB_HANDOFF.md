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
- Οι ακριβείς τελικοί implementation commits, deployment αποτελέσματα και receipt IDs καταγράφονται στην ενότητα «Επαληθευμένη δημοσίευση» μετά το πραγματικό Pages deployment.

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
- Default ordering κρατά σειρά πρώτης εμφάνισης· explicit priority/section επιτρέπει συντακτική αλλαγή. Χωρίς lead πεδίο επιλέγεται το νεότερο πρώτο θέμα, αλλιώς η πρώτη ταξινομημένη ιστορία. Δεν αξιολογεί AI τη σημασία.
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

Θα συμπληρωθεί με τους πραγματικούς ελέγχους live bytes μετά τη δημοσίευση της υλοποίησης.
