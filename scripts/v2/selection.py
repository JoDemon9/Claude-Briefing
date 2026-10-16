"""Editorial selection gates; existing snapshots retain their original inventory."""


def section(article):
    return article.get('daily', {}).get('section') or {'Κύπρος': 'cyprus', 'Πρώτο θέμα': 'cyprus', 'Διεθνή': 'world', 'Αθλητικά': 'sports'}[article['category']]


def validate(edition, articles):
    current = edition['status'] == 'published' and edition['date'] >= '2026-10-16'
    review = edition.get('selection_review')
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
