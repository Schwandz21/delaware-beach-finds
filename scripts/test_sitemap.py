#!/usr/bin/env python3
"""Sitemap stays in sync with published stories.

The sitemap used to be hand-maintained and quietly fell 17 stories behind.
This test fails the suite if that happens again, so a publish run notices
before search engines lose the discovery signal.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print('  %s - %s%s' % ('ok  ' if cond else 'FAIL', name,
                           '' if cond else '\n        >>> %s' % detail))


def main():
    stories = json.load(open(os.path.join(ROOT, 'data', 'stories.json'), encoding='utf-8'))
    published = {s['slug'] for s in stories if s.get('status') == 'published'}

    sm_path = os.path.join(ROOT, 'sitemap.xml')
    check('sitemap.xml exists', os.path.exists(sm_path))
    if not os.path.exists(sm_path):
        print('\nFailed: 1'); return 1

    sm = open(sm_path, encoding='utf-8').read()
    urls = re.findall(r'<loc>https://delawarebeachfinds\.com/(.*?)</loc>', sm)

    missing = [s for s in published if 'stories/%s.html' % s not in sm]
    check('every published story is in the sitemap', not missing, missing)

    referenced = {re.match(r'stories/([a-z0-9-]+)\.html', u).group(1)
                  for u in urls if re.match(r'stories/([a-z0-9-]+)\.html', u)
                  and re.match(r'stories/([a-z0-9-]+)\.html', u).group(1) not in
                  ('index', 'category-coast', 'category-history', 'category-people',
                   'category-field-guide', 'series-how-delaware-became-delaware')}
    stale = referenced - published
    check('no stale/removed story URLs remain in the sitemap', not stale, stale)

    missing_files = [u for u in urls if u and not os.path.exists(os.path.join(ROOT, u))]
    check('every sitemap URL resolves to a real file', not missing_files, missing_files)

    for required in ('today.html', 'live.html', '/'):
        loc = '' if required == '/' else required
        check('sitemap includes %s' % required,
              ('<loc>https://delawarebeachfinds.com/%s</loc>' % loc) in sm)

    print('\nPassed: %d   Failed: %d' % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
