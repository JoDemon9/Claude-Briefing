"""Versioned producer contract, shared identity registry and dated freshness checks.

All reports are deterministic as of the edition; they do not re-date historical news.
"""
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

PROTOCOL = 'oracle-briefing/3'
POLICY_START = '2026-10-16'


def digest(value):
    return hashlib.sha256(value).hexdigest()


def capabilities(root):
    schema = json.loads((root/'templates/v2/content.schema.json').read_text(encoding='utf-8'))
    return {'contract_version': 1, 'producer_protocol': PROTOCOL,
            'content_schema_sha256': digest((root/'templates/v2/content.schema.json').read_bytes()),
            'edition_schema_versions': [schema['properties']['schema_version']['const']],
            'edition_fields': sorted(schema['properties']),
            'article_fields': sorted(schema['$defs']['article']['properties']),
            'features': ['sports_interest', 'selection_review', 'daily.follow_ups', 'story_identity',
                         'story_registry', 'freshness', 'resumable_publication', 'research_packets', 'photo_reuse', 'change_aware_checks', 'section_coverage_v2', 'ci_built_candidate', 'favourite_news_links', 'bounded_context_views', 'producer_handoff', 'collapsible_findings', 'minimum_daily_checks', 'single_payload_compiler', 'partial_availability', 'shared_v3_rendering'],
            'daily_quality_checks':['content','preview','integrity'],
            'authoring_formats':['json','oracle-markdown/1'],
            'synthesis_protocol':'oracle-synthesis/1',
            'briefing_policy':'depth-markets-v1',
            'prefetch_before_model':True,
            'intelligence_contract':1,
            'explicit_baseline_reuse':True,
            'archive_browser_audit':'Explicit full profile only; not a daily publication requirement.',
            'producer_model_policy':'User-selected ChatGPT model, including Luna; identical editorial and release requirements. No external model API.',
            'section_targets': {'world': 4, 'cyprus': 4},
            'section_preferred_range': [4, 5],
            'selection_policy': 'balanced-v1',
            'selection_policy_required_from': '2026-10-28',
            'selection_review_version': 2,
            'section_coverage_required_from': '2026-10-18-evening',
            'favourite_news_required_from':'2026-10-19',
            'favourite_news_max_age_minutes':720,
            'editorial_protocol':'oracle-editorial/1',
            'runtime_policy_sha256':digest((root/'BRIEFING_SPEC.md').read_bytes()) if (root/'BRIEFING_SPEC.md').exists() else None,
            'required_from_local_date': POLICY_START,
            'reading_review_version': 2, 'image_review_version': 2,
            'schedules': 'Existing ChatGPT tasks; this contract creates no schedule.'}


def edition_fingerprint(edition, articles):
    return digest(json.dumps([edition,articles],sort_keys=True,ensure_ascii=False).encode())


def reporting_fingerprint(edition, articles):
    """Allow image-only archive maintenance without rewriting an old editorial contract."""
    e = {k:v for k,v in edition.items() if k not in ('image_review','image_revision_at','photo_policy')}
    aa = [{k:v for k,v in a.items() if k not in ('image','image_unavailable_reason')} for a in articles]
    return edition_fingerprint(e, aa)


def check_contract(root, edition, articles=()):
    declared = edition.get('producer_contract')
    if not declared:
        if edition['date'] >= POLICY_START and edition['status'] == 'published':
            raise ValueError('Published editions require producer_contract from fresh main capabilities')
        return
    if edition['date'] >= POLICY_START and edition['status']=='published' and any(not a.get('story_identity') for a in articles):
        raise ValueError('New articles require a stable, explicit story_identity event key')
    supported = capabilities(root)
    if declared != {k: supported[k] for k in ('producer_protocol', 'content_schema_sha256')}:
        history=root/'docs/data/edition-contracts.json'
        saved=json.loads(history.read_text()).get(edition['id'],{}) if history.exists() else {}
        if saved.get('contract')==declared and saved.get('source_sha256')==edition_fingerprint(edition,articles):
            return  # An unchanged historical edition keeps its accepted contract.
        if (edition.get('image_revision_at') and saved.get('contract')==declared
                and saved.get('reporting_sha256')==reporting_fingerprint(edition,articles)):
            return  # Only image metadata/bytes changed; all reporting remains exact.
        raise ValueError('Producer/renderer contract mismatch; fetch current main capabilities')
    if (edition['status'] == 'published' and edition['date'] >= supported['selection_policy_required_from']
            and edition.get('selection_policy') != supported['selection_policy']):
        raise ValueError('New current-contract editions require selection_policy=balanced-v1')


def instant(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Freshness timestamps require a timezone')
    return parsed


def freshness(edition, articles, now=None):
    """now is only for a private current audit; generated snapshots use publication time."""
    timestamp = now or edition.get('editorial_completed_at') or edition['published_at']
    if not timestamp:
        if edition.get('freshness') or any(a.get('freshness') for a in articles):
            raise ValueError('Structured freshness requires an edition timestamp')
        return {'edition_id':edition['id'],'as_of':None,'records':[], 'coverage':'legacy_unstructured'}
    as_of = instant(timestamp)
    records = [(edition['id'], r) for r in edition.get('freshness', [])]
    records += [(a['story_id'], r) for a in articles for r in a.get('freshness', [])]
    ids = set()
    results = []
    for owner, record in records:
        key = (owner, record['id'])
        if key in ids:
            raise ValueError('Duplicate freshness record: '+record['id'])
        ids.add(key)
        times = {k: instant(record[k]) for k in ('checked_at', 'valid_from', 'valid_until', 'starts_at', 'ends_at', 'recheck_at') if record.get(k)}
        if times['checked_at'] > as_of and now is None:
            raise ValueError('Freshness check cannot be later than edition completion')
        for start, end in (('valid_from','valid_until'), ('starts_at','ends_at')):
            if start in times and end in times and times[start] > times[end]:
                raise ValueError('Freshness interval is reversed: '+record['id'])
        if 'recheck_at' in times and times['recheck_at'] < times['checked_at']:
            raise ValueError('Recheck must follow the source check')
        state = 'current'
        if times.get('valid_from', as_of) > as_of:
            state = 'upcoming'
        if times.get('starts_at', as_of) > as_of:
            state = 'upcoming'
        if 'starts_at' in times and times['starts_at'] <= as_of:
            state = 'outcome_needs_check'
        if 'ends_at' in times and times['ends_at'] <= as_of:
            state = 'ended'
        if 'valid_until' in times and times['valid_until'] <= as_of:
            state = 'expired'
        if state in ('current','upcoming') and 'recheck_at' in times and times['recheck_at'] <= as_of:
            state = 'recheck_due'
        results.append({'owner': owner, **record, 'state': state})
    if edition['date'] >= POLICY_START and edition['status'] == 'published':
        if any(p['id'] == 'weather' for p in edition.get('panels', [])) and not any(r['kind'] == 'weather' for _,r in records):
            raise ValueError('Weather panel requires structured forecast validity')
        stale = [r['id'] for r in results if r['state'] in ('expired','recheck_due','outcome_needs_check','ended') and not r.get('historical_context')]
        if stale and now is None:
            raise ValueError('Refresh or explicitly mark historical freshness records: '+', '.join(stale))
    return {'edition_id': edition['id'], 'as_of': as_of.isoformat(), 'records': results,
            'coverage': 'structured' if records else 'legacy_unstructured'}


def normalized_url(value):
    parsed = urlsplit(value)
    query = [(k,v) for k,v in parse_qsl(parsed.query) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid')]
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip('/'), urlencode(sorted(query)), ''))


def story_registry(bundles, aliases, reviews=None, enforce_reviews=True):
    reviews = reviews or {}
    def canonical(sid):
        seen = set()
        while sid in aliases:
            if sid in seen:
                raise ValueError('Story alias cycle')
            seen.add(sid); sid = aliases[sid]
        return sid
    for sid in aliases:
        canonical(sid)
    # The day composer uses single-hop aliases; require an unambiguous flat map.
    if any(target in aliases for target in aliases.values()):
        raise ValueError('Flatten story aliases before publication')
    stories, titles, sources, identities = {}, {}, {}, {}
    identity_by_story={}
    issues = []
    for edition, articles in bundles:
        in_edition = set()
        for article in articles:
            sid = canonical(article['story_id'])
            if sid in in_edition:
                raise ValueError('Conflicting story IDs in edition: '+sid)
            in_edition.add(sid)
            reference = {'edition_id':edition['id'], 'article_id':article['id'], 'date':edition['date'], 'url':article['url']}
            stories.setdefault(sid, []).append(reference)
            if article.get('story_identity'):
                identity=article['story_identity']
                if sid in identity_by_story and identity_by_story[sid]!=identity:
                    raise ValueError('Conflicting identity for stable story ID: '+sid)
                identity_by_story[sid]=identity
                identities.setdefault(identity,set()).add(sid)
            title = ' '.join(re.findall(r'\w+', article['headline'].casefold()))
            titles.setdefault(title, set()).add(sid)
            for source in article['sources']:
                if source.get('used_for_claims') and source.get('access') == 'read':
                    sources.setdefault(normalized_url(source['url']), set()).add(sid)
    for kind, groups in (('same_headline',titles), ('shared_reporting_url',sources), ('shared_identity',identities)):
        for value, ids in sorted(groups.items()):
            if len(ids) < 2:
                continue
            key = digest(json.dumps([kind,value,sorted(ids)],ensure_ascii=False).encode())
            review = reviews.get(key)
            if review and (review.get('decision') != 'distinct_stories' or len(review.get('reason','').strip()) < 20):
                raise ValueError('Identity review needs a decision and meaningful reason: '+key)
            issues.append({'id':key,'kind':kind,'story_ids':sorted(ids),'evidence':value,
                           'review':review, 'status':'reviewed' if review else 'needs_review'})
    known = set(stories)
    for origin, target in aliases.items():
        if canonical(target) not in known:
            raise ValueError('Story alias target is absent: '+origin)
    for edition, _ in bundles:
        for link in edition.get('daily',{}).get('follow_ups',[]):
            origin, target = (canonical(link[k]) for k in ('from_story_id','to_story_id'))
            if origin not in known or target not in known or origin == target:
                raise ValueError('Invalid follow-up story identity')
            times = {e['id']:instant(e['published_at']) for e,_ in bundles if e.get('published_at')}
            for sid in (origin,target):
                if not any(r['date']==edition['date'] and r['edition_id'] in times and times[r['edition_id']]<=times[edition['id']] for r in stories[sid]):
                    raise ValueError('Follow-up references unavailable coverage')
    for issue in issues:
        if enforce_reviews and issue['status']=='needs_review' and any(r['date'] >= POLICY_START for sid in issue['story_ids'] for r in stories[sid]):
            raise ValueError('Editorial story identity review required: '+issue['id'])
    return {'schema_version':1,'stories':dict(sorted(stories.items())), 'aliases':aliases,
            'identities':dict(sorted(identity_by_story.items())),
            'issues':issues, 'matching_policy':'Candidates require editorial review; never auto-merge.'}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--audit-freshness',action='store_true')
    parser.add_argument('--audit-identities',action='store_true',help='Show candidates for review without bypassing publication gates')
    parser.add_argument('--at',help='Explicit timezone-aware audit time; omitted means current UTC')
    args=parser.parse_args()
    if args.audit_identities:
        bundles=[]
        for path in sorted((args.root/'content/editions').glob('*.json')):
            edition=json.loads(path.read_text())
            if edition['status']=='published':
                paths=[args.root/'content'/relative for relative in edition['articles']]
                if any(not p.resolve().is_relative_to((args.root/'content/articles').resolve()) for p in paths):
                    raise ValueError('Unsafe article input path')
                bundles.append((edition,[json.loads(p.read_text()) for p in paths]))
        read=lambda name:json.loads((args.root/'content'/name).read_text()) if (args.root/'content'/name).exists() else {}
        print(json.dumps(story_registry(bundles,read('day-story-aliases.json'),read('story-identity-reviews.json'),enforce_reviews=False),ensure_ascii=False,indent=2))
    elif args.audit_freshness:
        from datetime import timezone
        now=args.at or datetime.now(timezone.utc).isoformat()
        report=[]
        for path in sorted((args.root/'content/editions').glob('*.json')):
            edition=json.loads(path.read_text())
            if edition['status']=='published':
                articles=[json.loads((args.root/'content'/p).read_text()) for p in edition['articles']]
                report.append(freshness(edition,articles,now=now))
        print(json.dumps({'audit_at':now,'editions':report},ensure_ascii=False,indent=2))
    else:
        print(json.dumps(capabilities(args.root),ensure_ascii=False,indent=2))
