"""Evidence-bound favourite summaries and a separate, compact wider-sports allowance."""
import copy
import re

POLICY = 'intelligence-v1'
INTERESTS = ('omonoia', 'manutd', 'realmadrid', 'formula1')
TOPICS = ('padel', 'football', 'other-sport')


def active(sports):
    return sports.get('briefing_policy') == POLICY


def word_count(row):
    return sum(len(row.get(k, '').split()) for k in ('changed', 'meaning', 'watch'))


def hydrate(payload, pack):
    notes = payload.pop('sport_briefs', {})
    if not active(pack['data']['sports']):
        if notes:
            raise ValueError('SportBrief requires an intelligence-v1 prepared pack')
        return
    if set(notes) - set(INTERESTS):
        raise ValueError('Unknown favourite interest')
    result = {}
    for key, row in notes.items():
        refs = row.get('evidence', [])
        if not refs or len(refs) != len(set(refs)):
            raise ValueError('SportBrief needs distinct article evidence IDs')
        sources = []
        for ref in refs:
            ev = pack.get('evidence', {}).get(ref, {})
            if (ev.get('access') != 'article_excerpt' or not ev.get('source')
                    or ev.get('sports_lane') != key):
                raise ValueError('SportBrief requires readable evidence for this favourite')
            sources.append(copy.deepcopy(ev['source']))
        result[key] = {k: row[k] for k in ('changed', 'meaning', 'watch')}
        result[key]['sources'] = sources
    payload['sports']['briefings'] = result


def validate(sports, articles=()):
    if not active(sports):
        return
    for key, row in sports.get('briefings', {}).items():
        if key not in INTERESTS or any(not row.get(k, '').strip() for k in ('changed', 'meaning', 'watch')):
            raise ValueError('SportBrief needs change, consequence and next test')
        if word_count(row) > 70:
            raise ValueError('Favourite briefing must stay within 70 words')
        normalize = lambda s: re.sub(r'\W+', ' ', s.casefold()).strip()
        if normalize(row['changed']) == normalize(row['meaning']):
            raise ValueError('SportBrief meaning must add to the reported change')
        if not row.get('sources') or any(s.get('access') != 'read' or not s.get('used_for_claims') for s in row['sources']):
            raise ValueError('SportBrief needs reviewed article sources')
    extra = [a for a in articles if a.get('daily', {}).get('section', a.get('section')) == 'sports']
    topics = []
    for a in extra:
        if a.get('sports_interest') != 'other':
            raise ValueError('Beyond my four must not duplicate a favourite')
        topic = set(a.get('driver_tags', [])) & set(TOPICS)
        if len(topic) != 1:
            raise ValueError('Wider sports needs one topic: padel, football or other-sport')
        topics.extend(topic)
        meaning = a.get('second_order_effects', '')
        if not isinstance(meaning, str) or not meaning.strip() or not a.get('analysis_sources'):
            raise ValueError('Wider sports requires an evidence-backed consequence')
        if len((a['summary']+' '+meaning).split()) > 70:
            raise ValueError('Wider sports brief must stay within 70 words')
        if meaning.strip().casefold() == a['summary'].strip().casefold():
            raise ValueError('Wider sports consequence must add to the summary')
        if any(a.get(k) for k in ('mechanics_and_incentives','scenarios','newspaper_analysis')):
            raise ValueError('Wider sports uses concise facts and effects, not a long analysis')
    if len(topics) != len(set(topics)) or len(extra) > 3:
        raise ValueError('Choose at most one distinct story per wider-sports topic')
    if len(extra) < 2 and len(sports.get('major_stories_reason', '').strip()) < 20:
        raise ValueError('Explain fewer than two wider-sports stories without padding')
    if sum(word_count(r) for r in sports.get('briefings', {}).values()) + sum(
            len((a['summary']+' '+a.get('second_order_effects', '')).split()) for a in extra) > 450:
        raise ValueError('Sports overview exceeds 450 words')


def article_budget(articles, slot, sports):
    changed = [a for a in articles if a.get('change_status') != 'UNCHANGED']
    limit = 10 if slot == 'morning' else 6
    if active(sports):
        news = [a for a in changed if a.get('daily', {}).get('section', a.get('section')) != 'sports']
        extra = [a for a in changed if a not in news]
        if len(news) > limit or len(extra) > 3:
            raise ValueError('Separate news/sports story budget exceeded')
    elif len(changed) > limit:
        raise ValueError('Single-turn story budget exceeded')
