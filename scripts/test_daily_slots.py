#!/usr/bin/env python3
"""Tests for the current-week Daily Slots surface.

Architectural rule under test:
  weekly issue  = immutable historical publication record
  daily-slots   = mutable current-week editorial surface
Ingestion may update the latter; it must never rewrite the former, and the
live renderer must never read data/issues/*.json.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from apply_candidate import build_daily_slots, DailySlotError  # noqa: E402

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


def refuses(desc, candidate):
    try:
        build_daily_slots(candidate)
        check(desc, False, "expected DailySlotError, got success")
    except DailySlotError:
        check(desc, True)


DATA = json.load(open(os.path.join(ROOT, "data", "daily-slots.json")))
SITE_JS = open(os.path.join(ROOT, "assets", "js", "site.js"), encoding="utf-8").read()
THIS_WEEK = open(os.path.join(ROOT, "this-week.html"), encoding="utf-8").read()

# --- 1. data layer ---
check("daily-slots.json has a slots array", isinstance(DATA.get("slots"), list))
check("carries weekOf and verifiedAt", bool(DATA.get("weekOf")) and bool(DATA.get("verifiedAt")))
check("every slot has a real YYYY-MM-DD date",
      all(isinstance(s.get("date"), str) and len(s["date"]) == 10 for s in DATA["slots"]))
check("every slot has a headline", all(s.get("headline") for s in DATA["slots"]))
check("records provenance back to its candidate", bool(DATA.get("sourceCandidate")))

# --- 2. faithful to the accepted candidate (no re-dating, no merging) ---
cand_path = DATA.get("sourceCandidate")
if cand_path and os.path.exists(os.path.join(ROOT, cand_path)):
    cand = json.load(open(os.path.join(ROOT, cand_path)))
    check("slots are byte-identical to the accepted candidate's dailySlots",
          DATA["slots"] == cand["dailySlots"])
    check("slot count matches the candidate exactly",
          len(DATA["slots"]) == len(cand["dailySlots"]))

# --- 3. historical separation ---
check("renderer never reads data/issues/ for daily material",
      "daily-slots.json" in SITE_JS and
      "issues/" not in SITE_JS.split("data-mount=\"daily-slots\"")[1].split("Past Issues")[0])
w33 = json.load(open(os.path.join(ROOT, "data", "issues", "2026-W33.json")))
check("W33 issue record still holds its own original slots (not overwritten)",
      len(w33.get("dailySlots", [])) == 5)
check("W33 slots and current-week slots are genuinely separate sets",
      not ({s["headline"] for s in w33["dailySlots"]} & {s["headline"] for s in DATA["slots"]}))

# --- 4. renderer contract ---
check("renderer uses the site's Eastern-time date helper", "todayEasternISO()" in SITE_JS)
check("renderer selects strictly by exact date (no future leakage)",
      "s.date === today" in SITE_JS)
check("renderer self-hides via the shared gate helper",
      "gateHide(dailyMount)" in SITE_JS)
check("renderer honours a freshness policy", "freshnessPolicyDays" in SITE_JS)
check("renderer drops slots with a malformed/absent date rather than guessing",
      r"/^\d{4}-\d{2}-\d{2}$/.test(s.date)" in SITE_JS and
      "typeof s.date === 'string'" in SITE_JS)
check("external source links are marked as leaving the site",
      "opens external site" in SITE_JS)

# --- 5. public placement ---
check("mounted on this-week.html", 'data-mount="daily-slots"' in THIS_WEEK)
check("mount opts into gating so it can hide cleanly", "data-gate-hide" in THIS_WEEK)
check("mounted above the calendar",
      THIS_WEEK.index('data-mount="daily-slots"') < THIS_WEEK.index('data-mount="weekend"'))

# --- 6. ingestion: faithful, validating, loud ---
GOOD = {"weekOf": "2026-08-10", "verifiedAt": "2026-08-12",
        "dailySlots": [{"date": "2026-08-12", "day": "Wednesday", "kind": "x",
                        "headline": "H", "note": "N", "ref": None}]}
out = build_daily_slots(GOOD)
check("ingestion preserves slot data faithfully", out["slots"] == GOOD["dailySlots"])
check("ingestion carries weekOf/verifiedAt through",
      out["weekOf"] == "2026-08-10" and out["verifiedAt"] == "2026-08-12")

empty = build_daily_slots({"weekOf": "w", "verifiedAt": "v", "dailySlots": []})
check("explicitly empty list yields an explicitly empty file (no stale carry-forward)",
      empty is not None and empty["slots"] == [])
check("absent dailySlots key leaves the existing file untouched",
      build_daily_slots({"weekOf": "w"}) is None)

refuses("refuses a slot with no date (never infers one)",
        {"dailySlots": [{"headline": "H"}]})
refuses("refuses a non-ISO date",
        {"dailySlots": [{"date": "Aug 12 2026", "headline": "H"}]})
refuses("refuses an impossible calendar date",
        {"dailySlots": [{"date": "2026-02-30", "headline": "H"}]})
refuses("refuses a slot with no headline",
        {"dailySlots": [{"date": "2026-08-12"}]})
refuses("refuses dailySlots that is not a list",
        {"dailySlots": {"date": "2026-08-12"}})
refuses("refuses a non-object slot",
        {"dailySlots": ["just a string"]})

print()
print("================================")
print(f"Passed: {passed}   Failed: {failed}")
sys.exit(1 if failed else 0)
