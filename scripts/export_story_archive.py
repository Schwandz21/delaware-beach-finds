#!/usr/bin/env python3
"""Export the DBF story archive as a private owner ZIP.

Writes private-exports/dbf-story-archive-YYYYMMDD.zip (git-ignored; never
commit it). The ZIP is a self-contained, checksummed copy of the back catalog:

  README.md              what everything is
  story-archive.json     the ledger (data/story-archive.json), verbatim
  prose/<slug>.html      canonical prose for every archived story
  rendered/<slug>.html   the rendered public page for every archived story
  metadata/<slug>.json   the story's data/stories.json record (inline body removed;
                         the prose is in prose/)
  issue-history.json     every issue an archived story belongs to, plus the
                         stories with no issue
  issues/<issueId>.json  the full issue documents those stories belong to
  SHA256SUMS.txt         sha256 of every other file (verify: sha256sum -c)

The export refuses to run if the ledger is stale or any archived prose has
drifted from its recorded checksum, so a ZIP always matches its own ledger.

Usage:
  python3 scripts/export_story_archive.py [--date YYYYMMDD] [--out-dir DIR]
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from build_story_archive import LEDGER, ArchiveError, build, serialize, sha256_file  # noqa: E402

ZIP_TIME = (1980, 1, 1, 0, 0, 0)  # fixed timestamps keep the ZIP reproducible

README = """# Delaware Beach Finds — story archive export

Exported {date}. {count} archived stories ({nulls} published before the weekly issue
system existed, so their issueId is null — that is historical fact, not missing data).

This is a PRIVATE owner export. Do not commit it or publish it.

## Layout

- `story-archive.json` — the archival ledger (copy of data/story-archive.json). One
  entry per archived story: slug, headline, original publishedAt/date, issueId,
  publicationWeek (ISO week of the publication date), category, author desk,
  canonical URL, source prose and rendered page paths, sourceProseSHA256,
  archiveState, archivedAt, premiumEligible, currentAccessLevel, originalSources,
  imageProvenance, wordCount and revisions. It contains no prose.
- `prose/<slug>.html` — canonical prose (content/stories/<slug>.html in the repo).
  Its sha256 equals the ledger's sourceProseSHA256 (or the latest revision's sha256).
- `rendered/<slug>.html` — the public page as rendered at export time.
- `metadata/<slug>.json` — the full data/stories.json record, minus the inline
  `body` (the prose is in prose/).
- `issue-history.json` — each issue an archived story appeared in, with the
  registry entry and the archived slugs in it; `noIssue` lists the stories with
  issueId=null.
- `issues/<issueId>.json` — the full issue documents referenced above.
- `SHA256SUMS.txt` — sha256 of every other file here. Verify with
  `sha256sum -c SHA256SUMS.txt`.

## Rules the ledger follows

Entries are never removed. publishedAt, date and issueId are frozen. A change to
archived prose is only accepted with a revision record (see `revisions`).
"""


def export(repo=REPO, date=None, out_dir=None):
    """Write the ZIP; return (path, summary dict)."""
    date = date or datetime.date.today().strftime('%Y%m%d')
    ledger, changes = build(repo)  # raises ArchiveError on any integrity breach
    ledger_path = os.path.join(repo, LEDGER)
    on_disk = open(ledger_path, encoding='utf-8').read() if os.path.exists(ledger_path) else None
    if on_disk != serialize(ledger):
        raise ArchiveError('data/story-archive.json is stale (%s); run scripts/build_story_archive.py first'
                           % ('; '.join(changes) or 'formatting differs'))
    stories = {s['slug']: s for s in json.load(open(os.path.join(repo, 'data/stories.json'), encoding='utf-8'))}
    registry = json.load(open(os.path.join(repo, 'data/issues/index.json'), encoding='utf-8'))
    reg_issues = {i['issueId']: i for i in registry.get('issues', [])}

    files = {}  # zip path -> bytes
    files['story-archive.json'] = on_disk.encode('utf-8')
    history = {'issues': {}, 'noIssue': []}
    for e in ledger['stories']:
        slug = e['slug']
        prose = open(os.path.join(repo, e['sourceProsePath']), 'rb').read()
        if hashlib.sha256(prose).hexdigest() != e['sourceProseSHA256']:
            raise ArchiveError('%s: prose does not match its ledger checksum' % slug)
        files['prose/%s.html' % slug] = prose
        rendered = os.path.join(repo, e['renderedPagePath'])
        if os.path.exists(rendered):
            files['rendered/%s.html' % slug] = open(rendered, 'rb').read()
        rec = stories.get(slug)
        if rec is not None:
            meta = {k: v for k, v in rec.items() if k != 'body'}
            files['metadata/%s.json' % slug] = (json.dumps(meta, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
        if e['issueId'] is None:
            history['noIssue'].append({'slug': slug, 'date': e['date'], 'publicationWeek': e['publicationWeek']})
        else:
            h = history['issues'].setdefault(e['issueId'], {'registryEntry': reg_issues.get(e['issueId']), 'stories': []})
            h['stories'].append(slug)
            doc = os.path.join(repo, 'data/issues/%s.json' % e['issueId'])
            if os.path.exists(doc):
                files['issues/%s.json' % e['issueId']] = open(doc, 'rb').read()
    files['issue-history.json'] = (json.dumps(history, indent=2, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8')
    files['README.md'] = README.format(date=date, count=ledger['storyCount'],
                                       nulls=ledger['legacyNullIssueCount']).encode('utf-8')
    sums = ''.join('%s  %s\n' % (hashlib.sha256(files[p]).hexdigest(), p) for p in sorted(files))
    files['SHA256SUMS.txt'] = sums.encode('utf-8')

    out_dir = out_dir or os.path.join(repo, 'private-exports')
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, 'dbf-story-archive-%s.zip' % date)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(files):
            info = zipfile.ZipInfo(p, ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, files[p])
    with open(path, 'wb') as f:
        f.write(buf.getvalue())
    summary = {
        'path': path,
        'fileCount': len(files),
        'archivedStories': ledger['storyCount'],
        'checksumCount': sums.count('\n'),
        'proseFiles': sum(1 for p in files if p.startswith('prose/')),
        'renderedPages': sum(1 for p in files if p.startswith('rendered/')),
        'zipSHA256': sha256_file(path),
    }
    return path, summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--date', help='YYYYMMDD for the file name (default: today)')
    ap.add_argument('--out-dir', help='output directory (default: private-exports/)')
    args = ap.parse_args(argv)
    try:
        path, s = export(REPO, args.date, args.out_dir)
    except ArchiveError as exc:
        print('EXPORT REFUSED:\n' + str(exc), file=sys.stderr)
        return 1
    print('Archive export: %s' % os.path.relpath(path, REPO))
    print('  files in ZIP:      %d' % s['fileCount'])
    print('  archived stories:  %d (prose %d, rendered %d)' % (s['archivedStories'], s['proseFiles'], s['renderedPages']))
    print('  SHA256SUMS lines:  %d' % s['checksumCount'])
    print('  ZIP sha256:        %s' % s['zipSHA256'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
