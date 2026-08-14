#!/usr/bin/env python3
"""End-to-end proof of scheduled publication.

Runs the EXACT step sequence of .github/workflows/publish-scheduled.yml against
a throwaway sandbox copy of the repo, at controlled points in time. Production
data is never touched and the sandbox is deleted at the end.

What this proves:
  * the workflow's decision logic, step by step, including the CI gate
  * that nothing publishes early, held, unapproved, or twice
  * that an idle run produces NO commit (the timestamp-churn trap)

What this cannot prove on its own:
  * that GitHub's cron scheduler fires. That is GitHub's job and can only be
    observed after the workflow file exists in .github/workflows/ on a pushed
    branch. See the RUN ON GITHUB section printed at the end.

Usage: python3 scripts/prove_scheduled_publication.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

FIXTURE_SLUG = 'zz-test-fixture-do-not-publish'
PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print('   %s  %s%s' % ('ok  ' if cond else 'FAIL', name,
                           '' if cond else '\n          >>> %s' % detail))


class Repo:
    """A sandbox repo that can run the workflow's steps."""

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix='dbf-proof-')
        subprocess.run(['git', 'init', '-q', self.dir], check=True)
        for item in ('data', 'scripts', 'templates', 'content', 'stories',
                     'assets', 'admin', 'automation', 'towns', '.github'):
            src = os.path.join(REPO, item)
            if os.path.exists(src):
                shutil.copytree(src, os.path.join(self.dir, item))
        for f in os.listdir(REPO):
            if f.endswith('.html') or f in ('CNAME', 'feed.xml', 'sitemap.xml',
                                            'robots.txt', 'site.webmanifest'):
                p = os.path.join(REPO, f)
                if os.path.isfile(p):
                    shutil.copy(p, self.dir)
        self.git('add', '-A')
        self.git('-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-qm', 'base')
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.dir, ignore_errors=True)

    def git(self, *args):
        return subprocess.run(['git'] + list(args), cwd=self.dir,
                              capture_output=True, text=True)

    def read(self, *parts):
        with open(os.path.join(self.dir, *parts), encoding='utf-8') as fh:
            return json.load(fh)

    def write(self, obj, *parts):
        with open(os.path.join(self.dir, *parts), 'w', encoding='utf-8') as fh:
            json.dump(obj, fh, indent=2, ensure_ascii=False)

    # -- the workflow's steps, in order ------------------------------------
    def workflow_run(self, now, dry_run=False):
        """Mirror publish-scheduled.yml. Returns (outputs, committed)."""
        out = {'count': '0', 'published': ''}
        env = dict(os.environ)
        gho = os.path.join(tempfile.gettempdir(), 'dbf-gho-%d' % os.getpid())
        open(gho, 'w').close()
        env['GITHUB_OUTPUT'] = gho

        def run(*cmd):
            return subprocess.run(cmd, cwd=self.dir, capture_output=True,
                                  text=True, env=env)

        # step: Validate editorial data
        r = run(sys.executable, 'scripts/validate_editorial.py')
        if r.returncode != 0:
            return out, False, 'validation failed: %s' % r.stdout

        # step: Report what is due
        run(sys.executable, 'scripts/publish_due.py', '--dry-run', '--now', now)

        if dry_run:
            return out, False, ''

        # step: Publish due stories  (id: publish)
        r = run(sys.executable, 'scripts/publish_due.py', '--now', now)
        for line in open(gho, encoding='utf-8'):
            if '=' in line:
                k, v = line.strip().split('=', 1)
                out[k] = v

        # step: Run full test suite   (if count != '0')
        if out['count'] != '0':
            t = run('bash', 'scripts/run_tests.sh')
            if t.returncode != 0:
                return out, False, 'test suite failed, commit blocked'

        # step: Commit publication output  (if count != '0')
        committed = False
        if out['count'] != '0':
            self.git('add', 'data/stories.json', 'data/issues',
                     'data/content-index.json', 'stories')
            staged = self.git('diff', '--cached', '--name-only').stdout.strip()
            if staged:
                self.git('-c', 'user.email=b@b', '-c', 'user.name=bot',
                         'commit', '-qm', 'Publish: %s' % out['published'])
                committed = True
        return out, committed, ''

    def dirty(self):
        return bool(self.git('status', '--porcelain').stdout.strip())

    def commits(self):
        return len(self.git('log', '--oneline').stdout.strip().splitlines())


def add_fixture(sb, **over):
    stories = sb.read('data', 'stories.json')
    rec = {k: None for k in stories[0]}
    rec.update({
        'slug': FIXTURE_SLUG,
        'headline': 'TEST FIXTURE — Scheduled Publication Proof',
        'kicker': 'Test Fixture',
        'hook': 'Non-production test fixture. Not a Delaware news story.',
        'lede': 'Non-production test fixture used to prove the scheduled '
                'publisher. It reports nothing about Delaware.',
        'category': 'coast', 'author': 'coast-nature',
        'readTime': '1 min read', 'status': 'draft',
        'sources': ['Not applicable — synthetic test fixture.'],
        'etsyProductIds': [], 'relatedStories': [], 'body': [],
        'access_level': 'public', 'renderMode': 'generated',
        'seriesPage': False, 'shopTheStory': False, 'series': None,
        'featured': False, 'coverStory': False, 'placement': 'standard',
    })
    rec.update(over)
    stories.append(rec)
    sb.write(stories, 'data', 'stories.json')
    with open(os.path.join(sb.dir, 'content', 'stories', '%s.html' % FIXTURE_SLUG),
              'w', encoding='utf-8') as fh:
        fh.write('<p>Synthetic test fixture. Not editorial content.</p>\n')
    sb.git('add', '-A')
    sb.git('-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-qm', 'fixture')


def by_slug(sb):
    return {s['slug']: s for s in sb.read('data', 'stories.json')}


def main():
    print('=' * 72)
    print('PROOF: scheduled publication, running the workflow\'s own steps')
    print('=' * 72)

    # ---------------------------------------------------------------- A / B / C
    print('\nA-C. Approved future cover story\n')
    with Repo() as sb:
        old_cover = next(s['slug'] for s in sb.read('data', 'stories.json')
                         if s.get('coverStory'))
        add_fixture(sb, status='scheduled', approvedAt='2026-08-14',
                    publishAt='2026-09-07T06:00', placement='cover')
        base_commits = sb.commits()

        # --- A: three days early ------------------------------------------
        out, committed, err = sb.workflow_run('2026-09-04T06:00')
        s = by_slug(sb)
        check('A. future story does NOT publish early',
              s[FIXTURE_SLUG]['status'] == 'scheduled', err)
        check('A. workflow reports count=0', out['count'] == '0')
        check('A. no commit is made on an idle run', not committed)
        check('A. repo is left clean (no timestamp churn)', not sb.dirty(),
              sb.git('status', '--porcelain').stdout)
        check('A. incumbent cover untouched', s[old_cover]['coverStory'] is True)

        # --- B: due --------------------------------------------------------
        out, committed, err = sb.workflow_run('2026-09-07T06:00')
        s = by_slug(sb)
        f = s[FIXTURE_SLUG]
        check('B. workflow detects the due story without manual invocation',
              out['count'] == '1' and out['published'] == FIXTURE_SLUG,
              'outputs=%s %s' % (out, err))
        check('C. status becomes published', f['status'] == 'published')
        check('C. intended placement applied (cover)', f['coverStory'] is True)
        check('C. previous cover PRESERVED as published',
              s[old_cover]['status'] == 'published'
              and s[old_cover]['coverStory'] is False)
        check('C. issue membership updated', f['issueId'] == '2026-W37',
              'got %s' % f['issueId'])
        idx = sb.read('data', 'issues', 'index.json')
        check('C. issue index rolled', idx['currentIssueId'] == '2026-W37')
        check('C. previous issue archived, file retained',
              any(i['status'] == 'archived' and i.get('file') for i in idx['issues']))
        ci = sb.read('data', 'content-index.json')
        ids = {r['id'] for r in ci['records']}
        check('C. archive/search index contains the new story',
              any(FIXTURE_SLUG in str(i) for i in ids), sorted(ids)[:3])
        page = os.path.join(sb.dir, 'stories', '%s.html' % FIXTURE_SLUG)
        check('C. static SEO output generated', os.path.exists(page))
        if os.path.exists(page):
            html = open(page, encoding='utf-8').read()
            check('C. canonical + OG + Article JSON-LD present',
                  'rel="canonical"' in html and 'og:title' in html
                  and '"@type": "Article"' in html)
            check('C. category surface reachable from the story',
                  'category-coast.html' in html)
        check('C. validation + full suite ran before commit', committed, err)
        check('C. exactly one publication commit', sb.commits() == base_commits + 1,
              'commits=%d base=%d' % (sb.commits(), base_commits))

        # --- idempotence ---------------------------------------------------
        after = json.dumps(sb.read('data', 'stories.json'), sort_keys=True)
        n = sb.commits()
        out2, committed2, _ = sb.workflow_run('2026-09-07T07:00')
        out3, committed3, _ = sb.workflow_run('2026-09-08T06:00')
        check('C. next run publishes nothing (idempotent)',
              out2['count'] == '0' and out3['count'] == '0')
        check('C. no duplicate commit on subsequent runs',
              not committed2 and not committed3 and sb.commits() == n)
        check('C. registry unchanged by replay',
              json.dumps(sb.read('data', 'stories.json'), sort_keys=True) == after)

    # ---------------------------------------------------------------------- D
    print('\nD. Held story\n')
    with Repo() as sb:
        add_fixture(sb, status='held', approvedAt='2026-08-14',
                    publishAt='2026-09-07T06:00', placement='cover',
                    heldReason='Proof: held must never publish')
        out, committed, _ = sb.workflow_run('2026-09-07T06:00')
        check('D. held story does not publish when due',
              by_slug(sb)[FIXTURE_SLUG]['status'] == 'held')
        check('D. workflow makes no commit for a held story',
              out['count'] == '0' and not committed)

    print('\nD2. Unapproved story (no approvedAt)\n')
    with Repo() as sb:
        add_fixture(sb, status='scheduled', approvedAt=None,
                    publishAt='2026-09-07T06:00', placement='cover')
        # validate_editorial refuses this state outright, which is the point:
        # the workflow's first step fails and nothing downstream runs.
        r = subprocess.run([sys.executable, 'scripts/validate_editorial.py'],
                           cwd=sb.dir, capture_output=True, text=True)
        check('D2. scheduled-without-approval fails validation, blocking the run',
              r.returncode != 0, r.stdout)

    # ---------------------------------------------------------------------- E
    print('\nE. Cadence change is configuration, not code\n')
    with Repo() as sb:
        code_before = {}
        for root, _d, files in os.walk(os.path.join(sb.dir, 'scripts')):
            for f in files:
                if f.endswith('.py'):
                    p = os.path.join(root, f)
                    code_before[f] = open(p, encoding='utf-8').read()

        cal = sb.read('data', 'editorial-calendar.json')
        for slot in cal['cadence']:
            if slot['placement'] == 'cover':
                slot['weekday'] = 1          # Monday -> Tuesday
                slot['time'] = '07:30'
        cal['blackouts'] = [{'start': '2026-12-21', 'end': '2026-12-27',
                             'reason': 'Christmas week'}]
        sb.write(cal, 'data', 'editorial-calendar.json')

        sys.path.insert(0, os.path.join(sb.dir, 'scripts'))
        for mod in ('editorial_lib',):
            sys.modules.pop(mod, None)
        import editorial_lib as el
        nxt = el.next_slot_datetime('cover', cal,
                                    after=el.parse_publish_at('2026-08-14T09:00'))
        check('E. cover day moved to Tuesday by config alone', nxt.weekday() == 1,
              'weekday=%s' % nxt.weekday())
        check('E. cover time moved to 07:30 by config alone',
              (nxt.hour, nxt.minute) == (7, 30))
        check('E. blackout honoured from config alone',
              el.is_blackout(el.parse_publish_at('2026-12-24'), cal))

        code_after = {}
        for root, _d, files in os.walk(os.path.join(sb.dir, 'scripts')):
            for f in files:
                if f.endswith('.py'):
                    code_after[f] = open(os.path.join(root, f), encoding='utf-8').read()
        check('E. zero application code changed to achieve it',
              code_before == code_after,
              'changed: %s' % [k for k in code_before if code_before[k] != code_after.get(k)])
        sys.path.pop(0)

    print('\n' + '=' * 72)
    print('Passed: %d   Failed: %d' % (len(PASS), len(FAIL)))
    print('=' * 72)
    print("""
RUN ON GITHUB (only after the workflow file exists on a pushed branch):

  1. Actions -> "Publish scheduled stories" -> Run workflow
     with dry_run = true. Confirms the runner, Python and validation.
  2. Schedule a real story a few minutes out, then wait for the hourly cron
     and confirm the run publishes it and commits.

GitHub's cron firing is the one part of this that cannot be proven from here.
""")
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
