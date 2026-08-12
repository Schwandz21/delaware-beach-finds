#!/usr/bin/env python3
"""Promote a weekly issue to current, superseding the previous one.

The rule this enforces: making a new issue current must NEVER delete or rewrite
the issue it replaces. The outgoing issue moves to status "archived" and stays
on disk and in the registry forever. "Superseded" means "no longer the current
pointer" — it does not mean wrong, and it does not mean gone.

    python3 scripts/publish_issue.py 2026-W34            # dry run
    python3 scripts/publish_issue.py 2026-W34 --apply
"""
import argparse
import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISSUES = os.path.join(ROOT, "data", "issues")
INDEX = os.path.join(ISSUES, "index.json")


def load(p):
    with open(p) as f:
        return json.load(f)


def save(p, o):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(o, f, indent=2, ensure_ascii=False)
        f.write("\n")


def promote(index, issue_id, today=None):
    """Pure transition so tests can exercise it without touching disk."""
    today = today or date.today().isoformat()
    ids = [i["issueId"] for i in index.get("issues", [])]

    if issue_id not in ids:
        raise ValueError(f"issue {issue_id} is not in the registry")
    if len(ids) != len(set(ids)):
        raise ValueError("registry contains duplicate issueIds")
    if index.get("currentIssueId") == issue_id:
        raise ValueError(f"issue {issue_id} is already current")

    outgoing = []
    for entry in index["issues"]:
        if entry["issueId"] == issue_id:
            entry["status"] = "current"
            entry.setdefault("publishedAt", today)
        elif entry.get("status") == "current":
            entry["status"] = "archived"
            entry["supersededAt"] = today
            entry["supersededBy"] = issue_id
            outgoing.append(entry["issueId"])
    index["currentIssueId"] = issue_id
    return index, outgoing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("issue_id")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    index = load(INDEX)
    before = [(i["issueId"], i.get("status")) for i in index["issues"]]

    try:
        index, outgoing = promote(index, args.issue_id)
    except ValueError as exc:
        print(f"refused: {exc}")
        return 1

    print(f"current -> {args.issue_id}")
    for oid in outgoing:
        print(f"  {oid} archived (preserved, not deleted)")
    print("\nregistry before:", before)
    print("registry after: ", [(i["issueId"], i.get("status")) for i in index["issues"]])

    if not args.apply:
        print("\n(dry run — no files written; re-run with --apply)")
        return 0

    # Mirror the status onto each issue file itself.
    for entry in index["issues"]:
        path = os.path.join(ROOT, "data", entry["file"])
        if os.path.exists(path):
            doc = load(path)
            doc["status"] = entry["status"]
            if entry.get("supersededBy"):
                doc["supersededBy"] = entry["supersededBy"]
                doc["supersededAt"] = entry["supersededAt"]
            save(path, doc)

    save(INDEX, index)
    print(f"\nwrote {INDEX} and {len(index['issues'])} issue file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
