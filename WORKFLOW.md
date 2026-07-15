# Running Delaware Beach Finds week to week

This site is still a plain static site — no build step, no server, no CMS login.
Everything that needs to change weekly lives in small JSON files under `/data/`,
and the pages read those files live in the browser. Editing a JSON file is the
entire publishing workflow for the sections below.

## What updates weekly (edit these files directly on GitHub)

| Homepage section | File | Notes |
|---|---|---|
| Feature Story (hero) | `data/feature-story.json` | One object: kicker, headline, teaser, scene, link. |
| Happening This Weekend | `data/weekend.json` | Six entries: Friday, Saturday, Sunday, Next Weekend, Later This Month, Holiday Weekend. |
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

## Deployment

Unchanged: GitHub Pages, deployed from `main` / root, custom domain via
`CNAME`. No build step, no dependencies, nothing to install.
