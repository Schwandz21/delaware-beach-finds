# DBF Freshness Candidate Schema

A **candidate file** is the only way new event or "Coming Soon" data
enters the live site. It is produced by the weekly research task (see
`CLAUDE_WEEKLY_FRESHNESS_PROMPT.md`), checked by
`scripts/validate_candidate.py`, previewed and applied by
`UPDATE_DBF_FRESHNESS.command`. Nothing here is ever written directly by
an automated process — a human runs the updater and approves every step.

## Top-level fields

| Field | Required | Notes |
|---|---|---|
| `candidateMarker` | yes | Must be exactly `"DBF_FRESHNESS_CANDIDATE"`. Anything else is rejected outright. |
| `generatedAt` | yes | ISO 8601 timestamp of when the research ran. |
| `verifiedAt` | yes | `YYYY-MM-DD` — the date the facts were actually checked. |
| `editorialPeriodCovered` | no | Human-readable, e.g. `"Aug 1 – Aug 15, 2026"`. |
| `activeEvents` | no | Array of event objects (see below) — near-term events. |
| `laterEvents` | no | Array of event objects — further-out events worth flagging now. |
| `expireEventIds` | no | Array of event `id` strings to move from `events.json` to `events-archive.json`. |
| `cancelledOrPostponed` | no | Array of `{id, status, note}` — flips an existing event's status. |
| `comingSoonUpdates` | no | Array of guide status/review updates (see below). |
| `reviewNotes` | no | Free text — the human-readable summary. |
| `sourceUrls` | no | Flat list of every source URL used this run. |
| `validationWarnings` | no | The research task's own notes on anything uncertain. |

## Event object (`activeEvents` / `laterEvents`)

Matches `data/events.json`'s per-event schema:

```
title, description, town, venue, category,
startDate, endDate,        // YYYY-MM-DD, required
startTime, endTime,        // "HH:MM" 24h or null — never invent a time
displayDate,                // human-readable date text for the card
sourceUrl, sourceOrg,       // at least one required if status is "confirmed"
verifiedAt,                 // YYYY-MM-DD, required per-event
status,                     // confirmed | tentative | cancelled | postponed | sold-out | expired
featured,                   // bool
editorialNote,               // required (recommended) when status is cancelled/postponed
scene, relatedUrl,
archiveEligible,             // bool, defaults true
access_level                 // "public" — this system does not support "premium" yet
```

`id` is optional in a candidate — the updater generates a stable slug-based
id (`evt-{title-slug}-{startDate}`) if one isn't supplied.

## `comingSoonUpdates` entry

```
{
  "slug": "beach-access-parking",   // must already exist in data/guides.json
  "status": "coming-soon" | "published" | "paused" | "planned",
  "lastReviewed": "YYYY-MM-DD",      // required
  "href": "...",                     // required only if status is "published"
  "note": "..."                      // optional, human context
}
```

The research task should almost always propose `"coming-soon"` with a
refreshed `lastReviewed` — flipping something to `"published"` is a human
decision made only after the guide page itself has actually been built.

## Validation rules (enforced by `scripts/validate_candidate.py`)

- `candidateMarker` must match exactly, or the file is rejected before
  anything else is checked.
- `generatedAt` and `verifiedAt` are required and must parse.
- Every event needs `title`, `town`, `startDate`, `endDate`, `status`,
  and its own `verifiedAt`.
- `status` must be one of the controlled values — unknown statuses are
  rejected, not silently accepted.
- `endDate` cannot be before `startDate` (date reversal).
- An event cannot be proposed as active/upcoming if its `endDate` has
  already passed — that's a historical record, not a candidate for
  `events.json`.
- `status: "confirmed"` requires a `sourceUrl` or `sourceOrg`.
- Duplicate events (same title + startDate + town) within the candidate
  are rejected; a duplicate against an *existing* event is a warning
  (treated as an update, not blocked).
- `comingSoonUpdates` entries must reference a real guide `slug`, use a
  valid status, and include `lastReviewed`; `"published"` additionally
  requires `href`.

Any error rejects the whole candidate — nothing partial is ever applied.
Warnings are shown but don't block.

See `automation/sample-valid-candidate.json` and
`automation/sample-rejected-candidate.json` for worked examples, and run:

```
python3 scripts/validate_candidate.py automation/sample-valid-candidate.json
python3 scripts/validate_candidate.py automation/sample-rejected-candidate.json
```
