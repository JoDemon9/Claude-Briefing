#!/usr/bin/env python3
"""Reproducible saved-output measurements; never infer actual account quota or run traces."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tiktoken

ROOT=Path(__file__).resolve().parents[2]


def measure(root,eid):
    edition=json.loads((root/'content/editions'/(eid+'.json')).read_text(encoding='utf-8'))
    articles=[json.loads((root/'content'/p).read_text(encoding='utf-8')) for p in edition['articles']]
    spec=importlib.util.spec_from_file_location('audit_compose',Path(__file__).with_name('compose.py'))
    compose=importlib.util.module_from_spec(spec);spec.loader.exec_module(compose)
    raw={k:copy.deepcopy(edition[k]) for k in (*compose.REQUIRED,*compose.OPTIONAL) if k in edition}
    raw.update(edition_id=eid,edition_mode=compose.MODES[edition['type']],title=edition['title'],articles=[])
    generated={'id','edition_id','category','url','image','image_unavailable_reason','baseline_origin'}
    for article in articles:
        item={k:v for k,v in article.items() if k not in generated}
        item.update(slug=article['id'],section=article['daily']['section'],is_lead=article['story_id']==edition['daily']['lead_story_id'])
        image=article.get('image')
        if image:
            photo=image.get('reuse_review',{}).get('sha256') or hashlib.sha256((root/'docs'/image['url']).read_bytes()).hexdigest()
            item['image_selection']=dict(photo_id=photo,reviewed_at=image.get('reuse_review',{}).get('reviewed_at') or edition['image_review']['completed_at'],relevance_and_archive_date_checked=True,caption=image['caption'],alt=image['alt'])
        raw['articles'].append(item)
    serialized=json.dumps(raw,ensure_ascii=False,separators=(',',':'))
    enc=tiktoken.get_encoding('o200k_base')
    def prose(value):
        if isinstance(value,str):return len(value.split())
        if isinstance(value,list):return sum(prose(v) for v in value)
        if isinstance(value,dict):return sum(prose(v) for k,v in value.items() if k not in ('kind','heading'))
        return 0
    fields=('summary','sections','newspaper_analysis','mechanics_and_incentives','second_order_effects','scenarios','delta_update')
    return dict(edition_id=eid,articles=len(articles),market_rows=len(edition['markets']),
        saved_read_article_urls=len({s['url'] for a in articles for s in a['sources'] if s.get('access')=='read' and s.get('used_for_claims')}),
        summary_words=sum(len(a['summary'].split()) for a in articles),
        emitted_article_prose_words=sum(prose(a[k]) for a in articles for k in fields if k in a),
        equivalent_full_payload_utf8_bytes=len(serialized.encode()),
        equivalent_full_payload_reference_tokens=len(enc.encode(serialized)),
        new_synthesis_reference_token_cap=6500 if edition['type']=='morning' else 4000)


def audit(root=ROOT):
    root=Path(root);editions=[]
    for slot in ('morning','midday','evening'):
        path=max((root/'content/editions').glob('*-'+slot+'.json'))
        editions.append(measure(root,path.stem))
    return dict(version=1,tokenizer='o200k_base',editions=editions,
        legacy=dict(search_cap=None,url_read_cap=None,total_tool_cap=None,actual_searches=None,actual_url_reads=None,actual_tool_calls=None,
            reason='Repository content records evidence, not a model/tool transcript. Legacy prompts have no finite ceiling. Batch calls/retries and source access cannot be reconstructed.'),
        new=dict(morning=dict(searches=5,url_reads=2,total_tools=10,authored_stories=6,output_reference_tokens=6500),
            midday=dict(searches=3,url_reads=1,total_tools=7,authored_stories=4,output_reference_tokens=4000),
            evening=dict(searches=3,url_reads=1,total_tools=7,authored_stories=4,output_reference_tokens=4000)),
        limits='Saved payload replay counts are reference tokens, not actual generated/run tokens or an account-quota measurement. Prompt caps are instructions; the compiler enforces declared tool counts, output tokens and story counts, not hidden provider telemetry.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--output',type=Path)
    args=p.parse_args();result=json.dumps(audit(args.root),ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.write_text(result,encoding='utf-8')
    print(result)
