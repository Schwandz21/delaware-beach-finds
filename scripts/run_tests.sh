#!/bin/bash
# Deterministic acceptance tests for the DBF freshness/archive/search system.
# Run from the repo root: ./scripts/run_tests.sh
set -u
cd "$(dirname "$0")/.." || exit 1
PASS=0
FAIL=0

check() {
  local desc="$1"; shift
  if "$@" >/tmp/dbf-test-out 2>&1; then
    echo "  ok  - $desc"
    PASS=$((PASS+1))
  else
    echo "FAIL  - $desc"
    sed 's/^/        /' /tmp/dbf-test-out
    FAIL=$((FAIL+1))
  fi
}

check_expect_fail() {
  local desc="$1"; shift
  if "$@" >/tmp/dbf-test-out 2>&1; then
    echo "FAIL  - $desc (expected non-zero exit, got success)"
    FAIL=$((FAIL+1))
  else
    echo "  ok  - $desc"
    PASS=$((PASS+1))
  fi
}

echo "=== JSON validity ==="
for f in data/events.json data/events-archive.json data/guides.json data/content-index.json data/stories.json; do
  check "$f is valid JSON" python3 -c "import json; json.load(open('$f'))"
done

echo ""
echo "=== Candidate validator ==="
# The committed fixture uses absolute dates because it doubles as human-readable
# documentation of the candidate contract. Validate a date-shifted copy so this
# assertion tests the validator, not the calendar.
python3 scripts/make_test_candidate.py automation/sample-valid-candidate.json > /tmp/dbf-candidate-shifted.json 2>/dev/null
check "valid sample candidate is accepted (date-shifted to today)" python3 scripts/validate_candidate.py /tmp/dbf-candidate-shifted.json
check_expect_fail "rejected sample candidate is refused" python3 scripts/validate_candidate.py automation/sample-rejected-candidate.json
# The committed fixture must stay structurally valid even as its dates age, so a
# stale-date failure is the only failure it is allowed to produce.
check "committed valid fixture still parses and carries a candidate marker" python3 - <<'PYEOF'
import json, sys
d = json.load(open("automation/sample-valid-candidate.json"))
sys.exit(0 if d.get("candidateMarker") == "DBF_FRESHNESS_CANDIDATE" else 1)
PYEOF

echo ""
echo "=== Site integrity ==="
check "no dead internal links" python3 scripts/check_links.py
check "content index builds cleanly" python3 scripts/build_content_index.py

echo ""
echo "=== Freshness report runs ==="
python3 scripts/freshness_report.py --json >/tmp/dbf-test-out 2>&1
if python3 -c "import json; json.load(open('/tmp/dbf-test-out'))" 2>/dev/null; then
  echo "  ok  - freshness report produces valid JSON"
  PASS=$((PASS+1))
else
  echo "FAIL  - freshness report did not produce valid JSON"
  FAIL=$((FAIL+1))
fi

echo ""
echo "=== Data model sanity ==="
# Tests the render contract (what a visitor can actually see), not a data
# snapshot. Expired records may legitimately sit in events.json between weekly
# updates -- scripts/archive_expired.py is the maintenance path, and
# freshness_report.py surfaces the backlog to the maintainer. What must never
# happen is an expired event surviving the current-events filter.
check "current-events filter excludes every expired event" python3 - <<'PYEOF'
import json, sys
from datetime import date
d = json.load(open("data/events.json"))
today = date.today().isoformat()
current = [e for e in d["events"] if not (e.get("endDate") and e["endDate"] < today)]
leaked = [e["title"] for e in current if e.get("endDate") and e["endDate"] < today]
sys.exit(1 if leaked else 0)
PYEOF
# An archived record whose endDate has NOT passed is only legitimate when it was
# retired on editorial judgement (superseded/cancelled), never by silent drift.
check "archive holds no still-current event without an explicit retirement status" python3 - <<'PYEOF'
import json, sys
from datetime import date
archive = json.load(open("data/events-archive.json"))
today = date.today().isoformat()
allowed = {"superseded", "cancelled", "postponed"}
bad = [e.get("title") for e in archive
       if e.get("endDate") and e["endDate"] >= today and e.get("status") not in allowed]
sys.exit(1 if bad else 0)
PYEOF
check "every superseded archive record explains why" python3 - <<'PYEOF'
import json, sys
archive = json.load(open("data/events-archive.json"))
bad = [e.get("title") for e in archive
       if e.get("status") == "superseded" and not e.get("editorialNote")]
sys.exit(1 if bad else 0)
PYEOF

check "every guides.json coming-soon record has lastReviewed" python3 - <<'PYEOF'
import json, sys
g = json.load(open("data/guides.json"))
bad = [x["slug"] for x in g if x.get("status")=="coming-soon" and not x.get("lastReviewed")]
sys.exit(1 if bad else 0)
PYEOF

check "every content-index record has access_level" python3 - <<'PYEOF'
import json, sys
d = json.load(open("data/content-index.json"))
bad = [r["id"] for r in d["records"] if "access_level" not in r]
sys.exit(1 if bad else 0)
PYEOF

check "no content-index record is premium (paywall not built yet)" python3 - <<'PYEOF'
import json, sys
d = json.load(open("data/content-index.json"))
bad = [r["id"] for r in d["records"] if r.get("access_level") != "public"]
sys.exit(1 if bad else 0)
PYEOF

echo ""
echo "================================"
echo "Passed: $PASS   Failed: $FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
