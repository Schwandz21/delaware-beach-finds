#!/usr/bin/env python3
"""Tests for the story archive: ledger preservation, checksums, the private
export, the premium-access safety gate, and the archive page's view model.

Live checks assert invariants of the committed data. Everything that writes
runs against a throwaway copy, so production files are never touched.
"""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from build_story_archive import ArchiveError, build, serialize  # noqa: E402
from export_story_archive import export  # noqa: E402
from premium_archive import DEFAULT, load_config, premium_violations, public_exposures  # noqa: E402

passed = failed = 0


def check(desc, ok, detail=""):
    global passed, failed
    if ok:
        print(f"  ok  - {desc}")
        passed += 1
    else:
        print(f"FAIL  - {desc}")
        if detail:
            print("        " + str(detail)[:600])
        failed += 1


def jload(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def text_of(html):
    import re
    return ' '.join(re.sub(r'<[^>]+>', ' ', html).split())


LEDGER = jload(os.path.join(REPO, 'data/story-archive.json'))
STORIES = jload(os.path.join(REPO, 'data/stories.json'))
REGISTRY = jload(os.path.join(REPO, 'data/issues/index.json'))
CURRENT = REGISTRY['currentIssueId']
RECORDS = {s['slug']: s for s in STORIES}
ENTRIES = {e['slug']: e for e in LEDGER['stories']}
REQUIRED = ['slug', 'headline', 'publishedAt', 'date', 'issueId', 'publicationWeek', 'category', 'author',
            'canonicalUrl', 'sourceProsePath', 'renderedPagePath', 'sourceProseSHA256', 'archiveState',
            'archivedAt', 'premiumEligible', 'currentAccessLevel', 'originalSources', 'imageProvenance',
            'wordCount', 'revisions']

print("\n=== Archive ledger (committed data) ===")
try:
    fresh, changes = build(REPO)
    check("ledger is up to date with the registry (build --check)",
          serialize(fresh) == open(os.path.join(REPO, 'data/story-archive.json'), encoding='utf-8').read(), changes)
except ArchiveError as exc:
    check("ledger is up to date with the registry (build --check)", False, exc)

should = {s['slug'] for s in STORIES if s.get('status') == 'published' and s.get('issueId') != CURRENT}
check("every published story outside the current issue is archived", should <= set(ENTRIES), should - set(ENTRIES))
check("no current-issue story is in the archive",
      not [s for s in ENTRIES if (RECORDS.get(s) or {}).get('issueId') == CURRENT and s not in should])
check("storyCount matches the entries", LEDGER['storyCount'] == len(LEDGER['stories']))
missing = [(e['slug'], k) for e in LEDGER['stories'] for k in REQUIRED if k not in e]
check("every entry carries every required field", not missing, missing)
check("every entry is archived and premium-eligible",
      all(e['archiveState'] == 'archived' and e['premiumEligible'] is True for e in LEDGER['stories']))
nulls = [e['slug'] for e in LEDGER['stories'] if e['issueId'] is None]
check("legacy stories keep issueId=null (none fabricated)",
      all(RECORDS[s].get('issueId') is None for s in nulls if s in RECORDS)
      and LEDGER['legacyNullIssueCount'] == len(nulls), nulls)
check("publicationWeek is derived from the date, not the issue",
      all(e['publicationWeek'].startswith(e['date'][:4]) for e in LEDGER['stories']))

drift = []
for e in LEDGER['stories']:
    prose = os.path.join(REPO, e['sourceProsePath'])
    if not os.path.exists(prose):
        drift.append('%s: prose file vanished' % e['slug'])
        continue
    expected = e['revisions'][-1]['sha256'] if e['revisions'] else e['sourceProseSHA256']
    if sha(prose) != expected or e['sourceProseSHA256'] != expected:
        drift.append('%s: prose checksum changed without a revision record' % e['slug'])
    rec = RECORDS.get(e['slug'])
    if rec and (rec.get('date') or '')[:10] != e['date']:
        drift.append('%s: publication date changed (%s -> %s)' % (e['slug'], e['date'], rec.get('date')))
check("every archived prose file exists and matches its checksum or latest revision", not drift, drift)

raw = open(os.path.join(REPO, 'data/story-archive.json'), encoding='utf-8').read()
leaks = []
for e in LEDGER['stories']:
    body = text_of(open(os.path.join(REPO, e['sourceProsePath']), encoding='utf-8').read())
    para = body[len(body) // 2: len(body) // 2 + 160]
    if 'body' in e or (para and para in raw):
        leaks.append(e['slug'])
check("the ledger contains no article prose", not leaks and len(raw) < 4000 * max(1, len(ENTRIES)), leaks)

# Append-only against the last committed ledger.
try:
    prev = subprocess.run(['git', 'show', 'HEAD:data/story-archive.json'], cwd=REPO,
                          capture_output=True, text=True)
    if prev.returncode == 0:
        old = {e['slug']: e for e in json.loads(prev.stdout)['stories']}
        lost = sorted(set(old) - set(ENTRIES))
        moved = [s for s in old if s in ENTRIES and (old[s]['date'], old[s]['publishedAt'], old[s]['issueId'])
                 != (ENTRIES[s]['date'], ENTRIES[s]['publishedAt'], ENTRIES[s]['issueId'])]
        silent = [s for s in old if s in ENTRIES and old[s]['sourceProseSHA256'] != ENTRIES[s]['sourceProseSHA256']
                  and len(ENTRIES[s]['revisions']) <= len(old[s].get('revisions', []))]
        check("no previously archived slug has disappeared since HEAD", not lost, lost)
        check("no archived publication date or issue has changed since HEAD", not moved, moved)
        check("no archived checksum changed since HEAD without a new revision", not silent, silent)
    else:
        check("ledger has no committed predecessor yet (first build)", True)
except FileNotFoundError:
    check("git unavailable; HEAD comparison skipped", True)


print("\n=== Archive builder rules (sandbox) ===")


class Sandbox:
    def __enter__(self):
        self.root = tempfile.mkdtemp(prefix='dbf-archive-')
        for d in ('data', 'content/stories', 'stories'):
            shutil.copytree(os.path.join(REPO, d), os.path.join(self.root, d))
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.root, ignore_errors=True)

    def p(self, rel):
        return os.path.join(self.root, rel)

    def stories(self):
        return jload(self.p('data/stories.json'))

    def save_stories(self, st):
        json.dump(st, open(self.p('data/stories.json'), 'w', encoding='utf-8'), indent=2)

    def write_ledger(self, ledger):
        open(self.p('data/story-archive.json'), 'w', encoding='utf-8').write(serialize(ledger))

    def build(self, **kw):
        return build(self.p(''), today='2031-01-01', **kw)


def raises(fn, needle):
    try:
        fn()
    except ArchiveError as exc:
        return needle in str(exc)
    return False


one = sorted(ENTRIES)[0]
legacy = next(e['slug'] for e in LEDGER['stories'] if e['issueId'] is None)

with Sandbox() as sb:
    led, ch = sb.build()
    check("rebuilding unchanged inputs is a no-op (idempotent)", not ch and serialize(led) == raw, ch)
    led2, _ = sb.build()
    check("two rebuilds are byte-identical (deterministic)", serialize(led) == serialize(led2))

    st = [s for s in sb.stories() if s['slug'] != one]
    sb.save_stories(st)
    led, _ = sb.build()
    check("an archived story whose registry record disappears stays in the ledger",
          one in {e['slug'] for e in led['stories']} and led['storyCount'] == LEDGER['storyCount'])

with Sandbox() as sb:
    st = sb.stories()
    next(s for s in st if s['slug'] == one)['date'] = '2031-01-01'
    sb.save_stories(st)
    check("changing an archived story's publication date is refused", raises(sb.build, 'date changed'))

with Sandbox() as sb:
    st = sb.stories()
    next(s for s in st if s['slug'] == legacy)['issueId'] = '2026-W34'
    sb.save_stories(st)
    check("back-filling an issue onto a legacy issueId=null story is refused", raises(sb.build, 'issueId changed'))

with Sandbox() as sb:
    path = sb.p(ENTRIES[one]['sourceProsePath'])
    open(path, 'a', encoding='utf-8').write('\n<p>An unrecorded edit.</p>\n')
    check("changing archived prose without a revision record is refused", raises(sb.build, 'no revision record'))
    led, ch = sb.build(revise=one, reason='Corrected a date in paragraph two')
    e = next(x for x in led['stories'] if x['slug'] == one)
    check("a recorded revision is accepted and keeps the original checksum",
          e['sourceProseSHA256'] == sha(path) and e['revisions'][-1]['previousSHA256'] == ENTRIES[one]['sourceProseSHA256']
          and e['revisions'][-1]['reason'] and e['date'] == ENTRIES[one]['date'], e.get('revisions'))
    sb.write_ledger(led)
    led2, ch2 = sb.build()
    check("after a revision the ledger is stable again", not ch2, ch2)

with Sandbox() as sb:
    os.remove(sb.p(ENTRIES[one]['sourceProsePath']))
    check("an archived story whose prose file vanishes is an error", raises(sb.build, 'vanished'))

with Sandbox() as sb:
    # The issue rolls: the current issue's stories become archive.
    reg = jload(sb.p('data/issues/index.json'))
    reg['currentIssueId'] = '2031-W01'
    for i in reg['issues']:
        if i['issueId'] == CURRENT:
            i['status'], i['supersededAt'] = 'archived', '2031-01-05'
    json.dump(reg, open(sb.p('data/issues/index.json'), 'w'), indent=2)
    led, ch = sb.build()
    rolled = {e['slug']: e for e in led['stories']}
    cur = [s['slug'] for s in STORIES if s.get('status') == 'published' and s.get('issueId') == CURRENT]
    check("when an issue rolls, its stories join the archive with the supersede date",
          all(rolled.get(s, {}).get('archivedAt') == '2031-01-05' for s in cur) and set(ENTRIES) <= set(rolled), ch)
    check("rolling never removes an older entry", led['storyCount'] == LEDGER['storyCount'] + len(cur))


print("\n=== Private archive export ===")
check(".gitignore excludes private-exports/",
      'private-exports/' in open(os.path.join(REPO, '.gitignore')).read().split())
tracked = subprocess.run(['git', 'ls-files', 'private-exports'], cwd=REPO, capture_output=True, text=True).stdout.strip()
check("no private export is committed", tracked == '', tracked)

out = tempfile.mkdtemp(prefix='dbf-export-')
try:
    path, summary = export(REPO, '20310101', out)
    z = zipfile.ZipFile(path)
    names = set(z.namelist())
    n = LEDGER['storyCount']
    check("export is named dbf-story-archive-YYYYMMDD.zip", os.path.basename(path) == 'dbf-story-archive-20310101.zip')
    check("export holds the ledger, README, issue history and SHA256SUMS",
          {'story-archive.json', 'README.md', 'issue-history.json', 'SHA256SUMS.txt'} <= names)
    check("export holds every archived story's prose, rendered page and metadata",
          all({'prose/%s.html' % s, 'rendered/%s.html' % s, 'metadata/%s.json' % s} <= names for s in ENTRIES), n)
    sums = [l.split('  ', 1) for l in z.read('SHA256SUMS.txt').decode().splitlines()]
    bad = [p for h, p in sums if hashlib.sha256(z.read(p)).hexdigest() != h]
    check("SHA256SUMS covers every other file and every checksum verifies",
          not bad and {p for _, p in sums} == names - {'SHA256SUMS.txt'}, bad)
    check("exported prose matches the ledger checksums",
          all(hashlib.sha256(z.read('prose/%s.html' % s)).hexdigest() == e['sourceProseSHA256'] for s, e in ENTRIES.items()))
    check("exported metadata carries no inline body",
          all('body' not in json.loads(z.read('metadata/%s.json' % s)) for s in ENTRIES if s in RECORDS))
    hist = json.loads(z.read('issue-history.json'))
    check("issue history lists legacy stories under noIssue",
          {x['slug'] for x in hist['noIssue']} == set(nulls))
    path2, _ = export(REPO, '20310101', out)
    check("export is reproducible (byte-identical on re-run)", sha(path) == summary['zipSHA256'] == sha(path2))
finally:
    shutil.rmtree(out, ignore_errors=True)

with Sandbox() as sb:
    open(sb.p(ENTRIES[one]['sourceProsePath']), 'a').write('<p>drift</p>')
    shutil.copytree(os.path.join(REPO, 'scripts'), sb.p('scripts'))
    r = subprocess.run([sys.executable, sb.p('scripts/export_story_archive.py'), '--out-dir', sb.p('x')],
                       capture_output=True, text=True)
    check("export refuses to run when archived prose has drifted",
          r.returncode != 0 and not os.path.exists(sb.p('x')), r.stdout + r.stderr)


print("\n=== Premium access safety ===")
cfg = load_config(REPO)
check("premium archive is disabled by default with the stated reason",
      cfg.get('enabled') is False and cfg.get('reason') == DEFAULT['reason'], cfg)
check("disabled premium access raises no violation", premium_violations(cfg, REPO) == [])
check("the public full text of every archived story is detected",
      len(public_exposures(REPO)) >= 2 * len(ENTRIES))
enabled = dict(cfg, enabled=True, fullTextEndpoint='https://example.invalid/full',
               accessStateEndpoint='https://example.invalid/me')
check("enabling premium while full text is public is refused (even with a backend configured)",
      any('publicly shipped' in v for v in premium_violations(enabled, REPO)), premium_violations(enabled, REPO))
check("enabling premium with no backend is refused",
      any('fullTextEndpoint' in v for v in premium_violations(dict(cfg, enabled=True), REPO)))
with Sandbox() as sb:
    cfg_path = sb.p('data/premium-archive.json')
    json.dump(dict(cfg, enabled=True), open(cfg_path, 'w'))
    shutil.copytree(os.path.join(REPO, 'scripts'), sb.p('scripts'))
    r = subprocess.run([sys.executable, sb.p('scripts/premium_archive.py')], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    check("premium_archive.py exits non-zero when enabled while text is public", r.returncode != 0, r.stdout)
    r = subprocess.run([sys.executable, sb.p('scripts/validate_editorial.py')], capture_output=True, text=True,
                       cwd=sb.root, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    check("validate_editorial.py refuses premium enabled while text is public",
          r.returncode != 0 and 'publicly shipped' in r.stdout, r.stdout[-400:])
with Sandbox() as sb:
    # Only when the text is truly gone from the public build may it pass.
    st = sb.stories()
    for s in st:
        s.pop('body', None)
    sb.save_stories(st)
    for e in LEDGER['stories']:
        for rel in (e['sourceProsePath'], e['renderedPagePath']):
            if os.path.exists(sb.p(rel)):
                os.remove(sb.p(rel))
    check("premium can pass only once no premium full text is public and a backend is configured",
          premium_violations(enabled, sb.p('')) == [], premium_violations(enabled, sb.p('')))


print("\n=== Archive page view model (assets/js/site.js) ===")
node = shutil.which('node')
if not node:
    check("node unavailable; archive view check skipped", True)
else:
    js = r"""
const fs=require('fs');const src=fs.readFileSync(process.argv[1],'utf8');
const m=src.match(/\/\/ <story-archive-view>([\s\S]*?)\/\/ <\/story-archive-view>/);
const f=new Function(m[1]+';return buildStoryArchiveView;')();
const inp=JSON.parse(fs.readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(f(inp.ledger,inp.stories,inp.registry)));
"""
    def view(ledger, stories, registry):
        r = subprocess.run([node, '-e', js, os.path.join(REPO, 'assets/js/site.js')], capture_output=True, text=True,
                           input=json.dumps({'ledger': ledger, 'stories': stories, 'registry': registry}))
        return json.loads(r.stdout) if r.returncode == 0 else {'error': r.stderr}

    v = view(LEDGER, STORIES, REGISTRY)
    cur = {i['slug'] for i in v.get('current', [])}
    arc = {i['slug'] for i in v.get('archive', [])}
    check("every ledger story is listed as archive", set(ENTRIES) <= arc and all(i['state'] == 'archived' for i in v['archive']), v.get('error'))
    check("an archived story is never labelled current", not (cur & set(ENTRIES)))
    check("current-issue stories are listed separately as This Week",
          cur == {s['slug'] for s in STORIES if s.get('status') == 'published' and s.get('issueId') == CURRENT})
    led_less = copy.deepcopy(LEDGER)
    led_less['stories'] = led_less['stories'][1:]
    v2 = view(led_less, STORIES, REGISTRY)
    check("a published non-current story missing from the ledger still shows as archive, never dropped",
          LEDGER['stories'][0]['slug'] in {i['slug'] for i in v2.get('archive', [])})
    v3 = view({'stories': []}, STORIES, {})
    check("with no registry nothing is labelled This Week", v3.get('current') == [])
    page = open(os.path.join(REPO, 'archive.html'), encoding='utf-8').read()
    check("archive.html mounts the ledger-driven story archive", 'data-mount="story-archive"' in page)
    check("the archive page does not pretend to be paywalled",
          not any(w in page.lower() for w in ('subscribe to read', 'members only', 'paywall')))

print("\n================================")
print(f"Passed: {passed}   Failed: {failed}")
sys.exit(1 if failed else 0)
