# Delaware Beach Finds: editorial autopilot research run

This is the canonical prompt for the scheduled, repository-connected Claude
Code task that keeps the story runway full. Paste it, or point the scheduled
task at this file. It is the only automated process that writes new stories.

## The service level

* A new story about every **48 hours**.
* Never a planned gap longer than **72 hours**.
* Runway: at least **5** future scheduled stories and **10 days** of coverage.

Weekly issues organise stories; they are not the cadence. The hourly publisher
(`.github/workflows/publish-scheduled.yml` → `scripts/publish_due.py`)
publishes scheduled stories when they come due. **You never publish.** You
never set `status: published`, never edit `publishedAt`, and never run
`publish_due.py` without `--dry-run`.

## Each run

1. **Sync.**
   ```
   git fetch origin && git checkout main && git pull --ff-only origin main
   ```
2. **Measure.**
   ```
   python3 scripts/editorial_autopilot.py --status
   python3 scripts/editorial_autopilot.py --prepare
   ```
3. **If the runway is healthy**, meaning at least 5 scheduled stories, at
   least 10 days of runway and no planned gap over 72h, do **not** create
   filler. You may improve research notes for future topics. Then stop.
4. **Otherwise**, research enough high-quality stories to restore the
   runway. `--prepare` lists the slots needed (≈48h apart, Mondays preferred
   when a new issue week starts). Fill those slots and no more.
5. **Research** with current first-party and authoritative sources: town and
   city sites, DNREC and Delaware State Parks, the Division of Historical and
   Cultural Affairs, Delaware Public Archives, University of Delaware,
   Delaware Center for the Inland Bays, event organisers' own pages. Use
   secondary press only to corroborate.
   Priority beats: Lewes, Rehoboth, Dewey, Bethany, Fenwick, Cape Henlopen,
   Delaware Seashore State Park, the Inland Bays, coastal wildlife, Delaware
   history, seasonal practical knowledge, significant Sussex County coastal
   developments.
   * Check every date against its weekday. Search summaries mix years; an
     event "Wednesday, Oct. 8" cannot be 2026.
   * Where sources disagree, say so in the story or leave the claim out, and
     record the disagreement in `sourceNotes`.
   * Read `data/stories.json` first. Do not repeat a story already published
     or scheduled.
6. **Write complete stories, not outlines.** 450–1,000 words, in the house
   voice of the existing archive: useful, specific, plain. End each with a
   `Sources:` note that names the sources, says Delaware Beach Finds did not
   attend or visit where relevant, and tells readers to check organisers'
   current details.
7. **Never invent** quotes, visits, interviews, photos, observations, crowds,
   prices, access conditions, event times or historical claims. Never write
   in the first person about a visit. Never present a photograph as a place
   its record in `data/location-attributions.json` does not support. When no
   honest photo exists, use a house illustration (`*.svg` in
   `assets/images/scenes/`).
8. **Apply the policy** (`data/editorial-autopilot.json`,
   `automation/STORY_PACKAGE_SCHEMA.md`). A story is
   `autoApprovalEligible: true` only if it is in an auto-approvable risk class
   and meets every sourcing rule. Anything uncertain goes in as
   `autoApprovalEligible: false` with a `heldReason`. Never pad, guess, or
   lower the standard to hit a count. If a topic fails sourcing, replace it
   with a better-researched one; if none is available, leave the slot
   empty. The runway guard will raise it.
9. **Write the package** to
   `automation/story-packages/story_package_YYYY-MM-DD.json`, with
   `suggestedPublishAt` set from the `--prepare` slots.
10. **Ingest and validate.**
    ```
    python3 scripts/ingest_story_package.py automation/story-packages/story_package_YYYY-MM-DD.json --dry-run
    python3 scripts/ingest_story_package.py automation/story-packages/story_package_YYYY-MM-DD.json
    python3 scripts/editorial_autopilot.py --check
    python3 scripts/validate_editorial.py
    bash scripts/run_tests.sh
    python3 scripts/publish_due.py --dry-run
    ```
    If ingestion rejects the package, fix the story (or mark it held) and
    re-run. Never weaken a validator or a test to get through.
11. **Commit and push** only the package, the new prose in
    `content/stories/`, and `data/stories.json`, and only when every command
    above passes:
    ```
    git add automation/story-packages content/stories data/stories.json
    git commit -m "Autopilot: schedule <n> stories through <last publishAt>"
    git pull --rebase origin main && bash scripts/run_tests.sh && git push origin HEAD:main
    ```
    Do not force-push. If `main` moved, rebase, re-run the checks, push again.
12. **Report** the scheduled count, the next ten days of `publishAt` and
    headlines, the largest planned gap, the runway end, and every held story
    with its reason.

## Out of scope for this run

* Weekly issue records, daily slots and the event calendar. They still go
  through the weekly candidate workflow (`automation/CANDIDATE_SCHEMA.md`).
  The runway guard reports when they are stale.
* Editing or re-dating published stories.
* Anything in a held risk class, beyond writing it up as held.
