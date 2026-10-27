DEC-024: The user approved the Phase 1 architectural assessment and its Phase 2 checklist. Extend the existing compiler instead of replacing the renderer/publisher. Keep JSON as the canonical public model; pilot versioned Markdown as an authoring adapter. No HTML/CSS is written by the producer. Do not claim a 75% saving or treat byte counts as tokens or account quota. See decisions/DEC-024-intelligence-authoring-and-reading.md and MARKDOWN_AUTHORING.md. Actual live task installation and publication are separate.

# Oracle — Οδηγίες Scheduled Tasks v3.1

Τα τρία αυτοτελή prompts προς αντιγραφή στα υπάρχοντα ChatGPT Scheduled Tasks είναι:

- [Morning 07:30](prompts/morning.md), mode morning_scan.
- [Midday 13:30](prompts/midday.md), mode midday_delta.
- [Evening 19:30](prompts/evening.md), mode evening_synthesis.

Η ζώνη παραμένει Europe/Athens. Διατηρούνται τίτλοι/ώρες/enabled states/προορισμοί/μοντέλο και η τέταρτη ιστορική εργασία. Αλλαγή στο Git δεν ενημερώνει την πραγματική ρύθμιση task· χρειάζεται ξεχωριστή αποθήκευση και ανάγνωση της αποθηκευμένης ρύθμισης. Το παρόν audit παραδίδει τα prompts, δεν ισχυρίζεται ότι τα εγκατέστησε.

Οι έξι κινήσεις είναι: προετοιμασία πραγματικού main, πραγματική έρευνα, ένα payload, μία συντακτική ανασκόπηση, σύνθεση/υποβολή συγκεκριμένου candidate, παρακολούθηση πραγματικού αποτελέσματος και συγκεκριμένων κενών. Δεν απαιτείται χειροκίνητη γραφή hashes ή δώδεκα JSON. Ο compiler δεν ανακυκλώνει τιμές/προγνώσεις/ελέγχους από προηγούμενη έκδοση.

Η διευκρίνιση του χρήστη στις 22/10 υπερισχύει της καθολικής διακοπής για ελλείψεις: η προσωρινή απουσία μιας πηγής, τιμής, φωτογραφίας ή επαρκών νέων ειδήσεων περιορίζει μόνο το στοιχείο. Η έκδοση συνεχίζει με το αξιόπιστο υλικό. Δεν κατασκευάζονται υποκατάστατα. Πραγματικό stop παραμένουν η ασφάλεια/συνέπεια των αρχείων, η απουσία οποιουδήποτε τεκμηριωμένου άρθρου και η αποτυχία πραγματικών ελέγχων ή δημοσίευσης.

Το αναλυτικό συμβόλαιο δεδομένων, η μερική διαθεσιμότητα και οι δύο εναλλακτικές διαδρομές δημοσίευσης περιγράφονται στο [BRIEFING_RUNTIME.md](BRIEFING_RUNTIME.md). Η συνήθης παραγωγή δεν κάνει maintenance ή merge PR για να περάσει μια έκδοση.
