#!/usr/bin/env python3
"""Tests for the editorial operating system.

Every test that mutates state runs against a full sandbox copy of the repo's
data, so production JSON is never touched. The sandbox is deleted afterwards.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from editorial_lib import (  # noqa: E402
    is_due, parse_publish_at, next_slot_datetime, is_blackout, issue_id_for,
)

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print('  %s  - %s%s' % ('ok ' if cond else 'FAIL', name,
                            '' if cond else '  <<< %s' % detail))


# ------------------------------------------------------------------ sandbox --

class Sandbox:
    """A throwaway copy of the repo that the publisher can safely mutate."""

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix='dbf-editorial-test-')
        for item in ('data', 'scripts', 'templates', 'content', 'stories'):
            src = os.path.join(REPO, item)
            if os.path.exists(src):
                shutil.copytree(src, os.path.join(self.dir, item))
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.dir, ignore_errors=True)

    def stories(self):
        with open(os.path.join(self.dir, 'data', 'stories.json'), encoding='utf-8') as fh:
            return json.load(fh)

    def write_stories(self, stories):
        with open(os.path.join(self.dir, 'data', 'stories.json'), 'w', encoding='utf-8') as fh:
            json.dump(stories, fh, indent=2, ensure_ascii=False)

    def calendar(self):
        with open(os.path.join(self.dir, 'data', 'editorial-calendar.json'), encoding='utf-8') as fh:
            return json.load(fh)

    def write_calendar(self, cal):
        with open(os.path.join(self.dir, 'data', 'editorial-calendar.json'), 'w', encoding='utf-8') as fh:
            json.dump(cal, fh, indent=2, ensure_ascii=False)

    def issue_index(self):
        with open(os.path.join(self.dir, 'data', 'issues', 'index.json'), encoding='utf-8') as fh:
            return json.load(fh)

    def add_story(self, slug, **fields):
        stories = self.stories()
        base = {
            'slug': slug, 'kicker': 'Test Kicker', 'headline': 'A Test Story',
            'hook': 'Hook.', 'lede': 'Lede.', 'scene': None, 'heroImage': None,
            'ogImage': None, 'date': None, 'readTime': '5 min read',
            'featured': False, 'coverStory': False, 'category': 'coast',
            'series': None, 'seriesPage': False, 'seriesInstallment': None,
            'status': 'draft', 'photoCredit': 'Delaware Beach Finds',
            'sources': ['Test source'], 'etsyProductIds': [], 'body': [],
            'access_level': 'public', 'heroAlt': '', 'author': 'coast-nature',
            'placement': 'standard', 'publishAt': None, 'publishedAt': None,
            'approvedAt': None, 'issueId': None, 'relatedStories': [],
            'shopTheStory': False, 'metaTag': None, 'seoTitle': None,
            'seoDescription': None, 'canonicalUrl': None,
            'renderMode': 'generated', 'heldReason': None,
        }
        base.update(fields)
        stories.append(base)
        self.write_stories(stories)
        # Every published story needs prose on disk.
        with open(os.path.join(self.dir, 'content', 'stories', '%s.html' % slug),
                  'w', encoding='utf-8') as fh:
            fh.write('<p>Test prose.</p>\n')
        return base

    def publish(self, *args):
        return subprocess.run(
            [sys.executable, os.path.join(self.dir, 'scripts', 'publish_due.py')] + list(args),
            capture_output=True, text=True, cwd=self.dir)


# -------------------------------------------------------------- unit gates --

def test_gates():
    print('\n=== Story lifecycle gates ===')
    base = {'slug': 'x', 'publishAt': '2026-01-01T06:00', 'approvedAt': '2025-12-01'}
    at = parse_publish_at('2026-06-01T06:00')

    for status in ('draft', 'review', 'approved', 'held', 'retired', 'published'):
        s = dict(base, status=status)
        check('%s does not publish' % status, not is_due(s, at))

    check('scheduled + approved + due publishes',
          is_due(dict(base, status='scheduled'), at))
    check('scheduled without approvedAt does not publish',
          not is_due({'slug': 'x', 'status': 'scheduled',
                      'publishAt': '2026-01-01T06:00'}, at))
    check('approved but unscheduled (no publishAt) does not publish',
          not is_due({'slug': 'x', 'status': 'scheduled',
                      'approvedAt': '2025-12-01'}, at))
    check('future scheduled story does not publish early',
          not is_due(dict(base, status='scheduled',
                          publishAt='2026-12-01T06:00'), at))


def test_calendar_config():
    print('\n=== Editorial calendar is configuration, not code ===')
    cal = {'cadence': [{'placement': 'cover', 'weekday': 0, 'time': '06:00'}],
           'blackouts': []}
    after = parse_publish_at('2026-08-13T09:00')   # a Thursday
    nxt = next_slot_datetime('cover', cal, after=after)
    check('cover slot resolves to the configured weekday (Monday)',
          nxt.weekday() == 0, 'got weekday %s' % nxt.weekday())
    check('cover slot resolves to the configured time (06:00)',
          (nxt.hour, nxt.minute) == (6, 0), 'got %s:%s' % (nxt.hour, nxt.minute))

    cal['cadence'][0]['weekday'] = 1   # move cover day to Tuesday, data only
    nxt2 = next_slot_datetime('cover', cal, after=after)
    check('changing weekday in config moves cover day, no code change',
          nxt2.weekday() == 1, 'got weekday %s' % nxt2.weekday())

    cal['blackouts'] = [{'start': '2026-12-21', 'end': '2026-12-27'}]
    check('blackout window is respected',
          is_blackout(parse_publish_at('2026-12-24'), cal))
    check('date outside blackout is not blocked',
          not is_blackout(parse_publish_at('2026-12-28'), cal))


# ------------------------------------------------------- end-to-end scenarios --

def test_scenarios():
    print('\n=== Scheduled publication, end to end ===')
    with Sandbox() as sb:
        before = sb.stories()
        old_cover = next((s['slug'] for s in before if s.get('coverStory')), None)
        check('fixture has a current cover', old_cover is not None)

        sb.add_story('test-future-cover', status='scheduled',
                     approvedAt='2026-08-13', publishAt='2026-09-07T06:00',
                     placement='cover', headline='A Future Cover Story',
                     category='coast')

        # --- Scenario A: not yet due -----------------------------------------
        r = sb.publish('--now', '2026-09-01T06:00')
        s = {x['slug']: x for x in sb.stories()}
        check('A: future scheduled story does NOT publish early',
              s['test-future-cover']['status'] == 'scheduled', r.stdout)
        check('A: incumbent cover untouched',
              s[old_cover].get('coverStory') is True)

        # --- Scenario B: due -------------------------------------------------
        r = sb.publish('--now', '2026-09-07T06:00')
        s = {x['slug']: x for x in sb.stories()}
        new = s['test-future-cover']
        check('B: due approved story publishes',
              new['status'] == 'published', r.stdout[-600:])
        check('B: it becomes the cover', new.get('coverStory') is True)
        check('B: it is assigned to its publication-week issue',
              new.get('issueId') == issue_id_for(parse_publish_at('2026-09-07')),
              'got %s' % new.get('issueId'))
        check('B: previous cover is DEMOTED but still published',
              s[old_cover]['status'] == 'published'
              and not s[old_cover].get('coverStory'),
              'status=%s cover=%s' % (s[old_cover]['status'],
                                      s[old_cover].get('coverStory')))
        check('B: no story lost its published status',
              all(x['status'] == 'published' for x in sb.stories()
                  if x['slug'] in [y['slug'] for y in before]))
        page = os.path.join(sb.dir, 'stories', 'test-future-cover.html')
        check('B: an article page was generated', os.path.exists(page))

        idx = sb.issue_index()
        check('B: issue index rolled to the new issue',
              idx['currentIssueId'] == issue_id_for(parse_publish_at('2026-09-07')),
              'got %s' % idx['currentIssueId'])
        archived = [i for i in idx['issues'] if i['status'] == 'archived']
        check('B: previous issue archived, not deleted',
              len(archived) >= 1 and all(i.get('file') for i in archived))

        # --- idempotence -----------------------------------------------------
        snapshot = json.dumps(sb.stories(), sort_keys=True)
        sb.publish('--now', '2026-09-07T06:00')
        sb.publish('--now', '2026-09-08T06:00')
        check('publication is idempotent across repeated runs',
              json.dumps(sb.stories(), sort_keys=True) == snapshot)

    # --- Scenario C: hold ----------------------------------------------------
    print('\n=== Hold / reschedule ===')
    with Sandbox() as sb:
        sb.add_story('test-held', status='scheduled', approvedAt='2026-08-13',
                     publishAt='2026-09-07T06:00', placement='feature')
        stories = sb.stories()
        for x in stories:
            if x['slug'] == 'test-held':
                x['status'] = 'held'
                x['heldReason'] = 'Awaiting a source callback'
        sb.write_stories(stories)
        sb.publish('--now', '2026-09-07T06:00')
        s = {x['slug']: x for x in sb.stories()}
        check('C: held story does not publish even when due',
              s['test-held']['status'] == 'held')

    # --- Scenario D: cadence change, config only -----------------------------
    print('\n=== Pause and blackout ===')
    with Sandbox() as sb:
        sb.add_story('test-paused', status='scheduled', approvedAt='2026-08-13',
                     publishAt='2026-09-07T06:00', placement='feature')
        cal = sb.calendar()
        cal['paused'] = True
        sb.write_calendar(cal)
        sb.publish('--now', '2026-09-07T06:00')
        check('D: nothing publishes while the calendar is paused',
              {x['slug']: x for x in sb.stories()}['test-paused']['status'] == 'scheduled')

        cal['paused'] = False
        cal['blackouts'] = [{'start': '2026-09-01', 'end': '2026-09-30',
                             'reason': 'test blackout'}]
        sb.write_calendar(cal)
        sb.publish('--now', '2026-09-07T06:00')
        check('D: a blackout defers publication and keeps the story scheduled',
              {x['slug']: x for x in sb.stories()}['test-paused']['status'] == 'scheduled')

        cal['blackouts'] = []
        sb.write_calendar(cal)
        sb.publish('--now', '2026-09-07T06:00')
        check('D: clearing the blackout in config alone lets it publish',
              {x['slug']: x for x in sb.stories()}['test-paused']['status'] == 'published')


def test_authors_and_integrity():
    print('\n=== House desks and integrity ===')
    rc = subprocess.run([sys.executable, os.path.join(HERE, 'validate_editorial.py')],
                        capture_output=True, text=True, cwd=REPO)
    check('production editorial data validates', rc.returncode == 0, rc.stdout)

    with Sandbox() as sb:
        stories = sb.stories()
        stories[0]['author'] = 'not-a-real-desk'
        sb.write_stories(stories)
        rc = subprocess.run([sys.executable, os.path.join(sb.dir, 'scripts', 'validate_editorial.py')],
                            capture_output=True, text=True, cwd=sb.dir)
        check('an unknown author desk fails validation', rc.returncode != 0)

    with Sandbox() as sb:
        authors_path = os.path.join(sb.dir, 'data', 'authors.json')
        a = json.load(open(authors_path))
        a['desks'][0]['type'] = 'person'
        json.dump(a, open(authors_path, 'w'))
        rc = subprocess.run([sys.executable, os.path.join(sb.dir, 'scripts', 'validate_editorial.py')],
                            capture_output=True, text=True, cwd=sb.dir)
        check('a desk posing as a person fails validation', rc.returncode != 0)

    # The byline swapper in site.js once overwrote server-rendered desk names
    # with the literal attribute value, printing "By desk" on every article.
    import re as _re
    desk_names = {d['name'] for d in json.load(
        open(os.path.join(REPO, 'data', 'authors.json')))['desks']}
    bad = []
    for fn in os.listdir(os.path.join(REPO, 'stories')):
        if not fn.endswith('.html'):
            continue
        html = open(os.path.join(REPO, 'stories', fn), encoding='utf-8').read()
        for mode, text in _re.findall(r'<span data-byline="([^"]*)">([^<]*)</span>', html):
            if mode == 'desk' and text.replace('&amp;', '&') not in desk_names:
                bad.append('%s -> %r' % (fn, text))
    check('every desk byline renders a real desk name, not the mode keyword',
          not bad, '; '.join(bad[:3]))
    check('site.js leaves server-rendered desk bylines alone',
          "if(explicit === 'desk') return;" in
          open(os.path.join(REPO, 'assets', 'js', 'site.js'), encoding='utf-8').read())

    rc = subprocess.run([sys.executable, os.path.join(HERE, 'render_story.py'), '--check'],
                        capture_output=True, text=True, cwd=REPO)
    check('every published page matches its editorial source', rc.returncode == 0, rc.stdout)


def main():
    test_gates()
    test_calendar_config()
    test_scenarios()
    test_authors_and_integrity()
    print('\n' + '=' * 32)
    print('Passed: %d   Failed: %d' % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
