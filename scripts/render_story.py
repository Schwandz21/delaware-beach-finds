#!/usr/bin/env python3
"""Deterministic article renderer.

Builds stories/<slug>.html from:
  data/stories.json           the registry record
  content/stories/<slug>.html the prose
  templates/article.html      the page shell (design system lives here)
  data/authors.json           the house desk byline
  data/categories.json        breadcrumb + section labels

Deterministic: same inputs produce byte-identical output, so re-running never
churns the repo. Only `published` stories are written to disk — an unpublished
story must not leave a live URL behind.

Usage:
  python3 scripts/render_story.py                 # render all published
  python3 scripts/render_story.py <slug> [...]    # render specific slugs
  python3 scripts/render_story.py --check         # verify on-disk pages match
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from editorial_lib import (  # noqa: E402
    DATA, REPO, STORIES_DIR, SITE_ORIGIN, EditorialError,
    load_authors, load_json, load_stories, read_body, esc,
    parse_publish_at, story_url,
)

TEMPLATE = os.path.join(REPO, 'templates', 'article.html')
IMG_BASE = '%s/assets/images/scenes/' % SITE_ORIGIN


def human_date(value):
    dt = parse_publish_at(value)
    if not dt:
        return ''
    return '%s %d, %d' % (dt.strftime('%B'), dt.day, dt.year)


def category_map():
    cats = load_json(os.path.join(DATA, 'categories.json'))
    return {c['slug']: c for c in cats}


def series_map():
    items = load_json(os.path.join(DATA, 'series.json'), [])
    return {s['slug']: s for s in items}


def desk_map():
    a = load_authors()
    return {d['id']: d for d in a['desks']}, a['default']


def hero_media(story):
    """The opening art block. Empty string when the story has no scene asset."""
    # heroImage is the real published filename. `scene` is the registry's short
    # name and is NOT always extension-complete — using it dropped `.svg` and
    # broke two images, so heroImage wins.
    scene = story.get('heroImage') or story.get('scene')
    if not scene:
        return ''
    alt = esc(story.get('heroAlt') or story.get('headline') or '')
    return ('<div class="eq-media" style="margin-bottom:34px"><div class="scene">'
            '<img src="../assets/images/scenes/%s" alt="%s" loading="lazy"></div></div>'
            % (esc(scene), alt))


def series_nav(story):
    if not story.get('series'):
        return ''
    return ('<section class="section-tight"><div class="container">\n'
            '<div data-mount="series-nav" data-story="%s"></div>\n'
            '</div></section>' % esc(story['slug']))


def jsonld(story, desk, cat):
    """Article structured data. Author is the house desk, as an Organization —
    a house desk is not a Person and must never be modelled as one."""
    doc = {
        '@context': 'https://schema.org',
        '@type': 'Article',
        'headline': story.get('headline'),
        'description': story.get('seoDescription') or story.get('hook'),
        'datePublished': story.get('publishedAt') or story.get('date'),
        'dateModified': story.get('updatedAt') or story.get('publishedAt') or story.get('date'),
        'articleSection': (cat or {}).get('label'),
        'author': {'@type': 'Organization', 'name': desk['name']},
        'publisher': {'@type': 'Organization', 'name': 'Delaware Beach Finds'},
        'mainEntityOfPage': story_url(story['slug']),
    }
    if story.get('heroImage') or story.get('scene'):
        doc['image'] = IMG_BASE + (story.get('heroImage') or story['scene'])
    if story.get('series'):
        doc['isPartOf'] = {'@type': 'CreativeWorkSeries', 'name': story['series']}
    return json.dumps({k: v for k, v in doc.items() if v}, ensure_ascii=False)


def render(story, tpl, cats, desks, default_desk, series_index):
    slug = story['slug']
    cat = cats.get(story.get('category')) or {}
    desk = desks.get(story.get('author')) or desks[default_desk]

    seo_title = story.get('seoTitle') or ('%s | Delaware Beach Finds' % story.get('headline'))
    seo_desc = story.get('seoDescription') or story.get('hook') or ''
    canonical = story.get('canonicalUrl') or story_url(slug)
    published_at = story.get('publishedAt') or story.get('date') or ''

    # A house desk is the byline. `data-byline="house"` lets the existing
    # site-editorial.json swap the institutional name in one place; a named desk
    # is rendered literally and opts out of that swap.
    is_house_default = desk['id'] == default_desk
    byline_mode = 'house' if is_house_default else 'desk'

    # A story that belongs to a series with its own landing page is filed under
    # the series; everything else is filed under its category. `seriesPage`
    # records which case applies, because not every series has a page.
    hero_asset = story.get('heroImage') or story.get('scene')
    cat_href = 'category-%s.html' % story['category'] if story.get('category') else 'index.html'
    cat_label = cat.get('label') or 'Delaware Stories'
    if story.get('series') and story.get('seriesPage'):
        series_meta = series_index.get(story['series']) or {}
        crumb_href = 'series-%s.html' % story['series']
        crumb_label = series_meta.get('title') or story['series']
        aside_href, aside_label = crumb_href, 'The full series'
    else:
        crumb_href, crumb_label = cat_href, cat_label
        aside_href, aside_label = cat_href, 'More %s stories' % cat_label

    # Curated "Keep reading" links are editorial choices and are preserved
    # verbatim. The related-stories mount still fills in dynamically alongside.
    rel = story.get('relatedStories') or []
    if rel:
        related_list = ''.join('<li><a href="%s">%s</a></li>' % (esc(r['href']), esc(r['label']))
                               for r in rel)
    else:
        related_list = '<li><a href="%s">%s</a></li>' % (esc(aside_href), esc(aside_label))

    shop_block = ''
    if story.get('shopTheStory'):
        shop_block = ('<section class="section"><div class="container">\n'
                      '<div data-mount="shop-the-story" data-story="%s"></div>\n'
                      '</div></section>' % esc(slug))

    fields = {
        'SEO_TITLE': esc(seo_title),
        'SEO_DESCRIPTION': esc(seo_desc),
        'CANONICAL': esc(canonical),
        'OG_IMAGE': esc(story.get('ogImage') or (IMG_BASE + hero_asset) if hero_asset else ''),
        'PUBLISHED_AT': esc(published_at),
        'MODIFIED_AT': esc(story.get('updatedAt') or published_at),
        'CATEGORY_LABEL': esc(cat.get('label') or 'Delaware Stories'),
        'META_TAG': esc(story.get('metaTag') or story.get('kicker') or ''),
        'RELATED_LIST': related_list,
        'SHOP_THE_STORY': shop_block,
        'CRUMB_HREF': esc(crumb_href),
        'CRUMB_LABEL': esc(crumb_label),
        'ASIDE_HREF': esc(aside_href),
        'ASIDE_LABEL': esc(aside_label),
        'HEADLINE': esc(story.get('headline')),
        'KICKER': esc(story.get('kicker') or cat.get('label') or ''),
        # The article lede is its own published text. It often differs from
        # `hook`, which is the card/homepage summary — rendering hook here would
        # silently rewrite published articles.
        'HOOK': esc(story.get('lede') or story.get('hook') or ''),
        'HERO_MEDIA': hero_media(story),
        'BYLINE': esc(desk['name']),
        'BYLINE_MODE': byline_mode,
        'PUBLISHED_HUMAN': esc(human_date(published_at)),
        'READ_TIME': esc(story.get('readTime') or ''),
        'BODY': read_body(slug),
        'SLUG': esc(slug),
        'SERIES_NAV': series_nav(story),
        'JSONLD': jsonld(story, desk, cat),
    }

    out = tpl
    for key, val in fields.items():
        out = out.replace('{{%s}}' % key, val)
    if '{{' in out:
        leftover = out[out.index('{{'):out.index('{{') + 40]
        raise EditorialError('unfilled template placeholder near: %s' % leftover)
    return out


def render_all(slugs=None, check=False, quiet=False):
    tpl = open(TEMPLATE, encoding='utf-8').read()
    cats = category_map()
    desks, default_desk = desk_map()
    series_index = series_map()
    stories = load_stories()

    targets = [s for s in stories if s.get('status') == 'published']
    if slugs:
        want = set(slugs)
        targets = [s for s in stories if s['slug'] in want]

    written, drift = [], []
    for s in targets:
        if s.get('renderMode') == 'manual':
            continue
        html = render(s, tpl, cats, desks, default_desk, series_index)
        dest = os.path.join(STORIES_DIR, '%s.html' % s['slug'])
        current = open(dest, encoding='utf-8').read() if os.path.exists(dest) else None
        if current == html:
            continue
        if check:
            drift.append(s['slug'])
            continue
        with open(dest, 'w', encoding='utf-8') as fh:
            fh.write(html)
        written.append(s['slug'])
        if not quiet:
            print('  rendered %s' % s['slug'])

    if check:
        if drift:
            print('  DRIFT: %d page(s) differ from their source: %s'
                  % (len(drift), ', '.join(drift)))
            return 1
        if not quiet:
            print('  ok  - all %d rendered pages match their editorial source' % len(targets))
        return 0

    if not quiet:
        print('\n%d page(s) written, %d already current' % (len(written), len(targets) - len(written)))
    return 0


def main():
    args = [a for a in sys.argv[1:]]
    check = '--check' in args
    slugs = [a for a in args if not a.startswith('--')]
    try:
        return render_all(slugs or None, check=check)
    except EditorialError as exc:
        print('ERROR: %s' % exc)
        return 2


if __name__ == '__main__':
    sys.exit(main())
