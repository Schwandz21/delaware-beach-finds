#!/usr/bin/env python3
"""One-time migration: extend the story registry with lifecycle fields.

Adds the scheduling/placement/desk metadata the editorial OS needs, WITHOUT
inventing history. Every existing story is already genuinely published, so:

  * status stays `published`
  * publishedAt is taken from the record's real `date` — no dates are invented
  * publishAt mirrors publishedAt so the timeline is coherent
  * approvedAt mirrors publishedAt (a published story was, by definition,
    approved) — this is a statement about the past, not a new approval
  * issueId is derived from the real publication date's ISO week
  * the current featured story becomes placement `cover`; everything else keeps
    reading order by date and gets `standard`

Idempotent: fields already present are left alone.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from editorial_lib import (  # noqa: E402
    load_authors, load_stories, save_stories, parse_publish_at, issue_id_for,
)


def desk_for(story, authors):
    """Map a story to a house desk by category. Obvious cases only."""
    cat = story.get('category')
    for desk in authors['desks']:
        if cat in (desk.get('categories') or []):
            return desk['id']
    return authors['default']


def main():
    authors = load_authors()
    stories = load_stories()
    changed = 0

    for s in stories:
        before = dict(s)
        real_date = s.get('date')
        dt = parse_publish_at(real_date) if real_date else None

        s.setdefault('status', 'published')
        # Real publication date, carried across verbatim.
        s.setdefault('publishedAt', real_date)
        s.setdefault('publishAt', real_date)
        s.setdefault('approvedAt', real_date)
        s.setdefault('issueId', issue_id_for(dt) if dt else None)
        s.setdefault('author', desk_for(s, authors))
        s.setdefault('coverStory', bool(s.get('featured')))
        s.setdefault('placement', 'cover' if s.get('featured') else 'standard')
        s.setdefault('seriesInstallment', s.get('seriesInstallment'))
        s.setdefault('relatedStories', [])
        s.setdefault('seoTitle', None)
        s.setdefault('seoDescription', None)
        s.setdefault('canonicalUrl', None)
        s.setdefault('renderMode', 'generated')
        s.setdefault('heldReason', None)

        if s != before:
            changed += 1
            print('  updated %s' % s['slug'])

    save_stories(stories)
    print('\n%d/%d records extended. No dates invented.' % (changed, len(stories)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
