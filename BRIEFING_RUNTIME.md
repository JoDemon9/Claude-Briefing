# Oracle Briefing — Runtime v3.1

Το ενιαίο payload παραμένει η είσοδος. Η έρευνα δημιουργεί γεγονότα και συντακτική κρίση· ο compiler αναλαμβάνει διάσπαση, hashes, ακριβή αντιγραφή ελεγμένων WebP και rendering. Ο compiler δεν ανανεώνει timestamps, δεν κατασκευάζει πηγές και δεν εγκρίνει αυτόματα έρευνα. DEC-023 περιλαμβάνει τη διευκρίνιση του χρήστη στις 22/10: μια συνηθισμένη έλλειψη στοιχείου δεν σταματά ολόκληρη την έκδοση.

## Ανεξάρτητες εκδόσεις

| Ώρα Europe/Athens | Mode | Σκοπός |
| --- | --- | --- |
| 07:30 | morning_scan | Οριζόντια σάρωση και πραγματικοί καταλύτες ημέρας |
| 13:30 | midday_delta | Μόνο τεκμηριωμένες αλλαγές από το προηγούμενο στιγμιότυπο |
| 19:30 | evening_synthesis | Σύνθεση ημέρας και επόμενοι έλεγχοι· οι ΗΠΑ μπορεί να είναι ακόμη ανοικτές |

Τα πλήρη αυτοτελή prompts βρίσκονται στα prompts/morning.md, prompts/midday.md, prompts/evening.md. Η εγγραφή τους στο Git δεν ενημερώνει από μόνη της τις πραγματικές Scheduled Tasks. Διατηρούνται οι υπάρχουσες τρεις ώρες/ρυθμίσεις, το μοντέλο, οι προορισμοί και η τέταρτη ιστορική εργασία.

## Συμβόλαιο payload

Ελάχιστα απαιτούνται edition_id, πραγματικά published_at/editorial_completed_at, reading_review version=2 με πραγματικό χρόνο συντακτικής ανασκόπησης και τουλάχιστον ένα άρθρο με διαβασμένη τεκμηρίωση. Το edition_mode προκύπτει μηχανικά από το slot, ή πρέπει να συμφωνεί αν δοθεί. Το section του lead είναι cyprus/world/sports και χωρίζεται από το is_lead. Τα σταθερά IDs δεν προκύπτουν με ασαφή αντιστοίχιση τίτλων.

Τα source records δηλώνουν publisher, url, published_at (ή null), retrieved_at, reporting_group, kind, access και used_for_claims. Μια μη προσβάσιμη πηγή δεν στηρίζει ισχυρισμό. Απουσία επαρκών πηγών αφαιρεί το συγκεκριμένο άρθρο· δεν δημιουργεί URL του ΚΥΠΕ. Αν δεν μείνει κανένα αξιόπιστο άρθρο, η έκδοση αποτυγχάνει πραγματικά.

Προαιρετικά υποβάλλονται executive_scan, daily, markets, sports, panels, opportunities, freshness, selection_review, image_review, changes, market_summary, market_movers, market_core, market_next_event, market_notes, calculator, fast_wire και delta_log. Το scaffold δημιουργεί προσχέδιο χωρίς φρέσκες τιμές ή εικονικούς ελέγχους. Κανένα προηγούμενο edition δεν φορτώνεται σιωπηρά. Αμετάβλητες ευκαιρίες/αθλητικά δεδομένα αντιγράφονται μόνο ρητά με τους αρχικούς χρόνους τους.

Το executive_scan χρησιμοποιεί geopolitics_macro/cyprus_institutions/markets_tech και day_catalysts. Το delta_log αποθηκεύεται αυτούσιο. Τα daily.summary_story_ids συνδέουν πραγματικές ιστορίες· μη διαθέσιμες αναφορές παραλείπονται. Αν λείπει χρήσιμη επισκόπηση, επιλέγονται οι ίδιες οι πραγματικές περιλήψεις των άρθρων με τα ακριβή IDs τους. Δεν εφευρίσκεται συνολική αφήγηση. Τα daily.events δεν δημιουργούνται αυτόματα επειδή παράχθηκε νέα έκδοση.

Οι αναλυτικές ενότητες mechanics_and_incentives/second_order_effects/scenarios εμφανίζονται στις κάρτες, στους readers και στην ημερήσια σελίδα. Χρειάζονται analysis_sources από διαβασμένες πηγές· χωρίς αυτές παραλείπεται η αναλυτική επέκταση και παραμένει το τεκμηριωμένο ρεπορτάζ. Τα scenarios έχουν base_case/tail_risk/watch_next, χωρίς αυθαίρετα ποσοστά ή παρουσίαση πρόβλεψης ως γεγονότος. Το παλιό what_to_watch παραμένει ορατό για συμβατότητα.

## Συνέχιση με μερική διαθεσιμότητα

Οι νέες εκδόσεις από 22/10 έχουν availability_policy=partial-v1 και συγκεκριμένα availability_notes σε disclosure. Δεν εφαρμόζεται αναδρομικά στις αρχειακές εκδόσεις. Οι πέντε διεθνείς και πέντε κυπριακές ιστορίες είναι στόχοι έρευνας, όχι υποχρεωτική παραγωγή filler. Τα ανώτατα όρια και η διακριτή ταυτότητα των ιστοριών διατηρούνται.

| Συνήθης έλλειψη | Συμπεριφορά |
| --- | --- |
| Τιμή αγοράς δεν βρέθηκε | unavailable με null και χωρίς ανακύκλωση προηγούμενης τιμής· παραμένουν και τα 38 instruments |
| Αθλητική πηγή δεν απαντά | unavailable/cached, αρχικός χρόνος τελευταίου ελέγχου, χωριστό attempted_at όταν υπάρχει πραγματική απόπειρα |
| Αποτέλεσμα/fixture χωρίς επαρκή στοιχεία | null για το συγκεκριμένο πεδίο· τα υπόλοιπα της κάρτας παραμένουν |
| Φωτογραφία λείπει ή δεν είναι ελεγμένη | Άρθρο χωρίς εικόνα και με ειλικρινή ένδειξη· ποτέ άσχετη εικόνα ή ψευδές placeholder |
| Πρόγνωση έληξε ή δεν ελέγχθηκε | Δεν εμφανίζεται ως σημερινή πρόγνωση· σημειώνεται η έλλειψη |
| Opportunity χρειάζεται επανέλεγχο | Διατηρούνται verified_at/πηγές, review_due=true, αρχειακή ένδειξη και χωρίς ενεργή προτροπή αίτησης |
| Άρθρο χωρίς διαβασμένη τεκμηρίωση | Παραλείπεται μόνο το άρθρο· συνεχίζει η υπόλοιπη έκδοση |

Πραγματικά blocking errors: κατεστραμμένο ή ασυνεπές JSON/schema, μη ασφαλείς διαδρομές, σύγκρουση IDs/αρχικών χρόνων, μελλοντικοί χρόνοι ελέγχου, μηδέν αξιόπιστα άρθρα, ουσιώδες πρόβλημα browser/integrity, Git divergence/αποτυχημένο push ή μη επαλήθευση του συγκεκριμένου live release. Οι μηχανισμοί δεν καταργούνται για να βαφτίσουν επιτυχημένη μια αποτυχημένη δημοσίευση.

## Φωτογραφίες και αγορές

Το image_selection προσδιορίζει photo_id, reviewed_at, relevance_and_archive_date_checked=true, caption και alt. Τα bytes και τα δικαιώματα ανήκουν στην ίδια εγγραφή του πραγματικού photo-library.json. Καμία αυτόματη keyword επιλογή δεν θεωρείται συντακτική έγκριση. Η αρχική retrieved_at και τα credits διατηρούνται.

Το templates/v2/market-instruments.json περιέχει μόνο τις 38 σταθερές περιγραφές. Δεν περιέχει προηγούμενες τιμές. Κάθε νέα τιμή έχει πραγματικό quoted_at, νόμισμα, μονάδα, session status και πηγές. Το transmission_mechanism υποστηρίζεται στο schema και στο HTML. Κλείσιμο, fixing και ημερομηνία ισχύος δεν συγχέονται με το χρόνο παραγωγής.

## Εκτέλεση και δημοσίευση

```text
python -X utf8 scripts/v2/compose.py --scaffold /tmp/payload.json --edition-id YYYY-MM-DD-morning
# Συμπλήρωση και πραγματική συντακτική ανασκόπηση του ίδιου αρχείου.
python -X utf8 scripts/v2/compose.py --input /tmp/payload.json
```

Η συνήθης ροή υποβάλλει μόνο τον συγκεκριμένο reviewed candidate. Το υπάρχον content-checks CI εκτελεί content, preview και integrity μία φορά, με maintenance units μόνο σε αλλαγές κώδικα/πολιτικής. Το ακριβές artifact/receipt επαναχρησιμοποιείται. Το workflow απαιτεί PORTAL_DEPLOY_TOKEN για πραγματική αυτόνομη προώθηση και αποτυγχάνει καθαρά αν λείπει· το παρόν audit δεν μπορεί να επιβεβαιώσει την τιμή/εγκατάστασή του.

Εναλλακτικά, σε πλήρες local runtime με εξουσιοδότηση:

```text
python -X utf8 scripts/v2/compose.py --input /tmp/payload.json --portal-root <Oracle-checkout> --publish
```

Η εντολή καλεί τον resumable publish.py, ελέγχει branch/remote/allowlist, χρησιμοποιεί worktree από fresh main, επαληθεύει πραγματικά source Pages πριν από Oracle sync και επαληθεύει το Oracle release. Υπάρχει περιορισμένη επανάληψη για διάδοση CDN και συγκεκριμένα I/O timeouts. Αποτυχία αφήνει checkpoint και την τελευταία καλή έκδοση. Δεν υπάρχει ORACLE_SKIP_LIVE_POLL που να δηλώνει ψευδώς verified. Το quick_validate.py ελέγχει μόνο JSON/αναφορές και δεν αντικαθιστά αυτά τα gates. Χωρίς Playwright δεν δηλώνεται passing browser preview.

Δεν ενεργοποιείται private Pages, δεν εξάγονται ιδιωτικές σημειώσεις/caches και δεν αλλάζει ο ανεξάρτητος Wire ή το πρόγραμμα παραγωγής. Main, PR, CI, Pages και πραγματικά Scheduled Tasks αναφέρονται χωριστά.

Compatibility invariants: preserve original source/quote times and unchanged historical snapshots. No fuzzy automatic story matching. No arbitrary quota/time limit for editorial generation; I/O deadlines bound failed operations separately. No PR merge in scheduled runs. image_review.version=2 records actual reviewed photographs; the explicit partial-v1 unavailable-image path is permitted from 22 October.

Το CI push με GITHUB_TOKEN δεν ενεργοποιεί αυτόματα Pages: ο publisher ζητά ρητά το source Pages build με pages:write και περιμένει έως 10 λεπτά για φυσιολογική διάδοση, πριν δηλώσει πραγματική αποτυχία. Το portal PAT push διατηρεί το κανονικό trigger. Δεν δημιουργείται νέος scheduler ή νέα εξωτερική ειδοποίηση.


## DEC-024 — authoring and reading contract

Fresh capabilities advertise authoring_formats=[json, oracle-markdown/1]. compose.py --input accepts one .json or .md file and emits the same validated canonical records. See MARKDOWN_AUTHORING.md. New candidates use intelligence_contract=1; shared validation enforces mode/slot and the complete instrument inventory across input routes.

Use the bounded context_view/prepare_run baseline (edition_id, fingerprint). Explicit baseline plus carry_story_ids copies only selected unchanged stories with original times and rights. Baseline mismatch, unsafe identity and conflicting carry/write instructions block composition. No implicit inheritance of prices, weather, opportunities or sports checks. Planning digests are navigation; read real evidence for new/material/due claims.

Driver tags are normalized ASCII labels. change_status is NEW, UPDATED, REVERSAL, CORRECTION, UNCHANGED or UNKNOWN. Changed statuses require a factual delta; UNCHANGED requires baseline provenance. Use facts, mechanisms, incentives, effects, supported scenarios and measurable watches where they add intelligence; do not force analysis into routine notices. analysis_sources must reference actual read article evidence. Scenarios add optional alternative_case/alternative_label; watch_next remains independent.

Standard shows complete facts; Full opens depth; Executive uses existing synthesis and compact market data. Tabs, tags and filters are enhancements; no-JS and print retain the complete report. Delta identifies its comparison edition and reports unclassified material. Historic snapshots keep their accepted content contracts.

Role-specific ORACLE_PUBLIC_PUSH_TOKEN / ORACLE_PORTAL_PUSH_TOKEN support temporary worktrees. Both routes are preflighted before promotion. The portal companion must support snapshot-objects before the new source sync is deployed. Verify actual Pages bytes on both sites; do not label PR CI as publication.
