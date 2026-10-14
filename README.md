# The Oracle Sovereign — Claude-Briefing

Δημόσιες εκδόσεις, ανεξάρτητα άρθρα, renderer v2, αναζήτηση και δημόσιο μητρώο.

**Η παραγωγή γίνεται από scheduled actions μέσα στο ChatGPT.** Οι Gemini/Antigravity generators και οι παλιοί Telegram/daily runners έχουν αφαιρεθεί. Το Wire συλλέγει μόνο RSS χωρίς Telegram.

Ξεκίνα από [AGENTS.md](AGENTS.md) και [OPERATIONS.md](OPERATIONS.md). Η προδιαγραφή και το κοινό prompt συντηρούνται στο [Claude-Briefing](https://github.com/JoDemon9/Claude-Briefing/blob/main/BRIEFING_SPEC.md). Το παλιό audit είναι ιστορικό, δεν περιγράφει ενεργό scheduler.

Τα δημόσια URLs είναι [η εφημερίδα](https://jodemon9.github.io/Claude-Briefing/) και [η πύλη](https://jodemon9.github.io/oracle-briefing/). Το ιδιωτικό docs είναι preview και δεν φιλοξενείται δημόσια.

Οι ανάγκες του χρήστη και οι λόγοι πίσω από τις αλλαγές διατηρούνται στο [DECISIONS.md](DECISIONS.md). Διάβασέ το πριν από νέα διόρθωση. Η [ανασκόπηση εφημερίδας](NEWSPAPER_REVIEW.md) χωρίζει τις προτεινόμενες βελτιώσεις από τις αποδεκτές αποφάσεις και τις πραγματικά δημοσιευμένες αλλαγές.

```sh
python -m pip install -r requirements-v2.txt
python scripts/v2/build.py
python -m unittest discover -s tests -v
python scripts/v2/release.py
```
