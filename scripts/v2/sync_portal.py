#!/usr/bin/env python3
"""Save a complete public latest snapshot; no generation or remote writes."""
import argparse
import importlib.util
import json
import os
import shutil
import tempfile
from pathlib import Path

def sync(public_root, portal_root):
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
    snapshot,assets=latest.portal_snapshot(public_root,descriptor)
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
    target.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n', encoding='utf-8', newline='\n')
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',newline='\n',dir=docs,suffix='.html',delete=False) as staged:
        staged.write(snapshot)
        staged_path=Path(staged.name)
    try:
        os.replace(staged_path,docs/'index.html')
    finally:
        staged_path.unlink(missing_ok=True)
    print(f'Saved complete latest edition {descriptor["edition_id"]}; synced {len(records)} editions')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--public-root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--portal-root',type=Path,required=True)
    a=p.parse_args();sync(a.public_root,a.portal_root)
