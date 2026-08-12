#!/usr/bin/env python3
"""Turn a freshness report into (a) a status enum and (b) an issue-body file.

Why this exists
---------------
The daily freshness workflow used to build the GitHub issue body by
interpolating generated report text straight into JavaScript source:

    const body = [ "...", "${{ steps.summary.outputs.body }}", ... ]

GitHub substitutes that expression *before* the JavaScript is parsed, so the
moment the report contained a newline the literal was unterminated and the step
died with `SyntaxError: Invalid or unexpected token`. Every run from
2026-08-01 to 2026-08-11 failed this way. It only started then because the step
is guarded by `if: status != 'OK'` — while the data was fresh the step never
ran, so the latent bug stayed invisible for three days.

The durable fix is to stop treating generated prose as code:

* the STATUS (a short, known-safe enum) goes to GITHUB_OUTPUT
* the BODY (arbitrary text) is written to a FILE the workflow reads with
  fs.readFileSync — data, never source

That is safe for quotes, apostrophes, backticks, ${...}, newlines, Unicode,
URLs, Markdown, and a literal "EOF" line (which would otherwise terminate a
GITHUB_OUTPUT heredoc early).

Usage:
    python3 scripts/build_freshness_issue_body.py \
        --report freshness-report.json \
        --tests-outcome success \
        --body-out freshness-issue-body.md \
        --status-out "$GITHUB_OUTPUT"
"""
import argparse
import json
import sys

TESTS_FAILED_NOTE = (
    "scripts/run_tests.sh failed — see the 'Run deterministic test suite' "
    "step log for detail."
)


def build(report, tests_outcome):
    """Return (status, body_markdown). Pure function so tests can hit it."""
    status = report.get("overallStatus", "UNKNOWN")
    warnings = list(report.get("warnings", []))

    if tests_outcome == "failure":
        status = "REVIEW NEEDED"
        warnings.append(TESTS_FAILED_NOTE)

    if warnings:
        body = "\n".join("- " + str(w) for w in warnings)
    else:
        body = "- (no warnings reported)"

    return status, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--tests-outcome", default="success")
    ap.add_argument("--body-out", required=True)
    ap.add_argument("--status-out")
    args = ap.parse_args()

    try:
        with open(args.report) as f:
            report = json.load(f)
    except Exception as exc:  # a broken/missing report is itself a finding
        report = {
            "overallStatus": "REVIEW NEEDED",
            "warnings": [f"Could not read {args.report}: {exc}"],
        }

    status, body = build(report, args.tests_outcome)

    with open(args.body_out, "w", encoding="utf-8") as f:
        f.write(body)

    # Only the enum crosses into the workflow's variable space.
    if args.status_out:
        with open(args.status_out, "a", encoding="utf-8") as f:
            f.write(f"status={status}\n")

    print(f"status={status}")
    print(f"wrote {args.body_out} ({len(body)} chars, {body.count(chr(10)) + 1} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
