#!/usr/bin/env python3
"""Validate a DBF freshness candidate JSON file before anything is applied.

This is the gate the updater (UPDATE_DBF_FRESHNESS.command) and the weekly
Claude research task both go through. Nothing here writes to the repo —
it only reads the candidate and the current data files and reports.

Usage:
    python3 scripts/validate_candidate.py path/to/candidate.json
    python3 scripts/validate_candidate.py path/to/candidate.json --json

Exit code 0 = candidate is safe to preview/apply.
Exit code 1 = candidate rejected; do not apply.
"""
import json
import os
import sys
from datetime import datetime, date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

VALID_EVENT_STATUSES = {"confirmed", "tentative", "cancelled", "postponed", "sold-out",
                        "expired", "superseded"}
VALID_GUIDE_STATUSES = {"coming-soon", "published", "paused", "planned"}
CANDIDATE_MARKER = "DBF_FRESHNESS_CANDIDATE"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_date(s):
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()


class Validator:
    def __init__(self, candidate, existing_events, existing_guides):
        self.candidate = candidate
        self.existing_events = existing_events
        self.existing_guides = {g["slug"]: g for g in existing_guides}
        self.errors = []
        self.warnings = []
        self.today = date.today()

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def run(self):
        self.check_marker()
        if self.errors:
            return self.result()
        self.check_timestamps()
        events = (self.candidate.get("activeEvents") or []) + (self.candidate.get("laterEvents") or [])
        self.check_events(events)
        self.check_duplicates(events)
        self.check_coming_soon(self.candidate.get("comingSoonUpdates") or [])
        self.check_expire_ids(self.candidate.get("expireEventIds") or [])
        return self.result()

    def check_marker(self):
        if self.candidate.get("candidateMarker") != CANDIDATE_MARKER:
            self.error(
                f'This file is not marked as a DBF freshness candidate '
                f'(expected candidateMarker: "{CANDIDATE_MARKER}"). Refusing to treat it as trusted input.'
            )

    def check_timestamps(self):
        if not self.candidate.get("generatedAt"):
            self.error("Candidate is missing generatedAt — cannot tell when this research was produced.")
        if not self.candidate.get("verifiedAt"):
            self.error("Candidate is missing verifiedAt — cannot confirm the events were actually checked, not guessed.")
        else:
            try:
                parse_date(self.candidate["verifiedAt"])
            except ValueError:
                self.error(f'verifiedAt "{self.candidate["verifiedAt"]}" is not a valid YYYY-MM-DD date.')

    def check_events(self, events):
        for i, e in enumerate(events):
            label = e.get("title") or f"event #{i+1}"
            required = ["title", "town", "startDate", "endDate", "status"]
            for field in required:
                if not e.get(field):
                    self.error(f'"{label}": missing required field "{field}".')
            status = e.get("status")
            if status and status not in VALID_EVENT_STATUSES:
                self.error(f'"{label}": unknown status "{status}". Must be one of {sorted(VALID_EVENT_STATUSES)}.')
            start = end = None
            try:
                start = parse_date(e.get("startDate"))
            except ValueError:
                self.error(f'"{label}": startDate "{e.get("startDate")}" is not a valid YYYY-MM-DD date.')
            try:
                end = parse_date(e.get("endDate"))
            except ValueError:
                self.error(f'"{label}": endDate "{e.get("endDate")}" is not a valid YYYY-MM-DD date.')
            if start and end and end < start:
                self.error(f'"{label}": endDate ({end}) is before startDate ({start}) — date reversal.')
            if end and end < self.today and status != "expired":
                self.error(
                    f'"{label}": proposed as active/upcoming but its endDate ({end}) has already passed. '
                    f'Already-expired events must be submitted as historical, not active.'
                )
            if status == "confirmed" and not (e.get("sourceUrl") or e.get("sourceOrg")):
                self.error(f'"{label}": status is "confirmed" but has no sourceUrl or sourceOrg to back it up.')
            if status in ("cancelled", "postponed") and not e.get("editorialNote"):
                self.warn(f'"{label}": status is "{status}" but has no editorialNote explaining it.')
            if not e.get("verifiedAt"):
                self.error(f'"{label}": missing verifiedAt — every proposed event needs its own verification timestamp.')

    def check_duplicates(self, events):
        seen = {}
        existing_keys = {
            (e.get("title", "").strip().lower(), e.get("startDate"), e.get("town", "").strip().lower())
            for e in self.existing_events
        }
        for e in events:
            key = (e.get("title", "").strip().lower(), e.get("startDate"), e.get("town", "").strip().lower())
            if key in seen:
                self.error(f'Duplicate event in candidate: "{e.get("title")}" on {e.get("startDate")} in {e.get("town")}.')
            seen[key] = True
            if key in existing_keys:
                self.warn(f'"{e.get("title")}" on {e.get("startDate")} already exists in events.json — will be treated as an update, not a new record.')

    def check_coming_soon(self, updates):
        for u in updates:
            slug = u.get("slug")
            if not slug:
                self.error("A comingSoonUpdates entry is missing slug.")
                continue
            if slug not in self.existing_guides:
                self.error(f'comingSoonUpdates references unknown guide slug "{slug}".')
                continue
            status = u.get("status")
            if status and status not in VALID_GUIDE_STATUSES:
                self.error(f'"{slug}": unknown guide status "{status}". Must be one of {sorted(VALID_GUIDE_STATUSES)}.')
            if status == "published" and not u.get("href"):
                self.error(f'"{slug}": marked published but no href given — the guide page must already exist before this flip.')
            if not u.get("lastReviewed"):
                self.error(f'"{slug}": comingSoonUpdates entry missing lastReviewed date.')

    def check_expire_ids(self, ids):
        existing_ids = {e.get("id") for e in self.existing_events}
        for eid in ids:
            if eid not in existing_ids:
                self.warn(f'expireEventIds references "{eid}", which is not currently in events.json (may already be archived).')

    def result(self):
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "ok": len(self.errors) == 0,
        }


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv
    if not args:
        print("Usage: python3 scripts/validate_candidate.py path/to/candidate.json [--json]")
        return 2
    candidate_path = args[0]
    if not os.path.exists(candidate_path):
        print(f"Candidate file not found: {candidate_path}")
        return 2
    try:
        candidate = load_json(candidate_path)
    except json.JSONDecodeError as e:
        print(f"Candidate is not valid JSON: {e}")
        return 1

    existing_events_doc = {}
    events_path = os.path.join(DATA, "events.json")
    if os.path.exists(events_path):
        existing_events_doc = load_json(events_path)
    existing_events = existing_events_doc.get("events", [])

    guides_path = os.path.join(DATA, "guides.json")
    existing_guides = load_json(guides_path) if os.path.exists(guides_path) else []

    validator = Validator(candidate, existing_events, existing_guides)
    result = validator.run()

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        if result["errors"]:
            print(f"REJECTED — {len(result['errors'])} error(s):")
            for e in result["errors"]:
                print(f"  ✗ {e}")
        else:
            print("Candidate passes validation.")
        if result["warnings"]:
            print(f"\n{len(result['warnings'])} warning(s) (non-blocking):")
            for w in result["warnings"]:
                print(f"  ! {w}")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
