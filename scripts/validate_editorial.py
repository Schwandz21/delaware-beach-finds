#!/usr/bin/env python3
"""Validate the editorial operating system's data before anything publishes.

Run this after editing the registry, the calendar or the desks. The scheduled
publisher runs it too and refuses to publish if it fails.
"""

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from editorial_lib import (  # noqa: E402
    ALL_STATUSES, PLACEMENTS, CONTENT, STORIES_DIR,
    load_authors, load_calendar, load_stories, parse_publish_at, body_path,
    EditorialError,
)

ETSY_SHOP = 'https://www.etsy.com/shop/DelawareBeachFinds'
BANNED_COMMERCE = ['bluehenbasement', 'blue-hen-basement', 'Blue Hen Basement']


def main():
    errors, warnings = [], []

    authors = load_authors()
    desk_ids = {d['id'] for d in authors['desks']}
    for d in authors['desks']:
        if d.get('type') != 'house_desk':
            errors.append('author %s must be type house_desk (got %r) — DBF does '
                          'not publish under invented individual identities'
                          % (d['id'], d.get('type')))
    if authors.get('default') not in desk_ids:
        errors.append('authors.default %r is not a known desk' % authors.get('default'))

    cal = load_calendar()
    for slot in cal.get('cadence', []):
        if slot.get('placement') not in PLACEMENTS:
            errors.append('cadence slot has unknown placement %r' % slot.get('placement'))
        if not 0 <= int(slot.get('weekday', -1)) <= 6:
            errors.append('cadence slot %r has weekday outside 0-6' % slot.get('placement'))
    for b in cal.get('blackouts', []):
        if not b.get('start'):
            errors.append('blackout entry missing start date')

    stories = load_stories()
    seen = set()
    covers = []
    for s in stories:
        slug = s.get('slug')
        if not slug:
            errors.append('a story record has no slug')
            continue
        if slug in seen:
            errors.append('duplicate slug: %s' % slug)
        seen.add(slug)

        if s.get('status') not in ALL_STATUSES:
            errors.append('%s: unknown status %r' % (slug, s.get('status')))
        if s.get('placement') and s['placement'] not in PLACEMENTS:
            errors.append('%s: unknown placement %r' % (slug, s['placement']))
        if s.get('author') and s['author'] not in desk_ids:
            errors.append('%s: unknown author desk %r' % (slug, s['author']))

        for field in ('publishAt', 'publishedAt', 'approvedAt'):
            if s.get(field):
                try:
                    parse_publish_at(s[field])
                except EditorialError as exc:
                    errors.append('%s: %s' % (slug, exc))

        if s.get('status') == 'scheduled':
            if not s.get('approvedAt'):
                errors.append('%s is scheduled but has no approvedAt — it can '
                              'never publish, and should not be scheduled' % slug)
            if not s.get('publishAt'):
                errors.append('%s is scheduled but has no publishAt' % slug)

        if s.get('status') == 'published':
            if not s.get('publishedAt'):
                errors.append('%s is published with no publishedAt' % slug)
            page = os.path.join(STORIES_DIR, '%s.html' % slug)
            if not os.path.exists(page):
                errors.append('%s is published but has no page at %s' % (slug, page))
            if not os.path.exists(body_path(slug)):
                errors.append('%s is published but has no prose in %s'
                              % (slug, CONTENT))
            if s.get('coverStory') or s.get('featured'):
                covers.append(slug)

        if s.get('status') == 'held' and not s.get('heldReason'):
            warnings.append('%s is held with no heldReason' % slug)

        for pid in s.get('etsyProductIds') or []:
            if not str(pid).strip():
                errors.append('%s has an empty etsyProductIds entry' % slug)

    if len(covers) > 1:
        errors.append('more than one story is marked cover: %s' % ', '.join(covers))
    if not covers:
        warnings.append('no published story is marked as the cover')

    # Commerce guardrails.
    for root, _dirs, files in os.walk(os.path.dirname(STORIES_DIR)):
        if any(p in root for p in ('.git', 'dbf-rebuild-tmp', 'backups', 'node_modules')):
            continue
        for f in files:
            if not f.endswith(('.html', '.json')):
                continue
            p = os.path.join(root, f)
            try:
                text = open(p, encoding='utf-8').read()
            except (OSError, UnicodeDecodeError):
                continue
            low = text.lower()
            for banned in BANNED_COMMERCE:
                if banned.lower() in low:
                    errors.append('%s references a retired storefront (%s)'
                                  % (os.path.relpath(p), banned))
                    break

    # Audience metrics. A number we publish must say when it was checked and
    # where it came from; an empty metric must not claim verification.
    amp = os.path.join(os.path.dirname(STORIES_DIR), 'data', 'audience-metrics.json')
    metric_count = 0
    if os.path.exists(amp):
        am = json.load(open(amp, encoding='utf-8'))
        today = datetime.date.today().isoformat()
        seen = set()
        for m in am.get('metrics', []):
            k = m.get('key') or '(unnamed)'
            if not m.get('key'):
                errors.append('audience metric with no key')
            if k in seen:
                errors.append('duplicate audience metric key: %s' % k)
            seen.add(k)
            if not m.get('label'):
                errors.append('audience metric %s has no label' % k)
            has_value = m.get('value') not in (None, '', [])
            if has_value:
                metric_count += 1
                if not m.get('verifiedAt'):
                    errors.append('audience metric %s has a value but no verifiedAt '
                                  '(an unverified public claim)' % k)
                if not m.get('source'):
                    errors.append('audience metric %s has a value but no source' % k)
                if m.get('verifiedAt') and m['verifiedAt'] > today:
                    errors.append('audience metric %s is verified in the future (%s)'
                                  % (k, m['verifiedAt']))
            elif m.get('verifiedAt'):
                errors.append('audience metric %s is empty but carries verifiedAt' % k)

    for w in warnings:
        print('  warn - %s' % w)
    for e in errors:
        print('  FAIL - %s' % e)
    if errors:
        print('\n%d error(s). Nothing should publish until these are fixed.' % len(errors))
        return 1
    print('  ok  - editorial data valid (%d stories, %d desks, %d cadence slots, '
          '%d verified metric(s))'
          % (len(stories), len(desk_ids), len(cal.get('cadence', [])), metric_count))
    return 0


if __name__ == '__main__':
    sys.exit(main())
