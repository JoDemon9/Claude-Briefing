"""Editorial selection gates; existing snapshots retain their original inventory."""

from urllib.parse import urlsplit

TARGETS = {'world': 5, 'cyprus': 5}


def coverage_required(edition):
    """Start with the next unpublished slot; never invalidate published history."""
    return edition['date'] > '2026-10-18' or (
        edition['date'] == '2026-10-18' and edition['type'] == 'evening')


def inventory(articles):
    counts = {name: 0 for name in (*TARGETS, 'sports')}
    seen = set()
    for article in articles:
        sid = article.get('story_id') or article.get('id')
        if sid and sid in seen:
            raise ValueError('Section coverage requires distinct story IDs; duplicates cannot fill a target')
        if sid:
            seen.add(sid)
        counts[section(article)] += 1
    return counts


def coverage(edition, articles):
    counts = inventory(articles)
    return {'edition_id': edition['id'], 'counts': counts, 'targets': TARGETS.copy(),
            'required': coverage_required(edition),
            'shortfalls': {name: target-counts[name] for name, target in TARGETS.items() if counts[name] < target}}


def section(article):
    return article.get('daily', {}).get('section') or {'Κύπρος': 'cyprus', 'Πρώτο θέμα': 'cyprus', 'Διεθνή': 'world', 'Αθλητικά': 'sports'}[article['category']]


def validate(edition, articles):
    current = edition['status'] == 'published' and edition['date'] >= '2026-10-16'
    review = edition.get('selection_review')
    if current and coverage_required(edition):
        if not review or review.get('version') != 2:
            raise ValueError('Every edition requires selection_review.version=2 and separate world/Cyprus coverage')
        counts = inventory(articles)
        if counts['cyprus'] > 5 or counts['world'] > 7:
            raise ValueError('Section selection allows at most five Cyprus and seven global stories, including the lead')
        if counts['world'] > 5 and len((review.get('global_exception_reason') or '').strip()) < 20:
            raise ValueError('Six or seven global stories require an editorial reason')
        shortfalls = review.get('section_shortfalls', {})
        for name, target in TARGETS.items():
            exception = shortfalls.get(name)
            if counts[name] >= target:
                if exception:
                    raise ValueError(f'Remove stale {name} section shortfall after meeting its target')
                continue
            if not exception or len(exception.get('reason', '').strip()) < 40:
                raise ValueError(f'{name} section needs five distinct stories or an evidence-backed section shortfall')
            sources = exception.get('checked_sources', [])
            hosts = {urlsplit(url).hostname.removeprefix('www.') for url in sources
                     if urlsplit(url).scheme == 'https' and urlsplit(url).hostname}
            if len(hosts) < 2:
                raise ValueError(f'{name} shortfall requires two independent checked source domains')
    if current and edition['type'] == 'morning' and not review:
        raise ValueError('Morning publication requires selection_review.version=1 (DEC-010)')
    if edition['type'] == 'morning' and review:
        local = sum(section(a) == 'cyprus' for a in articles)
        world = sum(section(a) == 'world' for a in articles)
        if local > 5 or world > 7:
            raise ValueError('Morning selection allows at most five Cyprus and seven global stories, including the lead')
        if world > 5 and not (review.get('global_exception_reason') or '').strip():
            raise ValueError('Six or seven global stories require an editorial reason')
    if current:
        sports = {a['id']: a for a in articles if section(a) == 'sports'}
        if any('sports_interest' not in a for a in sports.values()):
            raise ValueError('Sports articles require explicit sports_interest (DEC-008)')
        extras = edition['sports']['major_stories']
        if len(extras) > 2:
            raise ValueError('Select at most two other sports stories')
        if any(sports.get(r['article_id'], {}).get('sports_interest') != 'other' for r in extras):
            raise ValueError('Other sports stories must be separate from the four favourites')
