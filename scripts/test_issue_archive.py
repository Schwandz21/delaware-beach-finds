#!/usr/bin/env python3
"""Tests for weekly-issue archival continuity.

The property that matters: publishing a new issue must never destroy the one it
replaces. These exercise the real transition function, not a snapshot.
"""
import copy
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from publish_issue import promote  # noqa: E402

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


INDEX = json.load(open(os.path.join(ROOT, "data", "issues", "index.json")))

# --- registry integrity ---
ids = [i["issueId"] for i in INDEX["issues"]]
check("registry has no duplicate issueIds", len(ids) == len(set(ids)), ids)
check("currentIssueId points at a real registered issue", INDEX["currentIssueId"] in ids)

current_entries = [i for i in INDEX["issues"] if i.get("status") == "current"]
check("exactly one issue is marked current", len(current_entries) == 1, current_entries)

for entry in INDEX["issues"]:
    p = os.path.join(ROOT, "data", entry["file"])
    check(f"issue file exists for {entry['issueId']}", os.path.exists(p), p)
    if os.path.exists(p):
        doc = json.load(open(p))
        check(f"{entry['issueId']} carries provenance sources", bool(doc.get("sources")))
        check(f"{entry['issueId']} declares access_level", "access_level" in doc)
        check(f"{entry['issueId']} weekOf matches registry", doc.get("weekOf") == entry.get("weekOf"))

# --- the transition itself ---
# Use an ID guaranteed absent from the real registry so this simulation cannot
# collide with issues that genuinely get created later.
SIM_ID = "9999-W99"
sim = copy.deepcopy(INDEX)
sim["issues"].append({
    "issueId": SIM_ID, "weekOf": "9999-01-01", "title": "Simulated future issue",
    "publishedAt": "9999-01-02", "status": "draft", "file": "issues/9999-W99.json",
    "access_level": "public",
})
before_ids = {i["issueId"] for i in sim["issues"]}

after, outgoing = promote(copy.deepcopy(sim), SIM_ID, today="9999-01-02")
after_ids = {i["issueId"] for i in after["issues"]}

check("promoting a new issue loses no issues", before_ids == after_ids, after_ids)
check("the new issue becomes current", after["currentIssueId"] == SIM_ID)
check("the outgoing issue is archived, not deleted",
      any(i["issueId"] == INDEX["currentIssueId"] and i["status"] == "archived" for i in after["issues"]))
check("the outgoing issue records what superseded it",
      any(i["issueId"] == INDEX["currentIssueId"] and i.get("supersededBy") == SIM_ID for i in after["issues"]))
check("still exactly one current issue after promotion",
      len([i for i in after["issues"] if i.get("status") == "current"]) == 1)
check("archived is distinct from expired/superseded-as-wrong",
      all(i.get("status") in {"current", "archived", "draft"} for i in after["issues"]))

# --- refusals ---
def refuses(desc, index, issue_id):
    try:
        promote(copy.deepcopy(index), issue_id)
        check(desc, False, "expected ValueError, got success")
    except ValueError:
        check(desc, True)

refuses("refuses an unknown issueId", sim, "2099-W01")
refuses("refuses re-promoting the already-current issue", sim, INDEX["currentIssueId"])

dup = copy.deepcopy(sim)
dup["issues"].append(dict(dup["issues"][0]))
refuses("refuses a registry with duplicate issueIds", dup, SIM_ID)

# --- staged drafts must never render publicly ---
site_js = open(os.path.join(ROOT, "assets", "js", "site.js"), encoding="utf-8").read()
check("archive renderer filters issues by publication state",
      "PUBLIC_STATES" in site_js and "'archived'" in site_js)
check("draft is not a public state",
      "PUBLIC_STATES = new Set(['current','archived'])" in site_js)

# --- no fabricated history ---
check("no issue is dated before the system existed (no backfilled weeks)",
      all(i["weekOf"] >= "2026-08-10" for i in INDEX["issues"]),
      [i["weekOf"] for i in INDEX["issues"]])

print()
print("================================")
print(f"Passed: {passed}   Failed: {failed}")
sys.exit(1 if failed else 0)
