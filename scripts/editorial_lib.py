"""Shared editorial-operating-system helpers.

Canonical sources of truth (documented in EDITORIAL_OPERATIONS.md):

  data/stories.json            story registry: lifecycle, scheduling, placement
  content/stories/<slug>.html  article prose (the body fragment, verbatim HTML)
  data/editorial-calendar.json cadence, publication windows, overrides
  data/authors.json            house editorial desks
  data/issues/                 issue records and issue index

Nothing here talks to the network and nothing here invents editorial content.
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA = os.path.join(REPO, 'data')
CONTENT = os.path.join(REPO, 'content', 'stories')
STORIES_DIR = os.path.join(REPO, 'stories')

STORIES_JSON = os.path.join(DATA, 'stories.json')
CALENDAR_JSON = os.path.join(DATA, 'editorial-calendar.json')
AUTHORS_JSON = os.path.join(DATA, 'authors.json')
ISSUE_INDEX = os.path.join(DATA, 'issues', 'index.json')

SITE_ORIGIN = 'https://delawarebeachfinds.com'

# ---------------------------------------------------------------- lifecycle --

# The canonical publishing-state model. Order is meaningful: it is the path a
# story travels. `held` and `retired` are off-path and handled explicitly.
LIFECYCLE = ['draft', 'review', 'approved', 'scheduled', 'published']
OFF_PATH = ['held', 'retired']
ALL_STATUSES = LIFECYCLE + OFF_PATH

# Only these statuses render on the public site.
PUBLIC_STATUSES = {'published'}

# A story may only be auto-published from this status.
PUBLISHABLE_FROM = 'scheduled'

# Placement controls homepage prominence. It is deliberately independent of
# publication status: demoting a cover story must never unpublish it.
PLACEMENTS = ['cover', 'feature', 'secondary', 'standard']


class EditorialError(Exception):
    """Raised for any condition that must stop a publication run."""


# ------------------------------------------------------------------- io -----

def load_json(path, default=None):
    if not os.path.exists(path):
        if default is not None:
            return default
        raise EditorialError('missing required file: %s' % path)
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def save_json(path, obj):
    """Write JSON deterministically so reruns produce no spurious diffs."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write('\n')


def load_stories():
    return load_json(STORIES_JSON)


def save_stories(stories):
    save_json(STORIES_JSON, stories)


def load_calendar():
    return load_json(CALENDAR_JSON)


def load_authors():
    return load_json(AUTHORS_JSON)


# ------------------------------------------------------------------ time -----

def publication_tz(cal=None):
    """Publication timezone as a fixed offset for the given moment.

    The repo targets the Python standard library only and cannot rely on
    zoneinfo's tz database being present on every runner, so US Eastern is
    computed directly: DST runs from the second Sunday in March to the first
    Sunday in November.
    """
    return (cal or {}).get('timezone', 'America/New_York')


def _second_sunday_march(year):
    d = datetime(year, 3, 8)
    return d + timedelta(days=(6 - d.weekday()) % 7)


def _first_sunday_november(year):
    d = datetime(year, 11, 1)
    return d + timedelta(days=(6 - d.weekday()) % 7)


def eastern_offset(naive_local):
    """Return the UTC offset in effect for a naive US/Eastern datetime."""
    y = naive_local.year
    start = _second_sunday_march(y).replace(hour=2)
    end = _first_sunday_november(y).replace(hour=2)
    return timedelta(hours=-4) if start <= naive_local < end else timedelta(hours=-5)


def now_eastern(now_utc=None):
    """Current wall-clock time in the publication timezone, as naive local."""
    now_utc = now_utc or datetime.now(timezone.utc)
    guess = now_utc.replace(tzinfo=None) + timedelta(hours=-5)
    return now_utc.replace(tzinfo=None) + eastern_offset(guess)


def parse_publish_at(value):
    """Parse a publishAt value into naive publication-local time.

    Accepts 'YYYY-MM-DD' (treated as 00:00 local) and 'YYYY-MM-DDTHH:MM'.
    """
    if not value:
        return None
    v = str(value).strip().replace('Z', '')
    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            continue
    raise EditorialError('unparseable publishAt: %r' % value)


def iso_local(dt):
    return dt.strftime('%Y-%m-%dT%H:%M')


def iso_date(dt):
    return dt.strftime('%Y-%m-%d')


# -------------------------------------------------------------- calendar -----

def week_of(dt):
    """Monday of the week containing dt, as YYYY-MM-DD."""
    return iso_date(dt - timedelta(days=dt.weekday()))


def issue_id_for(dt):
    """ISO-week issue id, e.g. 2026-W33 — matches the existing issue records."""
    iso = dt.isocalendar()
    return '%04d-W%02d' % (iso[0], iso[1])


def is_blackout(dt, cal):
    """True when the calendar forbids publishing on this date."""
    day = iso_date(dt)
    for entry in cal.get('blackouts', []) or []:
        start = entry.get('start')
        end = entry.get('end', start)
        if start and end and start <= day <= end:
            return True
    return False


def publication_paused(cal):
    return bool(cal.get('paused'))


def slot_for(placement, cal):
    """Return the configured cadence slot for a placement, or None."""
    for slot in cal.get('cadence', []) or []:
        if slot.get('placement') == placement:
            return slot
    return None


def next_slot_datetime(placement, cal, after=None):
    """Next configured publication moment for a placement.

    Reads weekday and time from the calendar so cadence changes never require a
    code change. Returns None when the placement has no configured slot.
    """
    slot = slot_for(placement, cal)
    if not slot:
        return None
    weekday = int(slot.get('weekday', 0))
    hh, mm = (slot.get('time', '06:00').split(':') + ['0'])[:2]
    base = (after or now_eastern()).replace(second=0, microsecond=0)
    candidate = base.replace(hour=int(hh), minute=int(mm))
    delta = (weekday - candidate.weekday()) % 7
    candidate = candidate + timedelta(days=delta)
    if candidate <= base:
        candidate += timedelta(days=7)
    while is_blackout(candidate, cal):
        candidate += timedelta(days=7)
    return candidate


# --------------------------------------------------------------- stories -----

def by_slug(stories):
    return {s['slug']: s for s in stories}


def published(stories):
    return [s for s in stories if s.get('status') in PUBLIC_STATUSES]


def current_cover(stories):
    for s in published(stories):
        if s.get('coverStory') or s.get('featured'):
            return s
    return None


def is_due(story, at=None):
    """True when a story is eligible for automatic publication.

    Deliberately strict. Every one of these gates must hold:
      * status is exactly `scheduled`
      * an approval timestamp exists (a human approved it)
      * publishAt exists and has arrived
    Anything else — draft, review, approved-but-unscheduled, held, retired —
    is not publishable by automation under any circumstance.
    """
    if story.get('status') != PUBLISHABLE_FROM:
        return False
    if not story.get('approvedAt'):
        return False
    when = parse_publish_at(story.get('publishAt'))
    if when is None:
        return False
    return when <= (at or now_eastern())


def story_url(slug):
    return '%s/stories/%s.html' % (SITE_ORIGIN, slug)


def body_path(slug):
    return os.path.join(CONTENT, '%s.html' % slug)


def read_body(slug):
    p = body_path(slug)
    if not os.path.exists(p):
        raise EditorialError('missing article prose for %s (expected %s)' % (slug, p))
    with open(p, encoding='utf-8') as fh:
        return fh.read().strip()


def esc(text):
    return (str(text or '')
            .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


def slugify(text):
    s = re.sub(r'[^a-z0-9]+', '-', str(text or '').lower()).strip('-')
    return re.sub(r'-{2,}', '-', s)
