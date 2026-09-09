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


def fail(message):
    """Abort the run loudly rather than writing a made-up edition."""
    print(f"\nFATAL: {message}", file=sys.stderr)
    sys.exit(1)


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
    """Live Limassol reading, or None. Never a stand-in number: a fabricated
    temperature is indistinguishable from a measured one once published."""
    try:
        url = ("https://api.open-meteo.com/v1/forecast?latitude=34.68&longitude=33.04"
               "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,uv_index"
               "&timezone=auto")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode('utf-8'))
            curr = data.get('current', {})
            if curr.get('temperature_2m') is None:
                print("Weather: Open-Meteo returned no current reading.")
                return None
            return {
                'temp': round(curr['temperature_2m']),
                'humidity': curr.get('relative_humidity_2m'),
                'wind': round(curr['wind_speed_10m']) if curr.get('wind_speed_10m') is not None else None,
                'uv': round(curr['uv_index']) if curr.get('uv_index') is not None else None,
            }
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None


def generate_with_gemini(api_key, cy_items, world_items, wx_info, today_str):
    try:
        if wx_info:
            weather_line = (f"Καιρός Λεμεσού (μέτρηση Open-Meteo): {wx_info['temp']}°C, "
                            f"Υγρασία {wx_info['humidity']}%, Άνεμος {wx_info['wind']} km/h, "
                            f"UV {wx_info['uv']}.")
        else:
            weather_line = ("Καιρός Λεμεσού: ΔΕΝ ΥΠΑΡΧΕΙ ΜΕΤΡΗΣΗ. Παράλειψε εντελώς "
                            "την ενότητα ΚΑΙΡΟΣ — μην εφεύρεις τιμές.")

        prompt = f"""Είσαι ο αρχισυντάκτης του «THE ORACLE SOVEREIGN», ενός αυστηρά εμπιστευτικού ημερήσιου briefing για επιφανή αναγνώστη στη Λεμεσό της Κύπρου.
Ημερομηνία: {today_str}.
{weather_line}

ΑΠΑΡΑΒΑΤΟΣ ΚΑΝΟΝΑΣ: μην εφεύρεις ποτέ γεγονός, αριθμό ή URL. Χρησιμοποίησε
μόνο όσα δίνονται παρακάτω ή όσα μπορείς να τεκμηριώσεις. Τιμές αγορών,
επιτόκια, αθλητικά αποτελέσματα και σημειώσεις χαρτοφυλακίου ΔΕΝ δίνονται εδώ:
παρέλειψε ολόκληρη την αντίστοιχη ενότητα αντί να συμπληρώσεις εικαζόμενα
νούμερα. Κάθε σύνδεσμος πρέπει να προέρχεται αυτούσιος από τη λίστα ειδήσεων.

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

    if not cy_items and not world_items:
        fail("No RSS items could be fetched — refusing to write an edition with "
             "no sourced material.")

    api_key = env_vars.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY')
    if not api_key:
        fail("GEMINI_API_KEY is not set. There is no non-model path that can "
             "honestly produce an edition: the previous RSS 'fallback' invented "
             "market prices, Euribor rows, sports fixtures, portfolio notes and "
             "deadlines. Author the edition instead, or set the key.")

    print("Synthesizing briefing via Gemini 2.0 Flash...")
    md_content = generate_with_gemini(api_key, cy_items, world_items, wx_info, today_str)
    if not md_content:
        fail("Gemini returned no briefing. Nothing was written.")

    os.makedirs(BRIEFINGS_DIR, exist_ok=True)
    with open(target_md, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"Created: {target_md}")
    print("NOTE: this is a draft. Every number, quote and URL must be verified "
          "against its source before the edition is built and published.")
    return target_md


if __name__ == '__main__':
    main()
