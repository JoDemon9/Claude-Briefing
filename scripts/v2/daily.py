"""Compose reviewed edition references into a day. No research or novelty inference."""
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from jsonschema import Draft202012Validator, FormatChecker

SLOTS = ('morning', 'midday', 'evening')
KINDS = {'Προσθήκη': 'new', 'Εξέλιξη': 'substantive_update', 'Διόρθωση': 'correction', 'Πλαίσιο': 'provenance'}
LABELS = {'new': 'Νέο', 'substantive_update': 'Ενημερώθηκε', 'correction': 'Συντακτική διόρθωση', 'enrichment': 'Εμπλουτισμός', 'provenance': 'Προέλευση'}

def load_editorial():
    spec=importlib.util.spec_from_file_location('day_editorial',Path(__file__).with_name('editorial.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

def instant(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))

def newer_quote(candidate, previous, timezone_name):
    """Compare real quote instants; unknown same-day hours use edition order."""
    from zoneinfo import ZoneInfo
    if candidate['status'] == 'unavailable':
        return previous['status'] == 'unavailable'
    if previous['status'] == 'unavailable':
        return True
    def time(q):
        value=q.get('quoted_at')
        if not value:
            return None
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=ZoneInfo(timezone_name))).astimezone(ZoneInfo(timezone_name))
    left,right=time(candidate),time(previous)
    if not left:
        return False
    if not right:
        return True
    if left.date()==right.date() and (len(candidate['quoted_at'])==10 or len(previous['quoted_at'])==10):
        return True
    return left>=right

def collect_follow_ups(stories, bundles, canonical=lambda sid:sid):
    """Use explicit editorial relationships; never match headlines or keywords."""
    by_edition={e['id']:index for index,(e,_) in enumerate(bundles)}
    relations={}
    for index,(edition,_) in enumerate(bundles):
        declared=set()
        for record in edition.get('daily',{}).get('follow_ups',[]):
            origin,target=(canonical(record[key]) for key in ('from_story_id','to_story_id'))
            if origin==target:raise ValueError('A story cannot follow up itself; use the same stable story ID for evolving versions')
            if origin in declared:raise ValueError('Declare only one follow-up target per story in an edition')
            declared.add(origin)
            if any(sid not in stories for sid in (origin,target)):
                raise ValueError('Follow-up references an unavailable participating story')
            if any(min(by_edition[r['edition_id']] for r in stories[sid]['references'])>index for sid in (origin,target)):
                raise ValueError('Follow-up cannot reference a future or draft edition')
            relations[origin]={'from_story_id':origin,'to_story_id':target,'reviewed_in':edition['id']}
    # A later update to the earlier story can make an old pointer obsolete.
    # Keep its historical declaration but never send readers backwards in time.
    return [record for origin,record in sorted(relations.items()) if
            by_edition[stories[record['to_story_id']]['selected']['edition_id']]>
            by_edition[stories[origin]['selected']['edition_id']]]

def compose(date, bundles, previous=None, aliases=None, now=None):
    if previous and previous['date'] != date:
        previous = None
    aliases = aliases or {}
    canonical = lambda sid: aliases.get(sid, sid)
    participating = sorted([(e, aa) for e, aa in bundles if e['date'] == date and e['status'] == 'published'], key=lambda pair: SLOTS.index(pair[0]['type']))
    if not participating:
        raise ValueError('A day needs a published edition')
    if len({e['type'] for e, _ in participating}) != len(participating):
        raise ValueError('Duplicate participating slot')
    if len({e['timezone'] for e, _ in participating}) != 1:
        raise ValueError('Mixed day timezones')
    stories = {}
    events = {}
    edition_refs = []
    for e, aa in participating:
        if len({canonical(a['story_id']) for a in aa}) != len(aa):
            raise ValueError('Duplicate canonical story in one edition')
        edition_refs.append({k: e[k] for k in ('id', 'type', 'url', 'published_at')})
        for position, a in enumerate(aa):
            sid = canonical(a['story_id'])
            ref = {'edition_id': e['id'], 'article_id': a['id'], 'source_story_id': a['story_id'], 'url': a['url']}
            story = stories.setdefault(sid, {'story_id': sid, 'first_seen_at': e['published_at'], 'last_substantive_at': None, 'references': [], 'selected': ref, 'section': 'cyprus' if a['category'] in ('Πρώτο θέμα', 'Κύπρος') else 'world' if a['category'] == 'Διεθνή' else 'sports', 'priority': 1000 + position})
            story['references'].append(ref)
            story['selected'] = ref
            editorial = a.get('daily', {})
            story['section'] = editorial.get('section', story['section'])
            story['priority'] = editorial.get('priority', story['priority'])
            additions = []
            for c in e['changes']:
                if c.get('story_id') and canonical(c['story_id']) == sid:
                    # Existing editorial change records are explicit documentation. Evidence
                    # comes from the referenced reviewed article, never a text/hash diff.
                    additions.append({'id': digest([e['id'], sid, c]), 'kind': KINDS[c['kind']], 'at': e['published_at'], 'summary': c['text'], 'source_urls': list(dict.fromkeys(s['url'] for s in a['sources'] if s.get('access') != 'inaccessible' and s.get('used_for_claims', True)))})
            additions.extend(editorial.get('events', []))
            allowed_sources = {s['url'] for s in a['sources'] if s.get('access') != 'inaccessible' and s.get('used_for_claims', True)}
            if any(url not in allowed_sources for event in editorial.get('events', []) for url in event['source_urls']):
                raise ValueError('Daily event evidence must reference reviewed article sources')
            additions.append({'id': digest([e['id'], sid, 'provenance']), 'kind': 'provenance', 'at': e['published_at'], 'summary': 'Συμμετοχή της ' + e['type'] + ' έκδοσης.', 'source_urls': []})
            for event in additions:
                item = dict(event, story_id=sid, origin=ref)
                if item['kind'] in ('new', 'substantive_update') and not item['source_urls']:
                    item['kind'] = 'provenance'
                if item['id'] in events and events[item['id']] != item:
                    raise ValueError('Editorial event IDs must be unique and immutable')
                events[item['id']] = item
        for field in ('image_revision_at', 'analysis_revision_at'):
            if e.get(field):
                item = {'id': digest([e['id'], field, e[field]]), 'story_id': None, 'kind': 'enrichment', 'at': e[field], 'summary': 'Εμπλουτισμός εικόνων.' if field == 'image_revision_at' else 'Εμπλουτισμός ανάλυσης.', 'source_urls': [], 'origin': {'edition_id': e['id'], 'url': e['url']}}
                events[item['id']] = item
    # Preserve documented earlier revisions to the same edition, never duplicate them.
    if previous and previous['date'] == date:
        published_ids = {e['id'] for e, _ in participating}
        for event in previous['updates']:
            if event['origin']['edition_id'] in published_ids and (event['story_id'] is None or event['story_id'] in stories):
                events.setdefault(event['id'], event)
    for sid, story in stories.items():
        substantive = [event['at'] for event in events.values() if event['story_id'] == sid and event['kind'] in ('new', 'substantive_update')]
        story['last_substantive_at'] = max(substantive, key=instant) if substantive else None
    lead_id = None
    for e, aa in participating:
        requested = e.get('daily', {}).get('lead_story_id')
        if requested:
            lead_id = canonical(requested)
        elif aa and aa[0]['category'] == 'Πρώτο θέμα':
            lead_id = canonical(aa[0]['story_id'])
    if lead_id is None or lead_id not in stories:
        lead_id = min(stories.values(), key=lambda story: (story['priority'], story['story_id']))['story_id'] if stories else None
    if lead_id not in stories:
        raise ValueError('Daily lead must reference a participating published story')
    model = {'schema_version': 1, 'date': date, 'timezone': participating[0][0]['timezone'], 'status': 'published', 'url': f'daily/{date}.html', 'editions': edition_refs, 'missing_slots': [slot for slot in SLOTS if slot not in {e['type'] for e, _ in participating}], 'lead_story_id': lead_id, 'stories': sorted(stories.values(), key=lambda s: (s['priority'], s['story_id'])), 'updates': sorted(events.values(), key=lambda event: (instant(event['at']), event['id']))}
    # Select the most recently verified record per stable programme ID.
    import importlib.util
    spec=importlib.util.spec_from_file_location('day_opportunities',Path(__file__).with_name('opportunities.py'))
    opportunity=importlib.util.module_from_spec(spec);spec.loader.exec_module(opportunity)
    model['opportunities']=opportunity.collect(participating)
    model['overview']=load_editorial().overview(model['stories'],participating,canonical)
    model['follow_ups']=collect_follow_ups(stories,participating,canonical)
    fingerprint = digest({'model': model, 'inputs': participating, 'aliases': aliases})
    moment = (now or datetime.now(timezone.utc)).isoformat()
    model['created_at'] = previous['created_at'] if previous else moment
    model['updated_at'] = previous['updated_at'] if previous and previous.get('input_sha256') == fingerprint else moment
    model['input_sha256'] = fingerprint
    return model

def validate(root, model, bundles):
    schema = json.loads((root/'templates/v2/day.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(model)
    lookup = {e['id']: (e, {a['id']: a for a in aa}) for e, aa in bundles}
    if len({s['story_id'] for s in model['stories']}) != len(model['stories']):
        raise ValueError('Duplicate daily story')
    known={s['story_id'] for s in model['stories']}
    if len({r['from_story_id'] for r in model.get('follow_ups',[])})!=len(model.get('follow_ups',[])):
        raise ValueError('Only one selected follow-up per story is allowed')
    # Model IDs have already been canonicalized by compose, including aliases.
    for record in model.get('follow_ups',[]):
        if record['from_story_id'] not in known or record['to_story_id'] not in known or record['reviewed_in'] not in {e['id'] for e in model['editions']}:
            raise ValueError('Follow-up references an unavailable participating story or edition')
        by_story={s['story_id']:s for s in model['stories']}
        times={e['id']:instant(e['published_at']) for e in model['editions']}
        if times[by_story[record['to_story_id']]['selected']['edition_id']]<=times[by_story[record['from_story_id']]['selected']['edition_id']]:
            raise ValueError('Follow-up target must be a later published edition')
    if any(sid not in known for point in model.get('overview',{}).get('points',[]) for sid in point['story_ids']):
        raise ValueError('Daily overview references an unavailable story')
    for edition in model['editions']:
        e, _ = lookup[edition['id']]
        if e['date'] != model['date'] or e['status'] != 'published' or not (root/'docs'/e['url']).is_file():
            raise ValueError('Day references an unavailable edition')
    for story in model['stories']:
        if story['selected'] not in story['references']:
            raise ValueError('Selection must be one of the published references')
        for ref in story['references']:
            _, articles = lookup[ref['edition_id']]
            a = articles[ref['article_id']]
            if a['url'] != ref['url'] or not (root/'docs'/a['url']).is_file():
                raise ValueError('Day references an unavailable reader')

def render(b, model, bundles):
    lookup = {e['id']: (e, {a['id']: a for a in aa}) for e, aa in bundles}
    follow_ups={r['from_story_id']:r['to_story_id'] for r in model.get('follow_ups',[])}
    story_lookup={s['story_id']:s for s in model['stories']}
    def selected(story):
        e, aa = lookup[story['selected']['edition_id']]
        return e, aa[story['selected']['article_id']]
    def card(story, hero=False):
        e, a = selected(story)
        doc = BeautifulSoup(b.card(e, a, hero), 'html.parser')
        node = doc.article
        node['id'] = 'story-' + digest(story['story_id'])[:12]
        node['data-story-id'] = story['story_id']
        eyebrow=node.select_one('.eyebrow')
        eyebrow.clear()
        if hero:eyebrow.append(BeautifulSoup(b.emblem('lead'),'html.parser'))
        eyebrow.append('Πρώτο θέμα' if hero else {'cyprus':'Κύπρος','world':'Διεθνή','sports':'Αθλητικά'}[story['section']])
        events = [x for x in model['updates'] if x['story_id'] == story['story_id'] and x['origin']['edition_id'] == e['id'] and e['id'] == bundles[-1][0]['id']]
        kinds = {x['kind'] for x in events}
        label = 'Συντακτική διόρθωση' if 'correction' in kinds else 'Ενημερώθηκε' if 'substantive_update' in kinds else 'Νέο' if 'new' in kinds else 'Από το πρωινό' if e['type'] == 'morning' else 'Από τη ' + b.TYPES[e['type']].lower()
        note = doc.new_tag('p', attrs={'class': 'story-origin'})
        badge_kind='correction' if 'correction' in kinds else 'substantive_update' if 'substantive_update' in kinds else 'new' if 'new' in kinds else 'provenance'
        successor=follow_ups.get(story['story_id'])
        if successor:
            label='Πρωινό πλαίσιο' if e['type']=='morning' else 'Προηγούμενη κάλυψη'
            badge_kind='background'
            node['class']=node.get('class',[])+['story-background']
        badge=doc.new_tag('span', attrs={'class':'story-status status-'+badge_kind})
        marker=doc.new_tag('span',attrs={'class':'status-marker','aria-hidden':'true'});marker.string={'new':'✨','substantive_update':'🔄','correction':'✏️','provenance':'🗂️','background':'🗂️'}[badge_kind]
        badge.append(marker);badge.append(label)
        note.append(badge)
        time=doc.new_tag('time',attrs={'datetime':e['published_at'],'title':'Δημοσίευση της επιλεγμένης έκδοσης'});time.string=b.stamp(e['published_at'],model['timezone'])
        note.append(time)
        node.select_one('.eyebrow').insert_after(note)
        if successor:
            _,outcome=selected(story_lookup[successor])
            follow=doc.new_tag('aside',attrs={'class':'story-follow-up','aria-label':'Μεταγενέστερη εξέλιξη'})
            link=doc.new_tag('a',href='#story-'+digest(successor)[:12],attrs={'data-follow-up-story-id':successor})
            prefix=doc.new_tag('span');prefix.string='Νεότερη εξέλιξη →';link.append(prefix)
            title=doc.new_tag('strong');title.string=outcome['headline'];link.append(title)
            follow.append(link);node.select_one('h2,h3').insert_after(follow)
        # Older legacy articles retain full text in their readers; cards keep their
        # factual abstract and available editorial preview, without concatenation.
        for more in node.select('.story-more'):
            more.decompose()
        if hero and node.select_one('.card-context') and not node.select_one('.lead-analysis'):
            context = node.select_one('.card-context')
            details = doc.new_tag('section', attrs={'class': 'lead-analysis'})
            summary = doc.new_tag('h3'); summary.string = 'Γιατί έχει σημασία'
            context.replace_with(details); details.append(summary); details.append(context)
            duplicate_label=context.find('b',recursive=False)
            if duplicate_label:duplicate_label.decompose()
        provenance = doc.new_tag('details', attrs={'class': 'sources-disclosure story-history'})
        summary = doc.new_tag('summary'); summary.string = 'Εκδόσεις και προηγούμενες αναφορές'
        provenance.append(summary)
        for ref in story['references']:
            origin, _ = lookup[ref['edition_id']]
            link = doc.new_tag('a', href='../' + ref['url']); link.string = b.TYPES[origin['type']] + ' · ' + b.stamp(origin['published_at'])
            provenance.append(link)
        (node.select_one('.lead-copy') if hero else node.select_one('.story-content')).append(provenance)
        for link in node.select('.read-link'):
            if link['href'].startswith('../articles/'):
                link['href'] += '?from=daily/' + model['date'] + '.html'
        return str(node)
    latest = bundles[-1][0]
    html = b.head('Εφημερίδα ημέρας · ' + model['date'], model['url'], 'newspaper', '../', 'daily')
    html += '<div class="line-top"></div><header class="masthead wrap"><div class="m-left">Εφημερίδα της ημέρας<br>Λεμεσός · Κύπρος</div><div class="brand"><h1>THE ORACLE <em>SOVEREIGN.</em></h1><p>Η ημέρα σε μία εφημερίδα</p></div><div class="m-right">' + model['date'] + '</div></header>'
    html += '<div class="stickybar"><div class="wrap"><nav class="navs" aria-label="Περιεχόμενα ημέρας">' + ''.join('<a href="#' + target + '">' + b.icon(symbol) + label + '</a>' for target, symbol, label in [('main','news','Κύρια νέα'), ('summary','clock','60 δευτερόλεπτα'), ('changes','clock','Τι άλλαξε'), ('cyprus','news','Κύπρος'), ('world','globe','Διεθνή'), ('sports','sport','Αθλητικά'), ('markets','chart','Αγορές')]) + '<a href="../daily/index.html">' + b.icon('archive') + 'Αρχείο ημερών</a></nav><div class="tools"><button data-theme-toggle aria-label="Εναλλαγή θέματος">◐ Θέμα</button><a href="../search.html">' + b.icon('search') + 'Αναζήτηση</a><button data-print>Εκτύπωση</button></div></div></div><main class="wrap" id="main">'
    html += '<div class="introbar"><b>Εφημερίδα ημέρας · ' + model['date'] + '</b><span>Τελευταία ανανέωση: ' + b.stamp(model['updated_at'], model['timezone']) + '</span></div><nav class="edition-desk" aria-label="Συμμετέχουσες εκδόσεις"><b>Συμμετέχουσες εκδόσεις</b>'
    for slot in SLOTS:
        ref = next((x for x in model['editions'] if x['type'] == slot), None)
        html += '<a href="../' + ref['url'] + '" title="Συμμετέχουσα δημοσιευμένη έκδοση">' + b.icon({'morning':'sun','midday':'clock','evening':'moon'}[slot]) + b.TYPES[slot] + '</a>' if ref else '<span>' + b.TYPES[slot] + ' · Μη διαθέσιμη</span>'
    html += '</nav>'
    if model['missing_slots']:
        html += '<p class="revision-note">Μερική ημέρα: περιλαμβάνονται μόνο οι διαθέσιμες δημοσιευμένες εκδόσεις.</p>'
    overview=model.get('overview') or load_editorial().overview(model['stories'],bundles)
    points=overview['points']
    links=[[{'url':'#story-'+digest(sid)[:12],'label':selected(next(s for s in model['stories'] if s['story_id']==sid))[1]['headline']} for sid in point['story_ids']] for point in points]
    html += b.load_module('newspaper_ui').summary(b,[p['text'] for p in points],'Η ημέρα σε 60 δευτερόλεπτα' if overview['kind']=='reviewed' else 'Επιλεγμένες ειδήσεις της ημέρας',links)
    lead = next(s for s in model['stories'] if s['story_id'] == model['lead_story_id'])
    # One editorial opening, with links into unique cards further down the page.
    picks = []
    for section in ('world', 'cyprus'):
        picks.extend([story for story in model['stories'] if story != lead and story['section'] == section][:2])
    picks.sort(key=lambda story: (story['priority'], story['story_id']))
    brief = ''.join('<div class="brief-line"><b>' + f'{i+1:02}' + '</b><p><a href="#story-' + digest(story['story_id'])[:12] + '">' + b.esc(selected(story)[1]['headline']) + '</a></p></div>' for i, story in enumerate(picks))
    html += '<div class="hero-grid day-lead">' + card(lead, True) + '<aside class="hero-side"><div class="brief-panel"><div class="heading">Η επιλογή της ημέρας</div><h3>Σημαντικά<br><em>σε μία ματιά.</em></h3>' + brief + '</div></aside></div>'
    changes_html = '<details class="section day-changes" id="changes"><summary>'+b.emblem('changes')+'Το χρονικό της ημέρας <span>Ενημερώσεις και προηγούμενες αναφορές</span></summary>'
    changes = [x for x in model['updates'] if x['kind'] != 'provenance']
    def event_html(event):
        origin,articles=lookup[event['origin']['edition_id']]
        article=articles.get(event['origin'].get('article_id'))
        title=article['headline'] if article else b.TYPES[origin['type']]+' έκδοση'
        source_names={s['url']:s['publisher'] for s in article['sources']} if article else {}
        links=''.join('<a href="'+b.esc(url)+'" rel="noopener noreferrer">'+b.esc(source_names.get(url,urlsplit(url).hostname))+' ↗</a>' for url in event['source_urls'])
        origin_link='<a class="update-origin" aria-label="'+b.esc('Διάβασε: '+title)+'" href="../'+event['origin']['url']+'">'+b.icon('book')+'Αρχική αναφορά ↗</a>'
        evidence='<details class="update-sources"><summary>Αναφορά και πηγές <span class="disclosure-count">'+str(len(event['source_urls']))+'</span></summary><div class="update-source-links">'+origin_link+links+'</div></details>'
        return '<li class="update-card"><div class="update-meta"><span class="story-status status-'+event['kind']+'">'+LABELS[event['kind']]+'</span><time datetime="'+b.esc(event['at'])+'">'+b.stamp(event['at'],model['timezone'])+'</time></div><div class="update-body"><h3 class="visually-hidden">'+b.esc(title)+'</h3><p>'+b.esc(event['summary'])+'</p></div><div class="update-actions">'+evidence+'</div></li>'
    from urllib.parse import urlsplit
    changes_html += '<ol class="update-timeline">' + ''.join(event_html(x) for x in changes[-5:][::-1]) + '</ol>' if changes else '<p class="empty-state">Δεν έχει τεκμηριωθεί νέα ουσιαστική εξέλιξη. Η προέλευση αναγράφεται σε κάθε ιστορία.</p>'
    if len(changes) > 5:
        changes_html += '<details class="changes-history"><summary>Όλο το ιστορικό ενημερώσεων</summary><ol class="update-timeline">' + ''.join(event_html(x) for x in changes[:-5][::-1]) + '</ol></details>'
    changes_html += '</details>'
    for section, label in [('world','Διεθνή'), ('cyprus','Κύπρος')]:
        stories = [story for story in model['stories'] if story['section'] == section and story != lead]
        if stories:
            html += '<section class="section" id="' + section + '"><div class="sectionhead"><h2>' + b.emblem(section) + label + '.</h2><span>' + str(len(stories)) + ' ιστορίες</span></div><div class="g3">' + ''.join(card(story) for story in stories) + '</div></section>'
    html += changes_html
    sports_module = b.load_module('sports')
    anchors = {}
    sport_stories = []
    for story in model['stories']:
        if story['section'] != 'sports' or story == lead:
            continue
        _, article = selected(story)
        interest = sports_module.interest(article)
        if interest in b.TEAMS:
            anchors.setdefault(interest, []).append((story['story_id'], digest(story['story_id'])[:12]))
        else:
            sport_stories.append(story)
    html += b.sports(latest, anchors=anchors, include_major=False)
    if sport_stories:
        # Latest participating reporting first; preserve older independent readers.
        sport_stories.sort(key=lambda story: (-SLOTS.index(lookup[story['selected']['edition_id']][0]['type']), story['priority'], story['story_id']))
        html += '<section class="section sports-other" id="other-sports"><div class="sectionhead"><h2>Από τον υπόλοιπο αθλητισμό.</h2></div><div class="g3">' + ''.join(card(story) for story in sport_stories[:2]) + '</div>'
        if len(sport_stories) > 2:
            html += '<details class="sports-archive"><summary>Περισσότερες αθλητικές ιστορίες της ημέρας</summary><div class="g3">' + ''.join(card(story) for story in sport_stories[2:]) + '</div></details>'
        html += '</section>'
    quotes = {}
    panels = {}
    for e, _ in bundles:
        for q in e['markets']:
            key = b.quote_key(q)
            old = quotes.get(key)
            if old is None or newer_quote(q,old,model['timezone']):
                quotes[key] = q
        for panel in e.get('panels', []):
            panels['watch' if panel['id'] in ('watch','risk-radar') else panel['id']] = panel
    market_edition = dict(latest, markets=list(quotes.values()), panels=list(panels.values()))
    html += b.load_module('opportunities').render(b,model.get('opportunities',[]))
    html += b.markets(market_edition) + b.calculator(latest) + b.edition_panels(market_edition)
    html += '<footer class="day-footer"><span>THE ORACLE SOVEREIGN · '+model['date']+'</span><a href="../'+model['url']+'">'+b.icon('book')+'Μόνιμο αρχείο αυτής της ημέρας</a><a href="../daily/index.html">'+b.icon('archive')+'Αρχείο ημερών</a><details class="edition-about"><summary>Τι αποθηκεύεται εδώ;</summary><p>Η εφημερίδα ημέρας συγκεντρώνει τα κύρια νέα των δημοσιευμένων πρωινών, μεσημεριανών και βραδινών εκδόσεων, χωρίς διπλές ιστορίες. Ανανεώνεται στην ίδια διεύθυνση και διατηρείται στο αρχείο ανά ημερομηνία. Τα τρία briefings και οι αναλυτικοί readers παραμένουν στα δικά τους URLs.</p><p>Δημιουργία ημερήσιου αρχείου: ' + b.stamp(model['created_at']) + ' · ' + model['timezone'] + '. Οι ώρες πηγών και τιμών διατηρούνται. Κάθε reader ανήκει στη συγκεκριμένη έκδοση.</p></details></footer></main></body></html>'
    return b.load_module('newspaper_ui').decorate(b,html,latest,model)

def publish(b, latest_module, bundles, affected_dates=None):
    root = b.ROOT
    alias_path = root/'content/day-story-aliases.json'
    aliases = b.read(alias_path) if alias_path.exists() else {}
    records = []
    for date in sorted({e['date'] for e, _ in bundles if e.get('published_at')}):
        day_bundles = sorted([(e, aa) for e, aa in bundles if e['date'] == date], key=lambda pair: SLOTS.index(pair[0]['type']))
        path = root/'docs/data/days'/f'{date}.json'
        previous = b.read(path) if path.exists() else None
        if affected_dates is not None and date not in affected_dates and previous and (root/'docs'/previous['url']).is_file():
            records.append({k:previous[k] for k in ('date','url','created_at','updated_at','missing_slots')})
            continue
        model = compose(date, day_bundles, previous, aliases)
        validate(root, model, bundles)
        b.write(path, json.dumps(model, ensure_ascii=False, indent=2)+'\n')
        text = render(b, model, day_bundles)
        text = latest_module.version_resources(text, root, model['url'])
        b.write(root/'docs'/model['url'], text)
        records.append({k: model[k] for k in ('date','url','created_at','updated_at','missing_slots')})
    b.write(root/'docs/data/days.json', json.dumps(records[::-1], ensure_ascii=False, indent=2)+'\n')
    archive = b.head('Αρχείο ημερών', 'daily/index.html', 'newspaper', '../') + '<main class="wrap" id="main"><h1>Αρχείο ημερών</h1><a href="../index.html">Ανεξάρτητες εκδόσεις</a><ul>' + ''.join('<li><a href="../'+r['url']+'">'+r['date']+'</a> · '+b.stamp(r['updated_at'])+'</li>' for r in records[::-1]) + '</ul></main></body></html>'
    b.write(root/'docs/daily/index.html', archive)
    if not records:
        return
    record = records[-1]
    doc = BeautifulSoup((root/'docs'/record['url']).read_text(encoding='utf-8'), 'html.parser')
    source = urljoin(b.BASE, record['url'])
    for node in doc.find_all(True):
        for attr in ('href','src','poster'):
            value = node.get(attr)
            if value and not value.startswith(('#','data:','mailto:','tel:')):
                node[attr] = urljoin(source, value)
    for name, value in [('oracle-day-id',record['date']), ('oracle-day-updated-at', record['updated_at'])]:
        doc.head.append(doc.new_tag('meta', attrs={'name':name,'content':value}))
    tools = doc.select_one('.tools')
    if tools:
        link = doc.new_tag('a', href=latest_module.PORTAL+'portal-archive.html#liveWireBar'); link.string = 'Ροή'; link['aria-label']='Ροή ειδήσεων'; (tools.select_one('.utility-list') or tools).append(link)
    text = str(doc)
    b.write(root/'docs/today.html', text)
    html_hash = hashlib.sha256(text.encode()).hexdigest()
    assets = {}
    from urllib.parse import urlsplit
    for node in doc.select('link[href],script[src],img[src]'):
        url = node.get('href') or node.get('src')
        if url.startswith(b.BASE+'assets/'):
            relative = urlsplit(url).path.removeprefix('/Claude-Briefing/')
            assets[url] = hashlib.sha256((root/'docs'/relative).read_bytes()).hexdigest()
    descriptor = {'schema_version':1,'status':'published','day_id':record['date'],'updated_at':record['updated_at'],'day_url':source,'html_url':b.BASE+'today.html','html_sha256':html_hash,'asset_sha256':assets,'version':digest([html_hash, assets])}
    b.write(root/'docs/data/day-latest.json', json.dumps(descriptor, ensure_ascii=False, indent=2)+'\n')
