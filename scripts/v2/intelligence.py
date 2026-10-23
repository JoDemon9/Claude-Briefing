"""Additive editorial contract. Historical snapshots retain their accepted contract."""
import json
import hashlib
import importlib.util
import re
from pathlib import Path

MODES = {'morning':'morning_scan', 'midday':'midday_delta', 'evening':'evening_synthesis'}
STATUSES = ('NEW', 'UPDATED', 'REVERSAL', 'CORRECTION', 'UNCHANGED', 'UNKNOWN')
EVENT_STATUS = {'new':'NEW', 'substantive_update':'UPDATED', 'correction':'CORRECTION'}


def tags(values):
    if not isinstance(values, list) or len(values) > 12:
        raise ValueError('Tags must be a list of at most 12 driver labels')
    result = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError('Driver tags must be text')
        value = value.removeprefix('#').strip().casefold()
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value) or len(value) > 48:
            raise ValueError('Use short ASCII driver tags separated by hyphens')
        if value not in result:
            result.append(value)
    return result


def validate(edition, articles, root):
    if edition.get('intelligence_contract') != 1:
        current = hashlib.sha256((Path(root)/'templates/v2/content.schema.json').read_bytes()).hexdigest()
        if edition.get('status') == 'published' and edition.get('producer_contract',{}).get('content_schema_sha256') == current:
            raise ValueError('Current producer requires intelligence_contract=1; legacy contracts remain historical')
        return
    if edition.get('edition_mode') != MODES[edition['type']]:
        raise ValueError('Edition mode must match its scheduled slot')
    spec = importlib.util.spec_from_file_location('intelligence_baseline', Path(__file__).with_name('baseline.py'))
    baseline = importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
    if edition.get('baseline'):
        baseline.load(root, edition['baseline'], edition['published_at'])
    inventory = json.loads((Path(root)/'templates/v2/market-instruments.json').read_text(encoding='utf-8'))
    expected = {q['instrument'] for q in inventory}
    actual = [q.get('instrument') for q in edition['markets']]
    if len(actual) != len(set(actual)) or not expected <= set(actual):
        raise ValueError('Keep every market instrument exactly once; absent quotes are unavailable')
    for article in articles:
        if article.get('driver_tags', []) != tags(article.get('driver_tags', [])):
            raise ValueError('Driver tags must be normalized')
        status = article.get('change_status', 'UNKNOWN')
        if status not in STATUSES:
            raise ValueError('Unknown editorial change status')
        if status in ('NEW', 'UPDATED', 'REVERSAL', 'CORRECTION'):
            if not article.get('delta_update'):
                raise ValueError('Changed stories need an explicit factual delta')
        if status == 'UNCHANGED' and not article.get('baseline_origin'):
            raise ValueError('Unchanged stories need an explicit fingerprinted baseline')
        if status == 'UNCHANGED':
            baseline.validate_carried(article, root, edition['published_at'])
        permitted = {s['url'] for s in article['sources'] if s.get('access') == 'read' and s.get('used_for_claims')}
        if not set(article.get('analysis_sources', [])) <= permitted:
            raise ValueError('Analytical evidence must refer to read article sources')
        if any(article.get(k) for k in ('mechanics_and_incentives', 'second_order_effects', 'scenarios')) and not article.get('analysis_sources'):
            raise ValueError('Analytical layers need read supporting evidence')
