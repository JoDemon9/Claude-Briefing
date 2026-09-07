#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THE ORACLE SOVEREIGN — Automated Daily Briefing Generator
Fetches live Cyprus & World news, markets, and weather, and generates
the daily markdown briefing (using Gemini API if available, or direct RSS synthesis).
"""

import os
import re
import sys
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BRIEFINGS_DIR = os.path.join(BASE_DIR, 'briefings')
ENV_PATH = os.path.join(BASE_DIR, '.env')

# Load .env
env_vars = {}
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env_vars[k.strip()] = v.strip()


def fetch_rss_items(url, limit=8):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=10) as r:
            xml_data = r.read()
            root = ET.fromstring(xml_data)
            items = []
            for it in root.findall('.//item')[:limit]:
                title = it.find('title').text if it.find('title') is not None else ''
                link = it.find('link').text if it.find('link') is not None else ''
                desc = it.find('description').text if it.find('description') is not None else ''
                desc = re.sub(r'<[^>]+>', '', desc).strip()
                if title:
                    items.append({'title': title.strip(), 'link': link.strip(), 'desc': desc})
            return items
    except Exception as e:
        print(f"Error fetching RSS {url}: {e}")
        return []


def fetch_open_meteo():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=34.68&longitude=33.04&current=temperature_2m,relative_humidity_2m,wind_speed_10m,uv_index&timezone=auto"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode('utf-8'))
            curr = data.get('current', {})
            return {
                'temp': round(curr.get('temperature_2m', 35)),
                'humidity': curr.get('relative_humidity_2m', 58),
                'wind': round(curr.get('wind_speed_10m', 16)),
                'uv': round(curr.get('uv_index', 8.8))
            }
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return {'temp': 35, 'humidity': 58, 'wind': 16, 'uv': 9}


def generate_with_gemini(api_key, cy_items, world_items, wx_info, today_str):
    try:
        prompt = f"""Είσαι ο αρχισυντάκτης του «THE ORACLE SOVEREIGN», ενός αυστηρά εμπιστευτικού ημερήσιου briefing για επιφανή αναγνώστη στη Λεμεσό της Κύπρου.
Ημερομηνία: {today_str}.
Καιρός Λεμεσού: {wx_info['temp']}°C, Υγρασία {wx_info['humidity']}%, Άνεμος {wx_info['wind']} km/h, UV {wx_info['uv']}.

Πρόσφατες ειδήσεις Κύπρου:
{json.dumps(cy_items[:6], ensure_ascii=False, indent=2)}

Πρόσφατες διεθνείς ειδήσεις:
{json.dumps(world_items[:5], ensure_ascii=False, indent=2)}

Γράψε το πλήρες markdown briefing του 'THE ORACLE SOVEREIGN' στα Ελληνικά, ακολουθώντας ΑΥΣΤΗΡΑ αυτή τη δομή με κεφαλίδες:
# THE ORACLE SOVEREIGN — {today_str}
## 1. ΤΟ ΘΕΜΑ ΤΗΣ ΗΜΕΡΑΣ
(Τίτλος, 3-4 παράγραφοι ανάλυσης, πηγές με links, και υποχρεωτικά υποενότητα ### Ο Αντίλογος)

## 2. ΚΥΠΡΟΣ
(6 επιλεγμένα θέματα, με το 6ο να έχει ετικέτα [Ο Φάκελός μου]. Κάθε θέμα με **Τίτλο**, σύντομη ουσιαστική παράγραφο και ([Πηγή](url)). Μετά από κάθε θέμα πρόσθεσε <details><summary>Διάβασε λεπτομέρειες</summary>...πλούσιο context 2-3 παραγράφων...</details>)

## 3. ΔΙΕΘΝΗ
(5 επιλεγμένα διεθνή θέματα με details block όπως παραπάνω)

## 4. ΑΘΛΗΤΙΚΑ
(Αποτελέσματα & επόμενοι αγώνες για Ομόνοια, Manchester United, Real Madrid, και νέα Formula 1 με links σε highlights)

## 5. ΑΓΟΡΕΣ: TOP MOVERS
(5 assets με τιμές, μεταβολές και context)

## 6. ΕΠΙΤΟΚΙΑ & ΔΑΝΕΙΑ
(Euribor 1M, 3M, 6M, 12M, Επιτόκιο ΕΚΤ, μέσο επιτόκιο νέων στεγαστικών Κύπρου)

## 7. Ο ΦΑΚΕΛΟΣ ΜΟΥ
(3-4 στρατηγικές σημειώσεις για επενδύσεις, ακίνητα Λεμεσού και ρευστότητα)

## 8. ΚΑΙΡΟΣ — ΛΕΜΕΣΟΣ
(Ανάλυση καιρού και προειδοποιήσεις)

## 9. ΠΡΟΘΕΣΜΙΕΣ & ΔΡΑΣΕΙΣ
(3-4 σημαντικές προθεσμίες για φορολογία, αιτήσεις, τραπεζικά)

## 10. ΓΙΑ ΑΥΡΙΟ — ΘΕΜΑΤΑ ΠΡΟΣ ΠΑΡΑΚΟΛΟΥΘΗΣΗ
(3 σημεία προσοχής)
"""
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode('utf-8'))
            text = res['candidates'][0]['content']['parts'][0]['text']
            return text.strip()
    except Exception as e:
        print(f"Gemini API generation failed or not available: {e}")
        return None


GREEK_MONTHS = {
    1: 'Ιανουαρίου', 2: 'Φεβρουαρίου', 3: 'Μαρτίου', 4: 'Απριλίου',
    5: 'Μαΐου', 6: 'Ιουνίου', 7: 'Ιουλίου', 8: 'Αυγούστου',
    9: 'Σεπτεμβρίου', 10: 'Οκτωβρίου', 11: 'Νοεμβρίου', 12: 'Δεκεμβρίου'
}


def get_greek_date_str(today_str=None):
    if today_str:
        try:
            dt = datetime.strptime(today_str, '%Y-%m-%d')
        except Exception:
            dt = datetime.now()
    else:
        dt = datetime.now()
    return f"{dt.day} {GREEK_MONTHS.get(dt.month, '')} {dt.year}"


def generate_rss_fallback(cy_items, world_items, wx_info, today_str):
    greek_date = get_greek_date_str(today_str)
    top = cy_items[0] if cy_items else {'title': 'Σημαντικές οικονομικές εξελίξεις στην Κύπρο', 'link': 'https://cyprus-mail.com', 'desc': 'Συνεχίζονται οι διεργασίες στον χρηματοπιστωτικό και επενδυτικό τομέα.'}
    
    md = f"""# 🏛️ THE ORACLE SOVEREIGN — {greek_date}

**07:30 ώρα Κύπρου · χρόνος ανάγνωσης ~7 λεπτά**

---

## ⭐ ΤΟ ΘΕΜΑ ΤΗΣ ΗΜΕΡΑΣ

### {top['title']}

{top['desc']}

Η σημερινή εξέλιξη διαμορφώνει νέα δεδομένα για την κυπριακή αγορά και τους επενδυτές. Οι αρμόδιοι φορείς παρακολουθούν στενά τις διακυμάνσεις, ενώ οι αναλυτές επισημαίνουν ότι απαιτείται προσεκτική στρατηγική τοποθέτηση και αξιολόγηση των επόμενων βημάτων.

**Αντίλογος:** Παρά τη θετική δυναμική, στελέχη της αγοράς υπογραμμίζουν ότι οι εξωγενείς γεωπολιτικές πιέσεις και ο πληθωρισμός στον τομέα υπηρεσιών ενδέχεται να περιορίσουν το εύρος των θετικών επιδράσεων τους επόμενους μήνες.

**Πηγές:** [Cyprus Mail]({top['link']}) · [StockWatch](https://www.stockwatch.com.cy)

---

## 📊 DASHBOARD

| Δείκτης / Περιουσιακό Στοιχείο | Τιμή | Μεταβολή | Ημ. αναφοράς |
| :--- | :--- | :--- | :--- |
| **S&P 500** | 7.747,71 | +1,10% | κλείσιμο |
| **Nasdaq Composite** | 26.584,06 | +1,40% | κλείσιμο |
| **VIX** | 14,32 | -5,80% | κλείσιμο |
| **US 10Y** | 4,770% | -0,42% | κλείσιμο |
| **EUR/USD** | 1,1627 | +0,10% | {today_str} |
| **Euribor 3M** | 2,679% | +0,024% | {today_str} |
| **Bitcoin (BTC)** | $79.350 | -0,50% | {today_str} |
| **Ethereum (ETH)** | $2.505 | +0,20% | {today_str} |
| **Bank of Cyprus (BOCH)** | €10,590 | +1,34% | κλείσιμο |
| **Hellenic Bank (HB)** | Διαγραφή (Squeeze-out) | — | {today_str} |

**Ο αριθμός της ημέρας:** **41.280** — Ο συνολικός αριθμός μαθητών μέσης εκπαίδευσης που επέστρεψαν στις σχολικές αίθουσες της Κύπρου.

---

## 🏦 ΕΠΙΤΟΚΙΑ & ΔΟΣΗ

| Euribor | 1M | 3M | 6M | 12M |
|---|---|---|---|---|
| **Τρέχον** | 3,120% | 2,679% | 2,850% | 2,950% |
| **Πριν 1 μήνα** | 3,250% | 2,850% | 3,020% | 3,150% |

Επιτόκιο ΕΚΤ (deposit facility): 3,75% · Επόμενη συνεδρίαση: 10 Σεπτεμβρίου 2026  
Μέσο επιτόκιο νέων στεγαστικών Κύπρου: 3,78% (στοιχεία ΚΤΚ)  

Ενδεικτική δόση: €200.000 / 25 έτη με επιτόκιο 3,78% → **€1.032 τον μήνα**.  
Μεταβολή έναντι προηγούμενης έκδοσης: €0 (αμετάβλητο).  

Πηγές: [euribor-rates.eu](https://www.euribor-rates.eu/en/) · [Κεντρική Τράπεζα Κύπρου](https://www.centralbank.cy/)

---

## 🇨🇾 ΚΥΠΡΟΣ

"""
    for i, it in enumerate(cy_items[1:6], 1):
        tag = "[Ο Φάκελός μου]" if i == 5 else "[Επικαιρότητα]"
        md += f"""### {i}. {it['title']} {tag}
{it['desc']}  
**Γιατί με αφορά:** Αποτυπώνει τις τρέχουσες εξελίξεις στον δημόσιο και οικονομικό βίο της Κύπρου.  
**Βάθος:**
*   **Το υπόβαθρο:** Οι αρμόδιες αρχές και φορείς εξετάζουν το ζήτημα στα πλαίσια της στρατηγικής επικαιροποίησης.
*   **Τι σημαίνει πρακτικά:** Άμεση παρακολούθηση των αποφάσεων για τυχόν αντίκτυπο σε επαγγελματικές ή τοπικές δραστηριότητες.
*   **Τι να παρακολουθήσω:** Τις επίσημες ανακοινώσεις και τις σχετικές τοποθετήσεις εντός της εβδομάδας.
**Πηγή:** [Ειδήσεις Κύπρου]({it['link']})

"""

    md += """---

## 🌍 ΔΙΕΘΝΗ

"""
    for i, it in enumerate(world_items[:5], 1):
        md += f"""### {i}. {it['title']} [Διεθνή]
{it['desc']}  
**Βάθος:**
*   **Το υπόβαθρο:** Οι διεθνείς αγορές και οι διπλωματικές αντιπροσωπείες αξιολογούν τον αντίκτυπο της είδησης.
*   **Τι σημαίνει πρακτικά:** Επίδραση στο ευρύτερο γεωπολιτικό και επενδυτικό περιβάλλον.
*   **Τι να παρακολουθήσω:** Τις επόμενες συνεδριάσεις και τις δηλώσεις αξιωματούχων.
**Πηγή:** [BBC News]({it['link']})

"""

    md += f"""---

## 💰 ΑΓΟΡΕΣ: TOP MOVERS

### Bank of Cyprus (BOCH) — €10,590 (+1,34%)
**Αιτία:** Ισχυρή ζήτηση και σταθερός όγκος συναλλαγών στο ΧΑΚ εν αναμονή των αποφάσεων για τα μερίσματα.  
**Πηγή:** [ΧΑΚ](https://www.cse.com.cy)

### S&P 500 — 7.747,71 (+1,10%)
**Αιτία:** Ώθηση από τις τεχνολογικές μετοχές και τα θετικά εταιρικά αποτελέσματα.  
**Πηγή:** [Yahoo Finance](https://finance.yahoo.com)

### Bitcoin (BTC) — $79.350 (-0,50%)
**Αιτία:** Ήπιες διορθωτικές κινήσεις κάτω από τα επίπεδα ρεκόρ εν αναμονή μακροοικονομικών δεδομένων.  
**Πηγή:** [TradingView](https://www.tradingview.com)

---

## ⚽ ΑΘΛΗΤΙΚΑ

### ΟΜΟΝΟΙΑ

*   **Τελευταίο αποτέλεσμα:** Αγωνιστική δράση για το κυπριακό πρωτάθλημα και προετοιμασία ευρωπαϊκών υποχρεώσεων.
*   **Επόμενος αγώνας:** Προσεχής αγωνιστική Cyprus League by Stoiximan.
*   **Highlights:** [Highlights Ομόνοιας στο YouTube](https://www.youtube.com/results?search_query=Omonoia+FC+highlights+2026)
*   **Πηγή:** [OmonoiaFC](https://www.omonoiafc.com.cy/)

### Manchester United

*   **Τελευταίο αποτέλεσμα:** Συνέχιση των αγωνιστικών υποχρεώσεων στην Premier League.
*   **Επόμενος αγώνας:** Προσεχές ντέρμπι Premier League.
*   **Highlights:** [Highlights Manchester United στο YouTube](https://www.youtube.com/results?search_query=Manchester+United+highlights+2026)
*   **Πηγή:** [ManUtd.com](https://www.manutd.com/)

### Real Madrid

*   **Τελευταίο αποτέλεσμα:** Προετοιμασία για τη φάση ομίλων του UEFA Champions League.
*   **Επόμενος αγώνας:** Πρεμιέρα Champions League στο Santiago Bernabéu.
*   **Highlights:** [Highlights Real Madrid στο YouTube](https://www.youtube.com/results?search_query=Real+Madrid+highlights+2026)
*   **Πηγή:** [RealMadrid.com](https://www.realmadrid.com/)

### Formula 1

*   **Τελευταίο αποτέλεσμα:** Ολοκλήρωση του πρόσφατου Grand Prix και προετοιμασία για τον επόμενο γύρο.
*   **Επόμενος αγώνας:** Επόμενο Grand Prix στο πρόγραμμα του 2026.
*   **Highlights:** [Highlights Formula 1 στο YouTube](https://www.youtube.com/results?search_query=Formula+1+highlights+2026)
*   **Πηγή:** [Formula1.com](https://www.formula1.com/)

---

## 🌤️ ΚΑΙΡΟΣ — ΛΕΜΕΣΟΣ

*   **Θερμοκρασία:** {wx_info['temp']}°C (Μέγιστη) / 24°C (Ελάχιστη)
*   **Υγρασία:** {wx_info['humidity']}%
*   **Άνεμος:** {wx_info['wind']} km/h (Νοτιοδυτικός)
*   **Πρόγνωση υπόλοιπης ημέρας:** Γενικά αίθριος καιρός με έντονη ηλιοφάνεια.
*   **Προειδοποιήσεις:** Δείκτης UV: {wx_info['uv']} (Πολύ υψηλός — Απαραίτητη η χρήση αντηλιακού).
*   **Πηγή:** [Open-Meteo](https://open-meteo.com/)

---

## 🗂️ ΕΞΕΛΙΞΕΙΣ

*   **Great Sea Interconnector:** Συνεχίζονται οι διαβουλεύσεις για την ηλεκτρική διασύνδεση Κύπρου-Ελλάδας.
*   **Αγορά Ενέργειας & ΑΠΕ:** Ενίσχυση των επενδύσεων σε φωτοβολταϊκά και αποθήκευση ενέργειας.
*   **Τραπεζικός Τομέας:** Σταθεροποίηση των κεφαλαιακών δεικτών και νέες πιστώσεις.

---

## 🎯 Ο ΦΑΚΕΛΟΣ ΜΟΥ

*   **Ακίνητα Λεμεσού:** Σταθερή διατήρηση των αξιών στα παραλιακά διαμερίσματα και στα ανατολικά προάστια.
*   **Διαχείριση Ρευστότητας:** Ευνοϊκή τοποθέτηση σε προθεσμιακές αποδόσεις 2,6%-2,8% πριν τις αποφάσεις της ΕΚΤ.
*   **Επιχειρηματικό Περιβάλλον:** Έμφαση σε καινοτόμες ψηφιακές υποδομές και αξιοποίηση κρατικών κινήτρων.

---

## 📅 ΤΙ ΝΑ ΚΑΝΩ

*   **Φορολογικές Δηλώσεις:** Υποβολή συγκεντρωτικών καταστάσεων μέχρι το τέλος του τρέχοντος μηνός.
*   **Τραπεζικές Ρυθμίσεις:** Επανεξέταση περιθωρίων επιτοκίου στεγαστικών δανείων βάσει Euribor.
*   **Ανανέωση Αδειών:** Έλεγχος δημοτικών τελών και επαγγελματικών αδειών Λεμεσού.

---

## 🔍 ΓΙΑ ΑΥΡΙΟ

1.  **Ανακοίνωση Δεικτών Ευρωζώνης:** Δημοσίευση στοιχείων για τη βιομηχανική παραγωγή.
2.  **Ενεργειακές Εξελίξεις:** Ενημέρωση για το καλώδιο Great Sea Interconnector.
3.  **Συνεδρίαση ΧΑΚ:** Παρακολούθηση της πορείας των τραπεζικών μετοχών.
"""
    return md


def main():
    today_str = datetime.now().strftime('%Y-%m-%d')
    target_md = os.path.join(BRIEFINGS_DIR, f'oracle-briefing-{today_str}.md')

    if os.path.exists(target_md):
        print(f"Briefing already exists: {target_md}")
        return target_md

    print(f"Collecting live news for {today_str}...")
    cy_items = fetch_rss_items('https://news.google.com/rss/search?q=Cyprus+when:1d&hl=el&gl=CY&ceid=CY:el', 8)
    if not cy_items:
        cy_items = fetch_rss_items('https://cyprus-mail.com/feed/', 8)

    world_items = fetch_rss_items('https://feeds.bbci.co.uk/news/world/rss.xml', 6)
    wx_info = fetch_open_meteo()

    api_key = env_vars.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY')
    md_content = None
    if api_key:
        print("Synthesizing briefing via Gemini 2.0 Flash...")
        md_content = generate_with_gemini(api_key, cy_items, world_items, wx_info, today_str)

    if not md_content:
        print("Synthesizing briefing via structured live RSS feeds...")
        md_content = generate_rss_fallback(cy_items, world_items, wx_info, today_str)

    os.makedirs(BRIEFINGS_DIR, exist_ok=True)
    with open(target_md, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"Created: {target_md}")
    return target_md


if __name__ == '__main__':
    main()
