"""Normalized DBF event record, plus the rules that keep ingestion honest."""

import html
import re
import unicodedata
from datetime import datetime

TZ = 'America/New_York'

# Source precedence. Lower wins a duplicate contest.
PRECEDENCE = {
    'municipal': 1,    # a town or city publishing its own calendar
    'state': 2,        # state agency / state tourism
    'nonprofit': 3,    # verified institution, park friends group, library
    'regional': 4,     # reputable regional calendar
    'commercial': 5,   # secondary commercial discovery
}

# ---------------------------------------------------------------- NO FREE ADS
#
# Ingestion imports facts, not marketing. A venue is named because the location
# is a fact; that does not entitle it to sales copy, a booking link or a
# superlative. Any source description matching PROMO is dropped entirely rather
# than cleaned, because partial cleaning of advertising copy still leaves
# advertising copy. Title/date/time/venue always survive — they are the facts a
# reader needs.
PROMO = re.compile(
    r'\b(award[- ]winning|world[- ]class|unforgettable|must[- ]see|don\'?t miss|'
    r'book now|reserve (your|now)|buy (your )?tickets|shop now|order now|'
    r'best[- ]in[- ]|voted best|mouth[- ]?watering|delicious|scrumptious|'
    r'stunning|breathtaking|luxurious|premier destination|special offer|'
    r'limited time|save \d+%?|discount|\d+% off|call today|visit us today|'
    r'family[- ]owned and operated|our friendly staff)\b', re.I)

TAG = re.compile(r'<[^>]+>')
WS = re.compile(r'\s+')


def clean_text(raw):
    """HTML source text to plain text. Entities resolved, tags and links gone."""
    if not raw:
        return ''
    t = TAG.sub(' ', str(raw))
    t = html.unescape(t)
    t = t.replace(' ', ' ')
    return WS.sub(' ', t).strip()


def safe_description(raw, limit=220):
    """A factual one-liner, or nothing at all.

    Returns '' when the source text reads as advertising. We would rather show
    an event with no description than hand a commercial host free copy.
    """
    t = clean_text(raw)
    if not t:
        return ''
    if PROMO.search(t):
        return ''
    # First sentence only; source blurbs run long and drift into promotion.
    m = re.split(r'(?<=[.!?])\s+', t)
    out = m[0] if m else t
    if len(out) > limit:
        out = out[:limit].rsplit(' ', 1)[0] + '…'
    return out


def norm_title(t):
    """Aggressively normalized title used only for duplicate matching."""
    t = clean_text(t).lower()
    t = unicodedata.normalize('NFKD', t)
    t = re.sub(r'[‘’“”]', '', t)
    t = re.sub(r'\b(the|a|an|at|in|on|of|and|&|presented by)\b', ' ', t)
    t = re.sub(r'[^a-z0-9 ]', ' ', t)
    return WS.sub(' ', t).strip()


def tidy_title(t):
    """Display title: entities resolved, source cruft trimmed."""
    t = clean_text(t)
    t = re.sub(r'\s*[-–—]\s*$', '', t)
    return t


# Sources spell the same town several ways ("Rehoboth Beach DE", "Rehoboth
# Beach, DE"). Left alone this fragments town filtering and looks sloppy on the
# page, so town names are canonicalised on the way in.
TOWNS = {
    'rehoboth beach': 'Rehoboth Beach', 'rehoboth': 'Rehoboth Beach',
    'bethany beach': 'Bethany Beach', 'north bethany': 'Bethany Beach',
    'dewey beach': 'Dewey Beach', 'lewes': 'Lewes',
    'fenwick island': 'Fenwick Island', 'milton': 'Milton',
    'ocean view': 'Ocean View', 'millsboro': 'Millsboro',
    'ocean city': 'Ocean City',
}


def norm_town(raw):
    if not raw:
        return None
    t = clean_text(raw)
    key = re.sub(r'[,\.]', ' ', t).lower()
    key = re.sub(r'\b(de|delaware|md|maryland)\b', ' ', key)
    key = WS.sub(' ', key).strip()
    return TOWNS.get(key, t)


def make_event(**kw):
    """Build a normalized record. Unknown means absent, never invented."""
    ev = {
        'id': kw['id'],
        'title': tidy_title(kw['title']),
        'startDate': kw['startDate'],
        'endDate': kw.get('endDate') or kw['startDate'],
        'startTime': kw.get('startTime'),
        'endTime': kw.get('endTime'),
        'allDay': bool(kw.get('allDay')),
        'timezone': kw.get('timezone') or TZ,
        'venue': kw.get('venue') or None,
        'town': norm_town(kw.get('town')),
        'state': kw.get('state') or 'DE',
        'category': kw.get('category') or None,
        'description': kw.get('description') or '',
        'sourceName': kw['sourceName'],
        'sourceUrl': kw['sourceUrl'],
        'sourceEventId': str(kw.get('sourceEventId') or ''),
        'sourceType': kw.get('sourceType') or 'municipal',
        'firstParty': bool(kw.get('firstParty', True)),
        'fetchedAt': kw['fetchedAt'],
        # Machine ingestion never confers editorial endorsement or sponsorship.
        'featured': False,
        'sponsored': False,
        'sponsorId': None,
    }
    return {k: v for k, v in ev.items() if v is not None or k in
            ('startTime', 'endTime', 'venue', 'town', 'category', 'sponsorId')}


DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def valid(ev):
    """Reject anything we cannot stand behind."""
    if not ev.get('title') or len(ev['title']) < 3:
        return False, 'missing title'
    for f in ('startDate', 'endDate'):
        if not DATE_RE.match(str(ev.get(f) or '')):
            return False, 'bad %s' % f
    if ev['endDate'] < ev['startDate']:
        return False, 'end before start'
    if not ev.get('sourceUrl'):
        return False, 'missing sourceUrl'
    try:
        datetime.strptime(ev['startDate'], '%Y-%m-%d')
    except ValueError:
        return False, 'unparseable startDate'
    return True, ''
