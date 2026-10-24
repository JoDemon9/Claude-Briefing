"""Explicit content-addressed reuse; never infer novelty or refresh evidence times."""
import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
import re


def fingerprint(edition, articles):
    return hashlib.sha256(json.dumps([edition, articles], sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def load(root, reference, published_at=None):
    if not isinstance(reference, dict) or set(reference) != {'edition_id', 'fingerprint'}:
        raise ValueError('Baseline needs edition_id and fingerprint')
    eid, expected = reference['edition_id'], reference['fingerprint']
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}-(morning|midday|evening)', eid) or not re.fullmatch(r'[a-f0-9]{64}', expected):
        raise ValueError('Unsafe baseline reference')
    root = Path(root).resolve()
    edition_path = root/'content/editions'/(eid+'.json')
    if edition_path.is_symlink() or not edition_path.resolve().is_relative_to(root/'content/editions'):
        raise ValueError('Unsafe baseline edition')
    edition = json.loads(edition_path.read_text(encoding='utf-8'))
    articles = []
    for relative in edition['articles']:
        if not re.fullmatch(r'articles/[a-z0-9-]+/[a-z0-9-]+\.json', relative):
            raise ValueError('Unsafe baseline article')
        path = root/'content'/relative
        if path.is_symlink() or not path.resolve().is_relative_to(root/'content'):
            raise ValueError('Unsafe baseline article')
        articles.append(json.loads(path.read_text(encoding='utf-8')))
    if edition['status'] != 'published' or fingerprint(edition, articles) != expected:
        raise ValueError('Baseline fingerprint mismatch; review the exact baseline again')
    if published_at and datetime.fromisoformat(edition['published_at']) >= datetime.fromisoformat(published_at):
        raise ValueError('Baseline must precede the candidate')
    return edition, articles


def expand(payload, root):
    payload = copy.deepcopy(payload)
    carried = {}
    if not payload.get('baseline'):
        if payload.get('carry_story_ids'):
            raise ValueError('Carry requires an explicit baseline')
        return payload, carried
    edition, articles = load(root, payload['baseline'], payload['published_at'])
    if edition['id'] == payload['edition_id']:
        raise ValueError('An edition cannot inherit itself')
    requested = payload.get('carry_story_ids', [])
    if not isinstance(requested, list) or len(requested) != len(set(requested)):
        raise ValueError('Carry story IDs must be unique')
    available = {a['story_id']:a for a in articles}
    if not set(requested) <= set(available):
        raise ValueError('Carry references a story absent from the baseline')
    written = {a.get('story_id') or a.get('slug') for a in payload['articles']}
    if written & set(requested):
        raise ValueError('A story cannot be both rewritten and carried')
    slugs = {a.get('slug') or a.get('id') for a in payload['articles']}
    for sid in requested:
        doc = copy.deepcopy(available[sid])
        slug = doc['id']
        if slug in slugs:
            raise ValueError('Carried and written article slugs collide')
        slugs.add(slug)
        section = doc['daily']['section']
        doc.update(edition_id=payload['edition_id'], url=f'articles/{payload["edition_id"]}/{slug}.html',
                   category={'cyprus':'Κύπρος','world':'Διεθνή','sports':'Αθλητικά'}[section],
                   change_status='UNCHANGED', baseline_origin=copy.deepcopy(payload['baseline']))
        doc.pop('delta_update', None)
        doc['daily']['events'] = []
        carried[slug] = doc
        payload['articles'].append({'slug':slug, 'story_id':sid, 'section':section, 'sources':doc['sources']})
    return payload, carried


def validate_carried(article, root, published_at):
    _, records = load(root, article['baseline_origin'], published_at)
    old = next((a for a in records if a['story_id']==article['story_id']), None)
    if old is None:
        raise ValueError('Carried story is absent from its baseline')
    expected = copy.deepcopy(old)
    expected.update(edition_id=article['edition_id'], url=article['url'], category=article['category'],
                    change_status='UNCHANGED', baseline_origin=article['baseline_origin'])
    expected.pop('delta_update', None)
    expected['daily']['events'] = []
    if expected != article:
        raise ValueError('Carried evidence/content changed; submit a reviewed update instead')
