#!/usr/bin/env python3
"""Print a maintainer freshness report for Delaware Beach Finds.

Not a public page — internal, terminal-only status output covering
current/future/expired events, coming-soon staleness, and the search
index. Used by the updater and by the daily GitHub Action.

Usage: python3 scripts/freshness_report.py [--json]
"""
import json
import os
import sys
from datetime import datetime, date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

EVENT_FRESHNESS_DAYS = 7
GUIDE_FRESHNESS_DAYS_DEFAULT = 14


def load(name, default=None):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def report():
    today = date.today()
    warnings = []
    ok = True

    events_doc = load("events.json", {"events": [], "verifiedAt": None})
    events = events_doc.get("events", [])
    verified_at = parse_date(events_doc.get("verifiedAt"))
    policy_days = events_doc.get("freshnessPolicyDays", EVENT_FRESHNESS_DAYS)

    archive = load("events-archive.json", [])

    active = [e for e in events if parse_date(e.get("endDate")) and parse_date(e.get("endDate")) >= today]
    stale_but_present = [e for e in events if parse_date(e.get("endDate")) and parse_date(e.get("endDate")) < today]
    tentative = [e for e in events if e.get("status") == "tentative"]
    cancelled_postponed = [e for e in events if e.get("status") in ("cancelled", "postponed")]

    dataset_stale = verified_at is None or (today - verified_at).days > policy_days
    if dataset_stale:
        ok = False
        age = "unknown" if verified_at is None else f"{(today - verified_at).days} days"
        warnings.append(f"events.json verifiedAt is stale ({age} old, policy is {policy_days} days). Public site will show the fallback state.")

    if stale_but_present:
        ok = False
        warnings.append(f"{len(stale_but_present)} event(s) in events.json already have an endDate in the past and should be moved to events-archive.json.")

    guides = load("guides.json", [])
    stale_guides = []
    for g in guides:
        if g.get("status") != "coming-soon":
            continue
        interval = g.get("reviewIntervalDays", GUIDE_FRESHNESS_DAYS_DEFAULT)
        last_reviewed = parse_date(g.get("lastReviewed"))
        if last_reviewed is None or (today - last_reviewed).days > interval:
            stale_guides.append(g.get("slug"))
    if stale_guides:
        ok = False
        warnings.append(f"{len(stale_guides)} Coming Soon guide(s) exceed their review interval: {', '.join(stale_guides)}")

    content_index = load("content-index.json", {"records": []})
    missing_urls = []
    for r in content_index.get("records", []):
        url = r.get("url", "")
        local_path = os.path.join(ROOT, url)
        if url and not os.path.exists(local_path):
            missing_urls.append(url)
    if missing_urls:
        ok = False
        warnings.append(f"{len(missing_urls)} content-index record(s) point at missing files: {', '.join(missing_urls[:5])}")

    next_review = None
    if verified_at:
        next_review = verified_at + timedelta(days=policy_days)

    summary = {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "eventsVerifiedAt": events_doc.get("verifiedAt"),
        "eventsActiveCount": len(active),
        "eventsFutureCount": len([e for e in active if parse_date(e.get("startDate")) and parse_date(e.get("startDate")) > today]),
        "eventsStaleInLiveFile": len(stale_but_present),
        "eventsArchivedCount": len(archive),
        "eventsTentativeCount": len(tentative),
        "eventsCancelledOrPostponedCount": len(cancelled_postponed),
        "staleComingSoonGuides": len(stale_guides),
        "contentIndexRecordCount": content_index.get("recordCount", len(content_index.get("records", []))),
        "contentIndexMissingUrls": len(missing_urls),
        "nextRequiredReview": next_review.isoformat() if next_review else "unknown — verify events.json",
        "overallStatus": "OK" if ok else "REVIEW NEEDED",
        "warnings": warnings,
    }
    return summary


def main():
    summary = report()
    if "--json" in sys.argv:
        print(json.dumps(summary, indent=2))
        return 0 if summary["overallStatus"] == "OK" else 1

    print("Delaware Beach Finds — Freshness Report")
    print("=" * 44)
    print(f"Generated:                 {summary['generatedAt']}")
    print(f"Events verified at:        {summary['eventsVerifiedAt']}")
    print(f"Active/current events:     {summary['eventsActiveCount']}")
    print(f"  of which future-dated:   {summary['eventsFutureCount']}")
    print(f"Stale events still live:   {summary['eventsStaleInLiveFile']}")
    print(f"Archived event records:    {summary['eventsArchivedCount']}")
    print(f"Tentative events:          {summary['eventsTentativeCount']}")
    print(f"Cancelled/postponed:       {summary['eventsCancelledOrPostponedCount']}")
    print(f"Stale Coming Soon guides:  {summary['staleComingSoonGuides']}")
    print(f"Search index records:      {summary['contentIndexRecordCount']}")
    print(f"Index records w/ dead URL: {summary['contentIndexMissingUrls']}")
    print(f"Next required review:      {summary['nextRequiredReview']}")
    print(f"Overall status:            {summary['overallStatus']}")
    if summary["warnings"]:
        print("\nWarnings:")
        for w in summary["warnings"]:
            print(f"  - {w}")
    return 0 if summary["overallStatus"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
