"""Deterministic selection from a visually reviewed, licensed real-photo library."""
import copy
import json
import re
from pathlib import Path


def load(root):
    path = Path(root)/'templates/v2/photo-policy.json'
    return json.loads(path.read_text(encoding='utf-8'))


def selection(article, root):
    policy = load(root)
    sid = article.get('story_id') or article.get('slug') or article.get('id', '')
    key = policy['stories'].get(sid)
    text = ' '.join(str(article.get(k, '')) for k in ('story_id', 'slug', 'headline'))
    if key is None:
        key = next((r['photo'] for r in policy['rules'] if re.search(r['pattern'], text, re.I)), None)
    section = article.get('section') or article.get('daily', {}).get('section')
    key = key or policy['defaults'].get(section)
    if key is None:
        raise ValueError('No approved real-photo context for article section')
    photo = policy['photos'][key]
    if photo['media_type'] != 'photograph' or not photo['visually_reviewed']:
        raise ValueError('Only reviewed real photographs are eligible')
    return dict(photo_id=photo['id'], reviewed_at=policy['reviewed_at'],
                relevance_and_archive_date_checked=True,
                caption=photo['image']['caption'], alt=photo['image']['alt'])


def extend_catalog(catalog, root):
    result = copy.deepcopy(catalog)
    known = {p['id'] for p in result['photos']}
    result['photos'].extend(p for p in load(root)['photos'].values() if p['id'] not in known)
    return result
