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
