#!/usr/bin/env python3
"""Emit a date-shifted copy of a sample candidate so validator tests never rot.

The committed fixtures in automation/ use absolute dates because they double as
human documentation for the scheduled-research contract — a reader needs to see
real-looking values. But absolute dates mean the "valid candidate is accepted"
test starts failing the moment those dates pass, which is a false alarm about
working code.

This rewrites the date fields relative to today, preserving each event's
duration and the original verified-before-start relationship, then prints the
result to stdout for the test to consume:

    python3 scripts/make_test_candidate.py automation/sample-valid-candidate.json > /tmp/c.json
"""
import json
import sys
from datetime import date, datetime, timedelta

ISO_DATE = "%Y-%m-%d"


def main():
    if len(sys.argv) < 2:
        print("usage: make_test_candidate.py <candidate.json>", file=sys.stderr)
        return 2

    with open(sys.argv[1]) as f:
        c = json.load(f)

    today = date.today()

    # Anchor on the original verifiedAt so every other date keeps its offset.
    anchor = datetime.strptime(c["verifiedAt"], ISO_DATE).date()
    shift = today - anchor

    def shift_date(value):
        if not value:
            return value
        return (datetime.strptime(value, ISO_DATE).date() + shift).strftime(ISO_DATE)

    c["verifiedAt"] = today.strftime(ISO_DATE)
    c["generatedAt"] = today.strftime("%Y-%m-%dT%H:%M:%SZ")

    for section in ("activeEvents", "laterEvents"):
        for e in c.get(section) or []:
            for field in ("startDate", "endDate", "verifiedAt", "lastModified"):
                if field in e and e[field]:
                    e[field] = shift_date(e[field])
            # An "active" event must not already be over. If shifting left it in
            # the past (because the fixture was authored mid-window), nudge it
            # forward far enough to stay a legitimate upcoming event.
            if section == "activeEvents" and e.get("endDate"):
                end = datetime.strptime(e["endDate"], ISO_DATE).date()
                if end < today:
                    delta = (today - end) + timedelta(days=2)
                    e["startDate"] = shift_date_by(e["startDate"], delta)
                    e["endDate"] = shift_date_by(e["endDate"], delta)

    for u in c.get("comingSoonUpdates") or []:
        if u.get("lastReviewed"):
            u["lastReviewed"] = today.strftime(ISO_DATE)

    json.dump(c, sys.stdout, indent=2, ensure_ascii=False)
    return 0


def shift_date_by(value, delta):
    return (datetime.strptime(value, ISO_DATE).date() + delta).strftime(ISO_DATE)


if __name__ == "__main__":
    sys.exit(main())
