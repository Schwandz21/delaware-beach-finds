"""Shared adapter for sites running The Events Calendar REST API.

Rehoboth and the Lewes Historical Society both publish through it, so the
retrieval and normalization live here once and each source supplies only its
identity. Adding another Events Calendar site is a few lines, not a new file.
"""
import json
import urllib.request
from datetime import datetime, timezone

from ..model import make_event, safe_description, valid

UA = 'DelawareBeachFinds/1.0 (+https://delawarebeachfinds.com)'


def fetch_tribe(*, name, home, api, source_type, first_party,
                default_town=None, id_prefix, per_page=50, timeout=25):
    report = {'source': name, 'url': api, 'method': 'JSON REST API',
              'firstParty': first_party, 'discovered': 0, 'accepted': 0,
              'rejected': 0, 'ok': False, 'error': None}
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        req = urllib.request.Request(
            '%s?per_page=%d&status=publish' % (api, per_page),
            headers={'User-Agent': UA, 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.loads(r.read().decode('utf-8'))
    except Exception as e:                                   # noqa: BLE001
        report['error'] = '%s: %s' % (type(e).__name__, e)
        return [], report

    raw = payload.get('events') or []
    report['discovered'] = len(raw)
    out = []
    for e in raw:
        try:
            start = str(e.get('start_date') or '')
            if not start:
                report['rejected'] += 1
                continue
            end = str(e.get('end_date') or start)
            sd, _, st = start.partition(' ')
            ed, _, et = end.partition(' ')
            v = e.get('venue') or {}
            cats = [c.get('name') for c in (e.get('categories') or []) if c.get('name')]
            ev = make_event(
                id='%s-%s' % (id_prefix, e.get('id')),
                title=e.get('title') or '',
                startDate=sd, endDate=ed or sd,
                startTime=(st[:5] if st and not e.get('all_day') else None),
                endTime=(et[:5] if et and not e.get('all_day') else None),
                allDay=bool(e.get('all_day')),
                timezone=e.get('timezone') or 'America/New_York',
                venue=v.get('venue') or None,
                town=v.get('city') or default_town,
                state='DE',
                category=(cats[0] if cats else None),
                description=safe_description(e.get('description')),
                sourceName=name, sourceUrl=e.get('url') or home,
                sourceEventId=e.get('id'),
                sourceType=source_type, firstParty=first_party,
                fetchedAt=stamp)
            good, _ = valid(ev)
            if not good:
                report['rejected'] += 1
                continue
            out.append(ev)
        except Exception:                                    # noqa: BLE001
            report['rejected'] += 1
    report['accepted'] = len(out)
    report['ok'] = True
    return out, report
