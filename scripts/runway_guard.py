#!/usr/bin/env python3
"""72-hour failsafe for the editorial autopilot.

Run every six hours by .github/workflows/editorial-runway-guard.yml. Reports
(and exits 1) when any of these hold:

  * no future scheduled story, next one >72h away, <5 scheduled, <10 days of
    runway, a planned gap >72h, or the last story is already >72h old
    (scripts/editorial_autopilot.py)
  * the current issue has no valid current lead, so the homepage is showing
    its "This Week" fallback instead of a story
  * editorial validation fails
  * daily slots are stale or have nothing for today or later
  * currentIssueId is stale (its week ended and no newer issue opened)

It never edits anything. It is deliberately NOT part of scripts/run_tests.sh:
the hourly publisher runs the test suite before committing, and a thin runway
must raise an alarm, not stop the stories that are due from publishing.

  python3 scripts/runway_guard.py          # human report, exit 1 if unhealthy
  python3 scripts/runway_guard.py --json   # machine-readable
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from editorial_lib import (  # noqa: E402
    DATA, EditorialError, REPO, iso_local, load_json, load_stories, now_eastern, parse_publish_at,
)
from editorial_autopilot import load_policy, published_moment, runway  # noqa: E402


def current_lead(stories, registry, now, policy):
    """Mirror of selectFrontPage in assets/js/site.js: what leads the homepage."""
    cur_id = (registry or {}).get('currentIssueId')
    issue = next((i for i in (registry or {}).get('issues', [])
                  if i.get('issueId') == cur_id and i.get('status') == 'current'), None)
    pub = [s for s in stories if s.get('status') == 'published' and published_moment(s)]
    pub.sort(key=published_moment, reverse=True)
    if not issue:
        return {'mode': 'none', 'issue': None, 'cover': pub[0]['slug'] if pub else None}
    newest = published_moment(pub[0]) if pub else None
    if newest is None or now - newest > timedelta(hours=policy['homepageStaleAfterHours']):
        return {'mode': 'issue', 'reason': 'stale', 'issue': cur_id, 'cover': None}
    current = [s for s in pub if s.get('issueId') == cur_id]
    cover = next((s for s in current if s.get('coverStory')), None) or \
        next((s for s in current if s.get('featured')), None) or (current[0] if current else None)
    if not cover:
        return {'mode': 'issue', 'reason': 'no-current-story', 'issue': cur_id, 'cover': None}
    return {'mode': 'story', 'issue': cur_id, 'cover': cover['slug']}


def guard(stories, registry, daily, now, policy, editorial_ok=True):
    """Pure check over loaded data. Returns {'healthy', 'problems', ...}."""
    problems = []
    r = runway(stories, now, policy)
    problems += [v['message'] for v in r['violations'] if v['severity'] == 'fail']

    lead = current_lead(stories, registry, now, policy)
    if lead['mode'] != 'story':
        problems.append('Homepage has no valid current lead (%s): it is showing the "This Week" fallback.'
                        % lead.get('reason', 'no current issue'))

    if not editorial_ok:
        problems.append('Editorial validation failed (scripts/validate_editorial.py).')

    today = now.strftime('%Y-%m-%d')
    slots = [s for s in (daily or {}).get('slots', []) if isinstance(s, dict) and s.get('date')]
    try:
        verified = parse_publish_at((daily or {}).get('verifiedAt'))
    except (EditorialError, TypeError):
        verified = None
    if verified is None or (now - verified).days > policy['dailySlotsMaxAgeDays']:
        problems.append('Daily slots are stale (verifiedAt %s).' % (daily or {}).get('verifiedAt'))
    elif not any(s['date'] >= today for s in slots):
        problems.append('Daily slots have nothing for today or later.')

    cur = next((i for i in (registry or {}).get('issues', [])
                if i.get('issueId') == (registry or {}).get('currentIssueId')), None)
    if not cur or not cur.get('weekOf'):
        problems.append('currentIssueId does not resolve to an issue.')
    else:
        # The week's first story opens the next issue; allow until Monday noon.
        week_over = parse_publish_at(cur['weekOf']) + timedelta(days=7, hours=12)
        if now > week_over:
            problems.append('currentIssueId %s is stale: its week ended and no newer issue opened.'
                            % cur['issueId'])

    return {'evaluatedAt': iso_local(now), 'healthy': not problems, 'problems': problems,
            'lead': lead, 'runway': r}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--now')
    a = ap.parse_args()
    now = parse_publish_at(a.now) if a.now else now_eastern().replace(second=0, microsecond=0)
    ed = subprocess.run([sys.executable, os.path.join(REPO, 'scripts', 'validate_editorial.py')],
                        capture_output=True, text=True)
    result = guard(load_stories(), load_json(os.path.join(DATA, 'issues', 'index.json'), {}),
                   load_json(os.path.join(DATA, 'daily-slots.json'), {}), now, load_policy(),
                   editorial_ok=ed.returncode == 0)
    if a.json:
        print(json.dumps(result, indent=2))
    else:
        r = result['runway']
        print('DBF editorial runway guard — %s' % result['evaluatedAt'])
        print('  lead:       %s' % json.dumps(result['lead']))
        print('  scheduled:  %d, runway end %s (%.1f days), largest gap %sh'
              % (r['scheduledCount'], r['runwayEnd'], r['runwayDays'], r['maxGapHours']))
        print('  status:     %s' % ('HEALTHY' if result['healthy'] else 'ATTENTION REQUIRED'))
        for p in result['problems']:
            print('   - %s' % p)
    return 0 if result['healthy'] else 1


if __name__ == '__main__':
    sys.exit(main())
