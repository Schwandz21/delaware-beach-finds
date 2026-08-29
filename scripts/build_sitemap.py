#!/usr/bin/env python3
"""Regenerate sitemap.xml from what actually exists.

The previous sitemap was a hand-maintained file that fell behind: 17 of 22
published stories, and today.html/live.html/advertise.html/category and
series pages, were simply never added as the archive grew. This script
derives the story list from data/stories.json (the single source of truth)
so the sitemap cannot drift out of sync with publication again.

Usage: python3 scripts/build_sitemap.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ORIGIN = 'https://delawarebeachfinds.com'

# Fixed top-level and utility pages, with hand-tuned priority/changefreq.
# (page, changefreq, priority)
STATIC_PAGES = [
    ('/', 'daily', '1.0'),
    ('today.html', 'daily', '0.9'),
    ('this-week.html', 'weekly', '0.9'),
    ('live.html', 'weekly', '0.8'),
    ('watch.html', 'weekly', '0.8'),
    ('stories/index.html', 'weekly', '0.8'),
    ('archive.html', 'weekly', '0.8'),
    ('hidden-gems.html', 'weekly', '0.8'),
    ('explore.html', 'monthly', '0.8'),
    ('guides.html', 'monthly', '0.8'),
    ('events.html', 'weekly', '0.7'),
    ('community.html', 'weekly', '0.7'),
    ('search.html', 'monthly', '0.6'),
    ('shop.html', 'monthly', '0.6'),
    ('advertise.html', 'monthly', '0.5'),
    ('gordons-pond-walking-guide.html', 'monthly', '0.7'),
    ('lewes-canal-waterfront-walk.html', 'monthly', '0.7'),
    ('surf-fishing-guide.html', 'monthly', '0.7'),
    ('sunset-spots.html', 'monthly', '0.7'),
    ('about.html', 'monthly', '0.5'),
    ('contact.html', 'monthly', '0.4'),
    ('privacy.html', 'yearly', '0.3'),
    ('terms.html', 'yearly', '0.3'),
    ('disclosure.html', 'yearly', '0.3'),
]

TOWNS = ['lewes', 'rehoboth-beach', 'dewey-beach', 'bethany-beach',
         'fenwick-island', 'cape-henlopen', 'assateague', 'ocean-city']

CATEGORIES = ['coast', 'history', 'people', 'field-guide']


def entry(loc, lastmod, changefreq, priority):
    return ('<url><loc>%s/%s</loc><lastmod>%s</lastmod>'
            '<changefreq>%s</changefreq><priority>%s</priority></url>'
            % (ORIGIN, loc.lstrip('/'), lastmod, changefreq, priority))


def main():
    stories = json.load(open(os.path.join(REPO, 'data', 'stories.json'), encoding='utf-8'))
    today = json.load(open(os.path.join(REPO, 'data', 'coast-now.json'), encoding='utf-8')
                       ) if os.path.exists(os.path.join(REPO, 'data', 'coast-now.json')) else {}
    default_lastmod = (today.get('generatedAt') or '2026-08-19T00:00:00Z')[:10]

    urls = []
    for loc, freq, pri in STATIC_PAGES:
        loc = '' if loc == '/' else loc
        urls.append(entry(loc, default_lastmod, freq, pri))

    for t in TOWNS:
        urls.append(entry('towns/%s.html' % t, default_lastmod, 'monthly', '0.6'))

    for cat in CATEGORIES:
        urls.append(entry('stories/category-%s.html' % cat, default_lastmod, 'weekly', '0.6'))

    if any(s.get('series') for s in stories):
        for series_slug in sorted({s['series'] for s in stories if s.get('series')}):
            path = os.path.join(REPO, 'stories', 'series-%s.html' % series_slug)
            if os.path.exists(path):
                urls.append(entry('stories/series-%s.html' % series_slug, default_lastmod, 'monthly', '0.6'))

    published = [s for s in stories if s.get('status') == 'published']
    for s in sorted(published, key=lambda x: x.get('date') or ''):
        lastmod = s.get('publishedAt') or s.get('date') or default_lastmod
        urls.append(entry('stories/%s.html' % s['slug'], lastmod, 'monthly', '0.7'))

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + '\n'.join(urls) + '\n</urlset>\n')

    out = os.path.join(REPO, 'sitemap.xml')
    old = open(out, encoding='utf-8').read() if os.path.exists(out) else ''
    if xml == old:
        print('sitemap.xml already current (%d urls)' % len(urls))
        return 0
    open(out, 'w', encoding='utf-8').write(xml)
    print('wrote sitemap.xml: %d urls (%d stories)' % (len(urls), len(published)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
