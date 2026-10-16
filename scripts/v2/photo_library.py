#!/usr/bin/env python3
"""Find and explicitly reuse already licensed, decoded photographs. No AI selection."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
from datetime import datetime
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]


def read(path):return json.loads(path.read_text())


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def asset(root,relative):
    if not relative.startswith('assets/editorial/') or Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('Only local editorial photographs can enter the library')
    path=root/'docs'/relative
    if path.is_symlink() or not path.resolve().is_relative_to((root/'docs/assets/editorial').resolve()):raise ValueError('Unsafe photo path')
    return path


def catalog(root=ROOT):
    root=Path(root);records={}
    for path in sorted((root/'content/editions').glob('*.json')):
        edition=read(path)
        if edition['status']!='published' or edition.get('image_review',{}).get('version')!=2:continue
        for relative in edition['articles']:
            source=root/'content'/relative
            if not source.resolve().is_relative_to((root/'content/articles').resolve()):raise ValueError('Unsafe photo source')
            article=read(source);photo=article.get('image')
            if not photo or any(not photo.get(k) for k in ('source_url','original_url','license','license_url','attribution','retrieved_at','caption','alt')):continue
            local=asset(root,photo['url'])
            if not local.is_file():continue
            with Image.open(local) as decoded:
                decoded.load()
                if min(decoded.size)<200:continue
                dimensions=list(decoded.size)
            key=sha(local)
            record=records.setdefault(key,{'id':key,'asset':photo['url'],'image':photo,'dimensions':dimensions,'references':[]})
            record['references'].append({'story_id':article['story_id'],'article_path':relative,'edition_id':edition['id']})
    return {'schema_version':1,'photos':[records[k] for k in sorted(records)],
            'policy':'Suggestions only. Check relevance, date, archive wording and rights before explicit reuse. Logos are excluded.'}


def find(root,story_id):
    return [r for r in catalog(root)['photos'] if any(ref['story_id']==story_id for ref in r['references'])]


def reuse(root,edition_id,article_id,photo_id,caption,alt,at,confirmed=False):
    root=Path(root).resolve()
    if not confirmed:raise ValueError('Explicit relevance and archive-date review is required')
    moment=datetime.fromisoformat(at.replace('Z','+00:00'))
    if moment.tzinfo is None:raise ValueError('Photo review requires a timezone')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}-(morning|midday|evening)',edition_id) or not re.fullmatch(r'[a-z0-9-]+',article_id):
        raise ValueError('Unsafe target article identity')
    edition=read(root/'content/editions'/f'{edition_id}.json')
    relative=f'articles/{edition_id}/{article_id}.json'
    if relative not in edition['articles']:raise ValueError('Photo target is absent from the edition')
    article_path=root/'content'/relative;article=read(article_path)
    if edition['status']=='published':raise ValueError('Use the correction workflow for a published edition')
    photo=next((r for r in catalog(root)['photos'] if r['id']==photo_id),None)
    if not photo:raise ValueError('Photograph is not in the verified library')
    source=asset(root,photo['asset'])
    if sha(source)!=photo_id:raise ValueError('Library image changed after review')
    target_relative=f'assets/editorial/{edition_id}/{article_id}.webp';target=asset(root,target_relative)
    if target==source:raise ValueError('Reuse target must have its own dated path')
    if min(len(caption.strip()),len(alt.strip()))<15:raise ValueError('A factual caption and accessible description are required')
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    # Retain original rights/retrieval provenance. reviewed_at records only the new editorial use.
    article['image']={**photo['image'],'url':target_relative,'caption':caption,'alt':alt,
        'reuse_review':{'source_asset':photo['asset'],'sha256':photo_id,'reviewed_at':at,'relevance_and_archive_date_checked':True}}
    spec=importlib.util.spec_from_file_location('photo_atomic',Path(__file__).with_name('atomic.py'))
    atomic=importlib.util.module_from_spec(spec);spec.loader.exec_module(atomic);atomic.write_json(article_path,article)
    return {'asset':target_relative,'sha256':photo_id,'original_retrieved_at':photo['image']['retrieved_at']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--story-id');parser.add_argument('--reuse');parser.add_argument('--edition');parser.add_argument('--article')
    parser.add_argument('--caption');parser.add_argument('--alt');parser.add_argument('--at')
    parser.add_argument('--confirm-relevance-and-archive-date',action='store_true');args=parser.parse_args()
    if args.reuse:
        result=reuse(args.root,args.edition,args.article,args.reuse,args.caption,args.alt,args.at,args.confirm_relevance_and_archive_date)
    else:result=find(args.root,args.story_id) if args.story_id else catalog(args.root)
    print(json.dumps(result,ensure_ascii=False,indent=2))
