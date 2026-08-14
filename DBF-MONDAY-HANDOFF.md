# Delaware Beach Finds — Handoff / Savepoint

**Last updated:** 2026-08-14 (operationalization sprint)

## State

| | |
| --- | --- |
| Final branch | `feature/dbf-editorial-ui-overhaul-2026-08-13` (preserved, not deleted) |
| Final commit on branch | `c6ec545` |
| Merge commit on `main` | `9b78189` |
| Merged | **Yes** — `--no-ff` into `main` |
| Pushed | **Yes** — `ef147ad..9b78189` |
| Production verified | **Yes** — see below |
| Deploy mechanism | GitHub Pages from `main`, CNAME `delawarebeachfinds.com` |

### Production checks (all 200)
`/` · `/advertise.html` · `/this-week.html` · `/archive.html` ·
`/stories/towers-on-the-dunes.html` · `/shop.html`

Live content confirmed: DBF Weekend franchise present; nav reads
Homes & Design / Delaware Stories / Field Notes / This Week / Explore / About;
Advertise link in footer; Etsy storefront intact; `dbf-weekend` renders above
`the-edit`; GA id `G-XR94ZKCF9J` served from `config.js`; all 4 new events live.

## !! UNPUSHED WORK ON LOCAL main !!

The git credential on this Mac **expired during the final sprint**. Local `main`
is one commit ahead of production:

| | |
| --- | --- |
| Local `main` | `a0ffdc5` — "Verified audience metrics layer" |
| Remote `main` (live) | `a44ab77` |

Everything from the earlier sprints **is live**. Only the audience-metrics layer
is waiting. Working tree is clean; nothing is lost.

**First thing Monday:** re-authenticate, then `git push origin main`.

```
gh auth login          # or refresh the PAT in the macOS keychain
git push origin main
```

## Scheduled publisher — STATUS: MANUAL GITHUB PASTE STILL REQUIRED

One install attempt was made this sprint and rejected; the local commit was
backed out so `main` has no divergence from that attempt. `.github/` on the
remote still contains only `freshness-check.yml`.

Everything the workflow needs is already on remote `main` (`validate_editorial.py`,
`publish_due.py`, `run_tests.sh`, `editorial-calendar.json`, `authors.json`), so
the workflow will work the moment the file exists.

**Install it in 5 steps:**

1. Open <https://github.com/Schwandz21/delaware-beach-finds> → **Add file** → **Create new file**
2. Filename: `.github/workflows/publish-scheduled.yml` (typing each `/` creates the folder)
3. Paste the entire contents of `automation/publish-scheduled.WORKFLOW.yml`
4. **Commit changes…** → commit directly to `main`
5. **Actions** → "Publish scheduled stories" → **Run workflow** with `dry_run = true`

Expected first run: nothing publishes, because nothing approved and scheduled is
due. That is the correct result, not a failure.

## Audience metrics — ready to fill

`data/audience-metrics.json` is the single source. Eight slots, all currently
`null`, so the advertise page makes **no audience claim at all** today — the
section hides itself entirely.

To go live Monday: set `value`, `verifiedAt` (the day you read it), `period` and
`source` on each metric you have ground-truthed, then:

```
python3 scripts/validate_editorial.py
```

The validator **refuses** a value without `verifiedAt` or `source`, a
future-dated verification, an empty metric that claims verification, and
duplicate keys. Verified by negative test: a bare number fails with exit 1 and
cannot reach production. A metric older than `staleAfterDays` (120) stops
rendering until re-checked.

No code or design change is needed — fill the file, validate, deploy.

## Advertise page

**Path:** `/advertise.html` — <https://delawarebeachfinds.com/advertise.html>

Flagship product **DBF Weekend Partner** (four-week integrated sponsorship),
with **DBF Feature Partner** and **DBF Seasonal Partner** beneath it. Founding
Partner section with no invented count and no published pricing. Contact routes
to `contact.html` and `michael@rentdelawarebeaches.com` (existing address; none
invented). Prints to PDF cleanly as an interim leave-behind.

**No** metrics, clients, testimonials, campaign results, prices, or guarantees.

## DBF Weekend — implementation state

Live as a named franchise on the homepage (`#dbf-weekend`): own nameplate,
standing line, real event data from `data/events.json`, links to This Week and
Events. **Not yet** a distinct page or archive of its own.

**Sponsor slot:** `data-mount="franchise-sponsor"` reads `data/sponsors.json`
(currently `[]`). Renders only for a record with `franchise`, `name`, `url` and
a current date window. With no sponsor it draws nothing — `:empty` hides it.
To sell it: add one record, no code change.

## Analytics added

`sponsor_click` · `advertise_page_view` · `advertiser_contact_click` ·
`advertising_product_interest` — all on the existing `gtag` convention in
`assets/js/site.js`. No second analytics system. Sponsor outbound links use
`data-sponsor-link`.

## Scheduled GitHub workflow — NOT INSTALLED

`automation/publish-scheduled.WORKFLOW.yml` is paste-ready. `.github/` is
untouched because the token lacks the `workflow` scope. Nothing publishes
automatically until it is created at `.github/workflows/publish-scheduled.yml`
via the GitHub web UI. With nothing scheduled it is safe to install any time.

## Known limitations

- Scheduled publishing is manual (`python3 scripts/publish_due.py`) until the
  workflow is installed.
- No newsletter, TikTok or app. The advertise page describes these as in
  development and never as existing reach.
- Instagram has no API: featured permalink in `data/instagram.json` is manual.
- `admin/editorial-planner.html` exports JSON; it cannot save to the repo.
- No audience metrics anywhere on the site. Deliberate — nothing unverified.

## Photography needs (blocking, see `automation/PHOTOGRAPHY_REQUIREMENTS.md`)

1. **Cape Henlopen / fire-control tower, min 2000px wide, landscape, golden
   hour.** `cape-henlopen-aerial-1.jpg` is 387×258 — the only low-res raster in
   the library and it belongs to the current cover story. The homepage cover is
   deliberately type-led because of it. On replacement: drop the file in, set
   `heroImage`, run `render_story.py`, delete the `max-width:387px` cap in the
   ITERATION 3 block of `styles.css`.
2. Vertical (4:5) coastal portrait for cover variety.
3. Detail/texture frames (dune fence, marsh grass, boardwalk plank).
4. Homes & Design interior/architectural frame.

## Monday

1. Ground-truth current audience metrics (IG, GA4) — nothing goes on the site unverified.
2. Formal DBF Media Network inventory.
3. Finalise DBF Weekend v1 (consider its own page + archive).
4. Advertiser tracking/reporting from real GA4 data.
5. Formal media kit.
6. Founding campaign pricing.
7. Prospect pipeline.
8. Launch-quality content bank.
9. Photography library integration.
10. Install the scheduled workflow.
