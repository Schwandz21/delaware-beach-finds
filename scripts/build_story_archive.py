#!/usr/bin/env python3
"""Build data/story-archive.json — the immutable ledger of the DBF back catalog.

Every published story that is not part of the current issue is archived here:
its original publication date, its issue (null when it never had one — the Aug.
19 stories predate the issue system and must not be given an invented issue),
where its prose and rendered page live, and the SHA-256 of its canonical prose.

The ledger holds METADATA ONLY. It never copies article prose.

Rules the builder enforces (and scripts/test_story_archive.py re-checks):
  * Append-only. An entry never leaves the ledger, not when a story ages, not
    when it is retired, not when its record disappears from data/stories.json.
  * The original publication date and issue of an entry are frozen.
  * A change to archived prose is refused unless it is recorded as a revision:
        python3 scripts/build_story_archive.py --revise SLUG --reason "why"
  * An archived story whose canonical prose file is missing is an error.
  * Deterministic and idempotent: rebuilding unchanged inputs changes nothing.

Usage:
  python3 scripts/build_story_archive.py            # update the ledger
  python3 scripts/build_story_archive.py --check    # exit 1 if stale or broken
  python3 scripts/build_story_archive.py --revise SLUG --reason TEXT
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LEDGER = 'data/story-archive.json'
SCHEMA_VERSION = 1
NOTE = ('Immutable archival ledger of the Delaware Beach Finds back catalog: every '
        'published story older than the current issue. Metadata only; prose lives in '
        'sourceProsePath and is pinned by sourceProseSHA256. Entries are never removed; '
        'publishedAt, date and issueId are frozen; a prose change must be recorded in '
        'revisions. issueId is null where the story was published before the issue '
        'system existed; it is never back-filled. Built by scripts/build_story_archive.py.')
FROZEN = ('publishedAt', 'date', 'issueId', 'publicationWeek', 'archivedAt')


class ArchiveError(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def word_count(html):
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'&[a-z#0-9]+;', ' ', text)
    return len(text.split())


def iso_week(date):
    y, w, _ = datetime.date.fromisoformat(date[:10]).isocalendar()
    return '%d-W%02d' % (y, w)


def load_json(repo, rel, default=None):
    path = os.path.join(repo, rel)
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def today_ny():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo('America/New_York')).date().isoformat()
    except Exception:
        return datetime.date.today().isoformat()


def is_archivable(story, current_issue):
    return story.get('status') == 'published' and story.get('issueId') != current_issue


def image_provenance(story, attributions):
    hero = story.get('heroImage')
    loc = attributions.get(hero) if hero else None
    prov = {
        'heroImage': hero,
        'scene': story.get('scene'),
        'heroAlt': story.get('heroAlt'),
        'heroImageAlt': story.get('heroImageAlt'),
        'photoCredit': story.get('photoCredit'),
        'heroProvenance': story.get('heroProvenance'),
        'locationAttribution': ({'place': loc.get('place'), 'evidence': loc.get('evidence'),
                                 'mustNotClaim': loc.get('mustNotClaim', [])} if loc else None),
    }
    return prov


def describe(story, repo, issues, attributions):
    """The ledger entry a story would get if it were archived today."""
    slug = story['slug']
    prose_rel = 'content/stories/%s.html' % slug
    prose = os.path.join(repo, prose_rel)
    if not os.path.exists(prose):
        raise ArchiveError('%s: canonical prose file %s is missing' % (slug, prose_rel))
    with open(prose, encoding='utf-8') as f:
        html = f.read()
    date = story.get('date') or story.get('publishedAt')
    published = story.get('publishedAt') or date
    if not date:
        raise ArchiveError('%s: published story has no date' % slug)
    issue = issues.get(story.get('issueId')) if story.get('issueId') else None
    return {
        'slug': slug,
        'headline': story.get('headline'),
        'publishedAt': published,
        'date': date[:10],
        'issueId': story.get('issueId'),
        'publicationWeek': iso_week(date),
        'category': story.get('category'),
        'author': story.get('author'),
        'canonicalUrl': story.get('canonicalUrl')
        or 'https://delawarebeachfinds.com/stories/%s.html' % slug,
        'sourceProsePath': prose_rel,
        'renderedPagePath': 'stories/%s.html' % slug,
        'sourceProseSHA256': sha256_file(prose),
        'archiveState': 'archived',
        # The date the story left the current issue, when it had one; otherwise
        # (filled in by build()) the date this ledger first recorded it.
        'archivedAt': (issue or {}).get('supersededAt'),
        'premiumEligible': True,
        'currentAccessLevel': story.get('access_level') or 'public',
        'originalSources': story.get('sources') or [],
        'imageProvenance': image_provenance(story, attributions),
        'wordCount': word_count(html),
        'revisions': [],
    }


def build(repo=REPO, today=None, revise=None, reason=None):
    """Return (ledger, changes). Raises ArchiveError on any integrity breach."""
    today = today or today_ny()
    stories = load_json(repo, 'data/stories.json', [])
    registry = load_json(repo, 'data/issues/index.json', {}) or {}
    current = registry.get('currentIssueId')
    issues = {i['issueId']: i for i in registry.get('issues', [])}
    attributions = {i['file']: i for i in (load_json(repo, 'data/location-attributions.json', {}) or {}).get('images', [])}
    old = load_json(repo, LEDGER, None) or {'stories': []}
    by_slug = {e['slug']: e for e in old.get('stories', [])}
    records = {s.get('slug'): s for s in stories}
    changes, errors = [], []

    if revise and revise not in by_slug:
        raise ArchiveError('--revise %s: no such archived story' % revise)

    entries = {}
    # 1. Everything already archived stays archived.
    for slug, prev in by_slug.items():
        rec = records.get(slug)
        prose_rel = prev['sourceProsePath']
        if not os.path.exists(os.path.join(repo, prose_rel)):
            errors.append('%s: archived prose file %s has vanished' % (slug, prose_rel))
            entries[slug] = prev
            continue
        if rec is None:
            # The registry lost the record; the ledger keeps the story.
            entries[slug] = prev
            continue
        try:
            fresh = describe(rec, repo, issues, attributions)
        except ArchiveError as exc:
            errors.append(str(exc))
            entries[slug] = prev
            continue
        for key in ('publishedAt', 'date', 'issueId'):
            if fresh[key] != prev.get(key):
                errors.append('%s: %s changed from %r to %r — archived publication history is frozen'
                              % (slug, key, prev.get(key), fresh[key]))
        entry = dict(fresh)
        for key in FROZEN:
            entry[key] = prev.get(key)
        entry['revisions'] = list(prev.get('revisions', []))
        if fresh['sourceProseSHA256'] != prev['sourceProseSHA256']:
            if slug == revise:
                if not reason:
                    raise ArchiveError('--revise needs --reason')
                entry['revisions'].append({
                    'revisedAt': today,
                    'previousSHA256': prev['sourceProseSHA256'],
                    'sha256': fresh['sourceProseSHA256'],
                    'previousWordCount': prev.get('wordCount'),
                    'reason': reason,
                })
            else:
                errors.append('%s: archived prose changed (sha256 %s… → %s…) with no revision record; '
                              'run build_story_archive.py --revise %s --reason "..."'
                              % (slug, prev['sourceProseSHA256'][:12], fresh['sourceProseSHA256'][:12], slug))
                entry['sourceProseSHA256'] = prev['sourceProseSHA256']
                entry['wordCount'] = prev.get('wordCount')
        if entry != prev:
            changes.append('updated %s' % slug)
        entries[slug] = entry

    # 2. Newly archivable stories join the ledger.
    for s in stories:
        slug = s.get('slug')
        if slug in entries or not is_archivable(s, current):
            continue
        try:
            entry = describe(s, repo, issues, attributions)
        except ArchiveError as exc:
            errors.append(str(exc))
            continue
        entry['archivedAt'] = entry['archivedAt'] or today
        entries[slug] = entry
        changes.append('archived %s' % slug)

    if errors:
        raise ArchiveError('\n'.join(errors))

    ordered = sorted(entries.values(), key=lambda e: (e['publishedAt'], e['date'], e['slug']))
    ledger = {
        '_note': NOTE,
        'schemaVersion': SCHEMA_VERSION,
        'storyCount': len(ordered),
        'legacyNullIssueCount': sum(1 for e in ordered if e['issueId'] is None),
        'stories': ordered,
    }
    return ledger, changes


def serialize(ledger):
    return json.dumps(ledger, indent=2, ensure_ascii=False) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true', help='verify only; exit 1 if the ledger is stale or broken')
    ap.add_argument('--revise', metavar='SLUG', help='record a deliberate change to archived prose')
    ap.add_argument('--reason', help='why the archived prose changed (required with --revise)')
    ap.add_argument('--today', help='YYYY-MM-DD to stamp new entries/revisions (default: today, New York)')
    ap.add_argument('--repo', default=REPO, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        ledger, changes = build(args.repo, args.today, args.revise, args.reason)
    except ArchiveError as exc:
        print('STORY ARCHIVE ERROR:\n' + str(exc), file=sys.stderr)
        return 1
    path = os.path.join(args.repo, LEDGER)
    text = serialize(ledger)
    existing = open(path, encoding='utf-8').read() if os.path.exists(path) else None
    if args.check:
        if existing != text:
            print('data/story-archive.json is stale: %s. Run scripts/build_story_archive.py.'
                  % ('; '.join(changes) or 'formatting differs'), file=sys.stderr)
            return 1
        print('Story archive OK: %d archived stories (%d with issueId=null).'
              % (ledger['storyCount'], ledger['legacyNullIssueCount']))
        return 0
    if existing != text:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
    print('Story archive: %d archived stories (%d with issueId=null). %s'
          % (ledger['storyCount'], ledger['legacyNullIssueCount'],
             ('Changes: ' + ', '.join(changes)) if changes else 'No changes.'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
