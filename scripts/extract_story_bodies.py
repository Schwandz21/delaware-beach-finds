#!/usr/bin/env python3
"""One-time migration: lift article prose out of the static pages.

The existing article pages are hand-authored and correct. Rather than retype
their prose into JSON — which would be lossy for inline links, <strong>, rules
and source notes — this copies the body fragment out verbatim into
content/stories/<slug>.html, which then becomes the canonical prose.

The hero image block and the byline meta line are NOT captured: those are
derived from the story registry so the renderer can keep them consistent (three
existing pages are missing a byline entirely, and generating it fixes that).

Idempotent. Running it twice produces the same files.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from editorial_lib import CONTENT, STORIES_DIR, load_stories, body_path  # noqa: E402

ARTICLE_RE = re.compile(r'<article class="article">(.*?)</article>', re.S)
HERO_RE = re.compile(r'\s*<div class="eq-media".*?</div></div>\s*', re.S)
META_RE = re.compile(r'\s*<div class="article-meta">.*?</div>\s*(?=<)', re.S)


def extract(slug):
    page = os.path.join(STORIES_DIR, '%s.html' % slug)
    if not os.path.exists(page):
        return None, 'no page'
    html = open(page, encoding='utf-8').read()
    m = ARTICLE_RE.search(html)
    if not m:
        return None, 'no <article class="article"> block'
    inner = m.group(1)
    # Strip the two generated regions, leaving prose only.
    inner = HERO_RE.sub('\n', inner, count=1)
    inner = META_RE.sub('\n', inner, count=1)
    return inner.strip() + '\n', None


def main():
    os.makedirs(CONTENT, exist_ok=True)
    stories = load_stories()
    wrote = skipped = 0
    for s in stories:
        slug = s['slug']
        body, err = extract(slug)
        if err:
            print('  skip %-46s (%s)' % (slug, err))
            skipped += 1
            continue
        dest = body_path(slug)
        existing = open(dest, encoding='utf-8').read() if os.path.exists(dest) else None
        if existing == body:
            print('  ok   %-46s (unchanged)' % slug)
        else:
            with open(dest, 'w', encoding='utf-8') as fh:
                fh.write(body)
            print('  wrote %-45s (%d bytes)' % (slug, len(body)))
        wrote += 1
    print('\n%d prose files in content/stories, %d skipped' % (wrote, skipped))
    return 0 if skipped == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
