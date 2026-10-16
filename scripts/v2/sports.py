"""Four direct news links, separate from the rest of the sports desk."""

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


def render(b, edition, articles=(), anchors=None, include_major=True):
    out = ['<section class="section" id="sports"><div class="sectionhead"><h2>' + b.emblem('sports') + 'Τα αθλητικά μου.</h2></div><div class="sports sports-links">']
    logos = {r['id']: r for r in b.read(b.ROOT/'templates/v2/sports-logos.json')}
    for key, url in NEWS.items():
        # Keep existing day-summary anchors for favourite stories without repeating
        # their articles in the separate, general sports desk.
        refs = ''.join('<span class="sport-story-anchor" id="story-' + sid_hash + '" data-story-id="' + b.esc(sid) + '"></span>' for sid, sid_hash in (anchors or {}).get(key, []))
        out.append('<article class="sport team-' + key + '">' + refs + '<span class="teamicon" aria-hidden="true"><img class="sport-logo" src="../' + logos[key]['asset'] + '" alt="" width="32" height="32" loading="lazy" decoding="async"></span><h3>' + b.TEAMS[key] + '</h3><a class="sport-news-link" href="' + url + '" rel="noopener noreferrer" aria-label="Τελευταία νέα · ' + b.TEAMS[key] + '">Τελευταία νέα ↗</a></article>')
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
