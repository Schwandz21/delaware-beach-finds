# Delaware Beach Finds — Editorial Operations

How to run the publication. Written for the editor-in-chief, not for a developer.

You do not need to touch HTML, CSS or Python to publish, schedule, hold, or
reschedule a story. You edit data files and run one or two commands.

---

## The one rule that governs everything

> **AI and research may prepare. Editorial approval authorizes. Automation publishes.**

Automation is allowed to publish a story **only** if all of these are true:

1. its `status` is exactly `scheduled`
2. it has an `approvedAt` date — meaning a human approved it
3. its `publishAt` time has arrived
4. the calendar is not paused, and the date is not in a blackout window

A draft cannot publish. A story in review cannot publish. An approved story with
no schedule cannot publish. A held story cannot publish. Nothing published by an
AI research pass reaches the public without you approving it first.

---

## Where things live

| What | File | This is the source of truth for |
| --- | --- | --- |
| Story queue | `data/stories.json` | status, schedule, placement, desk, SEO |
| Article prose | `content/stories/<slug>.html` | the words of the article |
| Publication schedule | `data/editorial-calendar.json` | cadence, pauses, blackouts |
| House desks | `data/authors.json` | bylines |
| Issues | `data/issues/` | which issue is current, issue history |
| Events | `data/events.json`, `data/events-archive.json` | what's on this week |
| Page shell | `templates/article.html` | how an article page is built |

Article pages under `stories/` are **generated**. Do not hand-edit them — your
change will be overwritten. Edit the prose file and re-render.

---

## The commands you actually need

```bash
python3 scripts/validate_editorial.py
```
Checks the queue, calendar and desks. Run this after any edit. Green means safe.

```bash
python3 scripts/publish_due.py --dry-run
```
Shows what *would* publish right now. Changes nothing.

```bash
python3 scripts/publish_due.py
```
Publishes everything that is due and approved. This is what the automation runs.

```bash
python3 scripts/render_story.py
```
Rebuilds article pages from the registry and prose.

```bash
bash scripts/run_tests.sh
```
The full suite. Run before you deploy anything.

---

## How do I schedule a story?

In `data/stories.json`, find the record and set:

```json
"status": "scheduled",
"approvedAt": "2026-08-20",
"publishAt": "2026-08-24T06:00",
"placement": "cover"
```

`approvedAt` is your signature. Without it the story will never publish, on
purpose. Then run `validate_editorial.py`.

## How do I change its publication time?

Change `publishAt`. Nothing else. If it has not published yet, that is all.

## How do I make a story the cover?

Set `"placement": "cover"`. When it publishes, it becomes the cover and the
previous cover is demoted automatically — demoted, **not** unpublished. The old
cover stays live at its own URL, stays in its issue, and stays in the archive.

## How do I hold a story?

```json
"status": "held",
"heldReason": "waiting on a source callback"
```

It stops being eligible immediately. To release it, set `status` back to
`scheduled` (keep `approvedAt`, adjust `publishAt` if the date has passed).

## How do I publish immediately?

```bash
python3 scripts/publish_due.py --slug my-story --force-now
```

This still refuses if the story has no `approvedAt`. It cannot be used to push
unapproved work live.

## How do I move a story to the next issue?

Change `publishAt` to a date in that week. Issue membership is derived from the
publication date — you do not set `issueId` by hand.

## How do I change the regular weekly cadence?

Edit `cadence` in `data/editorial-calendar.json`. Weekdays are `0`=Monday
through `6`=Sunday.

To move cover day from Monday to Tuesday:

```json
{ "placement": "cover", "weekday": 1, "time": "06:00" }
```

To give an eight-part series its own Thursday slot, add to `series`:

```json
{ "slug": "my-series", "weekday": 3, "time": "06:00" }
```

No code changes. A test covers this specifically.

## How do I pause publication?

```json
"paused": true
```

Everything stays scheduled and publishes when you set it back to `false`.

For a date range instead — Christmas week, say — add a blackout:

```json
"blackouts": [
  { "start": "2026-12-21", "end": "2026-12-27", "reason": "Christmas week" }
]
```

A story whose `publishAt` falls in a blackout is **skipped and reported**, never
silently dropped, and never republished twice.

---

## The editorial autopilot (story cadence)

Stories publish continuously. Weekly issues only organise them. The service
level, set in `data/editorial-autopilot.json`:

- a new story about every **48 hours**, never a planned gap over **72 hours**;
- a runway of at least **15** scheduled stories and **30 days**, researched up to **45 days** ahead.

How it runs:

1. A daily (about 04:00 America/New_York) repository-connected research task
   follows `automation/CLAUDE_EDITORIAL_AUTOPILOT_PROMPT.md`.
   When the runway is short, it researches and writes complete, sourced
   stories into `automation/story-packages/` (schema:
   `automation/STORY_PACKAGE_SCHEMA.md`).
2. `python3 scripts/ingest_story_package.py <package>` validates the
   package. Low-risk stories that meet every sourcing rule are
   **approved and scheduled** automatically (`approvedAt` + explicit
   `publishAt`). Anything else is **held** with a reason and never
   publishes until you approve it.
3. The hourly publisher, unchanged, publishes them when they're due.
4. `.github/workflows/editorial-runway-guard.yml` checks every 6 hours.
   When anything is wrong, it keeps one issue open, titled *DBF editorial
   autopilot: attention required*, and closes it when the runway is healthy
   again.
5. If no story has published for 72 hours, the homepage stops leading with
   a story. It shows a "This Week at the Delaware Coast" package built from
   the current issue, and never relabels an old story as new.

```bash
python3 scripts/editorial_autopilot.py --status    # the runway
python3 scripts/editorial_autopilot.py --prepare   # slots to fill
python3 scripts/runway_guard.py                    # the full failsafe check
```

To approve a held story: set `status` to `approved` with an `approvedAt`, then
run `python3 scripts/editorial_autopilot.py --schedule` to slot it.

## The story archive (back catalog)

Every published story older than the current issue is recorded in
`data/story-archive.json`, an append-only ledger of metadata. It holds no
prose. Each entry records the original date, the issue (null for the Aug. 19,
2026 stories, which predate issues; that is never back-filled), the prose and
page paths, and a SHA-256 of the canonical prose.

- `python3 scripts/build_story_archive.py` updates the ledger. The publisher
  runs it on every publication, so stories join the archive when their issue
  rolls over. `--check` verifies without writing.
- Entries are never removed. Dates and issues are frozen. To change archived
  prose, record why:
  `python3 scripts/build_story_archive.py --revise SLUG --reason "..."`.
  Otherwise the tests fail.
- `python3 scripts/export_story_archive.py` writes a private, checksummed owner
  copy to `private-exports/dbf-story-archive-YYYYMMDD.zip`. That folder is
  git-ignored. **Never commit an export.**
- `archive.html` lists the ledger with original dates. This-week stories are
  marked separately.

Premium access is **disabled** (`data/premium-archive.json`). See
`PREMIUM_ARCHIVE.md` for what it takes to enable it. It cannot be switched on
while archived full text is still public.

## How the event schedule works

Events are deliberately **not** on the story lifecycle. They move faster and are
verified differently.

1. **Research** runs weekly and produces a *candidate* file in
   `automation/candidates/`. Research never publishes.
2. **You review it.** Validate with `python3 scripts/validate_candidate.py <file>`.
3. **You apply it** with `python3 scripts/apply_candidate.py <file>`, which
   merges approved events into `data/events.json`.
4. **Expiry is automatic.** Events past their end date stop appearing in current
   surfaces on their own, and `scripts/archive_expired.py` moves them into
   `data/events-archive.json`, where they are preserved permanently.

Nothing about an event becomes public because research produced it. The apply
step is yours.

## How the archive works

Nothing is deleted. Ever.

- A published story stays published forever unless you deliberately retire it.
- When a new issue becomes current, the previous issue's **status** changes to
  `archived` — its file, its URL and its stories all remain.
- `data/content-index.json` (rebuilt automatically on publish) drives the
  archive page and search.

"Past Issues" means genuinely past issues. There are no invented back issues.

## How house bylines work

DBF publishes under **editorial desks**, not invented reporters. The desks are in
`data/authors.json`:

| Desk | Beat |
| --- | --- |
| DBF Coast & Nature Desk | Wildlife, ecology, marshes, dunes, weather, migration, conservation |
| First State History Desk | Delaware history, Native and colonial history, the Revolution, surveying, the Underground Railroad |
| Delaware Life Desk | Homes, architecture, objects, traditions, design |
| Field Notes | Short observational and practical local pieces |
| Delaware Beach Finds Editorial | Institutional stories, explainers, corrections, editor's notes |

Set a story's desk with `"author": "coast-nature"` (the desk `id`).

Validation **fails** if a desk is marked as anything other than `house_desk`.
That guard exists so the publication can never quietly start presenting a
fabricated person as a reporter.

---

## What happens automatically

Once the scheduled workflow is enabled, on its own:

- due + approved stories publish at their scheduled time
- each is assigned to the issue for its publication week
- the cover rotates, and the previous cover is demoted but stays published
- the issue index rolls, and the previous issue is archived
- article pages are generated with full SEO and structured data
- the archive and search index are rebuilt
- expired events drop out of current surfaces

## What still requires you

- **approving any story** (`approvedAt`) — always
- **approving event candidates** — always
- writing or editing prose
- choosing cover and placement
- changing cadence, pauses and blackouts
- updating the featured Instagram permalink (no API access — see Limitations)
- deploying

## What happens if automation fails

The publisher is **idempotent**: running it twice publishes nothing twice. If a
run fails partway, fix the cause and run it again — it recomputes from the
registry rather than from where it stopped.

If validation fails, publication stops and nothing is written. If the workflow
cannot run at all, nothing publishes and nothing is damaged; run
`python3 scripts/publish_due.py` locally and the same result is produced.
