# The Oracle Sovereign

Ελληνική στατική εφημερίδα και δημόσιο αρχείο στο [Claude-Briefing](https://jodemon9.github.io/Claude-Briefing/). Η [κεντρική πύλη](https://jodemon9.github.io/oracle-briefing/) παραμένει στο `oracle-briefing`. Το GitHub Pages δημοσιεύει αποκλειστικά `main:/docs`.

Η ενεργή παραγωγή περιγράφεται στο [BRIEFING_SPEC.md](BRIEFING_SPEC.md). Τα άρθρα αποθηκεύονται ανεξάρτητα στο `content/articles`, οι εκδόσεις στο `content/editions`, και ο renderer v2 παράγει ιστορικές σελίδες, μεταδεδομένα και αναζήτηση. Οι αρχικές εκδόσεις παραμένουν προσβάσιμες στις παλιές διευθύνσεις.

```sh
python -m pip install -r requirements-v2.txt
python scripts/v2/build.py
python -m unittest discover -s tests -v
python tests/browser_checks.py
python scripts/v2/sync_portal.py --portal-root ../oracle-briefing
```

Τα τρία ChatGPT tasks διαχειρίζονται εκτός repository. Οι ακριβείς αντικαταστάσεις των prompts βρίσκονται στο [CHATGPT_TASK_INSTRUCTIONS.md](CHATGPT_TASK_INSTRUCTIONS.md). Δεν εγκαθιστούμε scheduler ή backend. Δεν εκτελούμε legacy Gemini/Antigravity, catch-up generation ή Telegram delivery. Τα παλαιά scripts είναι ιστορικά βοηθήματα· το `build-html.py` χρησιμοποιεί v2 και απαιτεί ρητή `--legacy` για ιστορική μεταφορά.

Τα ιδιωτικά Markdown και οι ερευνητικές σημειώσεις ανήκουν στο `Claude-Briefing-Private`. Ο renderer δεν αντιγράφει ιδιωτικά Markdown στο δημόσιο `docs`.
