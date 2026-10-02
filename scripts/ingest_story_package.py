#!/usr/bin/env python3
"""Validate a researched story package and stage its stories for publication.

A story package (automation/story-packages/story_package_YYYY-MM-DD.json,
schema in automation/STORY_PACKAGE_SCHEMA.md) carries complete, sourced
stories. This script:

  * validates the whole package and rejects it outright on any error
    (nothing partial is ever written);
  * applies the auto-approval policy in data/editorial-autopilot.json:
      eligible   -> status=scheduled, approvedAt=<now>, publishAt=<slot>
      ineligible -> status=held, approvedAt=null, heldReason=<why>
  * writes content/stories/<slug>.html and the record in data/stories.json;
  * gives every issue week a cover (editorial_autopilot.assign_week_covers).

It NEVER sets status=published. scripts/publish_due.py, the hourly
publisher, is the only thing that publishes. Re-running the same package
changes nothing.

  python3 scripts/ingest_story_package.py PACKAGE.json             # validate + ingest
  python3 scripts/ingest_story_package.py PACKAGE.json --dry-run   # validate only
"""

import argparse
import copy
import json
import os
import re
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from editorial_lib import (  # noqa: E402
    DATA, PLACEMENTS, REPO, EditorialError, SITE_ORIGIN, body_path, iso_local,
    load_authors, load_json, load_stories, now_eastern, parse_publish_at, save_stories,
)
from editorial_autopilot import assign_week_covers, load_policy, runway  # noqa: E402

SCENES = os.path.join(REPO, 'assets', 'images', 'scenes')
ATTRIBUTIONS = os.path.join(DATA, 'location-attributions.json')

REQUIRED = ['slug', 'headline', 'kicker', 'hook', 'lede', 'body', 'author', 'category', 'placement',
            'sources', 'sourceNotes', 'verifiedAt', 'heroImage', 'heroAlt', 'heroProvenance',
            'seoTitle', 'seoDescription', 'places', 'riskClass', 'autoApprovalEligible']
SLUG_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


def words(html):
    return len(re.sub(r'<[^>]+>', ' ', html).split())


def visible_text(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html))


class PackageError(Exception):
    pass


def eligibility_problems(st, policy, now):
    """Why this story may NOT be auto-approved (empty list = eligible)."""
    ap = policy['autoApproval']
    out = []
    if st.get('riskClass') not in ap['autoApprovableRiskClasses']:
        out.append('risk class %r is not auto-approvable' % st.get('riskClass'))
    srcs = st.get('sources') or []
    if len(srcs) < ap['minimumSources']:
        out.append('%d source(s); auto-approval needs at least %d' % (len(srcs), ap['minimumSources']))
    authoritative = [s for s in srcs if isinstance(s, dict) and s.get('type') in ap['authoritativeSourceTypes']]
    if len(authoritative) < ap['minimumAuthoritativeSources']:
        out.append('no first-party/government/institutional source')
    try:
        verified = parse_publish_at(st.get('verifiedAt'))
        if now - verified > timedelta(days=ap['maximumVerificationAgeDays']):
            out.append('verification is older than %d days' % ap['maximumVerificationAgeDays'])
    except (EditorialError, TypeError):
        out.append('verifiedAt is not a valid date')
    if words(st.get('body') or '') < ap['minimumBodyWords']:
        out.append('body is shorter than %d words' % ap['minimumBodyWords'])
    text = visible_text(st.get('body') or '')
    for name, pattern in ap['forbiddenPatterns'].items():
        if name.startswith('_'):
            continue
        if re.search(pattern, text, re.I):
            out.append('prose matches forbidden pattern %r' % name)
    return out


def validate_package(pkg, stories, policy, now, desks):
    """Return a list of errors. Any error rejects the whole package."""
    errs = []
    items = pkg.get('stories')
    if not isinstance(items, list) or not items:
        return ['package has no stories list']
    if not pkg.get('packageId'):
        errs.append('package has no packageId')
    existing = {s['slug']: s for s in stories}
    seen = set()
    attributions = {i['file']: i for i in load_json(ATTRIBUTIONS, {'images': []}).get('images', [])}
    for i, st in enumerate(items):
        label = st.get('slug') or 'story #%d' % (i + 1)
        # `places` may be an empty list (a town with no DBF town page); it must be present.
        missing = [f for f in REQUIRED if st.get(f) in (None, '') or (st.get(f) == [] and f != 'places')]
        if not isinstance(st.get('places'), list):
            missing.append('places (as a list)')
        if missing:
            errs.append('%s: missing %s' % (label, ', '.join(missing)))
            continue
        slug = st['slug']
        if not SLUG_RE.match(slug):
            errs.append('%s: slug must be lowercase-hyphenated' % slug)
        if slug in seen:
            errs.append('%s: duplicate slug in package' % slug)
        seen.add(slug)
        old = existing.get(slug)
        if old and old.get('packageId') != pkg.get('packageId'):
            errs.append('%s: slug already exists in data/stories.json' % slug)
        if old and old.get('status') == 'published':
            errs.append('%s: already published; packages may not rewrite published stories' % slug)
        if st['author'] not in desks:
            errs.append('%s: unknown author desk %r' % (slug, st['author']))
        # The article template links to the category page, so it must exist.
        if not os.path.exists(os.path.join(REPO, 'stories', 'category-%s.html' % st['category'])):
            errs.append('%s: category %r has no category page (stories/category-%s.html)'
                        % (slug, st['category'], st['category']))
        if st['placement'] not in PLACEMENTS:
            errs.append('%s: invalid placement %r' % (slug, st['placement']))
        if st.get('status') == 'published' or st.get('publishedAt'):
            errs.append('%s: packages may never carry published state' % slug)
        if words(st['body']) < 100:
            errs.append('%s: body prose is missing or too short' % slug)
        urls = [s.get('url') if isinstance(s, dict) else s for s in st['sources']]
        if not urls or any(not (isinstance(u, str) and re.match(r'^https?://', u)) for u in urls):
            errs.append('%s: every source needs an http(s) url' % slug)
        if not os.path.exists(os.path.join(SCENES, st['heroImage'])):
            errs.append('%s: hero image %s does not exist' % (slug, st['heroImage']))
        reg = attributions.get(st['heroImage'])
        if reg:
            shown = ' '.join([st['heroAlt'], st['headline'], st['kicker']])
            for bad in reg.get('mustNotClaim') or []:
                if re.search(r'\b%s\b' % re.escape(bad), shown, re.I):
                    errs.append('%s: hero image may not be presented as %s' % (slug, bad))
        # Related links render on the article page the moment it publishes, so
        # each must resolve then: an existing page, or a story that publishes no
        # later than this one. A dead link fails the publisher's test suite.
        mine = st.get('suggestedPublishAt') or '9999'
        pkg_at = {s.get('slug'): (s.get('suggestedPublishAt') if s.get('autoApprovalEligible') else None) for s in items}
        for rel in st.get('relatedStories') or []:
            href = (rel or {}).get('href') or ''
            path = os.path.normpath(os.path.join(REPO, 'stories', href))
            target = href[:-5] if href.endswith('.html') and '/' not in href else None
            when = pkg_at.get(target) if target in pkg_at else (
                existing[target].get('publishAt') if target in existing and existing[target].get('status') == 'scheduled' else None)
            if os.path.exists(path):
                continue
            if when and str(when) <= mine:
                continue
            errs.append('%s: related link %r does not resolve when it publishes' % (slug, href))
        if st.get('autoApprovalEligible'):
            problems = eligibility_problems(st, policy, now)
            if problems:
                errs.append('%s: marked autoApprovalEligible but %s' % (slug, '; '.join(problems)))
            when = st.get('suggestedPublishAt')
            try:
                at = parse_publish_at(when)
                if at <= now:
                    errs.append('%s: suggestedPublishAt %s is not in the future' % (slug, when))
            except (EditorialError, TypeError):
                errs.append('%s: eligible stories need a valid suggestedPublishAt' % slug)
        elif not st.get('heldReason'):
            errs.append('%s: not auto-approvable, so heldReason is required' % slug)
    # Spacing among this package's eligible stories and already-scheduled ones.
    # Only pairs involving this package are judged: history is not re-litigated.
    times = sorted(
        [(parse_publish_at(s['suggestedPublishAt']), s['slug'], True) for s in items
         if s.get('autoApprovalEligible') and s.get('suggestedPublishAt') and not any('suggestedPublishAt' in e and s['slug'] in e for e in errs)]
        + [(parse_publish_at(s['publishAt']), s['slug'], False) for s in stories
           if s.get('status') in ('scheduled', 'published') and s.get('publishAt') and s['slug'] not in seen
           and len(str(s['publishAt'])) > 10])
    for (a, sa, pa), (b, sb, pb) in zip(times, times[1:]):
        if (pa or pb) and b - a < timedelta(hours=policy['minimumGapHours']):
            errs.append('%s and %s are %.1fh apart (minimum %dh)'
                        % (sa, sb, (b - a).total_seconds() / 3600, policy['minimumGapHours']))
    return errs


def build_record(st, pkg, approved_at, old):
    eligible = bool(st.get('autoApprovalEligible'))
    rec = dict(old or {})
    rec.update({
        'slug': st['slug'], 'kicker': st['kicker'], 'headline': st['headline'], 'hook': st['hook'],
        'lede': st['lede'], 'scene': st['heroImage'], 'heroImage': st['heroImage'],
        'heroAlt': st['heroAlt'], 'heroImageAlt': st.get('heroImageAlt') or st['heroAlt'],
        'photoCredit': st.get('photoCredit') or 'Delaware Beach Finds',
        'readTime': st.get('readTime') or '%d min read' % max(2, round(words(st['body']) / 200)),
        'category': st['category'], 'author': st['author'], 'metaTag': st.get('metaTag') or st['kicker'],
        'placement': st['placement'], 'places': st['places'],
        'sources': [s['url'] if isinstance(s, dict) else s for s in st['sources']],
        'relatedStories': st.get('relatedStories') or [],
        'seoTitle': st['seoTitle'], 'seoDescription': st['seoDescription'],
        'canonicalUrl': '%s/stories/%s.html' % (SITE_ORIGIN, st['slug']),
        'ogImage': '%s/assets/images/scenes/%s' % (SITE_ORIGIN, st['heroImage']),
        'featured': False, 'coverStory': False, 'series': None, 'seriesInstallment': None,
        'seriesTotal': None, 'seriesPage': False, 'etsyProductIds': [], 'shopTheStory': False,
        'access_level': 'public', 'renderMode': 'generated', 'body': [],
        'issueId': None, 'publishedAt': None,
        'riskClass': st['riskClass'], 'verifiedAt': st['verifiedAt'],
        'heroProvenance': st['heroProvenance'], 'packageId': pkg['packageId'],
        'autopilot': True,
    })
    if eligible:
        rec['status'] = 'scheduled'
        rec['approvedAt'] = (old or {}).get('approvedAt') or approved_at
        rec['publishAt'] = st['suggestedPublishAt']
        rec['date'] = st['suggestedPublishAt'][:10]
        rec['heldReason'] = None
    else:
        rec['status'] = 'held'
        rec['approvedAt'] = None
        rec['publishAt'] = None
        rec['date'] = None
        rec['heldReason'] = st['heldReason']
    assert rec['status'] != 'published'
    return rec


def ingest(pkg, now=None, dry_run=False, quiet=False):
    policy = load_policy()
    now = now or now_eastern().replace(second=0, microsecond=0)
    stories = load_stories()
    desks = {d['id'] for d in load_authors()['desks']}
    errs = validate_package(pkg, stories, policy, now, desks)
    if errs:
        raise PackageError('\n'.join(errs))

    if dry_run:
        stories = copy.deepcopy(stories)  # stage in memory so the runway report is what ingest would produce
    by_slug = {s['slug']: i for i, s in enumerate(stories)}
    before = {s['slug']: copy.deepcopy(s) for s in stories}
    prose_changed = set()
    for st in pkg['stories']:
        old = stories[by_slug[st['slug']]] if st['slug'] in by_slug else None
        rec = build_record(st, pkg, iso_local(now), old)
        prose_path = body_path(st['slug'])
        prose = st['body'].strip() + '\n'
        prose_old = open(prose_path, encoding='utf-8').read() if os.path.exists(prose_path) else None
        if prose != prose_old:
            prose_changed.add(st['slug'])
        if not dry_run and prose != prose_old:
            with open(prose_path, 'w', encoding='utf-8') as fh:
                fh.write(prose)
        if old is None:
            stories.append(rec)
            by_slug[st['slug']] = len(stories) - 1
        else:
            stories[by_slug[st['slug']]] = rec

    covers = assign_week_covers(stories)
    # Judge change on the final state, after cover placement, so a re-run of
    # the same package reports (and writes) nothing.
    changed = [s['slug'] for s in stories if s != before.get(s['slug'])]
    changed += [slug for slug in sorted(prose_changed) if slug not in changed]
    covers = [c for c in covers if c in changed]
    if not dry_run and changed:
        save_stories(stories)
    report = runway(stories, now, policy)
    if not quiet:
        print('%s %d stor%s: %s' % ('Would ingest' if dry_run else 'Ingested', len(changed),
                                    'y' if len(changed) == 1 else 'ies', ', '.join(changed) or '(no changes)'))
        for st in pkg['stories']:
            print('  %-42s %s' % (st['slug'], ('scheduled ' + st['suggestedPublishAt']) if st.get('autoApprovalEligible')
                                  else 'HELD — ' + st['heldReason']))
        if covers:
            print('  cover placement assigned: %s' % ', '.join(covers))
        if not report['healthy']:
            print('\nRUNWAY NOT HEALTHY after ingest:')
            for v in report['violations']:
                if v['severity'] == 'fail':
                    print('  [fail] %s' % v['message'])
    return {'changed': changed, 'covers': covers, 'runway': report}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('package')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--now')
    a = ap.parse_args()
    try:
        pkg = json.load(open(a.package, encoding='utf-8'))
        ingest(pkg, now=parse_publish_at(a.now) if a.now else None, dry_run=a.dry_run)
    except (PackageError, EditorialError, ValueError) as exc:
        print('REJECTED — nothing written:\n%s' % exc)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
