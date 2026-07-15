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
community.html           Full community page
shop.html                Coastal Shop
about.html               About
contact.html, privacy.html, terms.html, disclosure.html, 404.html

towns/                   One page per town (Lewes, Rehoboth, Dewey, Bethany,
                         Fenwick, Cape Henlopen, Assateague, Ocean City)
stories/                 Story articles + stories/index.html (the library)
data/                    JSON files that drive the weekly-rotating sections
admin/submit-helper.html  Internal tool for turning a follower photo into a
                         ready-to-paste community.json entry (not linked in nav)
assets/css/styles.css     One shared stylesheet
assets/js/config.js       Etsy / Shopify / Instagram / GA4 config — edit here
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

## Connecting the Shopify store

Open `assets/js/config.js` and replace `https://YOUR-SHOPIFY-STORE.myshopify.com`
with the real store URL. Every Shopify link sitewide updates from that one
setting. Etsy is already live at `etsy.com/shop/TheBlueHenBasement`.
