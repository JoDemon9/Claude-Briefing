"""Selection accountability and exact-copy freshness checks for new candidates."""
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def reporting(article):
    # Ignore labels/times/formatting: none makes identical reporting a new event.
    return ' '.join(article.get('summary', '').split()).casefold()


def validate(edition, articles, root):
    if edition.get('selection_policy') != 'balanced-v1':
        return
    selected = {a['story_id'] for a in articles}
    omitted = edition.get('selection_review', {}).get('omitted_stories', {})
    if not isinstance(omitted, dict) or any(not isinstance(v, str) or len(v.strip()) < 20 for v in omitted.values()):
        raise ValueError('Omitted baseline stories need specific reasons')
    spec = importlib.util.spec_from_file_location('continuity_baseline', Path(__file__).with_name('baseline.py'))
    baseline = importlib.util.module_from_spec(spec); spec.loader.exec_module(baseline)
    previous = []
    reference = edition.get('baseline')
    if reference:
        _, previous = baseline.load(root, reference, edition['published_at'])
    old_ids = {a['story_id'] for a in previous}
    if set(omitted) - old_ids or set(omitted) & selected:
        raise ValueError('Omission must reference an unselected baseline story')
    if edition['type'] != 'morning' and reference and old_ids - selected - set(omitted):
        raise ValueError('Account for every baseline story with an update, exact carry or explicit omission')
    if edition['type'] == 'morning' and omitted:
        raise ValueError('Morning selects afresh; baseline omissions belong to later editions')
    # If a direct JSON candidate omits baseline, still compare exact reporting
    # with the latest prior snapshot. No fuzzy title matching or identity merging.
    if not reference:
        candidates = []
        for path in (Path(root)/'content/editions').glob('*.json'):
            old = json.loads(path.read_text(encoding='utf-8'))
            if old['status'] == 'published' and old.get('published_at') and datetime.fromisoformat(old['published_at']) < datetime.fromisoformat(edition['published_at']):
                candidates.append(old)
        if candidates:
            old = max(candidates, key=lambda e: datetime.fromisoformat(e['published_at']))
            previous = [json.loads((Path(root)/'content'/p).read_text(encoding='utf-8')) for p in old['articles']]
    old_by_id = {a['story_id']: a for a in previous}
    old_reporting = {reporting(a) for a in previous}
    for article in articles:
        status = article.get('change_status')
        if status == 'UNCHANGED':
            origin = article.get('baseline_origin')
            if edition['type'] == 'morning' or not reference or origin != reference:
                raise ValueError('Unchanged carry requires the later edition\'s exact baseline')
            updated_day = datetime.fromisoformat(article['updated_at']).astimezone(ZoneInfo('Europe/Athens')).date().isoformat()
            if origin['edition_id'][:10] != edition['date'] or updated_day != edition['date']:
                raise ValueError('Unchanged carries are same-day only; omit stale coverage or supply new reporting')
        elif reporting(article) in old_reporting:
            raise ValueError('Identical reporting cannot be relabelled as new/updated; carry or omit it')
        previous_article = old_by_id.get(article['story_id'])
        if previous_article and status != 'UNCHANGED':
            if status not in ('UPDATED', 'REVERSAL', 'CORRECTION'):
                raise ValueError('An existing story needs an explicit material update status')
            if article['story_identity'] != previous_article['story_identity'] or article['published_at'] != previous_article['published_at']:
                raise ValueError('Story updates must preserve identity and original publication time')
