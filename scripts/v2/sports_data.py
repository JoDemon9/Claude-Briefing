"""Structured scores, standings and fixtures. Scorelines never imply tactics."""
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path


def module(name):
    spec=importlib.util.spec_from_file_location('sports_data_'+name,Path(__file__).with_name(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


HTTP=module('prefetch_http')
HOSTS={'site.api.espn.com','api.jolpi.ca'}
TEAMS={'omonoia':('cyp.1','617','Omonia Nicosia'),
       'manutd':('eng.1','360','Manchester United'),
       'realmadrid':('esp.1','86','Real Madrid')}
UEFA=('uefa.champions','uefa.europa','uefa.europa.conf')
SITE='https://site.api.espn.com/apis/site/v2/sports/soccer/'
STANDINGS='https://site.api.espn.com/apis/v2/sports/soccer/'


def instant(value):
    return datetime.fromisoformat(value.replace('Z','+00:00'))


def entries(value):
    if isinstance(value,dict):
        if isinstance(value.get('entries'),list):
            yield from value['entries']
        for key,child in value.items():
            if key != 'entries':
                yield from entries(child)
    elif isinstance(value,list):
        for child in value:
            yield from entries(child)


def score(value):
    value=value.get('displayValue',value.get('value')) if isinstance(value,dict) else value
    if not str(value).isdigit():
        raise ValueError('Unconfirmed score')
    return str(value)


def team_card(key,schedule,table,at,fixtures=None):
    league,tid,name=TEAMS[key]
    card={'name':name,'analysis':'Δομημένα δεδομένα ESPN· το πρόγραμμα αφορά όσα καλύπτει ο πάροχος. Δεν τεκμηριώνεται τακτική ανάλυση.',
          'last_match':None,'next_fixture':None,'updates':[],'league_position':None,
          'no_update_reason':'Μη διαθέσιμα ή μη επιβεβαιωμένα δεδομένα παρόχου.'}
    try:
        data=HTTP.data(schedule)
        if str(data['team']['id'])!=tid:
            return card
        events=[(event,schedule) for event in data.get('events',[])]
        if fixtures and fixtures.get('status')=='available':
            upcoming=HTTP.data(fixtures)
            if str(upcoming.get('team',{}).get('id'))==tid:
                events.extend((event,fixtures) for event in upcoming.get('events',[]))
        games=[]
        for event,origin in events:
            try:
                comp=event['competitions'][0]; teams=comp['competitors']
                own=next(t for t in teams if str(t['id'])==tid)
                opponent=next(t for t in teams if str(t['id'])!=tid)
                when=instant(event['date']); status=comp['status']['type']
                games.append((when,event,comp,own,opponent,status,origin))
            except (ValueError,KeyError,IndexError,StopIteration,TypeError):
                continue
        past=[g for g in games if g[0]<=at and g[5].get('completed') is True]
        future=[g for g in games if g[0]>at and g[5].get('state')=='pre' and g[1].get('timeValid',g[2].get('timeValid')) is True]
        def base(g):
            when,event,comp,own,opponent,status,origin=g
            evidence=HTTP.source('ESPN',origin['url'],origin['retrieved_at'],kind='reporting')
            return dict(opponent=opponent['team']['displayName'],competition=event.get('league',{}).get('name') or league,
                        date=when.date().isoformat(),venue=comp.get('venue',{}).get('fullName'),
                        verified_at=origin['retrieved_at'],sources=[evidence])
        if past:
            g=max(past,key=lambda g:g[0]); card['last_match']={**base(g),'result':score(g[3]['score'])+'–'+score(g[4]['score']),'scorers':None}
            card['just_played']=timedelta(0)<=at-g[0]<=timedelta(hours=24)
            card['last_match_at']=g[0].isoformat()
        if future:
            g=min(future,key=lambda g:g[0]); card['next_fixture']={**base(g),'kickoff_at':g[0].isoformat()}
        card['no_update_reason']='Δεν εξάγονται τραυματισμοί, xG ή τακτική από το σκορ.'
    except (ValueError,KeyError,IndexError,TypeError):
        pass
    try:
        standings=HTTP.data(table)
        season=standings['season']
        card['standings_season']=season.get('displayName')
        if not instant(season['startDate'])<=at<instant(season['endDate']):
            card['standings_status']='unavailable'
            card['analysis']+=' Δεν διατίθεται τρέχουσα κατάταξη· η πηγή επέστρεψε παλαιότερη περίοδο.'
            return card
        row=next(e for e in entries(standings) if str(e['team']['id'])==tid)
        rank=next(s for s in row['stats'] if s['name']=='rank')
        card['league_position']=str(rank.get('displayValue',rank.get('value')))
        card['standings_status']='available'
        card['standings_sources']=[HTTP.source('ESPN',table['url'],table['retrieved_at'],kind='reporting')]
    except (ValueError,KeyError,TypeError,StopIteration):
        pass
    return card


def f1_card(rows,urls,at):
    card={'name':'Formula 1','analysis':'Δομημένα δεδομένα jolpica-f1· καμία αυτόματη ερμηνεία στρατηγικής.',
          'last_match':None,'next_fixture':None,'updates':[],'sessions':[]}
    for role,url in urls.items():
        row=rows[url]
        try:
            data=HTTP.data(row)['MRData']
            evidence=HTTP.source('jolpica-f1',url,row['retrieved_at'],kind='reporting')
            if role=='standings':
                tables=data['StandingsTable']['StandingsLists']
                if tables:
                    card['standings']=[dict(position=r['position'],driver=r['Driver']['givenName']+' '+r['Driver']['familyName'],points=r['points']) for r in tables[0]['DriverStandings'][:5]]
                    card['standings_sources']=[evidence]
            else:
                races=data['RaceTable']['Races']
                if role=='results' and races:
                    race=races[-1]; when=instant(race['date']+'T'+race.get('time','00:00:00Z'))
                    if when+timedelta(hours=2)<=at and race.get('Results'):
                        card['latest_session']=dict(name=race['raceName'],date=race['date'],results=[dict(position=r['position'],driver=r['Driver']['familyName'],status=r['status']) for r in race['Results'][:5]],verified_at=row['retrieved_at'],sources=[evidence])
                elif role=='schedule':
                    future=[r for r in races if r.get('time') and instant(r['date']+'T'+r['time'])>at]
                    if future:
                        race=min(future,key=lambda r:r['date']+r['time']); card['next_grand_prix']=race['raceName']; card['next_gp_sources']=[evidence]
                        for name,session in [('Race',race)]+[(k,race[k]) for k in ('FirstPractice','SecondPractice','ThirdPractice','Qualifying','Sprint','SprintQualifying') if isinstance(race.get(k),dict)]:
                            if session.get('date') and session.get('time'):
                                stamp=instant(session['date']+'T'+session['time'])
                                if stamp>at:
                                    card['sessions'].append(dict(name=name,starts_at=stamp.isoformat(),sources=[evidence]))
        except (ValueError,KeyError,IndexError,TypeError):
            continue
    return card


def collect(client,at):
    dates=(at-timedelta(days=30)).strftime('%Y%m%d')+'-'+(at+timedelta(days=30)).strftime('%Y%m%d')
    team_urls={k:(SITE+'all/teams/'+tid+'/schedule?dates='+dates,STANDINGS+league+'/standings',SITE+'all/teams/'+tid+'/schedule?fixture=true') for k,(league,tid,_) in TEAMS.items()}
    uefa={}
    for league in UEFA:
        weekday=1 if league=='uefa.champions' else 3
        anchor=at-timedelta(days=(at.weekday()-weekday)%7)
        dates=[anchor+timedelta(days=offset) for offset in (0,7,14)]
        if league=='uefa.champions':dates += [d+timedelta(days=1) for d in dates[:]]
        uefa[league]=[SITE+league+'/scoreboard?dates='+d.strftime('%Y%m%d') for d in dates]+[STANDINGS+league+'/standings']
    f1={role:f'https://api.jolpi.ca/ergast/f1/{at.year}/'+path for role,path in dict(results='last/results/?limit=30',standings='driverStandings/?limit=30',schedule='?limit=30').items()}
    rows=client.many([u for pair in [*team_urls.values(),*uefa.values()] for u in pair]+list(f1.values()))
    cards={k:team_card(k,rows[urls[0]],rows[urls[1]],at,rows[urls[2]]) for k,urls in team_urls.items()}
    cards['formula1']=f1_card(rows,f1,at)
    competitions={}
    for league,urls in uefa.items():
        result={'scores':[],'fixtures':[],'standings':[],'status':'unavailable'}
        for url in urls[:-1]:
            try:
                row=rows[url]; evidence=HTTP.source('ESPN',row['url'],row['retrieved_at'],kind='reporting')
                for event in HTTP.data(row).get('events',[]):
                    comp=event['competitions'][0]; when=instant(event['date']); status=comp['status']['type']
                    item=dict(name=event['name'],starts_at=when.isoformat(),sources=[evidence])
                    if when<=at and status.get('completed') is True:
                        item['score']='–'.join(score(t['score']) for t in comp['competitors']); result['scores'].append(item)
                    elif when>at and status.get('state')=='pre':
                        result['fixtures'].append(item)
                result['status']='available'
            except (ValueError,KeyError,IndexError,TypeError):
                pass
        result['scores']=sorted(result['scores'],key=lambda r:r['starts_at'],reverse=True)[:6]
        result['fixtures']=sorted(result['fixtures'],key=lambda r:r['starts_at'])[:6]
        try:
            row=rows[urls[-1]]
            evidence=HTTP.source('ESPN',row['url'],row['retrieved_at'],kind='reporting')
            for entry in list(entries(HTTP.data(row)))[:5]:
                stats={s['name']:s.get('displayValue') for s in entry['stats']}
                result['standings'].append(dict(team=entry['team']['displayName'],rank=stats.get('rank'),points=stats.get('points'),sources=[evidence]))
        except (ValueError,KeyError,TypeError):
            pass
        competitions[league]=result
    return {'coverage':cards,'competitions':competitions,'major_stories':[],
            'major_stories_reason':'Επιλέγονται μόνο ουσιώδεις νέες αθλητικές εξελίξεις.'}
