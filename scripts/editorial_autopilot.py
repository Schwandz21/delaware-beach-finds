#!/usr/bin/env python3
"""Editorial autopilot: the story runway engine.

Delaware Beach Finds publishes a new story about every 48 hours and never
plans a gap longer than 72. Weekly issues organise stories; they are not the
cadence. This script measures the runway of approved, scheduled stories
against data/editorial-autopilot.json and keeps it in shape. It never writes
prose and never publishes: researched stories arrive through
scripts/ingest_story_package.py, and scripts/publish_due.py (the hourly
publisher) remains the only thing that moves a story to `published`.

  python3 scripts/editorial_autopilot.py --status     # human report
  python3 scripts/editorial_autopilot.py --status --json
  python3 scripts/editorial_autopilot.py --check      # exit 1 on any SLA breach
  python3 scripts/editorial_autopilot.py --prepare    # JSON: how many stories, which slots
  python3 scripts/editorial_autopilot.py --schedule   # slot approved-but-unscheduled stories

--now YYYY-MM-DDTHH:MM evaluates at a given publication-local time.
Every mode is idempotent.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from editorial_lib import (  # noqa: E402
    DATA, EditorialError, iso_local, issue_id_for, load_json, load_stories,
    now_eastern, parse_publish_at, save_stories,
)

POLICY_JSON = os.path.join(DATA, 'editorial-autopilot.json')


def load_policy():
    return load_json(POLICY_JSON)


def hours(delta):
    return round(delta.total_seconds() / 3600.0, 1)


# ------------------------------------------------------------------ timing --

def published_moment(story):
    """When a published story went live, in publication-local time.

    publishAt carries the time when the publisher stamped it; older records
    only carry a date, which counts as the start of that day.
    """
    pub_date = story.get('publishedAt') or story.get('date')
    at = story.get('publishAt')
    try:
        when = parse_publish_at(at) if at else None
    except EditorialError:
        when = None
    if when and (not pub_date or when.strftime('%Y-%m-%d') == pub_date):
        return when
    return parse_publish_at(pub_date) if pub_date else None


def is_live_schedule(story):
    return (story.get('status') == 'scheduled' and bool(story.get('approvedAt'))
            and bool(story.get('publishAt')))


def runway(stories, now, policy):
    """Measure the runway. Pure: no I/O, so tests can drive it directly."""
    target = policy['targetGapHours']
    maximum = policy['maximumGapHours']
    min_count = policy['minimumScheduledStories']
    min_days = policy['minimumRunwayDays']

    published = sorted((published_moment(s), s['slug']) for s in stories
                       if s.get('status') == 'published' and published_moment(s))
    last_pub = published[-1] if published else None

    scheduled, overdue, invalid = [], [], []
    for s in stories:
        if s.get('status') != 'scheduled':
            continue
        if not is_live_schedule(s):
            invalid.append(s['slug'])
            continue
        when = parse_publish_at(s['publishAt'])
        (scheduled if when > now else overdue).append((when, s))
    scheduled.sort(key=lambda x: x[0])

    timeline = ([(last_pub[0], last_pub[1], 'published')] if last_pub else []) + \
               [(w, s['slug'], 'scheduled') for w, s in scheduled]
    gaps = []
    for (a, sa, _), (b, sb, _) in zip(timeline, timeline[1:]):
        gaps.append({'from': sa, 'to': sb, 'fromAt': iso_local(a), 'toAt': iso_local(b),
                     'hours': hours(b - a)})
    max_gap = max((g['hours'] for g in gaps), default=None)

    runway_end = scheduled[-1][0] if scheduled else None
    runway_days = round((runway_end - now).total_seconds() / 86400.0, 2) if runway_end else 0.0
    since_last = hours(now - last_pub[0]) if last_pub else None
    until_next = hours(scheduled[0][0] - now) if scheduled else None

    violations = []

    def fail(code, msg):
        violations.append({'code': code, 'severity': 'fail', 'message': msg})

    if not scheduled:
        fail('NO_FUTURE_SCHEDULED', 'No approved story is scheduled to publish.')
    if until_next is not None and until_next > maximum:
        fail('NEXT_TOO_FAR', 'Next scheduled story is %.1fh away (maximum %dh).' % (until_next, maximum))
    if since_last is not None and since_last > maximum:
        fail('LAST_PUBLISHED_TOO_OLD', 'Last story published %.1fh ago (maximum %dh).' % (since_last, maximum))
    for g in gaps:
        if g['hours'] > maximum:
            fail('GAP_EXCEEDS_MAX', 'Planned gap of %.1fh between %s and %s (maximum %dh).'
                 % (g['hours'], g['from'], g['to'], maximum))
    if len(scheduled) < min_count:
        fail('TOO_FEW_SCHEDULED', '%d future stories scheduled (minimum %d).' % (len(scheduled), min_count))
    if runway_days < min_days:
        fail('RUNWAY_TOO_SHORT', 'Runway covers %.1f days (minimum %d).' % (runway_days, min_days))
    for slug in invalid:
        fail('INVALID_SCHEDULE', '%s is scheduled without approvedAt or publishAt.' % slug)
    for when, s in overdue:
        if now - when > timedelta(hours=2):
            violations.append({'code': 'OVERDUE', 'severity': 'warn',
                               'message': '%s was due %s and has not published.' % (s['slug'], iso_local(when))})
    for g in gaps:
        if target < g['hours'] <= maximum:
            violations.append({'code': 'ABOVE_TARGET', 'severity': 'info',
                               'message': 'Gap of %.1fh before %s is above the %dh target.' % (g['hours'], g['to'], target)})

    return {
        'evaluatedAt': iso_local(now),
        'policy': {k: policy[k] for k in ('targetGapHours', 'maximumGapHours',
                                          'minimumScheduledStories', 'minimumRunwayDays')},
        'lastPublished': {'slug': last_pub[1], 'at': iso_local(last_pub[0])} if last_pub else None,
        'hoursSinceLastPublished': since_last,
        'nextScheduled': {'slug': scheduled[0][1]['slug'], 'at': iso_local(scheduled[0][0])} if scheduled else None,
        'hoursUntilNext': until_next,
        'scheduledCount': len(scheduled),
        'scheduled': [{'slug': s['slug'], 'at': iso_local(w), 'headline': s.get('headline'),
                       'placement': s.get('placement'), 'issueId': issue_id_for(w)} for w, s in scheduled],
        'gaps': gaps,
        'maxGapHours': max_gap,
        'runwayEnd': iso_local(runway_end) if runway_end else None,
        'runwayDays': runway_days,
        'held': [{'slug': s['slug'], 'heldReason': s.get('heldReason')} for s in stories if s.get('status') == 'held'],
        'violations': violations,
        'healthy': not any(v['severity'] == 'fail' for v in violations),
    }


def at_publish_time(day, policy):
    hh, mm = (policy.get('defaultPublishTime', '06:00').split(':') + ['0'])[:2]
    return day.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)


def suggest_slots(stories, now, policy, extra=0):
    """Publication slots needed to restore the runway, plus `extra` more.

    Each slot is targetGapHours after the previous anchor (the last scheduled
    story, else the last publication), moved to the day's default publish
    time, and never later than maximumGapHours after its anchor.
    """
    r = runway(stories, now, policy)
    anchor_s = r['runwayEnd'] or (r['lastPublished'] or {}).get('at')
    anchor = parse_publish_at(anchor_s) if anchor_s else now
    anchor = max(anchor, now)
    count = r['scheduledCount']
    end = parse_publish_at(r['runwayEnd']) if r['runwayEnd'] else None
    horizon = now + timedelta(days=policy['minimumRunwayDays'])
    slots = []
    while count < policy['minimumScheduledStories'] or end is None or end < horizon or extra > 0:
        if count >= policy['minimumScheduledStories'] and end is not None and end >= horizon:
            extra -= 1
        slot = at_publish_time(anchor + timedelta(hours=policy['targetGapHours']), policy)
        if slot - anchor > timedelta(hours=policy['maximumGapHours']) or slot <= now + timedelta(hours=1):
            slot = anchor + timedelta(hours=policy['targetGapHours'])
        # A week's first story opens that week's issue, so when the next slot
        # would cross into a new week, open it on Monday morning instead.
        monday = at_publish_time(anchor + timedelta(days=(7 - anchor.weekday()) % 7 or 7), policy)
        if anchor < monday < slot and monday - anchor >= timedelta(hours=policy['minimumGapHours']):
            slot = monday
        slots.append(iso_local(slot))
        anchor, end, count = slot, slot, count + 1
        if len(slots) > 60:
            raise EditorialError('slot planning did not converge')
    return {'runway': r, 'storiesNeeded': len(slots), 'slots': slots}


# --------------------------------------------------------------- scheduling --

def assign_week_covers(stories):
    """Give every issue week its cover.

    The publisher makes a week's first published story create that week's
    issue. If that story is not placement=cover, the new issue has no cover
    and last week's cover keeps its flags. So the earliest scheduled story in
    each week without a published or scheduled cover becomes the cover.
    Returns the slugs changed.
    """
    weeks = {}
    for s in stories:
        if s.get('status') == 'published' and s.get('placement') == 'cover' and s.get('issueId'):
            weeks.setdefault(s['issueId'], {'cover': True, 'first': None})['cover'] = True
    sched = sorted((parse_publish_at(s['publishAt']), s) for s in stories if is_live_schedule(s))
    for when, s in sched:
        wk = weeks.setdefault(issue_id_for(when), {'cover': False, 'first': None})
        if s.get('placement') == 'cover':
            wk['cover'] = True
        if wk['first'] is None:
            wk['first'] = s
    changed = []
    for wk in weeks.values():
        if not wk['cover'] and wk['first'] is not None:
            wk['first']['placement'] = 'cover'
            changed.append(wk['first']['slug'])
    return changed


def schedule_approved(stories, now, policy):
    """Slot approved stories that have no future publishAt; return slugs."""
    waiting = [s for s in stories if s.get('status') == 'approved' and s.get('approvedAt')
               and not (s.get('publishAt') and parse_publish_at(s['publishAt']) > now)]
    if not waiting:
        return []
    slots = suggest_slots(stories, now, policy, extra=len(waiting))['slots']
    done = []
    for s, slot in zip(waiting, slots):
        s['publishAt'] = slot
        s['status'] = 'scheduled'
        done.append(s['slug'])
    return done


# ---------------------------------------------------------------------- CLI --

def print_report(r):
    print('Delaware Beach Finds — editorial runway (%s)' % r['evaluatedAt'])
    print('=' * 60)
    lp = r['lastPublished']
    print('Last published:     %s' % ('%s at %s (%.1fh ago)' % (lp['slug'], lp['at'], r['hoursSinceLastPublished']) if lp else 'none'))
    nx = r['nextScheduled']
    print('Next scheduled:     %s' % ('%s at %s (in %.1fh)' % (nx['slug'], nx['at'], r['hoursUntilNext']) if nx else 'none'))
    print('Scheduled stories:  %d (minimum %d)' % (r['scheduledCount'], r['policy']['minimumScheduledStories']))
    print('Runway end:         %s (%.1f days; minimum %d)' % (r['runwayEnd'], r['runwayDays'], r['policy']['minimumRunwayDays']))
    print('Largest gap:        %sh (target %dh, maximum %dh)' % (r['maxGapHours'], r['policy']['targetGapHours'], r['policy']['maximumGapHours']))
    if r['scheduled']:
        print('\nSchedule:')
        for s in r['scheduled']:
            print('  %s  %-8s %-9s %s' % (s['at'], s['issueId'], s['placement'] or '', s['headline']))
    if r['held']:
        print('\nHeld (will not publish):')
        for h in r['held']:
            print('  %s — %s' % (h['slug'], h['heldReason']))
    print('\nStatus:             %s' % ('HEALTHY' if r['healthy'] else 'ATTENTION REQUIRED'))
    for v in r['violations']:
        print('  [%s] %s' % (v['severity'], v['message']))


def main(argv=None):
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument('--status', action='store_true')
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--schedule', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--now', help='publication-local time to evaluate at')
    a = ap.parse_args(argv)

    policy = load_policy()
    now = parse_publish_at(a.now) if a.now else now_eastern().replace(second=0, microsecond=0)
    stories = load_stories()

    if a.prepare:
        print(json.dumps(suggest_slots(stories, now, policy), indent=2))
        return 0

    if a.schedule:
        slotted = schedule_approved(stories, now, policy)
        covers = assign_week_covers(stories)
        if slotted or covers:
            save_stories(stories)
        print(json.dumps({'scheduled': slotted, 'coverPlacementsAssigned': covers}, indent=2))
        return 0

    r = runway(stories, now, policy)
    if a.json:
        print(json.dumps(r, indent=2))
    else:
        print_report(r)
    if a.check and not r['healthy']:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
