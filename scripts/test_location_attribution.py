#!/usr/bin/env python3
"""Guard against publishing a photograph under the wrong place name.

This exists because it already happened. IMG_0943 was published as the Cape
Henlopen town hero on the strength of a filename and a prompt heading. EXIF GPS
on the adjacent frame put it on Coastal Highway about a mile south of Dewey
Beach — Delaware Seashore State Park, roughly 12 km away. A reader who knows
the coast would have caught it immediately.

Two rules, both mechanical:

  1. Every first-party field image carries a provenance record saying what
     place it may be presented as, and on what evidence.
  2. No page may pair such an image with a place name the record forbids.

Rule 2 is the one that catches the real mistake: alt text, captions and
filenames that assert a town the picture cannot support.

Usage: python3 scripts/test_location_attribution.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCENES = os.path.join(REPO, 'assets', 'images', 'scenes')

failures = []
checks = 0


def check(desc, ok, detail=''):
    global checks
    checks += 1
    if ok:
        print('  ok  - %s' % desc)
    else:
        print('FAIL  - %s' % desc)
        if detail:
            print('        %s' % detail)
        failures.append(desc)


def html_and_json_files():
    out = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', 'content')]
        for fn in files:
            if fn == 'location-attributions.json':
                continue  # the registry names forbidden claims on purpose
            if fn.endswith('.html'):  # JSON is checked structurally below
                out.append(os.path.join(root, fn))
    return out


def main():
    reg_path = os.path.join(REPO, 'data', 'location-attributions.json')
    reg = json.load(open(reg_path, encoding='utf-8'))
    records = {r['file']: r for r in reg['images']}

    # 1. Every field-* image on disk has a provenance record.
    on_disk = sorted(f for f in os.listdir(SCENES) if f.startswith('field-'))
    missing = [f for f in on_disk if f not in records]
    check('every field image has a location provenance record',
          not missing, 'undocumented: %s' % ', '.join(missing))

    # 2. Every record points at a file that exists.
    ghosts = [f for f in records if not os.path.exists(os.path.join(SCENES, f))]
    check('no provenance record points at a missing file',
          not ghosts, 'missing files: %s' % ', '.join(ghosts))

    # 3. Every record states its evidence, and it is a known level.
    levels = set(reg['_evidence_levels'])
    bad = [f for f, r in records.items() if r.get('evidence') not in levels]
    check('every record declares a known evidence level',
          not bad, 'bad evidence on: %s' % ', '.join(bad))

    # 4. Nothing claims a place its record forbids. This is the real guard:
    #    we look at the markup immediately around each use of the image.
    violations = []
    for path in html_and_json_files():
        rel = os.path.relpath(path, REPO)
        try:
            text = open(path, encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        for fname, rec in records.items():
            forbidden = rec.get('mustNotClaim') or []
            if not forbidden or fname not in text:
                continue
            for m in re.finditer(re.escape(fname), text):
                # Scope matters. A place name in the article's own prose is
                # legitimate — the towers story discusses Cape Henlopen at
                # length while correctly captioning a Delaware Seashore photo.
                # What must not happen is the *image's own* alt or caption
                # claiming the wrong place, so scan only the enclosing
                # <figure> block, or failing that the tag and a short caption.
                start = text.rfind('<figure', max(0, m.start() - 1200), m.start())
                if start != -1:
                    end = text.find('</figure>', m.end())
                    window = text[start:end + 9 if end != -1 else m.end() + 300]
                else:
                    tag_start = text.rfind('<', 0, m.start())
                    tag_end = text.find('>', m.end())
                    window = text[tag_start:tag_end + 1 if tag_end != -1 else m.end()]
                for claim in forbidden:
                    if re.search(r'\b%s\b' % re.escape(claim), window, re.I):
                        violations.append('%s: %s presented near "%s"'
                                          % (rel, fname, claim))
    # de-duplicate, keep it readable
    violations = sorted(set(violations))
    check('no image is presented under a place its provenance forbids',
          not violations, '\n        '.join(violations[:12]))


    # 5. Structural checks on the data that drives town pages and story heroes.
    #    This is the Fenwick class of defect: a photograph of Town A shipped as
    #    the face of Town B. Every raster town image must have provenance, and
    #    its proven place must be that town — or it must be declared neutral.
    TOWN = {'lewes': 'Lewes', 'rehoboth-beach': 'Rehoboth', 'dewey-beach': 'Dewey',
            'bethany-beach': 'Bethany', 'fenwick-island': 'Fenwick',
            'cape-henlopen': 'Cape Henlopen', 'assateague': 'Assateague',
            'ocean-city': 'Ocean City'}
    raster = lambda f: bool(f) and f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))

    def town_ok(img, name):
        rec = records.get(img)
        if rec is None:
            return 'no provenance record'
        if name in (rec.get('mustNotClaim') or []):
            return 'provenance forbids %s' % name
        if rec.get('neutral'):
            return None
        if rec.get('evidence') == 'none' or not rec.get('place'):
            return 'place unproven and not declared neutral'
        if name.lower() not in rec['place'].lower():
            return 'proven place is %s' % rec['place']
        return None

    bad_towns = []
    for t in json.load(open(os.path.join(REPO, 'data', 'towns.json'), encoding='utf-8')):
        name = TOWN.get(t['slug'])
        for key in ('heroScene', 'tileScene'):
            img = t.get(key)
            if name and raster(img):
                why = town_ok(img, name)
                if why:
                    bad_towns.append('%s.%s = %s (%s)' % (t['slug'], key, img, why))
        page = os.path.join(REPO, 'towns', t['slug'] + '.html')
        if name and os.path.exists(page):
            for m in re.finditer(r'<img[^>]+src="[^"]*/scenes/([^"/]+)"', open(page, encoding='utf-8').read()):
                if raster(m.group(1)):
                    why = town_ok(m.group(1), name)
                    if why:
                        bad_towns.append('towns/%s.html shows %s (%s)' % (t['slug'], m.group(1), why))
    check('every town hero, tile and town-page photo is proven for that town or neutral',
          not bad_towns, '\n        '.join(bad_towns))

    # Judge what a reader actually sees on the story: alt text, homepage
    # caption and kicker. The internal `places` tag is navigation metadata,
    # not a claim about the picture, and counting it flagged correct pairings.
    bad_stories = []
    for s in json.load(open(os.path.join(REPO, 'data', 'stories.json'), encoding='utf-8')):
        if s.get('status') != 'published' or not raster(s.get('heroImage')):
            continue
        rec = records.get(s['heroImage'])
        if not rec:
            continue
        visible = ' '.join(str(s.get(k) or '') for k in ('heroImageAlt', 'heroAlt', 'kicker'))
        for bad in rec.get('mustNotClaim') or []:
            if re.search(r'\b%s\b' % re.escape(bad), visible, re.I):
                bad_stories.append('%s hero %s shown as "%s"' % (s['slug'], s['heroImage'], bad))
        # A kicker that names a town is a lead-image claim: the hero must be
        # proven for that town (rule 1 — never Town A's landmark as Town B's lead).
        if not rec.get('neutral') and rec.get('place'):
            for name in TOWN.values():
                if re.search(r'\b%s\b' % re.escape(name), str(s.get('kicker') or ''), re.I) \
                        and name.lower() not in rec['place'].lower():
                    bad_stories.append('%s kicker names %s; hero %s is proven for %s'
                                       % (s['slug'], name, s['heroImage'], rec['place']))
    check('no story hero is paired with a place its provenance forbids',
          not bad_stories, '\n        '.join(bad_stories))

    print()
    print('=' * 32)
    print('Passed: %d   Failed: %d' % (checks - len(failures), len(failures)))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
