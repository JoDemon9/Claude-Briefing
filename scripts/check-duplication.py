import sys
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

filename = sys.argv[1] if len(sys.argv) > 1 else 'docs/index.html'
try:
    with open(filename, 'r', encoding='utf-8') as f:
        html = f.read()
except Exception as e:
    print(f"Error reading {filename}: {e}")
    sys.exit(1)

def strip(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s)).strip().lower()

cards = html.split('<article')[1:]
problems = []

for i, card in enumerate(cards):
    det_match = re.search(r'<details[\s\S]*?</details>', card)
    if not det_match:
        continue
    hidden = strip(det_match.group(0))
    visible = strip(card.replace(det_match.group(0), ''))
    hid_words = set(w for w in hidden.split(' ') if len(w) > 4)
    if not hid_words:
        continue
    shared = sum(1 for w in hid_words if w in visible)
    overlap = shared / len(hid_words)
    if overlap > 0.5:
        problems.append(f"Κάρτα #{i + 1}: επικάλυψη {overlap * 100:.0f}%")

if problems:
    print("Το αναπτυσσόμενο μπλοκ επαναλαμβάνει το ορατό κείμενο:\n" + "\n".join(problems))
    sys.exit(1)

print("Έλεγχος επανάληψης: καθαρό.")
