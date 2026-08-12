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
import re
import os
import sys
from datetime import date, datetime

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



DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class DailySlotError(Exception):
    """Malformed dailySlots must fail loudly, never be silently dropped."""


def build_daily_slots(candidate):
    """Return the new data/daily-slots.json payload, or None if the candidate
    carries no dailySlots key at all.

    Rules enforced here:
      * every slot needs a real YYYY-MM-DD date -- a missing date is never inferred
      * every slot needs a headline -- an untitled slot cannot render honestly
      * dates are used exactly as given -- nothing is re-dated into another week
      * an explicitly empty list produces an explicitly empty file, so the module
        hides rather than carrying stale material forward
    """
    if "dailySlots" not in candidate:
        return None

    slots = candidate.get("dailySlots")
    if not isinstance(slots, list):
        raise DailySlotError(f"dailySlots must be a list, got {type(slots).__name__}")

    problems = []
    for i, s in enumerate(slots):
        label = f"dailySlots[{i}]"
        if not isinstance(s, dict):
            problems.append(f"{label}: expected an object, got {type(s).__name__}")
            continue
        date = s.get("date")
        if not date:
            problems.append(f"{label}: missing 'date' — a slot date is never inferred")
        elif not (isinstance(date, str) and DATE_RE.match(date)):
            problems.append(f'{label}: date "{date}" is not YYYY-MM-DD')
        else:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                problems.append(f'{label}: date "{date}" is not a real calendar date')
        if not s.get("headline"):
            problems.append(f"{label}: missing 'headline'")
    if problems:
        raise DailySlotError("; ".join(problems))

    return {
        "_note": ("Mutable CURRENT-WEEK editorial surface. Weekly issue files in data/issues/ are "
                  "immutable publication history and are never read at render time. Candidate "
                  "ingestion updates this file; it never rewrites an issue record."),
        "weekOf": candidate.get("weekOf"),
        "verifiedAt": candidate.get("verifiedAt"),
        "sourceCandidate": candidate.get("_sourcePath"),
        "slots": [dict(s) for s in slots],
    }


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
    candidate["_sourcePath"] = args[0]

    events_doc = load("events.json", {"events": [], "verifiedAt": None, "freshnessPolicyDays": 7})
    archive = load("events-archive.json", [])
    guides = load("guides.json", [])

    plan = compute_plan(candidate, events_doc, archive, guides)
    print(describe_plan(plan))

    # Fail loudly before anything is written.
    try:
        daily_payload = build_daily_slots(candidate)
    except DailySlotError as exc:
        print(f"\nREFUSED — malformed dailySlots: {exc}")
        return 1
    if daily_payload is None:
        print("Daily slots:              (candidate has no dailySlots key — leaving existing file untouched)")
    else:
        n = len(daily_payload["slots"])
        print(f"Daily slots to write:     {n}" + ("  (explicitly empty — module will hide)" if n == 0 else ""))
        for s in daily_payload["slots"]:
            print(f"  * {s['date']}  {s.get('kind','')}  {s['headline'][:52]}")

    if not apply_mode:
        print("\n(dry run — no files written; re-run with --apply to write changes)")
        return 0

    new_events_doc, new_archive, new_guides = apply_plan(plan, candidate, events_doc, archive, guides)
    save("events.json", new_events_doc)
    save("events-archive.json", new_archive)
    save("guides.json", new_guides)
    written = ["data/events.json", "data/events-archive.json", "data/guides.json"]
    if daily_payload is not None:
        save("daily-slots.json", daily_payload)
        written.append("data/daily-slots.json")
    print("\nWrote " + ", ".join(written))
    return 0


if __name__ == "__main__":
    sys.exit(main())
