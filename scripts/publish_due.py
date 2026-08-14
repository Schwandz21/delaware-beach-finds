#!/usr/bin/env python3
"""The scheduled publisher.

Publishes stories that are ALREADY APPROVED and whose publishAt has arrived.
This script is the only thing permitted to move a story to `published`, and it
will only ever do so from `scheduled` + `approvedAt` + due. It cannot approve
anything, cannot write editorial copy, and cannot invent a date.

  AI/research may prepare.  Editorial approval authorizes.  Automation publishes.

What one run does:
  1. refuse to run at all if the calendar is paused
  2. find due stories (strict gate, see editorial_lib.is_due)
  3. skip any whose publishAt lands in a blackout window, and say so
  4. publish each in publishAt order:
       - status -> published, publishedAt stamped
       - assigned to the issue for its publication week
       - placement applied; a new cover DEMOTES the old cover without
         unpublishing it (publication status != homepage prominence)
  5. create/refresh the issue record for that week and roll the issue index
  6. re-render article pages
  7. rebuild the content index (archive + search)

Idempotent. A second run finds nothing due and changes nothing.

Usage:
  python3 scripts/publish_due.py --dry-run          # report only
  python3 scripts/publish_due.py                    # publish what is due
  python3 scripts/publish_due.py --now 2026-09-07T06:00   # evaluate at a time
  python3 scripts/publish_due.py --slug some-story --force-now   # publish now
"""

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import timedelta  # noqa: E402

from editorial_lib import (  # noqa: E402
    DATA, REPO, EditorialError, ISSUE_INDEX,
    load_calendar, load_json, load_stories, save_json, save_stories,
    is_due, issue_id_for, iso_date, iso_local, now_eastern, parse_publish_at,
    publication_paused, is_blackout, week_of,
)
import render_story  # noqa: E402


def log(msg):
    print(msg, flush=True)


def emit_output(slugs):
    """Publish a machine-readable result for CI.

    Without this the workflow cannot tell an idle hour from a real publication,
    and would commit `content-index.json`'s regenerated timestamp every run.
    """
    path = os.environ.get('GITHUB_OUTPUT')
    if not path:
        return
    with open(path, 'a', encoding='utf-8') as fh:
        fh.write('count=%d\n' % len(slugs))
        fh.write('published=%s\n' % ','.join(slugs))


# ------------------------------------------------------------------ issues ---

def issue_path(issue_id):
    return os.path.join(DATA, 'issues', '%s.json' % issue_id)


def ensure_issue(issue_id, when, story, dry_run=False):
    """Create or refresh the issue record for a publication week.

    Only ever called because a real story is publishing into that week, so this
    never fabricates an issue that did not happen.
    """
    path = issue_path(issue_id)
    monday = week_of(when)
    existing = load_json(path, None) if os.path.exists(path) else None
    if existing is None:
        existing = {
            'issueId': issue_id,
            'weekOf': monday,
            'weekEnding': iso_date(parse_publish_at(monday) + timedelta(days=6)),
            'title': 'Week of %s' % monday,
            'publishedAt': iso_date(when),
            'status': 'current',
            'coverStory': None,
            'eventIds': [],
            'sources': [],
            'access_level': 'public',
            'editorialNotes': 'Issue opened automatically when its first '
                              'approved story published.',
        }
        log('    + created issue record %s' % issue_id)
    if story.get('placement') == 'cover':
        existing['coverStory'] = story['slug']
    existing['status'] = 'current'
    existing.setdefault('access_level', 'public')
    # An issue's provenance is the provenance of the stories in it. These are
    # carried across from the story record — never invented, never a placeholder.
    srcs = list(existing.get('sources') or [])
    for src in story.get('sources') or []:
        if src not in srcs:
            srcs.append(src)
    existing['sources'] = srcs
    if not dry_run:
        save_json(path, existing)
    return existing


def roll_issue_index(new_issue_id, when, dry_run=False):
    """Make new_issue_id current and archive whatever was current before.

    Archiving is a status change only. Past issues keep their file, their URL
    and every story in them.
    """
    idx = load_json(ISSUE_INDEX)
    prev = idx.get('currentIssueId')
    if prev == new_issue_id:
        # Already current — make sure the entry exists and stop.
        pass
    known = {i['issueId'] for i in idx.get('issues', [])}
    if new_issue_id not in known:
        idx.setdefault('issues', []).append({
            'issueId': new_issue_id,
            'weekOf': week_of(when),
            'title': 'Week of %s' % week_of(when),
            'publishedAt': iso_date(when),
            'status': 'current',
            # Paths in the index resolve from data/, so the `issues/` prefix
            # is required — existing entries all carry it.
            'file': 'issues/%s.json' % new_issue_id,
            'access_level': 'public',
        })
    for entry in idx.get('issues', []):
        if entry['issueId'] == new_issue_id:
            entry['status'] = 'current'
        elif entry.get('status') == 'current':
            entry['status'] = 'archived'
            log('    · issue %s archived (stays published and reachable)'
                % entry['issueId'])
            p = issue_path(entry['issueId'])
            if os.path.exists(p) and not dry_run:
                rec = load_json(p)
                rec['status'] = 'archived'
                save_json(p, rec)
    idx['currentIssueId'] = new_issue_id
    idx['issues'].sort(key=lambda e: e.get('weekOf') or '', reverse=True)
    if not dry_run:
        save_json(ISSUE_INDEX, idx)
    return idx


# --------------------------------------------------------------- placement ---

def apply_placement(story, stories, dry_run=False):
    """Put the story in its homepage slot, demoting the incumbent if needed."""
    placement = story.get('placement') or 'standard'
    if placement != 'cover':
        story['coverStory'] = False
        story['featured'] = False
        return

    for other in stories:
        if other is story:
            continue
        if other.get('coverStory') or other.get('featured'):
            # Demotion is a prominence change, never a publication change.
            other['coverStory'] = False
            other['featured'] = False
            if other.get('placement') == 'cover':
                other['placement'] = 'feature'
            log('    · %s demoted from cover — still published (%s)'
                % (other['slug'], other.get('status')))
    story['coverStory'] = True
    story['featured'] = True


# ----------------------------------------------------------------- publish ---

def publish_story(story, stories, at, cal, dry_run=False):
    when = parse_publish_at(story.get('publishAt')) or at
    issue_id = issue_id_for(when)

    log('  publishing %s' % story['slug'])
    log('    placement=%s  publishAt=%s  issue=%s'
        % (story.get('placement'), story.get('publishAt'), issue_id))

    story['status'] = 'published'
    story['publishedAt'] = iso_date(when)
    story['date'] = story['publishedAt']
    story['issueId'] = issue_id
    apply_placement(story, stories, dry_run=dry_run)

    ensure_issue(issue_id, when, story, dry_run=dry_run)
    roll_issue_index(issue_id, when, dry_run=dry_run)
    return issue_id


def run(at=None, dry_run=False, only_slug=None, force_now=False):
    cal = load_calendar()
    at = at or now_eastern()
    log('Publication check at %s (%s)' % (iso_local(at), cal.get('timezone')))

    if publication_paused(cal):
        log('  publication is PAUSED in data/editorial-calendar.json — nothing published.')
        emit_output([])
        return 0

    stories = load_stories()

    if only_slug:
        target = next((s for s in stories if s['slug'] == only_slug), None)
        if not target:
            raise EditorialError('no story with slug %r' % only_slug)
        if not target.get('approvedAt'):
            raise EditorialError(
                '%s has no approvedAt — automation may not publish unapproved work.'
                % only_slug)
        if target.get('status') == 'published':
            log('  %s is already published — nothing to do.' % only_slug)
            emit_output([])
            return 0
        if force_now:
            target['status'] = 'scheduled'
            target['publishAt'] = iso_local(at)
        due = [target] if is_due(target, at) else []
    else:
        due = [s for s in stories if is_due(s, at)]

    if not due:
        log('  nothing due. %d scheduled, %d approved-not-scheduled, %d held.'
            % (sum(1 for s in stories if s.get('status') == 'scheduled'),
               sum(1 for s in stories if s.get('status') == 'approved'),
               sum(1 for s in stories if s.get('status') == 'held')))
        emit_output([])
        return 0

    due.sort(key=lambda s: parse_publish_at(s['publishAt']))

    published = []
    for s in due:
        when = parse_publish_at(s['publishAt'])
        if is_blackout(when, cal):
            log('  SKIP %s — publishAt %s falls in a calendar blackout. '
                'It stays scheduled and will publish when rescheduled.'
                % (s['slug'], s['publishAt']))
            continue
        publish_story(s, stories, at, cal, dry_run=dry_run)
        published.append(s['slug'])

    if not published:
        log('  nothing published (all due items were in blackout windows).')
        emit_output([])
        return 0

    if dry_run:
        log('\nDRY RUN — no files written. Would publish: %s' % ', '.join(published))
        emit_output([])
        return 0

    save_stories(stories)
    log('\n  registry updated (%d published)' % len(published))

    render_story.render_all(quiet=True)
    log('  article pages rendered')

    subprocess.run([sys.executable, os.path.join(REPO, 'scripts', 'build_content_index.py')],
                   check=True, capture_output=True)
    log('  content index rebuilt (archive + search)')

    emit_output(published)
    log('\nPublished: %s' % ', '.join(published))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--now', help='evaluate as if it were this publication-local time')
    ap.add_argument('--slug', help='restrict to one story')
    ap.add_argument('--force-now', action='store_true',
                    help='with --slug: publish an approved story immediately')
    a = ap.parse_args()
    try:
        at = parse_publish_at(a.now) if a.now else None
        return run(at=at, dry_run=a.dry_run, only_slug=a.slug, force_now=a.force_now)
    except EditorialError as exc:
        print('ERROR: %s' % exc)
        return 2


if __name__ == '__main__':
    sys.exit(main())
