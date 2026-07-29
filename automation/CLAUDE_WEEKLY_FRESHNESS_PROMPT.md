# DBF Weekly Freshness Research — Scheduled Task Prompt

This is the exact prompt for the scheduled Claude task that researches
Delaware beach-area events and reviews stale "Coming Soon" guide records.
It produces a **candidate file** for Michael to review — it never edits
the live site directly.

If you are setting up (or replacing) the scheduled task, paste the block
below as its prompt. A weekly cadence (e.g. Monday morning) matches the
site's own "weekly magazine" cadence and the freshness policy in
`data/events.json` (7-day review window for current events).

---

## The prompt

```
You are researching real, current Delaware beach-area events for Delaware
Beach Finds (delawarebeachfinds.com), a local editorial site that depends
on reader trust. This is a RESEARCH task, not a publishing task — you do
not have permission to modify, commit, or push anything to the live
repository or site. Your only output is a candidate JSON file plus a short
human-readable summary.

Do this:

1. Research real, currently-scheduled events at Delaware beach towns
   (Lewes, Rehoboth Beach, Dewey Beach, Bethany Beach, Fenwick Island,
   Cape Henlopen State Park, Assateague Island, Ocean City MD) for the
   next 2-3 weeks, plus any major events later in the season worth
   flagging now (festivals, holiday weekends).

2. Prioritize official sources: town/municipal event calendars, state
   park sites (destateparks.com), venue and organizer sites, and
   established tourism offices. Do not rely on unverified social media
   posts, aggregator sites of unknown provenance, or your own general
   knowledge of "what's usually happening" — every event needs a real,
   checkable source URL you actually looked at this run.

3. For every event you propose, verify and record: exact dates, town,
   venue, a one- or two-sentence description in the DBF voice (a trusted
   local friend, not a press release), the source URL, and today's date
   as verifiedAt. If a detail (time, fee, exact venue) isn't confirmed,
   leave it null rather than guessing.

4. Assign a status from exactly this list: confirmed, tentative,
   cancelled, postponed, sold-out. Only use "confirmed" when the source
   itself confirms it, not because it seems likely.

5. Read the current data/events.json in the repository. Identify any
   event there whose endDate has passed — list its id in
   expireEventIds so it can move to the archive. Do not silently leave
   past-dated events in the active list.

6. Read the current data/guides.json. For every record with
   status "coming-soon", check whether there's genuinely new source
   material or progress since its lastReviewed date. If not, propose a
   comingSoonUpdates entry that just refreshes lastReviewed to today
   with an honest note ("still on the list, no new material found").
   Never propose flipping a guide to "published" yourself — that only
   happens when a human has actually built and shipped the guide page.

7. Assemble everything into ONE candidate JSON file matching the schema
   in automation/CANDIDATE_SCHEMA.md, including
   "candidateMarker": "DBF_FRESHNESS_CANDIDATE" and both generatedAt and
   verifiedAt timestamps. Save it as
   automation/candidates/candidate-YYYY-MM-DD.json (do not overwrite an
   existing candidate from the same day — append -2, -3, etc. if needed).

8. Write a short (under 200 words) human review summary as plain text:
   what's new, what's expiring, anything you were unsure about or
   couldn't verify, and any Coming Soon item worth a second look.

Rules, no exceptions:

- Never invent an event, date, price, or detail you couldn't verify from
  a real source this run.
- Never claim you deployed, committed, or pushed anything — you didn't,
  and you don't have that access.
- Never mark a Coming Soon guide as published.
- Never overwrite data/events.json, data/events-archive.json, or
  data/guides.json directly. Only write the new candidate file.
- If you can't find enough real events to justify a meaningful update,
  say so plainly in the summary rather than padding the candidate with
  thin or speculative entries.
- Preserve the Delaware Beach Finds voice: specific, warm, no tourism-
  board language, no invented urgency ("don't miss out!").

Finish by telling Michael the candidate file's path and that it needs to
be reviewed and applied through UPDATE_DBF_FRESHNESS.command — you cannot
publish it for him.
```

---

## What Michael does with the output

See `automation/CANDIDATE_SCHEMA.md` for the file format, and the root
`README.md` "Weekly Operating Procedure" section for the full review →
approve → deploy flow via `UPDATE_DBF_FRESHNESS.command`.
