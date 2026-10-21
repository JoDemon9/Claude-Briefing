"""Visible favourite headlines, rich team scoreboards and official links, with full sports coverage."""
from datetime import datetime, timezone
from pathlib import Path

NEWS = {
    'omonoia': 'https://www.omonoiafc.com.cy/category-news/',
    'manutd': 'https://www.manutd.com/en/news',
    'realmadrid': 'https://www.realmadrid.com/en-US/news/football/first-team',
    'formula1': 'https://www.formula1.com/en/latest',
}

BRAND_LOGOS = {
    'omonoia': 'assets/brands/omonoia.png',
    'manutd': 'assets/brands/manutd.svg',
    'realmadrid': 'assets/brands/realmadrid.svg',
    'formula1': 'assets/brands/formula1.jpg',
}


def interest(article):
    return article.get('sports_interest', 'other')


def credits(b):
    records = b.read(b.ROOT/'templates/v2/sports-logos.json')
    return '<section id="sports-logos"><h2>Αθλητικά σήματα</h2><ul>' + ''.join('<li><a href="' + b.esc(r['source_url']) + '">' + b.esc(r['name']) + '</a> · ' + b.esc(r['owner']) + ' · <a href="' + b.esc(r['original_url']) + '">Αρχικό σήμα</a></li>' for r in records) + '</ul></section>'


def headlines(b, edition, key):
    record = edition.get('sports', {}).get('news_links', {}).get(key)
    rows = []
    status = 'archive'
    checked = None
    if record:
        rows = record.get('items', [])
        status = record.get('status', 'available')
        checked = record.get('checked_at')
    else:
        # Check coverage updates or verified links
        team_cov = edition.get('sports', {}).get('coverage', {}).get(key, {})
        if team_cov.get('verified_links'):
            for vl in team_cov['verified_links']:
                rows.append({'url': vl['url'], 'headline': vl['title'], 'published_at': None})
            status = 'available'
            checked = team_cov.get('updated_at')
        elif team_cov.get('updates'):
            updates = team_cov['updates']
            def order(item):
                value = datetime.fromisoformat(item['published_at'].replace('Z', '+00:00'))
                return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
            for update in sorted(updates, key=order, reverse=True):
                source = next((s for s in update['sources'] if s.get('access') in ('read', 'archived') and s.get('used_for_claims', True)), None)
                if source and source['url'] not in {r['url'] for r in rows}:
                    rows.append({'url': source['url'], 'headline': update['text'], 'published_at': update['published_at']})
                if len(rows) == 3:
                    break
            status = 'archive'
            checked = team_cov.get('updated_at')

    if not rows:
        return ''

    out = ['<div class="sport-headlines">']
    if status == 'unavailable':
        out.append('<span class="sport-source-status">Η πηγή δεν είναι διαθέσιμη' + (' · διατηρούνται παλιότεροι τίτλοι' if rows else '') + '.</span>')
    elif status == 'archive':
        out.append('<span class="sport-source-status">Από το αρχείο της έκδοσης</span>')
    out.append('<ul>')
    for row in rows[:2]:
        label = row.get('headline_el') or row['headline']
        stamp = '<time datetime="' + b.esc(row['published_at']) + '">' + b.esc(b.stamp(row['published_at'])) + '</time>' if row.get('published_at') else '<span>Η πηγή δεν δίνει ημερομηνία</span>'
        out.append('<li><a class="sport-headline-link" href="' + b.esc(row['url']) + '" rel="noopener noreferrer">' + b.esc(label) + '</a>' + stamp + '</li>')
    out.append('</ul>')
    if checked:
        out.append('<span class="sport-check-time">' + ('Απόπειρα ελέγχου: ' if status == 'unavailable' else 'Έλεγχος πηγής: ') + b.esc(b.stamp(checked)) + '</span>')
    out.append('</div>')
    return ''.join(out)


def render(b, edition, articles=(), anchors=None, include_major=True):
    out = ['<section class="section" id="sports"><div class="sectionhead"><h2>' + b.emblem('sports') + 'Τα αθλητικά μου.</h2></div><div class="sports sports-links">']
    logos = {r['id']: r for r in b.read(b.ROOT/'templates/v2/sports-logos.json')}
    for key, url in NEWS.items():
        refs = ''.join('<span class="sport-story-anchor" id="story-' + sid_hash + '" data-story-id="' + b.esc(sid) + '"></span>' for sid, sid_hash in (anchors or {}).get(key, []))

        # Prefer brand asset if available on disk, else fallback to sports-logos.json
        brand_rel = BRAND_LOGOS.get(key)
        logo_asset = brand_rel if (brand_rel and (b.ROOT/'docs'/brand_rel).exists()) else logos.get(key, {}).get('asset', '')

        # Rich details if present in coverage
        team_cov = edition.get('sports', {}).get('coverage', {}).get(key, {})
        meta_html = []
        badge = team_cov.get('status_badge') or team_cov.get('league_position') or team_cov.get('form')
        if badge:
            meta_html.append('<span class="sport-badge">' + b.esc(badge) + '</span>')

        last = team_cov.get('last_result') or (team_cov.get('last_match') if isinstance(team_cov.get('last_match'), str) else None)
        if not last and isinstance(team_cov.get('last_match'), dict):
            lm = team_cov['last_match']
            opp = lm.get('opponent', '')
            res = lm.get('result', '')
            last = f"{opp} ({res})" if opp or res else None
        if last:
            meta_html.append('<div class="sport-fixture"><strong>Τελευταίο:</strong> ' + b.esc(last) + '</div>')

        nxt = team_cov.get('next_fixture') if isinstance(team_cov.get('next_fixture'), str) else None
        if not nxt and isinstance(team_cov.get('next_fixture'), dict):
            nf = team_cov['next_fixture']
            nxt = f"{nf.get('opponent', '')} - {nf.get('date', '')}"
        if not nxt and team_cov.get('next_grand_prix'):
            nxt = team_cov['next_grand_prix']
        if nxt:
            meta_html.append('<div class="sport-fixture"><strong>Επόμενο:</strong> ' + b.esc(nxt) + '</div>')

        analysis = team_cov.get('editorial_summary') or team_cov.get('analysis')
        if analysis:
            meta_html.append('<div class="sport-summary">' + b.esc(analysis) + '</div>')

        extra = ''.join(meta_html)
        out.append('<article class="sport team-' + key + '">' + refs + '<span class="teamicon" aria-hidden="true"><img class="sport-logo" src="../' + logo_asset + '" alt="" width="32" height="32" loading="lazy" decoding="async"></span><h3>' + b.TEAMS[key] + '</h3><a class="sport-news-link" href="' + url + '" rel="noopener noreferrer" aria-label="Όλα τα νέα · ' + b.TEAMS[key] + '">Όλα τα νέα ↗</a>' + extra + headlines(b, edition, key) + '</article>')
    out.append('</div>')

    if include_major:
        lookup = {a['id']: a for a in articles}
        # In v3.0, major_stories can include any sport article, including favourite teams
        allow_all = edition.get('date', '') >= '2026-10-21'
        records = [r for r in edition.get('sports', {}).get('major_stories', []) if r['article_id'] in lookup and (allow_all or interest(lookup[r['article_id']]) == 'other')]
        title = "Κύρια αθλητικά θέματα & ανάλυση" if allow_all else "Από τον υπόλοιπο αθλητισμό"
        out.append('<div class="sports-other"><h3>' + title + '</h3><div class="g3">')
        for record in records[:3 if allow_all else 2]:
            full = lookup.get(record['article_id'])
            if full:
                out.append(b.card(edition, full))
            else:
                out.append('<article class="sport"><h3>' + b.esc(record['headline']) + '</h3><p>' + b.esc(record['summary']) + '</p><a href="../articles/' + edition['id'] + '/' + record['article_id'] + '.html">Διάβασε ↗</a></article>')
        out.append('</div>')
        if not records:
            reason = edition.get('sports', {}).get('major_stories_reason') or 'Δεν έχει επιλεγεί άλλη αθλητική είδηση σε αυτή την έκδοση.'
            out.append('<p class="muted">' + b.esc(reason) + '</p>')
        if len(records) > (3 if allow_all else 2):
            out.append('<details class="sports-archive"><summary>Περισσότερες αθλητικές αναφορές</summary><ul>' + ''.join('<li><a href="../articles/' + edition['id'] + '/' + r['article_id'] + '.html">' + b.esc(r['headline']) + '</a></li>' for r in records[(3 if allow_all else 2):]) + '</ul></details>')
        out.append('</div>')
    out.append('</section>')
    return ''.join(out)
