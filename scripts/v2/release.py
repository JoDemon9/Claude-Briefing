#!/usr/bin/env python3
"""Validate/stage public files and verify the served release. No scheduling or delivery."""
import argparse
import hashlib
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import shutil
import tempfile
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
BASE = 'https://jodemon9.github.io/Claude-Briefing/'
SUFFIXES = {'.html', '.css', '.js', '.json', '.png', '.jpg', '.jpeg', '.webp', '.svg', '.gif', '.ico', '.woff', '.woff2'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(value):
    path = Path(value)
    return not path.is_absolute() and bool(path.parts) and all(part not in {'.', '..'} and not part.startswith('.') for part in path.parts)


def manifest(root=ROOT):
    """An integrity record is not an attestation that the news claims are true."""
    root = Path(root).resolve()
    docs = root/'docs'
    records = json.loads((docs/'data/editions.json').read_text(encoding='utf-8'))
    if not records:
        raise ValueError('The release has no published editions')
    for record in records:
        if record['status'] != 'published' or not safe_path(record['url']) or not (docs/record['url']).is_file():
            raise ValueError('Missing or unsafe published edition')
    files = {}
    for path in sorted(docs.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(docs).as_posix()
        if path.is_symlink() or not safe_path(relative):
            raise ValueError('Symlinks/hidden paths cannot enter the public package')
        if relative == 'data/release.json':
            continue
        if path.suffix.lower() not in SUFFIXES:
            raise ValueError('Non-public file in docs: '+relative)
        files[relative] = digest(path)
    editions = sorted((root/'content/editions').glob('*.json'))
    source_paths = [root/'content/legacy-editions.json', *editions]
    for path in editions:
        edition = json.loads(path.read_text(encoding='utf-8'))
        for relative in edition['articles']:
            if not safe_path(relative):
                raise ValueError('Unsafe source path')
            source_paths.append(root/'content'/relative)
    source_paths += sorted((root/'templates/v2').rglob('*'))
    source_paths += sorted((root/'scripts/v2').glob('*.py'))
    source_paths += sorted((root/'content').glob('*.json'))
    source_paths += [root/name for name in ('AGENTS.md','BRIEFING_SPEC.md','CHATGPT_TASK_INSTRUCTIONS.md')]
    source_paths += sorted((root/'prompts').glob('*.md'))
    source_paths += sorted((root/'tests').rglob('*.py'))
    source_paths += sorted((root/'tests/fixtures').rglob('*.json'))
    source_paths += sorted((root/'.github/workflows').glob('*.yml'))
    source_paths += [root/'requirements-v2.txt']
    sources = {p.relative_to(root).as_posix(): digest(p) for p in source_paths if p.is_file()}
    identity = hashlib.sha256(json.dumps({'sources': sources, 'files': files}, sort_keys=True).encode()).hexdigest()
    return {'schema_version': 1, 'release_id': identity, 'edition_ids': [r['id'] for r in records],
            'sources': sources, 'files': files,
            'verification': 'File integrity only; editorial review and Pages verification are separate.'}


def record(root=ROOT):
    root = Path(root)
    receipt = manifest(root)
    target = root/'docs/data/release.json'
    spec=importlib.util.spec_from_file_location('record_atomic',Path(__file__).with_name('atomic.py'))
    atomic=importlib.util.module_from_spec(spec);spec.loader.exec_module(atomic)
    atomic.write_json(target,receipt)
    return receipt


def stage(root, destination):
    """Export only the validated docs allowlist; never private Markdown or notes."""
    root, destination = Path(root).resolve(), Path(destination).resolve()
    if destination == root or destination.is_relative_to(root/'docs') or root.is_relative_to(destination):
        raise ValueError('Unsafe release destination')
    if destination.exists():
        raise ValueError('Release destination must be new')
    receipt = record(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix='oracle-package-') as directory:
        candidate = Path(directory)/'package'
        candidate.mkdir()
        for relative in [*receipt['files'], 'data/release.json']:
            source = root/'docs'/relative
            if relative in receipt['files'] and digest(source) != receipt['files'][relative]:
                raise ValueError('Release changed during export')
            target = candidate/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        candidate.rename(destination)
    return receipt


def verify_live(root=ROOT, base=BASE, opener=None, full=False, workers=6):
    """Check exact deployed bytes, not just HTTP 200 or a green code test."""
    if base != BASE:
        raise ValueError('Only the configured public Pages origin may be verified')
    root = Path(root)
    receipt = json.loads((root/'docs/data/release.json').read_text(encoding='utf-8'))
    if manifest(root)['release_id'] != receipt['release_id']:
        raise ValueError('Rebuild the receipt; local files changed')
    opener = opener or urllib.request.urlopen
    output = root/'.work/publication-check.json'
    try:
        previous = json.loads(output.read_text())
        trusted = previous.get('files',{}) if previous.get('status')=='verified' and previous.get('base_url')==base else {}
    except (OSError,ValueError,TypeError):
        trusted = {}
    changed = {name for name,sha in receipt['files'].items() if trusted.get(name)!=sha}
    critical = {'data/release.json','data/editions.json'}
    critical.update(name for name in ('index.html','latest.html','data/latest.json','today.html','data/day-latest.json','data/days.json','data/capabilities.json','data/story-registry.json','data/freshness.json') if name in receipt['files'])
    records = json.loads((root/'docs/data/editions.json').read_text())
    current_date = max((r.get('date','') for r in records),default='')
    for record in records:
        if record.get('date','') == current_date:
            critical.add(record['url'])
            critical.update(name for name in receipt['files'] if name.startswith(('articles/'+record['id']+'/', 'data/articles/'+record['id']+'/')))
    for descriptor in ('data/latest.json','data/day-latest.json'):
        if descriptor in receipt['files']:
            info=json.loads((root/'docs'/descriptor).read_text())
            critical.update(urlsplit(url).path.removeprefix('/Claude-Briefing/') for url in info.get('asset_sha256',{}))
    names = ['data/release.json',*sorted((set(receipt['files']) if full else changed)|critical-{'data/release.json'})]
    def check(name):
        expected = digest(root/'docs'/name)
        request = urllib.request.Request(base+name+'?release='+receipt['release_id'], headers={'User-Agent': 'OracleReleaseCheck/1.0', 'Cache-Control': 'no-cache'})
        for attempt in range(3):
            try:
                with opener(request, timeout=20) as response:
                    if urlsplit(response.geturl()).hostname != 'jodemon9.github.io' or response.status != 200:
                        raise ValueError('Unexpected deployed destination: '+name)
                    raw = response.read(10_000_001)
                break
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if attempt == 2:
                    raise ValueError('Public release could not be reached: '+name) from None
                time.sleep(attempt+1)
        if len(raw) > 10_000_000 or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('Pages does not serve this release: '+name)
    # Verify the release pointer first, then fetch assets with bounded concurrency.
    check('data/release.json')
    with ThreadPoolExecutor(max_workers=max(1,min(workers,8))) as pool:
        list(pool.map(check,names[1:]))
    result = {'schema_version': 2, 'release_id': receipt['release_id'], 'status': 'verified', 'base_url': base,
              'mode':'full' if full or not trusted else 'changed_and_current',
              'checked_files':len(names),'files':receipt['files']}
    spec=importlib.util.spec_from_file_location('release_atomic',Path(__file__).with_name('atomic.py'))
    atomic=importlib.util.module_from_spec(spec);spec.loader.exec_module(atomic)
    atomic.write_json(output,result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--stage', type=Path)
    parser.add_argument('--verify-live', action='store_true')
    parser.add_argument('--full', action='store_true', help='Audit every archive file, independent of the last verified release')
    args = parser.parse_args()
    if args.verify_live:
        print(json.dumps(verify_live(args.root,full=args.full), ensure_ascii=False))
    elif args.stage:
        print('Staged release', stage(args.root, args.stage)['release_id'])
    else:
        print('Recorded release', record(args.root)['release_id'])
