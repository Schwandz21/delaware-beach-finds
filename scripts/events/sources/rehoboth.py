"""City of Rehoboth Beach — The Events Calendar REST API.

First-party municipal source. https://www.rehobothbeachde.gov/events/
Retrieval: JSON REST (preferred tier 1), no scraping, no auth bypass.
"""
import json
import urllib.request
from datetime import datetime, timezone

from ..model import make_event, safe_description, valid

NAME = 'City of Rehoboth Beach'
HOME = 'https://www.rehobothbeachde.gov/events/'
API = 'https://www.rehobothbeachde.gov/wp-json/tribe/events/v1/events'
SOURCE_TYPE = 'municipal'
FIRST_PARTY = True
UA = 'DelawareBeachFinds/1.0 (+https://delawarebeachfinds.com)'


def fetch(limit=100, timeout=25):
    """Return (events, report). Never raises."""
    report = {'source': NAME, 'url': API, 'method': 'JSON REST API',
              'firstParty': FIRST_PARTY, 'discovered': 0, 'accepted': 0,
              'rejected': 0, 'ok': False, 'error': None}
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        req = urllib.request.Request(
            '%s?per_page=%d&status=publish' % (API, min(limit, 50)),
            headers={'User-Agent': UA, 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.loads(r.read().decode('utf-8'))
    except Exception as e:                                  # noqa: BLE001
        report['error'] = '%s: %s' % (type(e).__name__, e)
        return [], report

    raw = payload.get('events') or []
    report['discovered'] = len(raw)
    out = []
    for e in raw:
        try:
            start = str(e.get('start_date') or '')
            end = str(e.get('end_date') or start)
            if not start:
                report['rejected'] += 1
                continue
            sd, _, st = start.partition(' ')
            ed, _, et = end.partition(' ')
            v = e.get('venue') or {}
            cats = [c.get('name') for c in (e.get('categories') or []) if c.get('name')]
            ev = make_event(
                id='rehoboth-%s' % e.get('id'),
                title=e.get('title') or '',
                startDate=sd, endDate=ed or sd,
                startTime=(st[:5] if st and not e.get('all_day') else None),
                endTime=(et[:5] if et and not e.get('all_day') else None),
                allDay=bool(e.get('all_day')),
                timezone=e.get('timezone') or 'America/New_York',
                venue=v.get('venue') or None,
                town=v.get('city') or 'Rehoboth Beach',
                state='DE',
                category=(cats[0] if cats else None),
                description=safe_description(e.get('description')),
                sourceName=NAME,
                sourceUrl=e.get('url') or HOME,
                sourceEventId=e.get('id'),
                sourceType=SOURCE_TYPE, firstParty=FIRST_PARTY,
                fetchedAt=stamp)
            good, why = valid(ev)
            if not good:
                report['rejected'] += 1
                continue
            out.append(ev)
        except Exception:                                   # noqa: BLE001
            report['rejected'] += 1
    report['accepted'] = len(out)
    report['ok'] = True
    return out, report
