"""Town of Bethany Beach — CivicPlus calendar RSS.

First-party municipal source. https://www.townofbethanybeach.com/Calendar.aspx
Retrieval: RSS with a calendarEvent namespace (preferred tier 3).
"""
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from ..model import make_event, safe_description, valid, clean_text

NAME = 'Town of Bethany Beach'
HOME = 'https://www.townofbethanybeach.com/Calendar.aspx'
FEED = ('https://www.townofbethanybeach.com/RSSFeed.aspx'
        '?ModID=58&CID=All-calendar.xml')
NS = {'ce': 'https://www.townofbethanybeach.com/Calendar.aspx'}
SOURCE_TYPE = 'municipal'
FIRST_PARTY = True
UA = 'DelawareBeachFinds/1.0 (+https://delawarebeachfinds.com)'

MONTHS = {m: i + 1 for i, m in enumerate(
    ['january', 'february', 'march', 'april', 'may', 'june', 'july',
     'august', 'september', 'october', 'november', 'december'])}
DATE = re.compile(r'([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})')
TIME = re.compile(r'(\d{1,2}):(\d{2})\s*([AaPp])\.?[Mm]')


def _date(txt):
    m = DATE.search(txt or '')
    if not m:
        return None
    mon = MONTHS.get(m.group(1).lower())
    if not mon:
        return None
    return '%04d-%02d-%02d' % (int(m.group(3)), mon, int(m.group(2)))


def _times(txt):
    """Return (start, end) as HH:MM, or (None, None) for an all-day span."""
    found = TIME.findall(txt or '')
    def to24(h, mi, ap):
        h = int(h)
        if ap.lower() == 'p' and h != 12:
            h += 12
        if ap.lower() == 'a' and h == 12:
            h = 0
        return '%02d:%s' % (h, mi)
    if len(found) >= 2:
        s, e = to24(*found[0]), to24(*found[1])
        # CivicPlus writes an all-day event as 12:00 AM - 11:59 PM.
        if s == '00:00' and e == '23:59':
            return None, None
        return s, e
    if len(found) == 1:
        return to24(*found[0]), None
    return None, None


def fetch(timeout=25):
    report = {'source': NAME, 'url': FEED, 'method': 'RSS (calendarEvent ns)',
              'firstParty': FIRST_PARTY, 'discovered': 0, 'accepted': 0,
              'rejected': 0, 'ok': False, 'error': None}
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        req = urllib.request.Request(FEED, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            root = ET.fromstring(r.read())
    except Exception as e:                                  # noqa: BLE001
        report['error'] = '%s: %s' % (type(e).__name__, e)
        return [], report

    items = root.findall('.//item')
    report['discovered'] = len(items)
    out = []
    for it in items:
        try:
            title = (it.findtext('title') or '').strip()
            link = (it.findtext('link') or HOME).strip()
            dates = it.findtext('ce:EventDates', default='', namespaces=NS)
            times = it.findtext('ce:EventTimes', default='', namespaces=NS)
            loc = clean_text(it.findtext('ce:Location', default='', namespaces=NS))
            sd = _date(dates)
            if not sd:
                report['rejected'] += 1
                continue
            st, et = _times(times)
            eid = ''
            m = re.search(r'EID=(\d+)', link)
            if m:
                eid = m.group(1)
            # Location often arrives as just "Bethany Beach, DE 19930", which is
            # a town, not a venue. Only treat it as a venue when it says more.
            venue = None
            if loc and not re.match(r'^Bethany Beach,?\s*DE', loc, re.I):
                venue = loc.split(',')[0].strip() or None
            ev = make_event(
                id='bethany-%s' % (eid or abs(hash(title + sd)) % 10**8),
                title=title, startDate=sd, endDate=sd,
                startTime=st, endTime=et, allDay=(st is None),
                venue=venue, town='Bethany Beach', state='DE',
                description=safe_description(it.findtext('description')),
                sourceName=NAME, sourceUrl=link, sourceEventId=eid,
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
