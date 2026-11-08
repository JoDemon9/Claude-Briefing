"""Historical exact-source identity hints. Never assign IDs or renew evidence."""
import copy
from datetime import datetime
import importlib.util
import json
from pathlib import Path


def module(name):
    spec=importlib.util.spec_from_file_location('continuity_'+name,Path(__file__).with_name(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def instant(value):
    return datetime.fromisoformat(value.replace('Z','+00:00'))


def match(candidates,history,aliases,reviewed,at,edition_id):
    """Expose all exact matches; shared roundups still require editorial judgment."""
    moment=instant(at) if isinstance(at,str) else at
    url=module('backend').normalized_url
    def canonical(sid):
        seen=set()
        while sid in aliases:
            if sid in seen:raise ValueError('Story alias cycle in continuity hints')
            seen.add(sid);sid=aliases[sid]
        return sid
    eligible=[r for r in history if r['edition_id']!=edition_id and instant(r['available_at'])<=moment]
    known={canonical(r['story_id']) for r in eligible}
    by_url={}
    for r in sorted(eligible,key=lambda r:instant(r['available_at'])):
        sid=canonical(r['story_id'])
        identity=canonical(r['identity']) if r.get('identity') else sid
        for source in r['sources']:
            by_url.setdefault(url(source['url']),{})[sid]={
                'story_id':sid,'identity':identity,'headline':r['headline'],
                'published_at':r['published_at'],'match':'exact_reporting_url'}
    explicit={}
    for source,review in reviewed.items():
        if instant(review['reviewed_at'])>moment:continue
        sid=canonical(review['story_id']);support=url(review['supporting_url'])
        if sid not in known or sid not in by_url.get(support,{}) or len(review.get('reason','').strip())<20:
            raise ValueError('Reviewed source identity needs a known story, its supporting URL and a reason: '+source)
        explicit[url(source)]={**by_url[support][sid],'match':'reviewed_source_identity'}
    result=copy.deepcopy(candidates)
    for candidate in result:
        matches={}
        for evidence in candidate['evidence']:
            addresses={evidence.get('url'),(evidence.get('source') or {}).get('url')}-{None}
            for address in sorted(addresses):
                key=url(address)
                for sid,record in by_url.get(key,{}).items():matches[sid]=record
                if key in explicit:matches.setdefault(explicit[key]['story_id'],explicit[key])
        if matches:
            candidate['known_story_matches']=[matches[sid] for sid in sorted(matches)]
    return result


def annotate(root,candidates,at,edition_id):
    root=Path(root)
    def read(name):
        p=root/'content'/name
        return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    return match(candidates,module('research').index(root)['stories'],read('day-story-aliases.json'),
                 read('story-source-identities.json'),at,edition_id)
