"""Editorial selection gates; existing snapshots retain their original inventory."""

from urllib.parse import urlsplit

TARGETS = {'world': 5, 'cyprus': 5}
BALANCED_START = '2026-10-28'


def balanced_required(edition):
    return edition.get('selection_policy') == 'balanced-v1' or edition.get('date', '') >= BALANCED_START


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
    targets = {'world': 4, 'cyprus': 4} if balanced_required(edition) else TARGETS.copy()
    return {'edition_id': edition['id'], 'counts': counts, 'targets': targets,
            'preferred_range': [4, 5],
            'carried_counts': inventory([a for a in articles if a.get('change_status') == 'UNCHANGED']),
            'coverage_notes': edition.get('selection_review', {}).get('coverage_notes', {}),
            'required': coverage_required(edition),
            'shortfalls': {name: target-counts[name] for name, target in targets.items() if counts[name] < target}}


def validate_balanced(edition, articles):
    if not balanced_required(edition):
        return
    if edition.get('selection_policy') != 'balanced-v1':
        raise ValueError('New editions require selection_policy=balanced-v1')
    counts = inventory(articles)
    review = edition.get('selection_review', {})
    notes = review.get('coverage_notes', {})
    if review.get('version') != 2 or not isinstance(notes, dict) or set(notes) - set(TARGETS):
        raise ValueError('Balanced selection requires a version-2 review and valid coverage_notes')
    for desk in TARGETS:
        reason = notes.get(desk, '')
        if counts[desk] < 4 and (not isinstance(reason, str) or len(reason.strip()) < 20):
            raise ValueError(f'{desk} coverage below four requires a specific @Coverage reason; do not pad')
        if counts[desk] >= 4 and reason:
            raise ValueError(f'Remove stale {desk} coverage note after meeting the target')
    if counts['cyprus'] > 5 or counts['world'] > 7:
        raise ValueError('Balanced selection allows at most five Cyprus and seven world stories')
    if counts['world'] > 5 and len((review.get('global_exception_reason') or '').strip()) < 20:
        raise ValueError('Six or seven world stories need an explicit editorial reason')
    if edition.get('daily', {}).get('lead_story_id') not in {a['story_id'] for a in articles}:
        raise ValueError('Edition lead must identify a selected story; filenames do not define the lead')


def section(article):
    return article.get('daily', {}).get('section') or {'Κύπρος': 'cyprus', 'Πρώτο θέμα': 'cyprus', 'Διεθνή': 'world', 'Αθλητικά': 'sports'}[article['category']]


def validate(edition, articles):
    validate_balanced(edition, articles)
    current = edition['status'] == 'published' and edition['date'] >= '2026-10-16'
    partial = edition.get('availability_policy') == 'partial-v1' and edition['date'] >= '2026-10-22'
    review = edition.get('selection_review')
    if edition.get('synthesis_profile') == 'single-turn-v1':
        validate_synthesis(edition, articles)
        return
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
            if partial:
                continue  # Publish supported stories without padding or invented shortage research.
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
        modern = edition.get('date', '') >= '2026-10-21'
        if len(extras) > (3 if modern else 2):
            raise ValueError('Select at most three sports stories' if modern else 'Select at most two other sports stories')
        allowed_interests = {'other', 'omonoia', 'manutd', 'realmadrid', 'formula1', 'f1'}
        if modern:
            if any(sports.get(r['article_id'], {}).get('sports_interest') not in allowed_interests for r in extras):
                raise ValueError('Sports major stories must match supported interests')
        else:
            if any(sports.get(r['article_id'], {}).get('sports_interest') != 'other' for r in extras):
                raise ValueError('Other sports stories must be separate from the four favourites')


def validate_synthesis(edition, articles):
    inventory(articles)
    review=edition.get('selection_review',{})
    if review.get('version')!=2 or not edition.get('prefetch_provenance'):
        raise ValueError('Synthesis requires a selection review and prepared data provenance')
    changed=[a for a in articles if a.get('change_status')!='UNCHANGED']
    if len(changed)>(10 if edition['type']=='morning' else 6):
        raise ValueError('At most ten morning stories or six delta stories may be written')
    if edition['type']=='morning' and len(articles)>10:
        raise ValueError('Morning has at most ten selected stories')
    if edition['type']!='morning' and not edition.get('baseline'):
        raise ValueError('Delta synthesis requires an exact baseline')
    leads={}
    for article in changed:
        desk=section(article)
        leads.setdefault(desk,article['story_id'])
        deep=any(article.get(k) for k in ('mechanics_and_incentives','second_order_effects','scenarios','newspaper_analysis'))
        mover=bool(set(article.get('driver_tags',[])) & {'market-mover','tactical-mover'})
        if deep and article['story_id']!=leads[desk] and not mover:
            raise ValueError('Deep analysis is reserved for desk leads and major market/tactical movers')
        if not deep and len(article['summary'].split())>70:
            raise ValueError('Secondary dispatches must be concise (at most 70 words)')
        if desk=='sports' and article.get('sports_interest') not in {'omonoia','manutd','realmadrid','formula1','other'}:
            raise ValueError('Sports dispatch requires an explicit priority interest')
    if len(edition['sports'].get('major_stories',[]))>3:
        raise ValueError('At most three major sports stories')
