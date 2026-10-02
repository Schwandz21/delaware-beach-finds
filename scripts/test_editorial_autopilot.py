#!/usr/bin/env python3
"""Tests for the editorial autopilot: runway SLA, package ingestion, the
72-hour failsafe, and the hand-off to the existing hourly publisher.

Pure checks run against fixtures at fixed times. Anything that writes runs the
real scripts inside a throwaway copy of the repo, so production data is never
touched and the suite never depends on today's date.
"""
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from editorial_lib import is_due, parse_publish_at  # noqa: E402
from editorial_autopilot import (  # noqa: E402
    assign_week_covers, load_policy, runway, schedule_approved, suggest_slots,
)
from ingest_story_package import eligibility_problems  # noqa: E402
from runway_guard import current_lead, guard  # noqa: E402

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


POLICY = load_policy()
T = parse_publish_at


def pub(slug, at, issue="2026-W40", **kw):
    s = {"slug": slug, "status": "published", "publishAt": at, "publishedAt": at[:10], "date": at[:10],
         "issueId": issue, "placement": "standard", "featured": False, "coverStory": False}
    s.update(kw)
    return s


def sched(slug, at, **kw):
    s = {"slug": slug, "status": "scheduled", "approvedAt": "2026-10-02", "publishAt": at,
         "placement": "standard", "headline": slug}
    s.update(kw)
    return s


def codes(r):
    return {v["code"] for v in r["violations"] if v["severity"] == "fail"}


NOW = T("2026-10-02T18:00")
HEALTHY = [pub("last", "2026-10-02T16:45")] + [
    sched("s%d" % i, at) for i, at in enumerate(
        ["2026-10-04T06:00", "2026-10-05T06:00", "2026-10-07T06:00", "2026-10-09T06:00",
         "2026-10-11T06:00", "2026-10-12T06:00", "2026-10-14T06:00"])]

print("\n=== Runway SLA ===")
r = runway(HEALTHY, NOW, POLICY)
check("healthy runway passes", r["healthy"] and not codes(r), r["violations"])
check("largest planned gap is computed", r["maxGapHours"] == 48.0, r["maxGapHours"])
check("runway end and days are computed", r["runwayEnd"] == "2026-10-14T06:00" and r["runwayDays"] >= 10, r)

gap = [pub("last", "2026-10-02T16:45")] + [sched("a", "2026-10-04T06:00"), sched("b", "2026-10-07T12:00"),
                                           sched("c", "2026-10-09T06:00"), sched("d", "2026-10-11T06:00"),
                                           sched("e", "2026-10-14T06:00")]
r = runway(gap, NOW, POLICY)
check("a planned gap over 72h fails", "GAP_EXCEEDS_MAX" in codes(r) and not r["healthy"], r["violations"])

r = runway(HEALTHY[:4], NOW, POLICY)
check("fewer than 5 scheduled stories fails", "TOO_FEW_SCHEDULED" in codes(r), r["violations"])
check("less than 10 days of runway fails", "RUNWAY_TOO_SHORT" in codes(r), r["violations"])

r = runway([pub("last", "2026-09-28T06:00")] + HEALTHY[1:], NOW, POLICY)
check("last story older than 72h fails", "LAST_PUBLISHED_TOO_OLD" in codes(r), r["violations"])

r = runway([pub("last", "2026-10-02T16:45")], NOW, POLICY)
check("no future scheduled story fails", "NO_FUTURE_SCHEDULED" in codes(r), r["violations"])

r = runway([pub("last", "2026-10-02T16:45"), sched("far", "2026-10-06T12:00")], NOW, POLICY)
check("next story more than 72h away fails", "NEXT_TOO_FAR" in codes(r), r["violations"])

bad = [pub("last", "2026-10-02T16:45"), {"slug": "x", "status": "scheduled", "publishAt": "2026-10-04T06:00"}]
check("a scheduled story without approvedAt is flagged", "INVALID_SCHEDULE" in codes(runway(bad, NOW, POLICY)))

print("\n=== Slot planning (48h target, 72h maximum) ===")
plan = suggest_slots([pub("last", "2026-10-02T16:45")], NOW, POLICY)
slots = [T(s) for s in plan["slots"]]
seq = [T("2026-10-02T16:45")] + slots
spacing = [(b - a).total_seconds() / 3600 for a, b in zip(seq, seq[1:])]
check("planner restores at least 5 stories and 10 days", len(slots) >= 5 and (slots[-1] - NOW).days >= 10, plan["slots"])
check("no planned gap exceeds 72h", max(spacing) <= 72, spacing)
check("planned gaps target ~48h (never below the 12h minimum)", all(12 <= h <= 48 for h in spacing), spacing)
check("every week the runway enters opens on Monday morning",
      all(s.strftime("%a %H:%M") == "Mon 06:00" for s in slots
          if s.isocalendar()[1] != (slots[slots.index(s) - 1] if slots.index(s) else T("2026-10-02T16:45")).isocalendar()[1]),
      plan["slots"])
r = runway([pub("last", "2026-10-02T16:45")] + [sched("p%d" % i, s) for i, s in enumerate(plan["slots"])], NOW, POLICY)
check("a runway built from the planner is healthy", r["healthy"], r["violations"])

stories = copy.deepcopy(HEALTHY) + [{"slug": "ok-approved", "status": "approved", "approvedAt": "2026-10-02",
                                     "publishAt": None, "placement": "standard"}]
done = schedule_approved(stories, NOW, POLICY)
s = next(x for x in stories if x["slug"] == "ok-approved")
check("--schedule slots an approved story after the runway end",
      done == ["ok-approved"] and s["status"] == "scheduled" and T(s["publishAt"]) > T("2026-10-14T06:00"), s)
check("--schedule is idempotent", schedule_approved(stories, NOW, POLICY) == [])

print("\n=== Weekly cover placement ===")
wk = [pub("lewes", "2026-10-02T16:44", placement="cover", coverStory=True, featured=True),
      sched("sun", "2026-10-04T06:00"), sched("mon", "2026-10-05T06:00"), sched("wed", "2026-10-07T06:00")]
changed = assign_week_covers(wk)
place = {s["slug"]: s["placement"] for s in wk}
check("first story of a new week becomes its cover", place["mon"] == "cover", place)
check("a week that already has a cover keeps it", place["sun"] == "standard", place)
check("only one cover is assigned per week", place["wed"] == "standard" and changed == ["mon"], changed)
check("cover assignment is idempotent", assign_week_covers(wk) == [])

print("\n=== Auto-approval policy ===")
BODY = "<p>" + " ".join(["The marsh edge changes with every tide along the Delaware coast."] * 40) + "</p>"


def story(slug, at="2026-10-09T06:00", **kw):
    s = {"slug": slug, "headline": "A Test Headline", "kicker": "Test", "hook": "Hook.", "lede": "Lede.",
         "body": BODY, "author": "coast-nature", "category": "coast", "placement": "standard",
         "sources": [{"url": "https://dnrec.delaware.gov/x", "type": "government", "publisher": "DNREC"},
                     {"url": "https://www.destateparks.com/y", "type": "first-party", "publisher": "Parks"}],
         "sourceNotes": "Both sources support every claim.", "verifiedAt": "2026-10-02",
         "heroImage": "dune-sunrise-1.svg", "heroAlt": "Dunes at sunrise (illustration)",
         "heroProvenance": "House illustration; no place claim.", "seoTitle": "T", "seoDescription": "D",
         "places": ["lewes"], "riskClass": "nature-explainer", "autoApprovalEligible": True,
         "suggestedPublishAt": at}
    s.update(kw)
    return s


check("a well-sourced nature explainer is eligible", eligibility_problems(story("ok"), POLICY, NOW) == [])
one = story("one", sources=[{"url": "https://example.com/blog", "type": "secondary"}])
check("a single weak source cannot auto-approve", eligibility_problems(one, POLICY, NOW) != [],
      eligibility_problems(one, POLICY, NOW))
check("an unverified (stale-verified) story cannot auto-approve",
      eligibility_problems(story("old", verifiedAt="2026-09-01"), POLICY, NOW) != [])
check("a held risk class cannot auto-approve",
      eligibility_problems(story("legal", riskClass="allegation"), POLICY, NOW) != [])
visit = story("visit", body=BODY + "<p>When we visited the point we walked the whole beach.</p>")
check("an invented first-person visit cannot auto-approve", eligibility_problems(visit, POLICY, NOW) != [],
      eligibility_problems(visit, POLICY, NOW))
quote = story("quote", body=BODY + '<p>“The birds come through here every single fall,” said the counter.</p>')
check("an invented direct quote cannot auto-approve", eligibility_problems(quote, POLICY, NOW) != [])

print("\n=== Ingestion, publication and the homepage (sandbox) ===")


class Sandbox:
    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="dbf-autopilot-test-")
        for item in ("data", "scripts", "templates", "content", "stories"):
            shutil.copytree(os.path.join(REPO, item), os.path.join(self.dir, item),
                            ignore=shutil.ignore_patterns("__pycache__"))
        os.makedirs(os.path.join(self.dir, "assets"))
        os.symlink(os.path.join(REPO, "assets", "images"), os.path.join(self.dir, "assets", "images"))
        shutil.copytree(os.path.join(REPO, "assets", "js"), os.path.join(self.dir, "assets", "js"))
        # Start from published history only, so whatever is scheduled in the
        # live runway today can never collide with these fixtures.
        path = os.path.join(self.dir, "data", "stories.json")
        live = json.load(open(path, encoding="utf-8"))
        json.dump([s for s in live if s.get("status") == "published"], open(path, "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run(self, *args):
        return subprocess.run([sys.executable] + list(args), cwd=self.dir, capture_output=True, text=True)

    def json(self, rel):
        return json.load(open(os.path.join(self.dir, rel), encoding="utf-8"))

    def write_pkg(self, pkg, name="pkg.json"):
        p = os.path.join(self.dir, name)
        json.dump(pkg, open(p, "w", encoding="utf-8"))
        return p

    def ingest(self, pkg, now="2031-10-04T18:00"):
        return self.run("scripts/ingest_story_package.py", self.write_pkg(pkg), "--now", now)

    def snapshot(self):
        return (open(os.path.join(self.dir, "data", "stories.json"), "rb").read(),
                sorted(os.listdir(os.path.join(self.dir, "content", "stories"))))


def sbstory(slug, at="2031-10-09T06:00", **kw):
    """Sandbox fixtures live in 2031 so they can never collide with the real runway."""
    kw.setdefault("verifiedAt", "2031-10-04")
    return story(slug, at=at, **kw)


def pkg(*stories, pid="test-package"):
    return {"packageId": pid, "preparedAt": "2026-10-02T17:00", "stories": list(stories)}


with Sandbox() as sb:
    old_cover = next(s["slug"] for s in sb.json("data/stories.json") if s.get("coverStory"))
    good = pkg(sbstory("autopilot-test-one", at="2031-10-06T06:00"),
               sbstory("autopilot-test-held", at=None, autoApprovalEligible=False, riskClass="uncertain-logistics",
                     heldReason="Parking rules not confirmed by the park."))
    res = sb.ingest(good)
    check("a valid package ingests", res.returncode == 0, res.stdout + res.stderr)
    by = {s["slug"]: s for s in sb.json("data/stories.json")}
    one, held = by.get("autopilot-test-one", {}), by.get("autopilot-test-held", {})
    check("eligible story is scheduled with approvedAt and explicit publishAt",
          one.get("status") == "scheduled" and one.get("approvedAt") and one.get("publishAt") == "2031-10-06T06:00", one)
    check("ineligible story is held with no approval", held.get("status") == "held" and held.get("approvedAt") is None
          and held.get("heldReason"), held)
    check("ingestion writes prose for both", all(os.path.exists(os.path.join(sb.dir, "content", "stories", s + ".html"))
                                                for s in ("autopilot-test-one", "autopilot-test-held")))
    check("ingestion never publishes", all(s.get("status") != "published" for s in (one, held)))
    check("the week's first scheduled story is made its cover", one.get("placement") == "cover", one.get("placement"))

    before = sb.snapshot()
    res = sb.ingest(good)
    check("re-ingesting the same package changes nothing", res.returncode == 0 and sb.snapshot() == before,
          res.stdout)
    check("re-ingesting reports no changes", "(no changes)" in res.stdout, res.stdout)

    dup = pkg(sbstory("autopilot-test-two"), sbstory("autopilot-test-two", at="2031-10-11T06:00"), pid="dup")
    res = sb.ingest(dup)
    check("a duplicate slug inside a package is rejected", res.returncode == 1 and "duplicate slug" in res.stdout, res.stdout)
    res = sb.ingest(pkg(sbstory(old_cover), pid="other"))
    check("a slug that already exists is rejected", res.returncode == 1 and "already" in res.stdout, res.stdout)
    res = sb.ingest(pkg(sbstory("autopilot-bad-desk", author="ghost-writer"), pid="desk"))
    check("an unknown author desk is rejected", res.returncode == 1 and "author desk" in res.stdout, res.stdout)
    res = sb.ingest(pkg(sbstory("autopilot-bad-place", placement="hero"), pid="place"))
    check("an invalid placement is rejected", res.returncode == 1 and "placement" in res.stdout, res.stdout)
    res = sb.ingest(pkg(sbstory("autopilot-no-catpage", category="community"), pid="cat"))
    check("a category without a category page is rejected", res.returncode == 1 and "category page" in res.stdout, res.stdout)
    res = sb.ingest(pkg(sbstory("autopilot-no-body", body=""), pid="nobody"))
    check("missing body prose is rejected", res.returncode == 1 and "body" in res.stdout, res.stdout)
    res = sb.ingest(pkg(sbstory("autopilot-no-src", sources=[]), pid="nosrc"))
    check("missing sources are rejected", res.returncode == 1 and "sources" in res.stdout, res.stdout)
    res = sb.ingest(pkg(sbstory("autopilot-weak", sources=[{"url": "https://example.com/a", "type": "secondary"}]), pid="weak"))
    check("an autoApprovalEligible story that violates policy rejects the package",
          res.returncode == 1 and "marked autoApprovalEligible" in res.stdout, res.stdout)
    res = sb.ingest(pkg(sbstory("autopilot-sneaky", status="published"), pid="sneaky"))
    check("a package may never carry published state", res.returncode == 1 and "published" in res.stdout, res.stdout)
    res = sb.ingest(pkg(sbstory("autopilot-crowded", at="2031-10-06T09:00"), pid="crowd"))
    check("a slot within 12h of another scheduled story is rejected", res.returncode == 1 and "apart" in res.stdout, res.stdout)
    res = sb.ingest(pkg(sbstory("autopilot-deadlink", relatedStories=[{"href": "category-nowhere.html", "label": "x"}]), pid="dead"))
    check("a related link to a page that does not exist is rejected",
          res.returncode == 1 and "related link" in res.stdout, res.stdout)
    res = sb.ingest(pkg(sbstory("autopilot-early", at="2031-10-08T06:00",
                                relatedStories=[{"href": "autopilot-late.html", "label": "x"}]),
                        sbstory("autopilot-late", at="2031-10-10T06:00"), pid="order"))
    check("a related link to a story that publishes later is rejected",
          res.returncode == 1 and "autopilot-early: related link" in res.stdout, res.stdout)
    check("rejected packages write nothing", sb.snapshot() == before)

    # Held stories never publish, however far past their time.
    res = sb.run("scripts/publish_due.py", "--now", "2031-12-31T23:00")
    by = {s["slug"]: s for s in sb.json("data/stories.json")}
    check("held stories never publish", by["autopilot-test-held"]["status"] == "held", res.stdout)
    check("held stories are never due", not is_due(by["autopilot-test-held"], T("2031-12-31T23:00")))
    check("scheduled stories publish through the existing hourly publisher",
          by["autopilot-test-one"]["status"] == "published" and "autopilot-test-one" in res.stdout, res.stdout)
    check("the publisher rendered the article page",
          os.path.exists(os.path.join(sb.dir, "stories", "autopilot-test-one.html")))
    reg = sb.json("data/issues/index.json")
    check("the publisher opened the story's week as the current issue", reg["currentIssueId"] == "2031-W41", reg["currentIssueId"])
    w41 = sb.json("data/issues/2031-W41.json")
    check("the new issue is titled in words and names its cover",
          w41["title"] == "Week of October 6, 2031" and w41["coverStory"] == "autopilot-test-one", w41)
    old = by[old_cover]
    check("the previous cover is demoted, still published",
          old["status"] == "published" and not old["coverStory"] and not old["featured"], old)

    sel = re.search(r"// <front-page-select>.*?// </front-page-select>",
                    open(os.path.join(sb.dir, "assets", "js", "site.js"), encoding="utf-8").read(), re.S).group(0)

    def lead_at(now):
        script = sel + ("\nconst a=JSON.parse(require('fs').readFileSync(0,'utf8'));"
                        "const r=selectFrontPage(a.s,a.r,Date.parse(a.now));"
                        "console.log(JSON.stringify({mode:r.mode,reason:r.reason||null,cover:r.cover&&r.cover.slug}));")
        out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True,
                             input=json.dumps({"s": sb.json("data/stories.json"), "r": reg, "now": now}))
        return json.loads(out.stdout)

    r = lead_at("2031-10-06T09:00:00-04:00")
    check("the auto-published story becomes the current issue's homepage lead",
          r == {"mode": "story", "reason": None, "cover": "autopilot-test-one"}, r)
    check("the old archived cover cannot masquerade as current", r["cover"] != old_cover, r)
    r = lead_at("2031-10-09T13:00:00-04:00")
    check("autopilot failure (>72h, no new story) switches the homepage to the This Week fallback",
          r["mode"] == "issue" and r["reason"] == "stale" and r["cover"] is None, r)
    py = current_lead(sb.json("data/stories.json"), reg, T("2031-10-09T13:00"), POLICY)
    check("the runway guard sees the same fallback", py["mode"] == "issue" and py["reason"] == "stale", py)

print("\n=== Runway guard ===")
REG = {"currentIssueId": "2026-W40", "issues": [{"issueId": "2026-W40", "status": "current", "weekOf": "2026-09-28"}]}
DAILY = {"verifiedAt": "2026-09-27", "slots": [{"date": "2026-10-02"}, {"date": "2026-10-04"}]}
lead_story = pub("lewes", "2026-10-02T16:44", placement="cover", coverStory=True, featured=True)
ok_set = [lead_story] + HEALTHY[1:]
g = guard(ok_set, REG, DAILY, NOW, POLICY)
check("guard is healthy for a full runway, current lead and fresh slots", g["healthy"], g["problems"])
g = guard([lead_story] + HEALTHY[1:3], REG, DAILY, NOW, POLICY)
check("guard reports a thin runway", not g["healthy"] and any("scheduled" in p for p in g["problems"]), g["problems"])
g = guard(ok_set, REG, {"verifiedAt": "2026-09-20", "slots": [{"date": "2026-09-26"}]}, NOW, POLICY)
check("guard reports stale daily slots", any("Daily slots" in p for p in g["problems"]), g["problems"])
g = guard(ok_set, REG, DAILY, T("2026-10-05T13:00"), POLICY)
check("guard reports a stale currentIssueId", any("currentIssueId" in p for p in g["problems"]), g["problems"])
g = guard(ok_set, REG, DAILY, NOW, POLICY, editorial_ok=False)
check("guard reports failed editorial validation", any("validation" in p for p in g["problems"]), g["problems"])
g = guard([pub("old", "2026-09-07T06:00", issue="2026-W37", coverStory=True)] + HEALTHY[1:], REG, DAILY, NOW, POLICY)
check("guard reports a homepage with no valid current lead", any("current lead" in p for p in g["problems"]), g["problems"])

wf = open(os.path.join(REPO, ".github", "workflows", "editorial-runway-guard.yml"), encoding="utf-8").read()
check("runway guard workflow runs at least every 6 hours", re.search(r'cron: "\S+ \*/6 \* \* \*"', wf) is not None)
check("runway guard maintains one named issue",
      wf.count('"DBF editorial autopilot: attention required"') == 2 and "issues.update" in wf)
pubwf = open(os.path.join(REPO, ".github", "workflows", "publish-scheduled.yml"), encoding="utf-8").read()
check("the hourly publisher workflow is still scheduled", "cron: '0 * * * *'" in pubwf and "publish_due.py" in pubwf)

print()
print("================================")
print(f"Passed: {passed}   Failed: {failed}")
sys.exit(1 if failed else 0)
