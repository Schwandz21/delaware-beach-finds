#!/usr/bin/env python3
"""Fetch official daily coastal conditions into data/coast-now.json.

Sources, all first-party government:
  National Weather Service   api.weather.gov          forecast + active alerts
  NOAA CO-OPS                api.tidesandcurrents...  tide predictions, water temp
  Delaware DNREC             recwaters.dnrec...       recreational water monitoring

Design rules this file exists to enforce:

  * Nothing is invented. A value we did not receive is absent, not estimated.
  * One failing source never takes down the others, and never takes down the
    page. Each source is fetched independently and its failure recorded.
  * Last-known-good: on failure we keep the previous value and mark it stale
    with the timestamp it was actually fetched. We never present stale data as
    current.
  * Measurements are labelled with the station that produced them. The Lewes
    water temperature is the Lewes water temperature, not "Delaware's".

Usage:
    python3 scripts/fetch_coast_now.py            # refresh all
    python3 scripts/fetch_coast_now.py --dry-run  # fetch, print, write nothing
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, 'data', 'coast-now.json')

UA = 'DelawareBeachFinds/1.0 (+https://delawarebeachfinds.com; michael@rentdelawarebeaches.com)'
TIMEOUT = 20

# Anything older than this is no longer presented as current.
STALE_AFTER_MIN = {'weather': 180, 'alerts': 90, 'tides': 1440, 'water': 360}

# Representative coastal points. Coordinates are the town centres; the NWS grid
# is discovered from /points rather than hard-coded, because grids do change.
LOCATIONS = [
    {'id': 'lewes',    'name': 'Lewes',          'lat': 38.7746, 'lon': -75.1393,
     'tideStation': '8557380', 'tideStationName': 'Lewes',
     'waterStation': '8557380', 'waterStationName': 'Lewes'},
    {'id': 'rehoboth', 'name': 'Rehoboth Beach', 'lat': 38.7168, 'lon': -75.0760,
     'tideStation': '8557380', 'tideStationName': 'Lewes',
     'waterStation': '8557380', 'waterStationName': 'Lewes'},
    {'id': 'dewey',    'name': 'Dewey Beach',    'lat': 38.6884, 'lon': -75.0755,
     'tideStation': '8557380', 'tideStationName': 'Lewes',
     'waterStation': '8557380', 'waterStationName': 'Lewes'},
    {'id': 'bethany',  'name': 'Bethany Beach',  'lat': 38.5385, 'lon': -75.0552,
     'tideStation': '8570283', 'tideStationName': 'Ocean City Inlet',
     'waterStation': '8570283', 'waterStationName': 'Ocean City Inlet'},
    {'id': 'fenwick',  'name': 'Fenwick Island', 'lat': 38.4610, 'lon': -75.0510,
     'tideStation': '8570283', 'tideStationName': 'Ocean City Inlet',
     'waterStation': '8570283', 'waterStationName': 'Ocean City Inlet'},
]

DNREC_URL = 'https://recwaters.dnrec.delaware.gov/'
DNREC_INFO = ('https://dnrec.delaware.gov/watershed-stewardship/assessment/'
              'recreational-water-monitoring/')

failures = []


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def get_json(url, tag):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode('utf-8'))


def try_json(url, tag):
    """Return (data, None) or (None, error-string). Never raises."""
    try:
        return get_json(url, tag), None
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError, TimeoutError) as e:
        msg = '%s: %s' % (tag, e)
        failures.append(msg)
        print('  !! %s' % msg)
        return None, str(e)


def load_previous():
    if os.path.exists(OUT):
        try:
            return json.load(open(OUT, encoding='utf-8'))
        except (ValueError, OSError):
            pass
    return {}


def prev_location(prev, loc_id):
    for l in (prev.get('locations') or []):
        if l.get('id') == loc_id:
            return l
    return {}


def keep_last_good(prev_block, kind, stamp_now):
    """Carry a previous reading forward, marked stale with its real age."""
    if not prev_block:
        return None
    block = dict(prev_block)
    fetched = block.get('fetchedAt')
    block['stale'] = True
    if fetched:
        try:
            age = (stamp_now - datetime.strptime(fetched, '%Y-%m-%dT%H:%M:%SZ')
                   .replace(tzinfo=timezone.utc)).total_seconds() / 60
            block['ageMinutes'] = int(age)
            # Past a point a stale reading is worse than none at all.
            if age > STALE_AFTER_MIN.get(kind, 240):
                return None
        except ValueError:
            return None
    return block


# ------------------------------------------------------------------ sources --

def fetch_grid(loc):
    """Discover the NWS grid + forecast zone for a point."""
    d, err = try_json('https://api.weather.gov/points/%.4f,%.4f' % (loc['lat'], loc['lon']),
                      'nws-points/%s' % loc['id'])
    if not d:
        return None
    p = d.get('properties', {})
    zone = (p.get('forecastZone') or '').rstrip('/').split('/')[-1]
    return {'gridId': p.get('gridId'), 'gridX': p.get('gridX'), 'gridY': p.get('gridY'),
            'forecast': p.get('forecast'), 'zone': zone}


def fetch_weather(grid, stamp):
    if not grid or not grid.get('forecast'):
        return None
    d, err = try_json(grid['forecast'], 'nws-forecast')
    if not d:
        return None
    periods = (d.get('properties') or {}).get('periods') or []
    if not periods:
        return None
    p = periods[0]
    out = {
        'period': p.get('name'),
        'temperature': p.get('temperature'),
        'temperatureUnit': p.get('temperatureUnit'),
        'shortForecast': p.get('shortForecast'),
        'windSpeed': p.get('windSpeed'),
        'windDirection': p.get('windDirection'),
        'isDaytime': p.get('isDaytime'),
        'source': 'National Weather Service',
        'sourceUrl': 'https://www.weather.gov/',
        'fetchedAt': iso(stamp),
        'stale': False,
    }
    pop = (p.get('probabilityOfPrecipitation') or {}).get('value')
    if pop is not None:
        out['precipProbability'] = pop
    return out


def fetch_alerts(zone, stamp):
    if not zone:
        return None
    d, err = try_json('https://api.weather.gov/alerts/active?zone=%s' % zone, 'nws-alerts')
    if d is None:
        return None
    items = []
    for f in d.get('features') or []:
        p = f.get('properties') or {}
        items.append({
            'event': p.get('event'),
            'severity': p.get('severity'),
            'headline': p.get('headline'),
            'url': p.get('@id') or p.get('id'),
            'ends': p.get('ends') or p.get('expires'),
        })
    # An empty list is a real, meaningful answer: nothing is in effect.
    return {'items': items, 'source': 'National Weather Service',
            'sourceUrl': 'https://www.weather.gov/', 'zone': zone,
            'fetchedAt': iso(stamp), 'stale': False}


def fetch_tides(station, station_name, stamp):
    today = stamp.astimezone(timezone(timedelta(hours=-4))).strftime('%Y%m%d')
    url = ('https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?'
           'product=predictions&application=DelawareBeachFinds&begin_date=%s&end_date=%s'
           '&datum=MLLW&station=%s&time_zone=lst_ldt&units=english&interval=hilo&format=json'
           % (today, today, station))
    d, err = try_json(url, 'noaa-tides/%s' % station)
    if not d or 'predictions' not in d:
        return None
    preds = [{'time': x['t'], 'type': 'high' if x['type'] == 'H' else 'low',
              'heightFt': round(float(x['v']), 1)} for x in d['predictions']]
    return {'station': station, 'stationName': station_name, 'predictions': preds,
            'source': 'NOAA Tides & Currents',
            'sourceUrl': 'https://tidesandcurrents.noaa.gov/stationhome.html?id=%s' % station,
            'fetchedAt': iso(stamp), 'stale': False}


def fetch_water(station, station_name, stamp):
    url = ('https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?'
           'product=water_temperature&application=DelawareBeachFinds&date=latest'
           '&station=%s&time_zone=lst_ldt&units=english&format=json' % station)
    d, err = try_json(url, 'noaa-watertemp/%s' % station)
    if not d or not d.get('data'):
        # Not every station reports water temperature. That is not an error and
        # is never estimated from a neighbouring station.
        return None
    rec = d['data'][0]
    try:
        val = round(float(rec['v']), 1)
    except (KeyError, ValueError):
        return None
    return {'station': station, 'stationName': station_name, 'temperatureF': val,
            'observedAt': rec.get('t'), 'source': 'NOAA Tides & Currents',
            'sourceUrl': 'https://tidesandcurrents.noaa.gov/stationhome.html?id=%s' % station,
            'fetchedAt': iso(stamp), 'stale': False}


def build_dnrec(stamp):
    """DNREC is presented as an official-source card, deliberately.

    Recreational water monitoring is periodic sampling, not a live safe/unsafe
    signal. We will not synthesise a swim-safety indicator from it. Readers get
    an honest description and a link to DNREC's own current guidance.
    """
    return {
        'label': 'Recreational water monitoring',
        'body': ('DNREC samples Delaware swimming areas on a schedule through the '
                 'season. It is periodic monitoring, not a live safe-to-swim '
                 'reading, so check their current guidance before you rely on it.'),
        'source': 'Delaware DNREC',
        'sourceUrl': DNREC_URL,
        'infoUrl': DNREC_INFO,
        'mode': 'official-link',
        'fetchedAt': iso(stamp),
    }


# -------------------------------------------------------------------- main ---

def main():
    dry = '--dry-run' in sys.argv
    stamp = now_utc()
    prev = load_previous()
    prev_grids = prev.get('_grids') or {}

    print('Fetching coastal conditions at %s' % iso(stamp))
    out = {
        'generatedAt': iso(stamp),
        'timezone': 'America/New_York',
        'locations': [],
        'dnrec': build_dnrec(stamp),
        'sources': [
            {'name': 'National Weather Service', 'url': 'https://www.weather.gov/',
             'used': 'forecast, active alerts'},
            {'name': 'NOAA Tides & Currents', 'url': 'https://tidesandcurrents.noaa.gov/',
             'used': 'tide predictions, water temperature'},
            {'name': 'Delaware DNREC', 'url': DNREC_URL,
             'used': 'recreational water monitoring (link-out)'},
        ],
        '_grids': {},
        '_failures': [],
    }

    for loc in LOCATIONS:
        print('  %s' % loc['name'])
        pl = prev_location(prev, loc['id'])

        # Grids rarely change; reuse yesterday's unless it is missing.
        grid = prev_grids.get(loc['id'])
        if not grid or not grid.get('forecast'):
            grid = fetch_grid(loc)
        if grid:
            out['_grids'][loc['id']] = grid

        weather = fetch_weather(grid, stamp) or keep_last_good(pl.get('weather'), 'weather', stamp)
        alerts = fetch_alerts((grid or {}).get('zone'), stamp) or \
            keep_last_good(pl.get('alerts'), 'alerts', stamp)
        tides = fetch_tides(loc['tideStation'], loc['tideStationName'], stamp) or \
            keep_last_good(pl.get('tides'), 'tides', stamp)
        water = fetch_water(loc['waterStation'], loc['waterStationName'], stamp) or \
            keep_last_good(pl.get('water'), 'water', stamp)

        entry = {'id': loc['id'], 'name': loc['name'],
                 'lat': loc['lat'], 'lon': loc['lon']}
        if weather: entry['weather'] = weather
        if alerts:  entry['alerts'] = alerts
        if tides:   entry['tides'] = tides
        if water:   entry['water'] = water
        out['locations'].append(entry)

    out['_failures'] = failures
    have = sum(1 for l in out['locations'] if l.get('weather'))
    print('\n  %d/%d locations have weather, %d source failure(s)'
          % (have, len(LOCATIONS), len(failures)))

    if dry:
        print(json.dumps(out['locations'][0], indent=2)[:900])
        print('\nDRY RUN — nothing written.')
        return 0

    # Refuse to overwrite good data with a totally failed run.
    if not have and prev.get('locations'):
        print('  every source failed — keeping the previous file untouched.')
        return 1

    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
        fh.write('\n')
    print('  wrote %s' % os.path.relpath(OUT, REPO))
    return 0


if __name__ == '__main__':
    sys.exit(main())
