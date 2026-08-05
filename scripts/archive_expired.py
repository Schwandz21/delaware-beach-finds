#!/usr/bin/env python3
"""Move events whose endDate has passed out of data/events.json and into
data/events-archive.json.

Why this exists: the public site already filters expired events out at render
time, so nothing broken is ever shown to a visitor. But between weekly candidate
updates, expired records accumulate in events.json. apply_candidate.py only
archives events a candidate explicitly names in expireEventIds, which means
routine expiry had no maintenance path. This is that path.

Safe by default: prints the plan and writes nothing unless --apply is passed.

    python3 scripts/archive_expired.py           # dry run
    python3 scripts/archive_expired.py --apply   # write changes
"""
import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def load(name, default):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def write(name, payload):
    path = os.path.join(DATA, name)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    apply_changes = "--apply" in sys.argv
    today = date.today().isoformat()

    events_doc = load("events.json", {"events": []})
    archive = load("events-archive.json", [])
    events = events_doc.get("events", [])

    expired = [e for e in events if e.get("endDate") and e["endDate"] < today]
    remaining = [e for e in events if not (e.get("endDate") and e["endDate"] < today)]

    print(f"Today: {today}")
    print(f"Events in events.json:   {len(events)}")
    print(f"Still current/upcoming:  {len(remaining)}")
    print(f"Expired -> archive:      {len(expired)}")
    for e in expired:
        print(f"  ⇒ {e['endDate']}  {e['title']}")

    if not expired:
        print("\nNothing to archive.")
        return 0

    if not apply_changes:
        print("\n(dry run — no files written; re-run with --apply)")
        return 0

    archive_ids = {e.get("id") for e in archive}
    for e in expired:
        rec = dict(e)
        rec["status"] = "expired"
        rec["lastModified"] = today
        if rec.get("id") not in archive_ids:
            archive.append(rec)

    events_doc["events"] = remaining
    write("events.json", events_doc)
    write("events-archive.json", archive)
    print(f"\nWrote data/events.json ({len(remaining)} current) "
          f"and data/events-archive.json ({len(archive)} archived).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
