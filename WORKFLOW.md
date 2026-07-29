# Running Delaware Beach Finds week to week

This site is still a plain static site — no build step, no server, no CMS login.
Everything that needs to change weekly lives in small JSON files under `/data/`,
and the pages read those files live in the browser. Editing a JSON file is the
entire publishing workflow for the sections below.

## What updates weekly (edit these files directly on GitHub)

| Homepage section | File | Notes |
|---|---|---|
| Feature Story (hero) | `data/feature-story.json` | One object: kicker, headline, teaser, scene, link. |
| Happening This Weekend / Events | `data/events.json` (+ `data/events-archive.json`) | Date-driven, not a manual edit — see **"Weekly Freshness & Archive System"** below. Don't hand-edit these two files; use `UPDATE_DBF_FRESHNESS.command`. |
| New on Instagram | `data/instagram.json` | Paste a real post/reel permalink into `permalink` once you have one — the embed goes live automatically. Leave it blank to show a fallback card that links to your Instagram profile instead. |
| Coastal Moments (video) | `data/coastal-moments.json` | Paste a Vimeo/YouTube link or a direct `.mp4/.webm/.mov` URL into `embedUrl` to show a real video. Leave it blank to show a fallback card that links to your Instagram profile instead. |
| Hidden Gem of the Week | `data/hidden-gems.json` | An array — add a new object at the top with `"current": true` and set the previous one to `false`. It becomes an archive automatically. |
| Community | `data/community.json` | See below — this is the one followers feed into. |

### Getting an Instagram permalink

Open the post or reel in the Instagram app or on instagram.com, tap the ···
menu, and choose Copy Link. That's the `permalink` value — paste it in
exactly as copied, no editing needed. There's no automatic "always show the
newest post" mode (Instagram's embed system requires a specific post's URL),
so this is a quick manual step each time you want to feature something new —
same 30-second update as everything else on this list.

To edit any of these on GitHub: open the file, click the pencil (edit) icon,
make the change, and commit to `main`. The live site updates within a minute
or two (GitHub Pages cache).

## Getting a follower's photo live (Community section)

You do not need to touch HTML for this.

1. Open **`admin/submit-helper.html`** in a browser (locally, or the GitHub
   Pages URL — it's not linked in the site nav, so visitors won't stumble
   onto it).
2. Fill in the feature type, name, handle and caption, and pick the photo
   file (this is just to generate a filename and preview — nothing uploads).
3. The tool gives you two things: the exact filename to save the photo as,
   and a ready-to-paste JSON snippet.
4. On GitHub: upload the photo into `assets/images/community/` using that
   filename, then open `data/community.json`, paste the snippet inside the
   array, and commit.

That's the whole process — roughly the same number of steps as reposting to
Instagram, and no code is ever touched.

### Entry types
- `photographer` — Photographer of the Week (one featured card)
- `dog` — Today's Beach Dog (one featured card)
- `fishing` — Favorite Fishing Photo (one featured card)
- `sunrise` — Your Sunrise grid (as many as you want; the six most recent show)

## Everything else (towns, stories, shop)

Town profiles, story articles and shop products don't rotate weekly, so
they're baked directly into their HTML pages rather than pulled from JSON.
To add a new story or town, the cleanest path is asking for one more page in
the same format — or duplicating an existing file under `/towns/` or
`/stories/` and editing the text directly.

## Weekly Freshness & Archive System

The site now keeps event data honest automatically instead of relying on
someone remembering to update it. Full detail lives in `automation/`, but
the short version:

- **`data/events.json`** holds only current/upcoming events with real
  `startDate`/`endDate` fields. The public site filters this by date at
  render time — an event past its `endDate` simply stops appearing,
  no redeploy required. If the file's own `verifiedAt` is more than 7
  days old, the calendar shows an honest "being verified" message instead
  of stale events.
- **`data/events-archive.json`** holds past events for the public
  [Archive](archive.html) — nothing gets deleted just because its date
  passed.
- **`data/content-index.json`** powers [Search](search.html) and the
  Archive. Rebuild it any time editorial content changes:
  `python3 scripts/build_content_index.py`
- **Coming Soon guides** (`data/guides.json`, `status: "coming-soon"`)
  carry `lastReviewed` + `reviewIntervalDays`. If a stub goes stale past
  its interval, the homepage/hub automatically relabels it from
  "Coming Soon" to "On Our List" rather than an indefinite false promise.

### The weekly loop

1. A scheduled Claude task (`dbf-weekly-freshness-research`, see
   `automation/CLAUDE_WEEKLY_FRESHNESS_PROMPT.md`) researches real events
   and writes a candidate file to `automation/candidates/`. It cannot
   publish anything itself.
2. Read its summary. Double-click **`UPDATE_DBF_FRESHNESS.command`**.
3. Select the candidate file. The updater validates it, shows a
   plain-language preview of every change, and waits for your yes before
   touching anything.
4. Approve → it backs up current data to `backups/`, applies the
   changes, rebuilds the search index, runs link/JSON checks, then asks
   again before committing, and again before pushing to `origin/main`.
5. It polls the live site and reports success or the exact failure.

No manual JSON editing or git commands required. Cancel at any prompt and
nothing beyond that point happens.

To check freshness status any time without running a full update:
`python3 scripts/freshness_report.py`

## Deployment

Unchanged: GitHub Pages, deployed from `main` / root, custom domain via
`CNAME`. No build step, no dependencies, nothing to install. A daily
GitHub Action (`.github/workflows/freshness-check.yml`) validates data
and opens a GitHub issue if something needs review — it never edits
content itself.
