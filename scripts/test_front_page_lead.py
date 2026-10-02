#!/usr/bin/env python3
"""Regression test: the homepage lead belongs to the current issue.

The front page picked `stories.find(s => s.featured) || newest`. The Sept. 7
cover kept featured=true, so it led the homepage under W39 and W40 as though
it were still this week's cover. The selector (selectFrontPage in
assets/js/site.js) is exercised here directly in Node, against fixtures and
against the real data, and freshness_report.check_current_cover is checked
for the same failure.

Usage: python3 scripts/test_front_page_lead.py
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from freshness_report import check_current_cover  # noqa: E402

passed = failed = 0


def check(desc, ok, detail=""):
    global passed, failed
    if ok:
        print(f"  ok  - {desc}")
        passed += 1
    else:
        print(f"FAIL  - {desc}")
        if detail:
            print("        " + str(detail))
        failed += 1


SITE_JS = open(os.path.join(ROOT, "assets", "js", "site.js"), encoding="utf-8").read()
m = re.search(r"// <front-page-select>.*?// </front-page-select>", SITE_JS, re.S)
check("site.js defines the marked selectFrontPage block", m is not None)
if not m:
    print(f"\nPassed: {passed}   Failed: {failed}")
    sys.exit(1)
SELECTOR = m.group(0)


# Fixtures are judged at a fixed moment so the suite never depends on the clock.
FIXTURE_NOW = "2026-10-03T12:00:00-04:00"


def select(stories, registry, now=FIXTURE_NOW):
    """Run the real selectFrontPage from site.js in Node, at `now` (None = real clock)."""
    script = SELECTOR + "\nconst a=JSON.parse(require('fs').readFileSync(0,'utf8'));" \
        "const r=selectFrontPage(a.stories,a.registry,a.now?Date.parse(a.now):undefined);" \
        "console.log(JSON.stringify({mode:r.mode,reason:r.reason||null,issue:r.issue&&r.issue.issueId," \
        "cover:r.cover&&r.cover.slug,thisWeek:r.thisWeek.map(s=>s.slug),archive:r.archive.map(s=>s.slug)}));"
    out = subprocess.run(["node", "-e", script], input=json.dumps({"stories": stories, "registry": registry, "now": now}),
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def story(slug, issue, date, **kw):
    s = {"slug": slug, "issueId": issue, "date": date, "status": "published",
         "featured": False, "coverStory": False}
    s.update(kw)
    return s


REG = {"currentIssueId": "W40", "issues": [
    {"issueId": "W37", "status": "archived", "weekOf": "2026-09-07"},
    {"issueId": "W40", "status": "current", "weekOf": "2026-09-28", "title": "Week of September 28, 2026",
     "summary": "Current summary."}]}
OLD_COVER = story("old-cover", "W37", "2026-09-07", featured=True, coverStory=True)

# 1. Current issue has a cover -> that cover leads.
r = select([OLD_COVER, story("new-cover", "W40", "2026-10-02", featured=True, coverStory=True),
            story("new-second", "W40", "2026-10-02")], REG)
check("current issue's cover renders as the lead", r["mode"] == "story" and r["cover"] == "new-cover", r)
check("other current-issue stories head the secondary stack", r["thisWeek"] == ["new-second"], r)
check("older stories are offered only as archive", r["archive"] == ["old-cover"], r)

# 2. Current issue has stories but none marked cover -> newest current story leads.
r = select([OLD_COVER, story("cur-older", "W40", "2026-09-29"), story("cur-newest", "W40", "2026-10-01")], REG)
check("no cover in current issue -> newest current story leads",
      r["mode"] == "story" and r["cover"] == "cur-newest", r)

# 3. Current issue has zero published stories -> issue lead, never an old cover.
r = select([OLD_COVER, story("draft-cur", "W40", "2026-10-02", status="scheduled")], REG)
check("no current stories -> current issue lead renders", r["mode"] == "issue" and r["issue"] == "W40", r)
check("no current stories -> old cover is not the lead", r["cover"] is None, r)
check("no current stories -> nothing is presented as 'this week'", r["thisWeek"] == [], r)

# 4. An archived issue's featured story can never become the current cover.
r = select([OLD_COVER, story("cur-plain", "W40", "2026-10-01")], REG)
check("archived issue's featured story never becomes the current cover",
      r["cover"] == "cur-plain" and "old-cover" not in r["thisWeek"], r)
r = select([story("newer-but-old-issue", "W37", "2026-10-05", featured=True)], REG)
check("a featured story from another issue is not the cover even when newest", r["mode"] == "issue", r)

# 6. Display failsafe: no new story for more than 72h -> "This Week" issue lead,
#    even though the current issue's cover is still flagged. Never a stale cover.
fresh = [OLD_COVER, story("new-cover", "W40", "2026-09-28", featured=True, coverStory=True,
                           publishAt="2026-09-28T06:00", publishedAt="2026-09-28")]
r = select(fresh, REG, now="2026-09-30T06:00:00-04:00")
check("story 48h old: the current cover still leads", r["mode"] == "story" and r["cover"] == "new-cover", r)
r = select(fresh, REG, now="2026-10-01T07:00:00-04:00")
check("autopilot stalled >72h: homepage switches to the This Week issue lead",
      r["mode"] == "issue" and r["reason"] == "stale" and r["cover"] is None, r)
check("stalled: older stories stay below as recent reading, not as 'this week'",
      r["thisWeek"] == [] and "new-cover" in r["archive"], r)
check("stalled lead is titled This Week at the Delaware Coast",
      "This Week at the Delaware Coast" in SITE_JS)
policy = json.load(open(os.path.join(ROOT, "data", "editorial-autopilot.json"), encoding="utf-8"))
check("site.js stale threshold matches the autopilot policy",
      f"FRONT_STALE_HOURS = {policy['homepageStaleAfterHours']};" in SITE_JS)

# 5. Registry unavailable -> newest story, labelled latest rather than cover.
r = select([OLD_COVER, story("cur-newest", "W40", "2026-10-02")], None)
check("no registry -> mode 'none' (rendered as Latest Story, not Cover Story)",
      r["mode"] == "none" and r["cover"] == "cur-newest", r)
check("front page labels mode 'none' as Latest Story", "'Cover Story':'Latest Story'" in SITE_JS)

# The renderers use the selector and the registry.
front = SITE_JS[SITE_JS.find("const frontMount"):SITE_JS.find("const frontMount") + 1400]
check("front page reads issues/index.json", "fetchJson('issues/index.json')" in front)
check("front page uses selectFrontPage", "selectFrontPage(list, registry)" in front)
check("the featured-or-newest cover selection is gone", "pub.find(s=>s.featured) || pub[0]" not in SITE_JS)
pic = SITE_JS[SITE_JS.find("const pictureMount"):SITE_JS.find("const pictureMount") + 1400]
check("picture feature excludes what the lead package shows", "selectFrontPage(list, registry)" in pic)

# freshness_report detects cover / current-issue mismatch.
w, lead = check_current_cover([OLD_COVER], REG)
check("freshness report flags cover flags left on an archived issue's story",
      any("old-cover" in x and "W37" in x for x in w), w)
check("freshness report flags a current issue with no published stories",
      any("no published stories" in x for x in w), w)
w, lead = check_current_cover([story("cur", "W40", "2026-10-01")], REG)
check("freshness report flags a current issue with stories but no cover", any("none is marked coverStory" in x for x in w), w)
w, lead = check_current_cover([story("stale", "W40", "2026-09-20", coverStory=True, featured=True)], REG)
check("freshness report flags a cover dated before the current issue's week", any("before the current issue" in x for x in w), w)
w, lead = check_current_cover([OLD_COVER | {"featured": False, "coverStory": False},
                               story("new-cover", "W40", "2026-10-02", coverStory=True, featured=True)], REG)
check("freshness report is clean for a current, in-issue cover", w == [] and lead == "new-cover", w)

# The real data.
stories = json.load(open(os.path.join(ROOT, "data", "stories.json"), encoding="utf-8"))
registry = json.load(open(os.path.join(ROOT, "data", "issues", "index.json"), encoding="utf-8"))
# These hold whatever the date: the hourly publisher runs this suite before it
# commits, so a live check here must be an invariant the publisher maintains,
# never a freshness judgement (that belongs to scripts/runway_guard.py).
r = select(stories, registry, now=None)
by_slug = {s["slug"]: s for s in stories}
check("live data: the lead is never a story from another issue",
      r["mode"] != "story" or by_slug[r["cover"]].get("issueId") == registry["currentIssueId"], r)
check("live data: 'Also This Week' holds only current-issue stories",
      all(by_slug[x].get("issueId") == registry["currentIssueId"] for x in r["thisWeek"]), r)
covers = [s["slug"] for s in stories if s.get("status") == "published" and (s.get("coverStory") or s.get("featured"))]
check("live data: exactly one published story carries cover flags", len(covers) == 1, covers)

print()
print("================================")
print(f"Passed: {passed}   Failed: {failed}")
sys.exit(1 if failed else 0)
