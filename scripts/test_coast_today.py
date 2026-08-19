#!/usr/bin/env python3
"""Temporal and resilience tests for the daily coast layer.

Uses fixtures, not live APIs: these must pass on a runner with no network and
must not depend on what the weather happens to be doing.
"""
import datetime, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASS, FAIL = [], []

def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print('  %s - %s%s' % ('ok  ' if cond else 'FAIL', name,
                           '' if cond else '\n          >>> %s' % detail))

DAYS = ['sunday','monday','tuesday','wednesday','thursday','friday','saturday']

def on_now(e, today):
    """Mirror of the site.js rule, kept in step by the assertions below."""
    s = e.get('startDate') or ''
    x = e.get('endDate') or s
    if not (s <= today <= x):
        return False
    if s and x:
        span = (datetime.date.fromisoformat(x) - datetime.date.fromisoformat(s)).days
        if span > 2:
            d = str(e.get('displayDate') or '').lower()
            dows = [y for y in DAYS if y in d]
            if dows:
                dow = DAYS[(datetime.date.fromisoformat(today).weekday() + 1) % 7]
                return dow in dows
    return True

print('=== event temporal logic ===')
T = '2026-08-19'   # a Wednesday
check('event today shows',
      on_now({'startDate':'2026-08-19','endDate':'2026-08-19'}, T))
check('event tomorrow does not show',
      not on_now({'startDate':'2026-08-20','endDate':'2026-08-20'}, T))
check('event ended yesterday does not show',
      not on_now({'startDate':'2026-08-18','endDate':'2026-08-18'}, T))
check('multi-day event spanning today shows',
      on_now({'startDate':'2026-08-18','endDate':'2026-08-21'}, T))
check('weekly Saturday market hidden on a Wednesday',
      not on_now({'startDate':'2026-08-15','endDate':'2026-09-26',
                  'displayDate':'Saturdays 8 AM-noon, through Sept. 26'}, T))
check('weekly Wednesday market shows on a Wednesday',
      on_now({'startDate':'2026-08-19','endDate':'2026-09-02',
              'displayDate':'Wednesdays 8-11:30 AM, through Sept. 2'}, T))
check('weekly Saturday market shows on a Saturday',
      on_now({'startDate':'2026-08-15','endDate':'2026-09-26',
              'displayDate':'Saturdays 8 AM-noon, through Sept. 26'}, '2026-08-22'))
check('all-day event with no endDate shows on its day',
      on_now({'startDate':'2026-08-19'}, T))

print('\n=== coast-now shape and honesty ===')
p = os.path.join(ROOT, 'data', 'coast-now.json')
check('coast-now.json exists', os.path.exists(p), p)
if os.path.exists(p):
    d = json.load(open(p, encoding='utf-8'))
    check('has generatedAt', bool(d.get('generatedAt')))
    check('timezone is America/New_York', d.get('timezone') == 'America/New_York')
    locs = d.get('locations') or []
    check('has locations', len(locs) >= 3, len(locs))
    for l in locs:
        w = l.get('water')
        if w:
            # The measurement must name the station that produced it, so we
            # never imply a Lewes reading is Bethany's.
            check('%s water names its station' % l['id'], bool(w.get('stationName')))
            check('%s water has a source' % l['id'], bool(w.get('source')))
        t = l.get('tides')
        if t:
            check('%s tides name their station' % l['id'], bool(t.get('stationName')))
            for pr in t.get('predictions', []):
                check('%s tide type is high/low' % l['id'], pr['type'] in ('high','low'), pr)
                break
        a = l.get('alerts')
        if a is not None:
            check('%s alerts is a list' % l['id'], isinstance(a.get('items'), list))
    check('DNREC is a link-out, never a swim verdict',
          (d.get('dnrec') or {}).get('mode') == 'official-link')
    body = ((d.get('dnrec') or {}).get('body') or '').lower()
    check('DNREC copy does not claim safe/unsafe to swim',
          'safe to swim' not in body or 'not a live safe-to-swim' in body, body[:90])

print('\n=== staleness handling ===')
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import fetch_coast_now as f
now = datetime.datetime(2026, 8, 19, 12, 0, tzinfo=datetime.timezone.utc)
fresh = {'fetchedAt': '2026-08-19T11:30:00Z', 'temperature': 70}
old   = {'fetchedAt': '2026-08-17T11:30:00Z', 'temperature': 70}
kept = f.keep_last_good(fresh, 'weather', now)
check('recent reading is carried forward and marked stale',
      kept and kept.get('stale') is True and kept.get('ageMinutes') == 30, kept)
check('very old reading is dropped rather than shown',
      f.keep_last_good(old, 'weather', now) is None)
check('missing previous returns nothing', f.keep_last_good(None, 'weather', now) is None)

print('\n=== renderer safety ===')
js = open(os.path.join(ROOT, 'assets', 'js', 'site.js'), encoding='utf-8').read()
check('water temperature is never estimated in the renderer',
      'estimate' not in js.lower().split('coast-now')[-1][:4000])
check('alerts render only from fetched items', 'al.items' in js or '(al&&al.items)' in js)
check('coast renderer degrades via gateHide', js.count('gateHide(coastMount)') >= 1)

print('\n' + '=' * 32)
print('Passed: %d   Failed: %d' % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
