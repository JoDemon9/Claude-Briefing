"""Conservative dependency cache. Missing, corrupt or altered outputs force a full build."""
import hashlib
import json
import re
from pathlib import Path


def hashes(directory):
    return {p.relative_to(directory).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob('*')) if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def inputs(root, scripts):
    common = {'templates':hashes(root/'templates/v2'), 'scripts':hashes(scripts),
              'assets':hashes(root/'docs/assets')}
    common['runtime_policy']=(root/'BRIEFING_RUNTIME.md').read_text(encoding='utf-8') if (root/'BRIEFING_RUNTIME.md').exists() else None
    for name in ('legacy-editions.json','day-story-aliases.json','story-identity-reviews.json'):
        path = root/'content'/name
        common[name] = path.read_text(encoding='utf-8') if path.exists() else None
    editions = {}
    for path in sorted((root/'content/editions').glob('*.json')):
        edition = json.loads(path.read_text(encoding='utf-8'))
        if any(not re.fullmatch(r'articles/[a-z0-9-]+/[a-z0-9-]+\.json',relative) for relative in edition['articles']):
            raise ValueError('Unsafe article path')
        editions[edition['id']] = {'date':edition['date'], 'fingerprint':fingerprint([edition,
            [(root/'content'/relative).read_text(encoding='utf-8') for relative in edition['articles']]])}
    return {'common':fingerprint(common),'editions':editions}


def affected(root, scripts, enabled):
    if not enabled:
        return None
    current = inputs(root,scripts)
    try:
        saved = json.loads((root/'.work/build-cache.json').read_text(encoding='utf-8'))
        outputs = hashes(root/'docs'); outputs.pop('data/release.json',None)
        if not enabled or saved['inputs']['common'] != current['common'] or saved['outputs'] != outputs:
            return None
        prior = saved['inputs']['editions']
        changed_dates = {item['date'] for key,item in {**prior,**current['editions']}.items()
                         if prior.get(key) != current['editions'].get(key)}
        # All slots of a changed day depend on its edition navigation and selected stories.
        return {key for key,value in current['editions'].items() if value['date'] in changed_dates}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def save(root, scripts, atomic):
    outputs = hashes(root/'docs'); outputs.pop('data/release.json',None)
    atomic.write_json(root/'.work/build-cache.json', {'inputs':inputs(root,scripts),'outputs':outputs})
