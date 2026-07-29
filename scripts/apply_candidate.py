#!/usr/bin/env python3
"""Preview or apply a validated DBF freshness candidate.

Always run scripts/validate_candidate.py first — this script does not
re-validate. It assumes the caller (UPDATE_DBF_FRESHNESS.command) already
rejected an invalid candidate.

Modes:
    python3 scripts/apply_candidate.py candidate.json            # dry-run preview, no writes
    python3 scripts/apply_candidate.py candidate.json --apply    # writes data/events.json,
                                                                   # data/events-archive.json,
                                                                   # data/guides.json

Never touches anything outside data/events.json, data/events-archive.json
and data/guides.json's status/lastReviewed fields. It cannot invent or
modify editorial article content.
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
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(name, payload):
    path = os.path.join(DATA, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def next_id(title, start_date):
    slug = "".join(c if c.isalnum() else "-" for c in title.lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return f"evt-{slug}-{start_date}"


def compute_plan(candidate, events_doc, archive, guides):
    plan = {
        "toAddOrUpdate": [],
        "toArchive": [],
        "guideUpdates": [],
    }
    existing_by_key = {}
    for e in events_doc.get("events", []):
        key = (e.get("title", "").strip().lower(), e.get("startDate"), e.get("town", "").strip().lower())
        existing_by_key[key] = e

    incoming = (candidate.get("activeEvents") or []) + (candidate.get("laterEvents") or [])
    for e in incoming:
        e = dict(e)
        if not e.get("id"):
            e["id"] = next_id(e["title"], e["startDate"])
        e.setdefault("lastModified", date.today().isoformat())
        e.setdefault("access_level", "public")
        key = (e.get("title", "").strip().lower(), e.get("startDate"), e.get("town", "").strip().lower())
        action = "update" if key in existing_by_key else "add"
        plan["toAddOrUpdate"].append((action, e))

    for status_change in candidate.get("cancelledOrPostponed") or []:
        eid = status_change.get("id")
        for e in events_doc.get("events", []):
            if e.get("id") == eid:
                updated = dict(e)
                updated["status"] = status_change.get("status")
                updated["editorialNote"] = status_change.get("note", updated.get("editorialNote"))
                updated["lastModified"] = date.today().isoformat()
                plan["toAddOrUpdate"].append(("status-change", updated))

    for eid in candidate.get("expireEventIds") or []:
        for e in events_doc.get("events", []):
            if e.get("id") == eid:
                archived = dict(e)
                archived["status"] = "expired"
                archived["lastModified"] = date.today().isoformat()
                plan["toArchive"].append(archived)

    for update in candidate.get("comingSoonUpdates") or []:
        plan["guideUpdates"].append(update)

    return plan


def describe_plan(plan):
    lines = []
    added = [e for a, e in plan["toAddOrUpdate"] if a == "add"]
    updated = [e for a, e in plan["toAddOrUpdate"] if a == "update"]
    status_changed = [e for a, e in plan["toAddOrUpdate"] if a == "status-change"]

    lines.append(f"Events to add:            {len(added)}")
    for e in added:
        lines.append(f"  + {e['title']} — {e['startDate']} ({e['town']}) [{e['status']}]")
    lines.append(f"Events to update:         {len(updated)}")
    for e in updated:
        lines.append(f"  ~ {e['title']} — {e['startDate']} ({e['town']})")
    lines.append(f"Status changes:           {len(status_changed)}")
    for e in status_changed:
        lines.append(f"  ! {e['title']} -> {e['status']}")
    lines.append(f"Events to archive:        {len(plan['toArchive'])}")
    for e in plan["toArchive"]:
        lines.append(f"  ⇒ {e['title']} — {e['startDate']} moves to events-archive.json")
    lines.append(f"Coming Soon updates:      {len(plan['guideUpdates'])}")
    for u in plan["guideUpdates"]:
        lines.append(f"  * {u['slug']} -> {u.get('status')}, lastReviewed {u.get('lastReviewed')}")
    return "\n".join(lines)


def apply_plan(plan, candidate, events_doc, archive, guides):
    events_by_id = {e["id"]: e for e in events_doc.get("events", [])}
    for action, e in plan["toAddOrUpdate"]:
        events_by_id[e["id"]] = e

    archived_ids = {e["id"] for e in plan["toArchive"]}
    remaining_events = [e for e in events_by_id.values() if e["id"] not in archived_ids]
    events_doc["events"] = remaining_events
    events_doc["verifiedAt"] = candidate.get("verifiedAt", events_doc.get("verifiedAt"))

    archive_ids_present = {e.get("id") for e in archive}
    for e in plan["toArchive"]:
        if e["id"] not in archive_ids_present:
            archive.append(e)

    guides_by_slug = {g["slug"]: g for g in guides}
    for u in plan["guideUpdates"]:
        g = guides_by_slug.get(u["slug"])
        if not g:
            continue
        g["status"] = u.get("status", g.get("status"))
        g["lastReviewed"] = u.get("lastReviewed", g.get("lastReviewed"))
        if u.get("href"):
            g["href"] = u["href"]

    return events_doc, archive, list(guides_by_slug.values())


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply_mode = "--apply" in sys.argv
    if not args:
        print("Usage: python3 scripts/apply_candidate.py candidate.json [--apply]")
        return 2

    with open(args[0], encoding="utf-8") as f:
        candidate = json.load(f)

    events_doc = load("events.json", {"events": [], "verifiedAt": None, "freshnessPolicyDays": 7})
    archive = load("events-archive.json", [])
    guides = load("guides.json", [])

    plan = compute_plan(candidate, events_doc, archive, guides)
    print(describe_plan(plan))

    if not apply_mode:
        print("\n(dry run — no files written; re-run with --apply to write changes)")
        return 0

    new_events_doc, new_archive, new_guides = apply_plan(plan, candidate, events_doc, archive, guides)
    save("events.json", new_events_doc)
    save("events-archive.json", new_archive)
    save("guides.json", new_guides)
    print("\nWrote data/events.json, data/events-archive.json, data/guides.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
