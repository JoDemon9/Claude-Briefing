#!/usr/bin/env python3
"""Copy only the public edition registry; no generation, scheduling or remote writes."""
import argparse
import json
from pathlib import Path

def sync(public_root, portal_root):
    records=json.loads((public_root/'docs/data/editions.json').read_text())
    for record in records:
        if record['status']!='published' or not (public_root/'docs'/record['url']).is_file():
            raise ValueError('Only existing published editions may appear in the portal')
    target=portal_root/'docs/data/editions.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    print(f'Synced {len(records)} published editions to {target}')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--public-root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--portal-root',type=Path,required=True)
    a=p.parse_args();sync(a.public_root,a.portal_root)
