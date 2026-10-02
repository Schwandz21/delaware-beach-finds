#!/usr/bin/env python3
"""Regression test: public markup must not hard-code the current issue's week.

The homepage shipped "Week of September 7, 2026" and "September 7–13" in raw
HTML. JavaScript replaced the first only when the registry loaded and never
touched the second, so W37's week stayed on the live homepage for weeks after
W39 was published. data/issues/index.json is the single source of truth for
the current week; markup carries no week of its own.

    python3 scripts/test_current_week_markup.py              # check the working tree
    python3 scripts/test_current_week_markup.py FILE.html    # check one page
"""
import glob
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MONTH = (r"(?:January|February|March|April|May|June|July|August|September|October|"
         r"November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\.?")
# "Week of September 7", "Week of September 7, 2026"
WEEK_OF = re.compile(r"Week of " + MONTH + r"\s+\d{1,2}", re.I)
# "September 7–13", "September 28–October 4"
DATE_RANGE = re.compile(MONTH + r"\s+\d{1,2}\s*[–-]\s*(?:" + MONTH + r"\s+)?\d{1,2}\b")

# Containers whose text the reader takes as "this week". Their raw text must
# never carry a date.
CURRENT_WEEK_CONTAINER = re.compile(
    r'<(\w+)[^>]*(?:class="[^"]*\b(?:issue-strip-inner|franchise-line)\b[^"]*"|'
    r'data-current-week-line|data-mount="issue-folio")[^>]*>(.*?)</\1>', re.S)

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


def public_pages():
    pages = glob.glob(os.path.join(ROOT, "*.html")) + glob.glob(os.path.join(ROOT, "towns", "*.html"))
    return sorted(p for p in pages if os.path.basename(p) != "404.html")


def text_of(fragment):
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment))


def check_page(path):
    raw = open(path, encoding="utf-8").read()
    name = os.path.relpath(path, ROOT)
    week_of = WEEK_OF.findall(html.unescape(raw))
    check(f"{name}: no hard-coded 'Week of <date>'", not week_of, week_of)
    dated = []
    for m in CURRENT_WEEK_CONTAINER.finditer(raw):
        t = text_of(m.group(2))
        if WEEK_OF.search(t) or DATE_RANGE.search(t):
            dated.append(" ".join(t.split())[:80])
    check(f"{name}: current-week containers carry no date", not dated, dated)


targets = sys.argv[1:] or public_pages()
for p in targets:
    check_page(p)

if not sys.argv[1:]:
    index = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    check("homepage DBF Weekend line is registry-driven (data-current-week-line)",
          re.search(r'class="franchise-line"[^>]*data-current-week-line', index) is not None)
    check("homepage issue strip is a registry mount (data-mount=\"issue-folio\")",
          'data-mount="issue-folio"' in index)

    js = open(os.path.join(ROOT, "assets", "js", "site.js"), encoding="utf-8").read()
    i = js.find("[data-current-week-line]")
    check("site.js fills data-current-week-line", i != -1)
    check("site.js derives the week from issues/index.json",
          i != -1 and "fetchJson('issues/index.json')" in js[i:i + 600])

    reg = json.load(open(os.path.join(ROOT, "data", "issues", "index.json")))
    cur = [x for x in reg["issues"] if x.get("status") == "current"]
    check("registry has exactly one current issue, matching currentIssueId",
          len(cur) == 1 and cur[0]["issueId"] == reg["currentIssueId"], cur)

print()
print("================================")
print(f"Passed: {passed}   Failed: {failed}")
sys.exit(1 if failed else 0)
