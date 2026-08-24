#!/usr/bin/env python3
"""Fixture-based tests for the event ingestion engine. No network required."""
import json, os, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from events.model import make_event, safe_description, valid, norm_town, norm_title  # noqa
from events.dedupe import dedupe, is_duplicate                                        # noqa

PASS, FAIL = [], []
def check(n, c, d=''):
    (PASS if c else FAIL).append(n)
    print('  %s - %s%s' % ('ok  ' if c else 'FAIL', n, '' if c else '\n          >>> %s' % d))

S = '2026-08-19T12:00:00Z'
def ev(**kw):
    base = dict(id='x', title='Test Event', startDate='2026-08-19',
                sourceName='Src', sourceUrl='https://example.org/e',
                fetchedAt=S)
    base.update(kw)
    return make_event(**base)

print('=== normalization and validation ===')
check('valid event passes', valid(ev())[0])
check('missing title rejected', not valid(ev(title=''))[0])
check('end before start rejected', not valid(ev(startDate='2026-08-19', endDate='2026-08-18'))[0])
check('bad date format rejected', not valid(ev(startDate='19/08/2026'))[0])
check('missing sourceUrl rejected', not valid(ev(sourceUrl=''))[0])
check('missing optional venue is fine', valid(ev(venue=None))[0] and ev(venue=None).get('venue') is None)
check('missing optional description is fine', ev(description='').get('description') == '')
check('html entities resolved in title', ev(title='Farmers&#8217; Market')['title'] == 'Farmers’ Market')
check('town normalized: Rehoboth Beach DE', norm_town('Rehoboth Beach DE') == 'Rehoboth Beach')
check('town normalized: rehoboth', norm_town('rehoboth') == 'Rehoboth Beach')
check('unknown town preserved verbatim', norm_town('Slaughter Beach') == 'Slaughter Beach')

print('\n=== no free ads ===')
promo = '<p>Join us at the <b>award-winning</b> Ocean Breeze Bistro for an unforgettable evening!</p>'
check('promotional copy is dropped entirely', safe_description(promo) == '')
check('factual copy survives',
      safe_description('<p>Live music on the bandstand from 7-10 p.m.</p>').startswith('Live music'))
check('booking CTA dropped', safe_description('Book now for the best seats!') == '')
check('discount language dropped', safe_description('Save 20% on tickets this week.') == '')
check('html tags and links stripped',
      '<' not in safe_description('<p>Talk at the <a href="http://x.com">library</a> at 6 p.m.</p>'))
check('ingested event is never featured', ev()['featured'] is False)
check('ingested event is never sponsored', ev()['sponsored'] is False)
check('ingested event has no sponsorId', ev().get('sponsorId') is None)

print('\n=== deduplication and precedence ===')
a = ev(id='a', title='Bandstand Concert', town='Rehoboth Beach', startTime='19:00',
       sourceName='City of Rehoboth Beach', sourceType='municipal', firstParty=True)
b = ev(id='b', title='Bandstand Concert', town='Rehoboth Beach', startTime='19:00',
       sourceName='Regional Calendar', sourceType='regional', firstParty=False)
kept, removed = dedupe([b, a])
check('exact duplicate collapsed', len(kept) == 1 and removed == 1)
check('first-party municipal source wins', kept[0]['sourceName'] == 'City of Rehoboth Beach')
check('absorbed source kept as provenance',
      any(x['sourceName'] == 'Regional Calendar' for x in kept[0].get('alsoReportedBy', [])))

c1 = ev(id='c', title='Bandstand Concert Series', town='Rehoboth Beach', startTime='19:00')
check('fuzzy duplicate detected', is_duplicate(a, c1))
d1 = ev(id='d', title='Farmers Market', town='Rehoboth Beach', startTime='19:00')
check('distinct events not merged', not is_duplicate(a, d1))
e1 = ev(id='e', title='Bandstand Concert', town='Bethany Beach', startTime='19:00')
check('same title in another town not merged', not is_duplicate(a, e1))
f1 = ev(id='f', title='Bandstand Concert', town='Rehoboth Beach', startTime='12:00')
check('same title different sitting not merged', not is_duplicate(a, f1))
g1 = ev(id='g', title='Bandstand Concert', town='Rehoboth Beach',
        startDate='2026-08-20', startTime='19:00')
check('same title another day not merged', not is_duplicate(a, g1))

print('\n=== generated file integrity ===')
p = os.path.join(ROOT, 'data', 'events-generated.json')
check('events-generated.json exists', os.path.exists(p))
if os.path.exists(p):
    g = json.load(open(p, encoding='utf-8'))
    evs = g.get('events') or []
    check('has ingested events', len(evs) > 0, len(evs))
    check('every event carries a source url', all(e.get('sourceUrl') for e in evs))
    check('every event carries a source name', all(e.get('sourceName') for e in evs))
    check('no ingested event is featured', not any(e.get('featured') for e in evs))
    check('no ingested event is sponsored', not any(e.get('sponsored') for e in evs))
    check('no duplicate ids', len({e['id'] for e in evs}) == len(evs))
    check('every event validates', all(valid(e)[0] for e in evs))
    check('source reports recorded', len(g.get('sources') or []) >= 2)
    towns = {e.get('town') for e in evs if e.get('town')}
    check('town names are canonical (no "DE" suffixes)',
          not any(t.endswith(' DE') for t in towns), towns)

print('\n=== reader relevance (audience classification) ===')
from events.model import audience_of
check('variance hearing classified civic',
      audience_of('Board of Adjustment Variance Hearing for 1 Rehoboth Avenue') == 'civic')
check('commission meeting classified civic',
      audience_of('Parks & Shade Tree Commission Meeting') == 'civic')
check('private rental classified private',
      audience_of('Stockley Park Pavilion - Private Rental') == 'private')
check('farmers market stays public', audience_of('Rehoboth Beach Farmers Market') == 'public')
check('concert stays public', audience_of('Summer Concert Series: Earth Jam') == 'public')
check('swim stays public', audience_of('Boardwalk Mile Swim') == 'public')

gp = os.path.join(ROOT, 'data', 'events-generated.json')
if os.path.exists(gp):
    gen = json.load(open(gp, encoding='utf-8'))
    evs = gen.get('events') or []
    check('every ingested event carries an audience',
          all(e.get('audience') in ('public', 'civic', 'private') for e in evs))
    pub = [e for e in evs if e.get('audience') == 'public']
    check('the public feed is not empty', len(pub) > 0, len(pub))
    # The franchise went dark for 12 days because a stale legacy file gated it.
    check('reader-facing events exist for the homepage franchise',
          len(pub) >= 5, '%d public events' % len(pub))

js = open(os.path.join(ROOT, 'assets', 'js', 'site.js'), encoding='utf-8').read()
check('DBF Weekend reads the ingested pipeline, not the stale legacy file',
      "Promise.all([loadEvents(), fetchJson('events-generated.json')" in js)
check('full-calendar pages can opt out of the reader filter',
      "data-audience" in js and "showAll" in js)
check('civic entries are labelled where shown', 'event-civic-badge' in js)

print('\n=== editorial overlay contract ===')
ep = os.path.join(ROOT, 'data', 'events-editorial.json')
check('events-editorial.json exists', os.path.exists(ep))
if os.path.exists(ep):
    ed = json.load(open(ep, encoding='utf-8'))
    check('overrides is a list', isinstance(ed.get('overrides'), list))
    check('no override sets sponsored',
          not any(o.get('sponsored') for o in ed.get('overrides', [])),
          'editorial must never sell placement')
    check('how-to documented in file', bool(ed.get('_howTo')))

js = open(os.path.join(ROOT, 'assets', 'js', 'site.js'), encoding='utf-8').read()
check('renderer applies suppression', 'o.suppress' in js)
check('renderer forces sponsored false on merge', 'merged.sponsored = e.sponsored || false' in js)
check('renderer has an honest empty state', 'Nothing we can verify' in js)

print('\n' + '=' * 32)
print('Passed: %d   Failed: %d' % (len(PASS), len(FAIL)))
sys.exit(1 if FAIL else 0)
