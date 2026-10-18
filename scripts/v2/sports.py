"""Visible favourite headlines and official links, separate from other sports."""

from datetime import datetime, timezone

NEWS = {
    'omonoia': 'https://www.omonoiafc.com.cy/category-news/',
    'manutd': 'https://www.manutd.com/en/news',
    'realmadrid': 'https://www.realmadrid.com/en-US/news/football/first-team',
    'formula1': 'https://www.formula1.com/en/latest',
}


def interest(article):
    return article.get('sports_interest', 'other')


def credits(b):
    records = b.read(b.ROOT/'templates/v2/sports-logos.json')
    return '<section id="sports-logos"><h2>Αθλητικά σήματα</h2><ul>' + ''.join('<li><a href="' + b.esc(r['source_url']) + '">' + b.esc(r['name']) + '</a> · ' + b.esc(r['owner']) + ' · <a href="' + b.esc(r['original_url']) + '">Αρχικό σήμα</a></li>' for r in records) + '</ul></section>'


def headlines(b,edition,key):
    record=edition['sports'].get('news_links',{}).get(key)
    if record:
        rows=record['items'];status=record['status'];checked=record['checked_at']
    else:
        # Older source-backed updates were hidden by the links-only renderer.
        # Show them with their original dates; never refresh archived findings.
        updates=edition['sports']['coverage'][key]['updates']
        def order(item):
            value=datetime.fromisoformat(item['published_at'].replace('Z','+00:00'))
            return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
        rows=[]
        for update in sorted(updates,key=order,reverse=True):
            source=next((s for s in update['sources'] if s.get('access') in ('read','archived') and s.get('used_for_claims',True)),None)
            if source and source['url'] not in {r['url'] for r in rows}:
                rows.append({'url':source['url'],'headline':update['text'],'published_at':update['published_at']})
            if len(rows)==2:break
        status='archive';checked=edition['sports']['coverage'][key]['updated_at']
    out=['<div class="sport-headlines">']
    if status=='unavailable':
        out.append('<span class="sport-source-status">Η πηγή δεν είναι διαθέσιμη'+(' · διατηρούνται παλιότεροι τίτλοι' if rows else '')+'.</span>')
    elif status=='archive':out.append('<span class="sport-source-status">Από το αρχείο της έκδοσης</span>')
    if rows:
        out.append('<ul>')
        for row in rows:
            label=row.get('headline_el') or row['headline']
            stamp='<time datetime="'+b.esc(row['published_at'])+'">'+b.esc(b.stamp(row['published_at']))+'</time>' if row.get('published_at') else '<span>Η πηγή δεν δίνει ημερομηνία</span>'
            out.append('<li><a class="sport-headline-link" href="'+b.esc(row['url'])+'" rel="noopener noreferrer">'+b.esc(label)+'</a>'+stamp+'</li>')
        out.append('</ul>')
    else:out.append('<span class="sport-source-status">Δεν υπάρχει διαθέσιμος επαληθεύσιμος τίτλος.</span>')
    out.append('<span class="sport-check-time">'+('Απόπειρα ελέγχου: ' if status=='unavailable' else 'Έλεγχος πηγής: ')+b.esc(b.stamp(checked))+'</span></div>')
    return ''.join(out)


def render(b, edition, articles=(), anchors=None, include_major=True):
    out = ['<section class="section" id="sports"><div class="sectionhead"><h2>' + b.emblem('sports') + 'Τα αθλητικά μου.</h2></div><div class="sports sports-links">']
    logos = {r['id']: r for r in b.read(b.ROOT/'templates/v2/sports-logos.json')}
    for key, url in NEWS.items():
        # Keep existing day-summary anchors for favourite stories without repeating
        # their articles in the separate, general sports desk.
        refs = ''.join('<span class="sport-story-anchor" id="story-' + sid_hash + '" data-story-id="' + b.esc(sid) + '"></span>' for sid, sid_hash in (anchors or {}).get(key, []))
        out.append('<article class="sport team-' + key + '">' + refs + '<span class="teamicon" aria-hidden="true"><img class="sport-logo" src="../' + logos[key]['asset'] + '" alt="" width="32" height="32" loading="lazy" decoding="async"></span><h3>' + b.TEAMS[key] + '</h3><a class="sport-news-link" href="' + url + '" rel="noopener noreferrer" aria-label="Όλα τα νέα · ' + b.TEAMS[key] + '">Όλα τα νέα ↗</a>'+headlines(b,edition,key)+'</article>')
    out.append('</div>')
    if include_major:
        lookup = {a['id']: a for a in articles}
        records = [r for r in edition['sports']['major_stories'] if r['article_id'] in lookup and interest(lookup[r['article_id']]) == 'other']
        out.append('<div class="sports-other"><h3>Από τον υπόλοιπο αθλητισμό</h3><div class="g3">')
        for record in records[:2]:
            full = lookup.get(record['article_id'])
            if full:
                out.append(b.card(edition, full))
            else:
                out.append('<article class="sport"><h3>' + b.esc(record['headline']) + '</h3><p>' + b.esc(record['summary']) + '</p><a href="../articles/' + edition['id'] + '/' + record['article_id'] + '.html">Διάβασε ↗</a></article>')
        out.append('</div>')
        if not records:
            reason = edition['sports']['major_stories_reason'] if not edition['sports']['major_stories'] else 'Δεν έχει επιλεγεί άλλη επαληθευμένη αθλητική είδηση σε αυτή την έκδοση.'
            out.append('<p class="muted">' + b.esc(reason) + '</p>')
        if len(records) > 2:
            out.append('<details class="sports-archive"><summary>Περισσότερες αθλητικές αναφορές</summary><ul>' + ''.join('<li><a href="../articles/' + edition['id'] + '/' + r['article_id'] + '.html">' + b.esc(r['headline']) + '</a></li>' for r in records[2:]) + '</ul></details>')
        out.append('</div>')
    out.append('</section>')
    return ''.join(out)
