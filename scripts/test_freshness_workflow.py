#!/usr/bin/env python3
"""Regression tests for the daily freshness workflow's issue-reporting step.

The August 2026 outage: report text was interpolated into JavaScript source, so
a multiline warning produced an unterminated string literal and the step failed
with `SyntaxError: Invalid or unexpected token` every day from 08-01 to 08-11.

These tests pin the two properties that prevent it recurring:
  1. the workflow must not interpolate the report body into a script block
  2. the body builder must survive genuinely hostile text
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from build_freshness_issue_body import build  # noqa: E402

# The push credential in this environment lacks GitHub's `workflow` scope, so
# .github/workflows/ cannot always be updated from here. The paste-ready fixed
# workflow therefore lives at automation/freshness-check.FIXED.yml and is the
# authoritative artifact to test whenever it is present.
_FIXED = os.path.join(ROOT, "automation", "freshness-check.FIXED.yml")
_LIVE = os.path.join(ROOT, ".github", "workflows", "freshness-check.yml")
WORKFLOW = _FIXED if os.path.exists(_FIXED) else _LIVE

passed = failed = 0


def check(desc, ok, detail=""):
    global passed, failed
    if ok:
        print(f"  ok  - {desc}")
        passed += 1
    else:
        print(f"FAIL  - {desc}")
        if detail:
            print("        " + str(detail).replace("\n", "\n        "))
        failed += 1


# --- 1. The workflow must never interpolate the report body into a script ---
wf = open(WORKFLOW, encoding="utf-8").read()

check(
    "workflow does not interpolate a report body into a script block",
    "${{ steps.summary.outputs.body }}" not in wf,
    "found the exact expression that caused the August SyntaxError",
)

# Any ${{ }} inside a `script:` block is the same class of hazard. Allow only
# the github-script context globals, which are structural, not report text.
script_blocks = re.findall(r"script:\s*\|(.*?)(?=\n      - |\Z)", wf, re.S)
interpolations = []
for blk in script_blocks:
    interpolations += re.findall(r"\$\{\{\s*([^}]+?)\s*\}\}", blk)
check(
    f"no GitHub expression interpolated inside script blocks ({len(interpolations)} found)",
    not interpolations,
    interpolations,
)

check(
    "issue body is read from a file at runtime, not embedded",
    "readFileSync" in wf and "freshness-issue-body.md" in wf,
)

check(
    "status is still passed as a workflow output (guards remain functional)",
    "steps.summary.outputs.status" in wf,
)


# --- 2. The body builder must survive hostile text ---
HOSTILE = [
    'double "quotes" everywhere',
    "apostrophes: it's Delaware's coast",
    "backticks `like this` and ${notAnExpression}",
    "a URL: https://example.com/x?a=1&b=2#frag",
    "unicode: — … ’ 🦀 café",
    "markdown **bold** _em_ [link](https://x.com)",
    "a literal EOF line follows",
    "EOF",
    "trailing backslash \\",
    "</script><script>alert(1)</script>",
]

status, body = build({"overallStatus": "REVIEW NEEDED", "warnings": HOSTILE}, "success")

check("hostile warnings all survive into the body", all(h in body for h in HOSTILE))
check("body is multiline (the exact shape that broke the old workflow)", "\n" in body)
check("status enum stays clean and shell-safe", status == "REVIEW NEEDED")

# A literal "EOF" line would have prematurely closed the old GITHUB_OUTPUT
# heredoc. It must never reach GITHUB_OUTPUT now.
with tempfile.TemporaryDirectory() as td:
    report_p = os.path.join(td, "r.json")
    body_p = os.path.join(td, "b.md")
    status_p = os.path.join(td, "out.txt")
    json.dump({"overallStatus": "REVIEW NEEDED", "warnings": HOSTILE}, open(report_p, "w"))

    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "build_freshness_issue_body.py"),
         "--report", report_p, "--tests-outcome", "success",
         "--body-out", body_p, "--status-out", status_p],
        capture_output=True, text=True,
    )
    check("builder exits cleanly on hostile input", r.returncode == 0, r.stderr)

    written_status = open(status_p, encoding="utf-8").read()
    check("only the status enum reaches GITHUB_OUTPUT",
          written_status.strip() == "status=REVIEW NEEDED", repr(written_status))
    check("no report text leaks into GITHUB_OUTPUT",
          not any(h in written_status for h in HOSTILE))
    check("body file round-trips hostile text intact",
          all(h in open(body_p, encoding="utf-8").read() for h in HOSTILE))

# --- 3. Failed tests must escalate status even when the report says OK ---
s2, b2 = build({"overallStatus": "OK", "warnings": []}, "failure")
check("a failed test run escalates status to REVIEW NEEDED", s2 == "REVIEW NEEDED")
check("a failed test run explains itself in the body", "run_tests.sh failed" in b2)

# --- 4. A missing/corrupt report is a finding, not a crash ---
with tempfile.TemporaryDirectory() as td:
    body_p = os.path.join(td, "b.md")
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "build_freshness_issue_body.py"),
         "--report", os.path.join(td, "missing.json"), "--body-out", body_p],
        capture_output=True, text=True,
    )
    check("missing report is reported, not fatal",
          r.returncode == 0 and "REVIEW NEEDED" in r.stdout, r.stdout + r.stderr)

# Loud, non-fatal notice while the live workflow still awaits a manual paste.
if os.path.exists(_FIXED) and os.path.exists(_LIVE):
    if open(_FIXED, encoding="utf-8").read() != open(_LIVE, encoding="utf-8").read():
        print()
        print("  NOTE - .github/workflows/freshness-check.yml still differs from the")
        print("         fixed version. Paste automation/freshness-check.FIXED.yml over")
        print("         it via the GitHub web UI to activate the repair.")

print()
print("================================")
print(f"Passed: {passed}   Failed: {failed}")
sys.exit(1 if failed else 0)
