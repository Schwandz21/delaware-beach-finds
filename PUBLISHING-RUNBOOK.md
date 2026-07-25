# Delaware Beach Finds — Publishing Runbook

This site is static HTML with a light data layer. Almost everything you update week to
week lives in the JSON files under `/data/`. Editing a JSON file updates the live site
immediately after commit — no rebuild, no code changes, in most cases.

All edits below can be made directly in the GitHub web editor (click a file, pencil icon,
edit, commit to `main`). GitHub Pages redeploys automatically within about a minute.

---

## Add a new article

1. Copy `stories/ARTICLE-TEMPLATE.html` to `stories/your-slug.html`. Fill in every
   `[BRACKETED]` placeholder and delete the instructions comment at the top.
2. Add a matching record to `data/stories.json`. Copy an existing entry and update:
   - `slug` — must exactly match the filename (without `.html`)
   - `category` — one of the slugs in `data/categories.json` (`coast`, `history`,
     `people`, `field-guide`, `community`)
   - `series` / `seriesInstallment` / `seriesTotal` — set if this article belongs to a
     series in `data/series.json`, otherwise leave `series` as `null`
   - `status` — use `"published"` once it's live; other values (`idea`, `researching`,
     `drafting`, `fact-check`, `approved`, `archived`) are for your own tracking and are
     not currently filtered anywhere on the site
   - `photoCredit`, `sources`, `etsyProductIds` — fill in as available; `etsyProductIds`
     is optional and only needed for the Shop the Story block (see below)
3. Commit both files. The article will now automatically appear on the homepage recent
   stories rail, the Stories index, and any category or series page whose slug matches.

## Change the homepage cover story

Edit `data/feature-story.json`. It's a single field:

```json
{ "slug": "six-oclock-shift-indian-river-inlet" }
```

Change the slug to any existing entry in `data/stories.json` and commit. The homepage
hero pulls the headline, photo, kicker and hook straight from that story record — nothing
else needs to change.

## Add an Instagram feature (Reel or post)

Edit `data/instagram.json` and set `permalink` to the real Instagram post/Reel URL:

```json
{ "permalink": "https://www.instagram.com/p/XXXXXXXXX/", "caption": "...", "scene": "...", "handle": "delawarebeachfinds" }
```

While `permalink` is empty, the homepage shows a caption/scene fallback card instead of a
broken embed — this is expected and requires no other changes once you add a real URL.

## Select (or archive) the First State Frame of the Week

Edit `data/frame-of-the-week.json`:

```json
{
  "current": { "name": "...", "handle": "@...", "caption": "...", "scene": "...", "week": "..." },
  "hallOfFame": []
}
```

- To publish a new winner: fill in `current` with the real photographer's name, handle,
  caption and photo (or scene image).
- To archive the outgoing winner: move the old `current` object into the `hallOfFame`
  array (append it), then set `current` to the new winner.
- If there is no confirmed winner yet, leave `current` as `null` — the Community page
  will show a "Submissions Opening Soon" panel instead of an empty section.

Never invent a winner, quote, or photo credit here. Only enter real, permissioned entries.

## Add an Etsy product

1. Add the product to `data/shop.json` (copy an existing entry — needs `name`,
   `description`, `price`, `url`, `scene`).
2. To link a product to a specific article ("Shop the Story"), add the Etsy listing ID
   (the number in the product URL, e.g. `4536906363` in
   `.../listing/4536906363/...`) to that story's `etsyProductIds` array in
   `data/stories.json`.
3. Uncomment the Shop the Story block near the bottom of that article's HTML file (it's
   left commented out in `ARTICLE-TEMPLATE.html` and in already-published articles by
   default):

```html
<section class="section"><div class="container">
<div data-mount="shop-the-story" data-story="your-slug"></div>
</div></section>
```

## Add a sponsor

`data/sponsors.json` is schema-ready but intentionally empty until there's a real sponsor
to add. Add an object per sponsor (name, logo/scene, link, placement notes) — no site.js
rendering logic is wired to it yet, since there is nothing to render truthfully today.
Treat this as the next build step once a sponsor is signed.

## Categories and series at a glance

- Categories live in `data/categories.json`; each has a landing page at
  `stories/category-{slug}.html` that auto-lists every story with a matching
  `category` field. Empty categories show a "Nothing published here yet" panel instead
  of a blank page.
- Series live in `data/series.json`; each has a landing page at
  `stories/series-{slug}.html` that auto-lists every story with a matching `series`
  field, ordered by `seriesInstallment`.
- Both page types are just a page-hero plus a single `data-mount="stories"` div with a
  `data-category` or `data-series` attribute — no per-article code changes required.

## What NOT to fabricate

Per the site's editorial standards, never invent: a Frame of the Week winner, a community
photo credit, an Instagram permalink, a sponsor, or article facts/sources. Empty states are
designed to look intentional — use them instead of placeholder content.
