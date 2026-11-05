#!/usr/bin/env python3
"""Compile one reviewed payload. Mechanical work never establishes editorial facts."""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import importlib.util
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
MODES = {'morning': 'morning_scan', 'midday': 'midday_delta', 'evening': 'evening_synthesis'}
TEAMS = ('omonoia', 'manutd', 'realmadrid', 'formula1')
REQUIRED = ('published_at', 'editorial_completed_at', 'reading_review', 'articles')
OPTIONAL = ('executive_scan', 'daily', 'markets', 'sports', 'panels', 'opportunities',
            'freshness', 'selection_review', 'image_review', 'changes', 'market_summary',
            'market_next_event', 'market_movers', 'market_core', 'market_notes',
            'calculator', 'fast_wire', 'delta_log', 'baseline', 'synthesis_profile', 'prefetch_provenance', 'selection_policy', 'briefing_policy', 'technology_briefing',
            'financial_policy', 'financial_insights', 'financial_review')


def module(name):
    spec = importlib.util.spec_from_file_location('compose_' + name, Path(__file__).with_name(name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def instant(value):
    return module('backend').instant(value)


def ensure_str_list(value):
    if isinstance(value, str):
        value = [line.strip() for line in value.splitlines() if line.strip()]
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError('Expected text or a list of nonempty strings')
    return value


def safe_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value):
        raise ValueError('Explicit safe ASCII article/story identity required')
    return value


def sources(raw):
    if not isinstance(raw, list) or not raw:
        raise ValueError('Real, explicitly reviewed source records are required')
    result = copy.deepcopy(raw)
    for source in result:
        if not isinstance(source, dict):
            raise ValueError('Source URLs alone do not establish access, dates or provenance')
        if 'publisher' not in source and source.get('name'):
            source['publisher'] = source.pop('name')
        required = ('publisher', 'url', 'published_at', 'retrieved_at', 'reporting_group',
                    'kind', 'access', 'used_for_claims')
        if any(key not in source for key in required):
            raise ValueError('Incomplete source evidence; unknown publication time is null')
        url = urlsplit(source['url'])
        if url.scheme != 'https' or not url.hostname or url.username or url.password:
            raise ValueError('Source must have an explicit HTTPS URL')
        if source['access'] == 'inaccessible' and source['used_for_claims']:
            raise ValueError('Inaccessible evidence cannot support claims')
    return result


def reviewed_image(raw, edition_id, slug, root, catalog):
    """Select by explicit photo ID, retaining that exact photo's rights provenance."""
    review = raw.get('image_selection')
    if not isinstance(review, dict) or review.get('relevance_and_archive_date_checked') is not True:
        raise ValueError('Explicit image_selection and relevance/archive-date review required')
    instant(review['reviewed_at'])
    library = module('photo_library')
    photo = next((p for p in catalog['photos'] if p['id'] == review.get('photo_id')), None)
    if photo is None:
        raise ValueError('Selected photo_id is absent from the photo library')
    source = library.asset(root, photo['asset'])
    if library.sha(source) != photo['id']:
        raise ValueError('Selected photograph changed after review')
    from PIL import Image
    with Image.open(source) as decoded:
        decoded.load()
        if decoded.format != 'WEBP' or min(decoded.size) < 200:
            raise ValueError('Selected asset must be a decoded editorial WebP photograph')
    for key in ('caption', 'alt'):
        if not isinstance(review.get(key), str) or len(review[key].strip()) < 15:
            raise ValueError('Reviewed factual caption and alt text required')
    image = copy.deepcopy(photo['image'])
    image.update(url=photo['asset'], caption=review['caption'], alt=review['alt'])
    image['reuse_review'] = {'source_asset': photo['asset'], 'sha256': photo['id'],
                             'reviewed_at': review['reviewed_at'], 'relevance_and_archive_date_checked': True}
    return image, source.read_bytes()


def article(raw, edition_id, index, root, catalog, published_at=None, completed_at=None, require_photo=False, used_photos=()):
    slug = safe_id(raw.get('slug') or raw.get('id'))
    section = raw.get('section')
    if section not in ('cyprus', 'world', 'sports'):
        raise ValueError('section must be cyprus/world/sports; mark the lead with is_lead')
    doc = {key: copy.deepcopy(raw[key]) for key in (
        'headline', 'summary', 'published_at', 'updated_at', 'reader_mode', 'reader_value',
        'analysis_sources', 'newspaper_analysis', 'evidence_note', 'related_story_ids',
        'sports_interest', 'delta_update', 'mechanics_and_incentives', 'second_order_effects',
        'scenarios', 'freshness', 'revision_note', 'change_status', 'driver_tags') if key in raw}
    doc['driver_tags'] = module('intelligence').tags(raw.get('driver_tags', []))
    doc.setdefault('change_status', 'UNKNOWN')
    previous = root/'docs/data/articles'/edition_id/(slug + '.json')
    original = json.loads(previous.read_text(encoding='utf-8')) if previous.exists() else {}
    doc.setdefault('published_at', original.get('published_at') or published_at)
    doc.setdefault('updated_at', completed_at)
    doc.setdefault('reader_mode', 'source')
    for key in ('headline', 'summary', 'published_at', 'updated_at', 'reader_mode'):
        if not doc.get(key):
            raise ValueError('Article requires ' + key + ': ' + slug)
    doc.update(id=slug, story_id=safe_id(raw.get('story_id') or slug), story_identity=safe_id(raw.get('story_identity') or raw.get('story_id') or slug),
               edition_id=edition_id, category='Πρώτο θέμα' if raw.get('is_lead') else
               {'cyprus': 'Κύπρος', 'world': 'Διεθνή', 'sports': 'Αθλητικά'}[section],
               url=f'articles/{edition_id}/{slug}.html', sources=sources(raw.get('sources')))
    doc['sections'] = copy.deepcopy(raw.get('sections')) or [
        {'kind': 'reported', 'heading': 'Δημοσιευμένα γεγονότα', 'paragraphs': ensure_str_list(raw.get('paragraphs') or [doc['summary']])}]
    doc['daily'] = copy.deepcopy(raw.get('daily', {}))
    doc['daily'].update(section=section, priority=doc['daily'].get('priority', index + 1))
    doc['daily'].setdefault('events', [])
    doc.setdefault('related_story_ids', [])
    if 'scenarios' in doc and 'what_to_watch' in doc['scenarios']:
        doc['scenarios'].setdefault('watch_next', doc['scenarios'].pop('what_to_watch'))
    doc.setdefault('analysis_sources', [])
    if not doc.get('analysis_sources'):
        for key in ('mechanics_and_incentives', 'second_order_effects', 'scenarios', 'newspaper_analysis'):
            doc.pop(key, None)
        doc['reader_mode'] = 'source'
    if doc.get('sports_interest') == 'f1':
        doc['sports_interest'] = 'formula1'
    if section == 'sports' and doc.get('sports_interest') not in (*TEAMS, 'other'):
        raise ValueError('Explicit sports_interest required')
    try:
        source_photo = module('source_photos').select(raw, used_photos) if 'image_selection' not in raw else None
        if source_photo:
            doc['image'], asset = source_photo
        else:
            if require_photo and 'image_selection' not in raw:
                raw = {**raw, 'image_selection': module('photo_policy').selection(raw, root, used_photos)}
            doc['image'], asset = reviewed_image(raw, edition_id, slug, root, catalog)
    except (ValueError, KeyError, OSError) as error:
        if require_photo:
            raise ValueError('Required real photograph failed validation: ' + slug) from error
        doc['image'] = None
        doc['image_unavailable_reason'] = 'Δεν είναι διαθέσιμη ελεγμένη φωτογραφία για αυτό το άρθρο.'
        asset = None
    if previous.exists() and json.loads(previous.read_text(encoding='utf-8'))['published_at'] != doc['published_at']:
        raise ValueError('Preserve original article publication time on correction')
    return doc, asset


def compile_payload(payload, root=ROOT):
    """Build in memory. No previous edition is selected or silently inherited."""
    root = Path(root)
    if not isinstance(payload, dict):
        raise ValueError('Payload must be an object')
    if payload.get('research_pack_sha256') and not payload.get('synthesis_profile'):
        raise ValueError('A research-pack synthesis requires --research-pack hydration')
    payload, carried = module('baseline').expand(payload, root)
    missing = [key for key in REQUIRED if key not in payload]
    if missing:
        raise ValueError('Missing reviewed payload blocks: ' + ', '.join(missing))
    edition_id = payload.get('edition_id', '')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}-(morning|midday|evening)', edition_id):
        raise ValueError('Explicit YYYY-MM-DD-slot edition_id required')
    date, slot = edition_id.rsplit('-', 1)
    dt.date.fromisoformat(date)
    if payload.get('edition_mode', MODES[slot]) != MODES[slot]:
        raise ValueError('edition_mode must match the scheduled slot')
    published, completed = instant(payload['published_at']), instant(payload['editorial_completed_at'])
    if completed > published:
        raise ValueError('Editorial completion cannot follow publication')
    payload = copy.deepcopy(payload)
    notes = []
    draft = scaffold(edition_id, root)
    if payload.get('briefing_policy') != 'depth-markets-v1':
        draft['markets']=[q for q in draft['markets'] if q['instrument']!='AMZN']
    for key in OPTIONAL:
        if key not in payload and key in draft:
            payload[key] = copy.deepcopy(draft[key])
    payload.setdefault('selection_review', {'version':2,'completed_at':payload['reading_review']['completed_at'],
                                           'global_exception_reason':None,'section_shortfalls':{}})
    if payload['selection_review'].get('completed_at') is None:
        payload['selection_review']['completed_at'] = payload['reading_review']['completed_at']
    if payload.get('image_review', {}).get('completed_at') is None:
        payload.pop('image_review', None)
    scan = payload['executive_scan']
    for key in ('geopolitics_macro', 'cyprus_institutions', 'markets_tech'):
        if not scan.get(key):
            scan[key] = 'Δεν υπάρχει νεότερη επαληθευμένη ενημέρωση για αυτόν τον άξονα.'
    scan['day_catalysts'] = ensure_str_list(scan.get('day_catalysts', []))
    if slot == 'midday' and not payload.get('delta_log'):
        notes.append('Δεν υποβλήθηκε τεκμηριωμένο ημερολόγιο μεταβολών από την πρωινή έκδοση.')
    edition = {key: copy.deepcopy(payload[key]) for key in (*REQUIRED, *OPTIONAL) if key in payload and key != 'articles'}
    capabilities = module('backend').capabilities(root)
    edition.update(schema_version=2, intelligence_contract=1, id=edition_id, date=date, type=slot, timezone='Europe/Athens',
                   availability_policy='partial-v1',
                   status='published', title=payload.get('title') or {'morning':'Πρωινή σάρωση', 'midday':'Μεσημεριανές εξελίξεις', 'evening':'Βραδινή σύνθεση'}[slot] + ' · ' + date,
                   url=f'{slot}/{date}.html', edition_mode=MODES[slot], scheduled_slot={'morning':'07:30','midday':'13:30','evening':'19:30'}[slot],
                   producer_contract={key:capabilities[key] for key in ('producer_protocol','content_schema_sha256')})
    edition.setdefault('changes', [])
    if date >= module('selection').BALANCED_START:
        edition['selection_policy'] = 'balanced-v1'
    edition['daily']['summary_60s'] = ensure_str_list(edition['daily'].get('summary_60s', []))
    # Coerce singleton groups only; never guess which story supports a summary.
    edition['daily'].setdefault('summary_story_ids', [])
    if not isinstance(edition['daily']['summary_story_ids'], list):
        raise ValueError('summary_story_ids must be a list of explicit supporting groups')
    edition['daily']['summary_story_ids'] = [ensure_str_list(group) for group in edition['daily']['summary_story_ids']]
    edition['summary_60s'] = edition['daily']['summary_60s']
    for key in ('selection_review', 'reading_review', 'image_review'):
        if key in edition and instant(edition[key]['completed_at']) > completed:
            raise ValueError(key + ' cannot follow editorial completion')
    current_weather = False
    for record in edition['freshness']:
        expired = any(record.get(key) and instant(record[key]) <= completed for key in ('valid_until','recheck_at','ends_at'))
        if expired:
            record['historical_context'] = True
        elif record['kind'] == 'weather':
            current_weather = True
    if not current_weather:
        edition['panels'] = [p for p in edition['panels'] if p['id'] != 'weather']
        notes.append('Καιρός: δεν είναι διαθέσιμη νεότερη επαληθευμένη πρόγνωση.')
    policy = json.loads((root/'templates/v2/research-policy.json').read_text(encoding='utf-8'))
    for record in edition['opportunities']:
        if module('research').opportunity_due(record, completed, policy)['due']:
            record['review_due'] = True
            notes.append('Χορηγίες και δικαιώματα: διατηρούνται παλιότερα στοιχεία με σαφή ένδειξη επανελέγχου.')
        else:
            record.pop('review_due', None)
    sports = edition['sports']
    for key in TEAMS:
        sports.setdefault('coverage', {}).setdefault(key, copy.deepcopy(draft['sports']['coverage'][key]))
    for key, team in sports['coverage'].items():
        team.setdefault('updates', [])
        for key in ('last_match', 'next_fixture'):
            if isinstance(team.get(key), str):
                team[key] = None
                notes.append('Αθλητικά: παραλείφθηκε αποτέλεσμα ή πρόγραμμα χωρίς δομημένη τεκμηρίωση.')
    quotes = {q['instrument']:q for q in draft['markets']}
    for q in edition['markets']:
        key = module('compact_markets').quote_key(q)
        quotes[key] = q
    edition['markets'] = list(quotes.values())
    if any(q['status'] == 'unavailable' for q in edition['markets']):
        notes.append('Αγορές: ορισμένες τιμές δεν είναι διαθέσιμες· δεν αντικαταστάθηκαν με παλιές τιμές.')
    raw_articles = payload['articles']
    if not raw_articles or sum(bool(a.get('is_lead')) for a in raw_articles) > 1:
        raise ValueError('Articles need a single unambiguous lead')
    library_path = root/'docs/data/photo-library.json'
    catalog = json.loads(library_path.read_text(encoding='utf-8')) if library_path.exists() else {'photos':[]}
    require_photo = date >= '2026-10-26'
    if require_photo:
        catalog = module('photo_policy').extend_catalog(catalog, root)
        edition['photo_policy'] = 'real-photos-v1'
    docs, files = [], {}
    photos = module('photo_policy')
    used_photos = photos.used_today(root, date, {a['story_id'] for a in raw_articles})
    for carried_doc in carried.values():
        used_photos.update(photos.identities(carried_doc.get('image')))
    for index, raw in enumerate(raw_articles):
        try:
            sources(raw.get('sources'))
            if not any(s.get('access') == 'read' and s.get('used_for_claims') for s in raw['sources']):
                raise ValueError('No readable evidence')
        except (ValueError, KeyError):
            notes.append('Παραλείφθηκε άρθρο χωρίς επαρκή τεκμηρίωση: '+str(raw.get('slug') or raw.get('id') or index))
            continue
        if raw.get('slug') in carried:
            doc, asset = carried[raw['slug']], None
        else:
            doc, asset = article(raw, edition_id, index, root, catalog, edition['published_at'], edition['editorial_completed_at'], require_photo, used_photos)
        if require_photo and not doc.get('image'):
            raise ValueError('Carried article requires a maintained real photograph: ' + doc['id'])
        if doc['id'] in {a['id'] for a in docs}:
            raise ValueError('Duplicate article slug')
        docs.append(doc)
        used_photos.update(photos.identities(doc.get('image')))
        if asset is not None:
            files['docs/' + doc['image']['url']] = asset
        elif not doc.get('image'):
            notes.append('Φωτογραφία μη διαθέσιμη: '+doc['headline'])
        files[f'content/articles/{edition_id}/{doc["id"]}.json'] = json_bytes(doc)
    if not docs:
        raise ValueError('No supported article remains; an empty or unverified edition cannot be published')
    counts = module('selection').inventory(docs)
    for key, label in (('cyprus','Κύπρος'),('world','Διεθνή')):
        if module('selection').balanced_required(edition) and counts[key] < 4:
            reason = edition['selection_review'].get('coverage_notes', {}).get(key)
            if reason:
                notes.append(label + ': ' + reason)
        if counts[key] < 5 and not edition.get('synthesis_profile'):
            notes.append(label+': περιορισμένη επαληθευμένη κάλυψη σε αυτή την έκδοση.')
        else:
            edition['selection_review'].get('section_shortfalls',{}).pop(key,None)
    lead = next((a for a in docs if a['category']=='Πρώτο θέμα'), docs[0])
    edition['daily']['lead_story_id'] = lead['story_id']
    if any(a.get('image') for a in docs) and 'image_review' not in edition:
        edition['image_review'] = {'version':2,'completed_at':payload['reading_review']['completed_at']}
    edition['articles'] = [f'articles/{edition_id}/{a["id"]}.json' for a in docs]
    sports['major_stories'] = [r for r in sports.get('major_stories', []) if r['article_id'] in {a['id'] for a in docs}]
    if not sports['major_stories']:
        sports['major_stories'] = []
        for doc in docs:
            raw = next(r for r in raw_articles if (r.get('slug') or r.get('id')) == doc['id'])
            if doc['daily']['section'] != 'sports':
                continue
            sports['major_stories'].append({key:doc[key] for key in ('headline','published_at','summary','sources')})
            sports['major_stories'][-1].update(article_id=doc['id'], why_it_matters=raw.get('why_it_matters') or doc.get('second_order_effects') or doc['summary'])
            if len(sports['major_stories']) == 3:
                break
        sports.setdefault('major_stories_reason', 'Τα αθλητικά άρθρα που επέλεξε ο συντάκτης για αυτή την έκδοση.')
    known = {a['story_id'] for a in docs}
    for path in (root/'content/editions').glob(date + '-*.json'):
        old = json.loads(path.read_text(encoding='utf-8'))
        if old['id'] != edition_id and old['status'] == 'published':
            known.update(json.loads((root/'content'/relative).read_text(encoding='utf-8'))['story_id'] for relative in old['articles'])
    groups = edition['daily']['summary_story_ids']
    points = [(text,group) for text,group in zip(edition['daily']['summary_60s'],groups) if group and all(sid in known for sid in group)]
    if not points:
        total = 0
        for doc in docs:
            count = len(doc['summary'].split())
            if total + count <= 220 and len(points) < 3:
                points.append((doc['summary'], [doc['story_id']]))
                total += count
    edition['daily']['summary_60s'] = [p[0] for p in points]
    edition['daily']['summary_story_ids'] = [p[1] for p in points]
    edition['summary_60s'] = edition['daily']['summary_60s']
    # This traversal only verifies supplied times. It never refreshes them.
    def evidence_times(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in ('retrieved_at','verified_at','checked_at','attempted_at','updated_at','reviewed_at') and child:
                    if instant(child) > completed:
                        raise ValueError(key + ' cannot follow editorial completion')
                evidence_times(child)
        elif isinstance(value, list):
            for child in value:
                evidence_times(child)
    evidence_times([edition, docs])
    for row in edition.get('fast_wire', []):
        if not row.get('source_url') or not row['source_url'].startswith('https://'):
            notes.append('Παραλείφθηκε τηλεγραφική είδηση χωρίς σύνδεσμο πηγής.')
    edition['fast_wire'] = [r for r in edition.get('fast_wire',[]) if r.get('source_url','').startswith('https://')]
    edition['availability_notes'] = list(dict.fromkeys(notes))
    module('intelligence').validate(edition, docs, root)
    schema = json.loads((root/'templates/v2/content.schema.json').read_text(encoding='utf-8'))
    from jsonschema import Draft202012Validator, FormatChecker
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(edition)
    for doc in docs:
        Draft202012Validator({'$ref':'#/$defs/article', '$defs':schema['$defs']}, format_checker=FormatChecker()).validate(doc)
    module('selection').validate(edition, docs)
    files[f'content/editions/{edition_id}.json'] = json_bytes(edition)
    return edition, docs, files


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')


def scaffold(edition_id, root=ROOT):
    """An intentionally incomplete draft, never an assertion that research happened."""
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}-(morning|midday|evening)', edition_id):
        raise ValueError('Explicit YYYY-MM-DD-slot edition_id required')
    slot = edition_id.rsplit('-',1)[1]
    quotes = json.loads((Path(root)/'templates/v2/market-instruments.json').read_text(encoding='utf-8'))
    for quote in quotes:
        quote.update(value=None, change_pct=None, quoted_at=None, status='unavailable', sources=[])
    return {'edition_id':edition_id, 'edition_mode':MODES[slot], 'published_at':None,
            'editorial_completed_at':None, 'executive_scan':{key:'' for key in ('geopolitics_macro','cyprus_institutions','markets_tech')} | {'day_catalysts':[]},
            'daily':{'lead_story_id':'','summary_60s':[],'summary_story_ids':[],'follow_ups':[]},
            'markets':quotes, 'market_summary':[], 'market_movers':[],
            'sports':{'coverage':{key:{'analysis':'Δεν έχει επαληθευτεί νέα ενημέρωση.', 'last_match':None,
                                      'next_fixture':None, 'updates':[], 'no_update_reason':'Εκκρεμεί ο έλεγχος πηγών.'} for key in TEAMS}},
            'panels':[], 'opportunities':[], 'freshness':[], 'fast_wire':[], 'delta_log':[],
            'selection_review':{'version':2,'completed_at':None,'global_exception_reason':None,'section_shortfalls':{}},
            'reading_review':{'version':2,'completed_at':None}, 'image_review':{'version':2,'completed_at':None}, 'articles':[]}


def compose_edition(payload_path, publish=False, portal_root=None, root=ROOT, research_pack=None):
    root = Path(root).resolve()
    if publish and (portal_root is None or not (Path(portal_root)/'.git').exists()):
        raise ValueError('--publish requires an explicit --portal-root Git checkout')
    path = Path(payload_path)
    text = path.read_text(encoding='utf-8')
    pack = module('research_pack').load(research_pack) if research_pack else None
    payload = module('markdown_input').parse(text, root, pack=pack) if path.suffix.lower() == '.md' else json.loads(text)
    if pack:
        module('research_pack').output_budget(text,payload['edition_id'].rsplit('-',1)[1])
        payload = module('research_pack').hydrate(payload, pack, root)
    with module('atomic').lock(root/'.work/compose.lock'):
        edition, docs, files = compile_payload(payload, root)
        # Validate target paths before recording or writing any bytes.
        for name in files:
            target = root/name
            if target.is_symlink() or not target.resolve().is_relative_to(root):
                raise ValueError('Unsafe composition target')
        before = {name:(root/name).read_bytes() if (root/name).exists() else None for name in files}
        try:
            for name, data in files.items():
                target = root/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            builder = module('build'); builder.ROOT = root
            builder.validate(edition, docs)
            module('backend').freshness(edition, docs)
        except BaseException:
            for name, data in before.items():
                target = root/name
                if data is None:
                    target.unlink(missing_ok=True)
                else:
                    target.write_bytes(data)
            raise
    print('[COMPOSE] Validated source candidate: ' + edition['id'])
    if publish:
        state = module('publish').run(root, Path(portal_root), publish=True)
        print(json.dumps({'stages':state['stages'], 'release_id':state.get('release_id')}, ensure_ascii=False))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--input', '-i', type=Path)
    source.add_argument('--scaffold', type=Path, help='Write an incomplete one-file draft; does not research or publish')
    parser.add_argument('--edition-id')
    parser.add_argument('--research-pack',type=Path,help='Sealed private pre-run pack; inserts routine data mechanically')
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--portal-root', type=Path)
    args = parser.parse_args()
    try:
        if args.scaffold:
            if args.publish:
                raise ValueError('Scaffolding cannot publish')
            draft = scaffold(args.edition_id or '')
            args.scaffold.parent.mkdir(parents=True, exist_ok=True)
            with args.scaffold.open('xb') as stream:
                stream.write(json_bytes(draft))
            print('[COMPOSE] Incomplete draft; actual evidence/reviews still required: '+str(args.scaffold))
            return 0
        return compose_edition(args.input, args.publish, args.portal_root, research_pack=args.research_pack)
    except (ValueError, KeyError, OSError) as error:
        print('[COMPOSE] Blocked: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
