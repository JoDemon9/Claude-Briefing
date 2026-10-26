"""Visible favourite headlines, rich team scoreboards and official links, with full sports coverage."""
from datetime import datetime, timezone
from pathlib import Path


def prefetch(client, at):
    """Preparation entry point; rendering stays independent of network collection."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('structured_sports', Path(__file__).with_name('sports_data.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value.collect(client, at)

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
    value = article.get('sports_interest', 'other')
    return 'formula1' if value == 'f1' else value


def credits(b):
    records = b.read(b.ROOT/'templates/v2/sports-logos.json')
    photos = b.read(b.ROOT/'templates/v2/photo-policy.json')['photos']
    photo_credits = ''.join('<section id="sports-photo-'+key+'"><h3>'+b.esc(p['image']['alt'])+'</h3><p>'+b.esc(p['image']['caption'])+'</p><a href="'+b.esc(p['image']['source_url'])+'">'+b.esc(p['image']['attribution'])+'</a> · <a href="'+b.esc(p['image']['license_url'])+'">'+b.esc(p['image']['license'])+'</a></section>' for key,p in photos.items() if key in ('omonoia','manutd','realmadrid','formula1'))
    return '<section id="sports-logos"><h2>Αθλητικά σήματα και φωτογραφίες</h2><ul>' + ''.join('<li><a href="' + b.esc(r['source_url']) + '">' + b.esc(r['name']) + '</a> · ' + b.esc(r['owner']) + ' · <a href="' + b.esc(r['original_url']) + '">Αρχικό σήμα</a></li>' for r in records) + '</ul>'+photo_credits+'</section>'


def table(b, title, headings, rows):
    if not rows:
        return ''
    return '<div class="sport-table"><table><caption>'+b.esc(title)+'</caption><thead><tr>'+''.join('<th scope="col">'+b.esc(h)+'</th>' for h in headings)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+b.esc(str(v if v is not None else '—'))+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def evidence(b, sources):
    unique = {s['url']:s for s in sources if s.get('access') == 'read'}
    return '<div class="sport-evidence">'+'<br>'.join('<a href="'+b.esc(url)+'" rel="noopener noreferrer">'+b.esc(s['publisher'])+'</a> · '+b.esc(b.stamp(s['retrieved_at'])) for url,s in list(unique.items())[:2])+'</div>' if unique else ''


def competitions(b, edition):
    names = {'uefa.champions':'Champions League','uefa.europa':'Europa League','uefa.europa.conf':'Conference League'}
    data = edition.get('sports', {}).get('competitions', {})
    if not data:
        return ''
    out = ['<div class="sports-europe"><h3>Ευρωπαϊκές διοργανώσεις · UEFA</h3><div class="sports-europe-grid">']
    for key,name in names.items():
        row = data.get(key, {})
        out.append('<article class="sport competition"><h4>'+name+'</h4>')
        out.append(table(b,'Πρόσφατα αποτελέσματα',('Αγώνας','Σκορ'),[(r['name']+' · '+r['starts_at'][:10],r['score']) for r in row.get('scores',[])[:6]]))
        out.append(table(b,'Επόμενοι αγώνες · ώρα Κύπρου',('Αγώνας','Έναρξη'),[(r['name'],b.stamp(r['starts_at'])) for r in row.get('fixtures',[])[:6]]))
        out.append(table(b,'Κατάταξη · πρώτες 5 ομάδες',('Θέση','Ομάδα','Βαθμοί'),[(r.get('rank'),r['team'],r.get('points')) for r in row.get('standings',[])[:5]]))
        if not any(row.get(k) for k in ('scores','fixtures','standings')):
            out.append('<p class="muted">Δεν υπάρχουν επιβεβαιωμένα στοιχεία σε αυτή την έκδοση.</p>')
        out.append(evidence(b,[s for k in ('scores','fixtures','standings') for r in row.get(k,[]) for s in r.get('sources',[])]))
        out.append('</article>')
    return ''.join(out)+'</div></div>'


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
    if record and record.get('attempted_at') and status == 'unavailable':
        out.append('<span class="sport-check-time">Νεότερη απόπειρα: '+b.esc(b.stamp(record['attempted_at']))+'</span>')
    out.append('</div>')
    return ''.join(out)


def render(b, edition, articles=(), anchors=None, include_major=True):
    out = ['<section class="section" id="sports"><div class="sectionhead"><h2>' + b.emblem('sports') + 'Τα αθλητικά μου.</h2></div><p class="sports-intro">Αποτελέσματα, βαθμολογία, επόμενοι αγώνες και ειδήσεις για τις ομάδες σου, τη Formula 1 και τις ευρωπαϊκές διοργανώσεις.</p><div class="sports sports-links">']
    logos = {r['id']: r for r in b.read(b.ROOT/'templates/v2/sports-logos.json')}
    photos = b.read(b.ROOT/'templates/v2/photo-policy.json')['photos']
    for key, url in NEWS.items():
        refs = ''.join('<span class="sport-story-anchor" id="story-' + sid_hash + '" data-story-id="' + b.esc(sid) + '"></span>' for sid, sid_hash in (anchors or {}).get(key, []))

        # Prefer brand asset if available on disk, else fallback to sports-logos.json
        brand_rel = BRAND_LOGOS.get(key)
        logo_asset = brand_rel if (brand_rel and (b.ROOT/'docs'/brand_rel).exists()) else logos.get(key, {}).get('asset', '')

        # Rich details if present in coverage
        team_cov = edition.get('sports', {}).get('coverage', {}).get(key, {})
        meta_html = []
        badge = team_cov.get('status_badge') or ('Θέση πρωταθλήματος: '+str(team_cov['league_position']) if team_cov.get('league_position') else team_cov.get('form'))
        if badge:
            meta_html.append('<span class="sport-badge">' + b.esc(badge) + '</span>')

        last = team_cov.get('last_result') or (team_cov.get('last_match') if isinstance(team_cov.get('last_match'), str) else None)
        if not last and isinstance(team_cov.get('last_match'), dict):
            lm = team_cov['last_match']
            opp = lm.get('opponent', '')
            res = lm.get('result', '')
            last = f"{opp} ({res})" if opp or res else None
            if last and lm.get('date'):
                last += ' · ' + lm['date']
            if last and lm.get('scorers'):
                last += ' · ' + ', '.join(lm['scorers'])
        if not last and isinstance(team_cov.get('latest_session'), dict):
            last = ' · '.join(str(team_cov['latest_session'][key]) for key in ('name','result','date') if team_cov['latest_session'].get(key))
        if last:
            meta_html.append('<div class="sport-fixture"><strong>Τελευταίο:</strong> ' + b.esc(last) + '</div>')
        if isinstance(team_cov.get('latest_session'), dict):
            session = team_cov['latest_session']
            results = session.get('results', [])
            if isinstance(results, list):
                meta_html.append(table(b,'Αποτελέσματα · πρώτοι 5',('Θέση','Οδηγός','Κατάσταση'),[(r['position'],r['driver'],r['status']) for r in results[:5] if isinstance(r,dict) and all(k in r for k in ('position','driver','status'))]))
        standings = team_cov.get('standings', [])
        if isinstance(standings, list):
            meta_html.append(table(b,'Βαθμολογία οδηγών · πρώτοι 5',('Θέση','Οδηγός','Βαθμοί'),[(r['position'],r['driver'],r['points']) for r in standings[:5] if isinstance(r,dict) and all(k in r for k in ('position','driver','points'))]))
        stats = team_cov.get('league_stats', {})
        labels = {'gamesPlayed':'Αγώνες','wins':'Νίκες','ties':'Ισοπαλίες','losses':'Ήττες','points':'Βαθμοί','pointDifferential':'Διαφορά τερμάτων'}
        if stats:
            meta_html.append('<dl class="sport-stats">'+''.join('<div><dt>'+labels[k]+'</dt><dd>'+b.esc(str(v))+'</dd></div>' for k,v in stats.items() if k in labels)+'</dl>')

        nxt = team_cov.get('next_fixture') if isinstance(team_cov.get('next_fixture'), str) else None
        if not nxt and isinstance(team_cov.get('next_fixture'), dict):
            nf = team_cov['next_fixture']
            nxt = f"{nf.get('opponent', '')} · {nf.get('date', '')}"
            if nf.get('kickoff_at'):
                nxt += ' · ' + b.stamp(nf['kickoff_at'])
            if nf.get('venue'):
                nxt += ' · ' + nf['venue']
        if not nxt and team_cov.get('next_grand_prix'):
            nxt = team_cov['next_grand_prix']
        if nxt:
            meta_html.append('<div class="sport-fixture"><strong>Επόμενο:</strong> ' + b.esc(nxt) + '</div>')
        session_names={'Race':'Αγώνας','Qualifying':'Κατατακτήριες','FirstPractice':'Ελεύθερα 1','SecondPractice':'Ελεύθερα 2','ThirdPractice':'Ελεύθερα 3','Sprint':'Σπριντ','SprintQualifying':'Κατατακτήριες σπριντ'}
        for session in sorted(team_cov.get('sessions', []),key=lambda s:s['starts_at']):
            meta_html.append('<div class="sport-fixture">'+b.esc(session_names.get(session['name'],session['name']))+' · '+b.stamp(session['starts_at'])+'</div>')

        analysis = team_cov.get('editorial_summary') or team_cov.get('analysis')
        if analysis and analysis.startswith('Δομημένα δεδομένα'):
            analysis = None
        if analysis:
            meta_html.append('<div class="sport-summary">' + b.esc(analysis) + '</div>')
        if team_cov.get('updated_at'):
            meta_html.append('<span class="sport-check-time">Στοιχεία έως: '+b.esc(b.stamp(team_cov['updated_at']))+'</span>')
        refs_data = team_cov.get('standings_sources', []) + team_cov.get('next_gp_sources', [])
        for field in ('last_match','next_fixture','latest_session'):
            if isinstance(team_cov.get(field), dict):
                refs_data += team_cov[field].get('sources', [])
        meta_html.append(evidence(b, refs_data))

        extra = ''.join(meta_html)
        photo = photos[key]
        hero = '<figure class="sport-photo"><img src="../'+b.esc(photo['asset'])+'" alt="'+b.esc(photo['image']['alt'])+'" loading="lazy" decoding="async"><figcaption><a href="../photo-credits.html#sports-photo-'+key+'">Φωτογραφία αρχείου</a></figcaption></figure>'
        out.append('<article class="sport team-' + key + '">' + refs + hero + '<span class="teamicon" aria-hidden="true"><img class="sport-logo" src="../' + logo_asset + '" alt="" width="32" height="32" loading="lazy" decoding="async"></span><h3>' + b.TEAMS[key] + '</h3><a class="sport-news-link" href="' + url + '" rel="noopener noreferrer" aria-label="Όλα τα νέα · ' + b.TEAMS[key] + '">Όλα τα νέα ↗</a>' + extra + headlines(b, edition, key) + '</article>')
    out.append('</div>')
    out.append(competitions(b, edition))

    if include_major:
        lookup = {a['id']: a for a in articles}
        # In v3.0, major_stories can include any sport article, including favourite teams
        allow_all = edition.get('date', '') >= '2026-10-21'
        records = [r for r in edition.get('sports', {}).get('major_stories', []) if r['article_id'] in lookup and (allow_all or interest(lookup[r['article_id']]) == 'other')]
        if allow_all:
            known = {r['article_id'] for r in records}
            records += [dict(article_id=a['id'],headline=a['headline']) for a in articles if a.get('daily',{}).get('section')=='sports' and a['id'] not in known]
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
