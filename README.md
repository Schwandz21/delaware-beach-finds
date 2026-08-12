# Delaware Beach Finds

A dependency-free static site for `delawarebeachfinds.com` — a weekly coastal
magazine and the web home of [@delawarebeachfinds](https://www.instagram.com/delawarebeachfinds/).

No framework, no build step, no server. Every page is plain HTML, one shared
stylesheet, and a small amount of JavaScript that reads a handful of JSON
files for the sections that change week to week.

## Layout

```
index.html              Homepage
this-week.html           Full weekend calendar
hidden-gems.html         Hidden gem archive
events.html              Recurring events + what's coming up
explore.html             Town hub (links to /towns/)
guides.html               Local guides hub
archive.html              Browsable archive of current + past content
search.html               Lightweight client-side site search
community.html           Full community page
shop.html                Coastal Shop
about.html               About
contact.html, privacy.html, terms.html, disclosure.html, 404.html

towns/                   One page per town (Lewes, Rehoboth, Dewey, Bethany,
                         Fenwick, Cape Henlopen, Assateague, Ocean City)
stories/                 Story articles + stories/index.html (the library)
data/                    JSON files that drive the weekly-rotating sections,
                         events, guides, and the search/archive index
scripts/                 Python validation/build scripts (no dependencies
                         beyond the standard library) — see WORKFLOW.md
automation/               Weekly research prompt contract, candidate schema
                         and sample candidates for the freshness system
UPDATE_DBF_FRESHNESS.command  Double-click updater — review, validate and
                         deploy a weekly freshness candidate, no manual
                         JSON editing or git commands required
.github/workflows/        Daily automated freshness/link/JSON validation
admin/submit-helper.html  Internal tool for turning a follower photo into a
                         ready-to-paste community.json entry (not linked in nav)
assets/css/styles.css     One shared stylesheet
assets/js/config.js       Etsy / Instagram / GA4 config — edit here
assets/js/site.js         Nav toggle, link wiring, and the JSON-driven renderers
assets/images/scenes/     Placeholder photography (custom coastal art) —
                         swap individual files for real photos any time,
                         same filenames, zero code changes
assets/images/community/  Where follower photo submissions live
```

## Updating weekly content

See **`WORKFLOW.md`** — it covers the feature story, weekend calendar, hidden
gem, Instagram embed and community submissions, all of which are editable
through plain JSON files with no HTML or layout changes required.

## Freshness, archive & search

Event data is date-driven and self-expiring, "Coming Soon" guide stubs
can't go stale forever without notice, and everything ever published stays
browsable in `archive.html` and searchable in `search.html` even after its
current-events promotion expires. See the **"Weekly Freshness & Archive
System"** section of `WORKFLOW.md` for the full weekly loop, and
`automation/CANDIDATE_SCHEMA.md` for the data contract behind it.

## Replacing placeholder photography

Every hero, town tile, hidden-gem photo and community card currently uses a
custom-illustrated coastal scene from `assets/images/scenes/`, referenced by
filename from the JSON data or from the page HTML for towns/stories. To swap
in a real photo, replace the file (same name) or point the relevant `scene`
field at a new file — no other changes needed.

## Deployment

GitHub Pages, deployed from `main` / root. Custom domain via `CNAME`
(`delawarebeachfinds.com`). Google Analytics (GA4) is wired through
`assets/js/config.js` — unchanged from before.

