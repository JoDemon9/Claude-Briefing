"""All 38 inventory rows and Limassol weather, collected without model inference."""
import csv
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
import math
from pathlib import Path
import re
from urllib.parse import quote
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup


def module(name):
    spec=importlib.util.spec_from_file_location('prefetch_'+name,Path(__file__).with_name(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


HTTP=module('prefetch_http')
ALIASES={'eurusd':'EURUSD=X','brent':'BZ=F'}
ECB={'ecb-deposit':'DFR','ecb-mro':'MRR_FR','ecb-mlf':'MLFR'}
EURIBOR={'euribor-3m':('2','3'), 'euribor-6m':('3','6'), 'euribor-12m':('4','12')}
CSE='https://www.cse.com.cy/en-GB/regulated-market/market-indices/'
CSE_FALLBACK='https://www.stockwatch.com.cy/en/stockexchange/cse'
WEATHER='https://api.open-meteo.com/v1/forecast?latitude=34.68&longitude=33.04&current=temperature_2m,precipitation,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=UTC&timeformat=unixtime&forecast_days=2'
WEATHER_FALLBACK='https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=34.68&lon=33.04'
HOSTS={'query1.finance.yahoo.com','data-api.ecb.europa.eu','www.euribor-rates.eu','www.cse.com.cy','www.stockwatch.com.cy','api.open-meteo.com','api.met.no'}


def endpoint(instrument):
    if instrument in ECB:
        return 'https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.'+ECB[instrument]+'.LEV?lastNObservations=1&format=csvdata'
    if instrument in EURIBOR:
        number, months=EURIBOR[instrument]
        return f'https://www.euribor-rates.eu/en/current-euribor-rates/{number}/euribor-rate-{months}-months/'
    if instrument == 'cse':
        return CSE
    return 'https://query1.finance.yahoo.com/v8/finance/chart/'+quote(ALIASES.get(instrument,instrument),safe='')+'?interval=1d&range=5d'


def finite(value):
    return type(value) in (int,float) and math.isfinite(value)


def parse_quote(item,row,at):
    result={**item,'value':None,'change_pct':None,'quoted_at':None,'status':'unavailable','sources':[]}
    instrument=item['instrument']
    try:
        if row.get('status') != 'available':
            return result
        if instrument in ECB:
            rows=list(csv.DictReader(io.StringIO(row['text'])))
            point=rows[-1]; value=float(point['OBS_VALUE']); stamp=point['TIME_PERIOD']
            publisher='ECB Data Portal'; status='reference'
        elif instrument == 'cse' and row['url']==CSE_FALLBACK:
            text=BeautifulSoup(row['text'],'html.parser').get_text(' ',strip=True)
            index=re.search(r'GENERAL INDEX CSE:\s*([\d,]+\.\d+)\s*\(([+-]?[\d.]+)%\)',text)
            dated=re.search(r'Last Update:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})',text)
            if not index or not dated:
                return result
            value=float(index[1].replace(',',''));result['change_pct']=float(index[2])
            stamp=datetime.strptime(dated[1],'%d/%m/%Y %H:%M').replace(tzinfo=ZoneInfo(item['market_timezone'])).isoformat()
            publisher='StockWatch · ΧΑΚ (καθυστέρηση 15 λεπτών)';status='delayed'
        elif instrument in EURIBOR or instrument == 'cse':
            soup=BeautifulSoup(row['text'],'html.parser'); found=[]
            for tr in soup.select('tr'):
                cells=[' '.join(c.get_text(' ',strip=True).split()) for c in tr.select('td')]
                if not cells:
                    continue
                dates=re.findall(r'\b(20\d{2}-\d{2}-\d{2})\b',' '.join(cells))
                if not dates:
                    dates=[datetime.strptime(d,'%m/%d/%Y').date().isoformat() for d in re.findall(r'\b\d{1,2}/\d{1,2}/20\d{2}\b',' '.join(cells))]
                if instrument in EURIBOR:
                    rates=re.findall(r'(-?\d+[.,]\d+)\s*%', ' '.join(cells))
                    if dates and rates:
                        found.append((dates[0],float(rates[0].replace(',','.'))))
                elif re.search(r'general index|γενικ', ' '.join(cells),re.I) and dates:
                    # A number without the provider's observation date is never a quote.
                    numbers=re.findall(r'(?<![\d-])(\d+[.,]\d+)(?![\d-])',' '.join(cells[1:]))
                    if numbers:
                        found.append((dates[0],float(numbers[0].replace(',','.'))))
            day,value=sorted(found)[-1]; stamp=day
            publisher='Euribor Rates' if instrument in EURIBOR else 'Cyprus Stock Exchange'; status='reference'
        else:
            meta=HTTP.data(row)['chart']['result'][0]['meta']
            if meta['symbol'] != ALIASES.get(instrument,instrument) or meta['currency'] != item['currency']:
                return result
            value=meta['regularMarketPrice']; timestamp=meta['regularMarketTime']
            if not finite(timestamp):
                return result
            stamp=datetime.fromtimestamp(timestamp,timezone.utc).isoformat(); publisher='Yahoo Finance'; status='delayed'
            previous=meta.get('previousClose')
            if finite(previous) and previous>0 and finite(value):
                result['change_pct']=round((value/previous-1)*100,4)
        if not finite(value) or (item['asset_class']!='rate' and value<=0):
            return {**result,'change_pct':None}
        observed=datetime.fromisoformat(stamp)
        if observed.tzinfo is None:
            observed=observed.replace(tzinfo=timezone.utc)  # Ordering anchor only; public value stays date-only.
        retrieved=datetime.fromisoformat(row['retrieved_at'])
        # Missing/stale providers never trigger an AI price search. Historical snapshots stay dated.
        max_age=timedelta(days=10 if instrument in ECB else 5)
        if observed>at or observed>retrieved or at-observed>max_age:
            return {**result,'change_pct':None}
        # Public schema calls rate/index observations 'delayed'; date is the observation, never retrieval.
        result.update(value=value,quoted_at=stamp,status='delayed',sources=[HTTP.source(publisher,row['url'],row['retrieved_at'],kind='reporting' if instrument in EURIBOR or row['url']==CSE_FALLBACK else 'primary')])
    except (ValueError,KeyError,IndexError,TypeError,OverflowError):
        result.update(value=None,change_pct=None,quoted_at=None,status='unavailable',sources=[])
    return result


def weather(row,at):
    result={'status':'unavailable','location':'Λεμεσός','panels':[],'freshness':[],'warnings':'Δεν συλλέχθηκαν επίσημες προειδοποιήσεις.'}
    try:
        data=HTTP.data(row); current=data['current']; daily=data['daily']; units=data['current_units']
        if units['temperature_2m']!='°C' or units['wind_speed_10m']!='km/h':
            return result
        stamp=datetime.fromtimestamp(current['time'],timezone.utc)
        if stamp>at or at-stamp>timedelta(hours=2):
            return result
        values=[current[k] for k in ('temperature_2m','wind_speed_10m','precipitation')]
        values += [daily['temperature_2m_min'][0],daily['temperature_2m_max'][0],daily['precipitation_probability_max'][0]]
        if not all(finite(v) for v in values):
            return result
        temp,wind,rain,low,high,prob=values
        evidence=HTTP.source('Open-Meteo · μοντέλο πρόγνωσης',row['url'],row['retrieved_at'])
        until=stamp+timedelta(hours=2)
        result.update(status='available',observed_at=stamp.isoformat(),retrieved_at=row['retrieved_at'],
            panels=[dict(id='weather',heading='Καιρός · Λεμεσός',paragraphs=[f'Μοντέλο Open-Meteo: {temp:g} °C, άνεμος {wind:g} km/h, υετός {rain:g} mm. Ημερήσιο εύρος {low:g}–{high:g} °C, πιθανότητα υετού {prob:g}%. Δεν αποτελεί έλεγχο επίσημων προειδοποιήσεων.'],sources=[evidence])],
            freshness=[dict(id='weather-limassol',kind='weather',label='Μοντέλο καιρού · Λεμεσός',checked_at=row['checked_at'],valid_from=stamp.isoformat(),valid_until=until.isoformat(),recheck_at=until.isoformat(),sources=[row['url']])])
    except (ValueError,KeyError,IndexError,TypeError,OverflowError):
        pass
    return result


def collect(root,client,at):
    inventory=json.loads((Path(root)/'templates/v2/market-instruments.json').read_text(encoding='utf-8'))
    urls=[endpoint(q['instrument']) for q in inventory]
    rows=client.many(urls+[WEATHER])
    quotes=[parse_quote(q,rows[endpoint(q['instrument'])],max(at,datetime.fromisoformat(rows[endpoint(q['instrument'])].get('retrieved_at',at.isoformat())))) for q in inventory]
    for index,q in enumerate(quotes):
        if q['instrument']=='cse' and q['status']=='unavailable':
            fallback=client.get(CSE_FALLBACK)
            quotes[index]=parse_quote(inventory[index],fallback,max(at,datetime.fromisoformat(fallback.get('retrieved_at',at.isoformat()))))
    forecast=weather(rows[WEATHER],max(at,datetime.fromisoformat(rows[WEATHER].get('retrieved_at',at.isoformat()))))
    if forecast['status']=='unavailable':
        forecast=met_weather(client.get(WEATHER_FALLBACK),at)
    return {'markets':quotes,'weather':forecast,
            'availability':{q['instrument']:q['status'] for q in quotes}}


def met_weather(row,at):
    result={'status':'unavailable','location':'Λεμεσός','panels':[],'freshness':[]}
    try:
        data=HTTP.data(row)['properties']; times=data['timeseries']
        current=min((r for r in times if datetime.fromisoformat(r['time'].replace('Z','+00:00'))>=at-timedelta(hours=1)),key=lambda r:r['time'])
        start=datetime.fromisoformat(current['time'].replace('Z','+00:00'))
        if not at-timedelta(hours=1)<=start<=at+timedelta(hours=1):
            return result
        details=current['data']['instant']['details']; temp=details['air_temperature']; wind=details['wind_speed']
        if not finite(temp) or not finite(wind):
            return result
        evidence=HTTP.source('MET Norway · μοντέλο πρόγνωσης',row['url'],row['retrieved_at'])
        until=start+timedelta(hours=2)
        result.update(status='available',panels=[dict(id='weather',heading='Καιρός · Λεμεσός',paragraphs=[f'Μοντέλο MET Norway: {temp:g} °C, άνεμος {wind:g} m/s. Ώρα πρόγνωσης {start.isoformat()}. Δεν αποτελεί έλεγχο επίσημων προειδοποιήσεων.'],sources=[evidence])],
            freshness=[dict(id='weather-limassol',kind='weather',label='Μοντέλο καιρού · Λεμεσός',checked_at=row['checked_at'],valid_from=start.isoformat(),valid_until=until.isoformat(),recheck_at=until.isoformat(),sources=[row['url']])])
    except (ValueError,KeyError,IndexError,TypeError):
        pass
    return result
