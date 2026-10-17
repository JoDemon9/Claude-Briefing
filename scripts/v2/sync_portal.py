#!/usr/bin/env python3
"""Save a complete public latest snapshot; no generation or remote writes."""
import argparse
import importlib.util
import json
import os
import shutil
import tempfile
from pathlib import Path

def _sync(public_root, portal_root):
    records=json.loads((public_root/'docs/data/editions.json').read_text(encoding='utf-8'))
    for record in records:
        if record['status']!='published' or not (public_root/'docs'/record['url']).is_file():
            raise ValueError('Only existing published editions may appear in the portal')
    public_root,portal_root=Path(public_root).resolve(),Path(portal_root).resolve()
    descriptor=json.loads((public_root/'docs/data/latest.json').read_text(encoding='utf-8'))
    spec=importlib.util.spec_from_file_location('portal_latest',Path(__file__).with_name('latest.py'))
    latest=importlib.util.module_from_spec(spec);spec.loader.exec_module(latest)
    if descriptor['status']!='published' or descriptor['edition_id']!=latest.newest(records)['id']:
        raise ValueError('Latest snapshot must match the published registry')
    day_path=public_root/'docs/data/day-latest.json'
    is_day=day_path.is_file()
    if is_day:
        descriptor=json.loads(day_path.read_text())
        day=json.loads((public_root/'docs/data/days'/f'{descriptor["day_id"]}.json').read_text())
        if day['date']!=max(r['date'] for r in records) or day['date']!=descriptor['day_id']:
            raise ValueError('Daily snapshot must match the latest published date')
    snapshot,assets=latest.portal_snapshot(public_root,descriptor,'today.html' if is_day else 'latest.html')
    docs=portal_root/'docs'
    docs.mkdir(parents=True,exist_ok=True)
    target=docs/'data/editions.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    archive=docs/'portal-archive.html'
    if (docs/'index.html').exists() and not archive.exists():
        shutil.copyfile(docs/'index.html',archive)
    for relative,source in assets.items():
        destination=docs/'assets/latest-snapshot'/descriptor['version']/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,destination)
    shutil.copyfile(public_root/'docs/assets/latest-briefing.js',docs/'assets/latest-briefing.js')
    shutil.copyfile(public_root/'docs/latest.html',docs/'data/latest-snapshot.html')
    shutil.copyfile(public_root/'docs/data/latest.json',docs/'data/latest.json')
    if is_day:
        shutil.copyfile(public_root/'docs/today.html',docs/'data/day-snapshot.html')
        shutil.copyfile(day_path,docs/'data/day-latest.json')
        shutil.copyfile(public_root/'docs/data/days.json',docs/'data/days.json')
    target.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n', encoding='utf-8', newline='\n')
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',newline='\n',dir=docs,suffix='.html',delete=False) as staged:
        staged.write(snapshot)
        staged_path=Path(staged.name)
    try:
        os.replace(staged_path,docs/'index.html')
    finally:
        staged_path.unlink(missing_ok=True)
    # Existing publication actions already call sync; keep the central receipt in
    # step with its complete snapshot without requiring a new scheduler/prompt.
    release_script=portal_root/'scripts/daily_release.py'
    if is_day and release_script.is_file():
        release_spec=importlib.util.spec_from_file_location('central_daily_release',release_script)
        release=importlib.util.module_from_spec(release_spec);release_spec.loader.exec_module(release)
        release.record(portal_root)
    print(f'Saved complete newspaper {descriptor.get("day_id",descriptor.get("edition_id"))}; synced {len(records)} editions')

def sync(public_root, portal_root):
    """Prepare every descriptor/asset/receipt before replacing the saved newspaper."""
    public_root,portal_root=Path(public_root).resolve(),Path(portal_root).resolve()
    atomic_spec=importlib.util.spec_from_file_location('sync_atomic',Path(__file__).with_name('atomic.py'))
    atomic=importlib.util.module_from_spec(atomic_spec);atomic_spec.loader.exec_module(atomic)
    with atomic.lock(portal_root/'.work/publication.lock'):
        # Avoid synchronisers recreating staged files during promotion/cleanup.
        # Keep the sibling fallback when system temp is on another filesystem.
        staging_parent=Path(tempfile.gettempdir()).resolve()
        if staging_parent.stat().st_dev != portal_root.stat().st_dev:
            staging_parent=portal_root.parent
        with tempfile.TemporaryDirectory(prefix='oracle-sync-',dir=staging_parent) as directory:
            candidate=Path(directory)/'candidate';candidate.mkdir()
            for name in ('docs','scripts'):
                if (portal_root/name).exists():shutil.copytree(portal_root/name,candidate/name)
            _sync(public_root,candidate)
            live=portal_root/'docs';backup=Path(directory)/'previous-docs'
            had_live=live.exists()
            if had_live:os.replace(live,backup)
            try:
                os.replace(candidate/'docs',live)
            except BaseException:
                if had_live:os.replace(backup,live)
                raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--public-root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--portal-root',type=Path,required=True)
    a=p.parse_args();sync(a.public_root,a.portal_root)
