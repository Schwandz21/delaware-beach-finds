#!/usr/bin/env python3
"""Premium archive access: configuration, the safety gate, and the interface a
future protected backend must implement.

TODAY: premium access is DISABLED (data/premium-archive.json "enabled": false).
Every archived story is free to read, and the site says so. Nothing here is a
paywall.

THE SAFETY RULE: premium access may not be enabled while the full text of any
premium-eligible story is still shipped publicly. This site is a static GitHub
Pages build of a public repository, so today the full text of every archived
story is public in three places:
  * content/stories/<slug>.html   (canonical prose, in the public repo)
  * stories/<slug>.html           (the rendered public page)
  * data/stories.json "body"      (the inline body, fetched by the browser)
A JavaScript lock over any of those is cosmetic, not access control.
`premium_violations()` finds every such exposure; validate_editorial.py and the
test suite refuse "enabled": true while it returns anything.

FUTURE INTERFACE (a backend must implement all three before enabling):
  1. Public metadata / teaser — anyone, no auth. Served from the static site:
       {slug, headline, kicker, hook, date, issueId, category, author,
        heroImage, wordCount, premium: true}
     (exactly the ledger fields in data/story-archive.json plus the hook.)
  2. Authenticated full text — GET {fullTextEndpoint}/<slug> with the
     subscriber's session credential; returns {slug, html} for an entitled
     subscriber, 401 when not signed in, 403 when not entitled. The prose must
     then live ONLY behind that endpoint (moved out of the public repo and out
     of the public static HTML).
  3. Subscriber access state — GET {accessStateEndpoint}; returns
     {signedIn: bool, entitled: bool, plan: str|null, expiresAt: str|null}.
     Payment/entitlement is the backend's job; the static site only reads it.

Usage:
  python3 scripts/premium_archive.py          # report status; exit 1 if unsafe
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CONFIG = 'data/premium-archive.json'
DEFAULT = {'enabled': False, 'reason': 'Protected premium-content backend is not yet configured.'}
REQUIRED_WHEN_ENABLED = ('fullTextEndpoint', 'accessStateEndpoint')


def load_config(repo=REPO):
    path = os.path.join(repo, CONFIG)
    if not os.path.exists(path):
        return dict(DEFAULT)
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def public_exposures(repo=REPO):
    """Every place the full text of a premium-eligible archived story is public."""
    ledger_path = os.path.join(repo, 'data/story-archive.json')
    if not os.path.exists(ledger_path):
        return []
    ledger = json.load(open(ledger_path, encoding='utf-8'))
    stories_path = os.path.join(repo, 'data/stories.json')
    records = {s.get('slug'): s for s in json.load(open(stories_path, encoding='utf-8'))} \
        if os.path.exists(stories_path) else {}
    found = []
    for e in ledger.get('stories', []):
        if not e.get('premiumEligible'):
            continue
        slug = e['slug']
        if os.path.exists(os.path.join(repo, e['sourceProsePath'])):
            found.append('%s: full prose is public in the repository at %s' % (slug, e['sourceProsePath']))
        if os.path.exists(os.path.join(repo, e['renderedPagePath'])):
            found.append('%s: full text is public static HTML at %s' % (slug, e['renderedPagePath']))
        if (records.get(slug) or {}).get('body'):
            found.append('%s: full body is public in data/stories.json' % slug)
    return found


def premium_violations(config=None, repo=REPO):
    """Reasons premium access must not be enabled. Empty when disabled, or when
    enabled with a real backend and no publicly shipped premium text."""
    config = load_config(repo) if config is None else config
    if not config.get('enabled'):
        return []
    problems = []
    for key in REQUIRED_WHEN_ENABLED:
        if not config.get(key):
            problems.append('premium access is enabled but %s is not configured' % key)
    exposures = public_exposures(repo)
    if exposures:
        problems.append('premium access is enabled while premium full text is publicly shipped '
                        '(%d exposures, e.g. %s). A JavaScript lock is not a paywall.'
                        % (len(exposures), exposures[0]))
    return problems


def main():
    cfg = load_config()
    problems = premium_violations(cfg)
    if problems:
        for p in problems:
            print('  FAIL - ' + p)
        return 1
    if cfg.get('enabled'):
        print('Premium archive: ENABLED (backend configured, no public premium text).')
    else:
        print('Premium archive: disabled — %s' % cfg.get('reason', ''))
        print('  %d public full-text exposures would have to be removed before enabling.'
              % len(public_exposures()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
