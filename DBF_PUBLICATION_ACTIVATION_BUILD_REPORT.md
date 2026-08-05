# DBF Publication Activation — Build Report

**Branch:** `dbf/editorial-expansion-preview`
**Commit:** `57be7bb`
**Base:** `354d314` (Phase 2 preview) → `main` @ `58ab4ee`

**Production was not deployed. Nothing was pushed, merged, or PR'd. `main` and `origin/main` both remain at `58ab4ee`.**

---

## 1. Preflight found two red tests. Both were real; neither was a code regression.

The suite was **12/14 on arrival**, not the 14/14 the last session left. The cause was the passage of time, and the two failures were genuinely different problems:

**a) A time-bombed test fixture.** `automation/sample-valid-candidate.json` carried absolute dates (Aug 2). Today is 2026-08-05, so a perfectly working validator correctly rejected an expired event — and the test read that as failure. A test that predictably fails every week is noise, so I made the test generate a date-shifted copy (`scripts/make_test_candidate.py`) while keeping the committed fixture readable, since it doubles as contract documentation for the scheduled research task.

**b) A test asserting an invariant the architecture never maintained.** `no expired event remains in events.json` — but expired records legitimately sit in that file until the next weekly candidate is applied; the public site filters them at render. So the test cried wolf about normal state. I replaced it with the invariant that actually protects visitors — *the render filter must never leak an expired event* — and added `scripts/archive_expired.py` as the maintenance path that was missing (it archived the 4 genuinely-expired August events).

**Then the new inverse test caught a real data-modeling bug.** I added "archive holds no still-current event," which immediately flagged *"Bandstand season, in full swing"* — sitting in the archive marked `expired` despite an `endDate` of Aug 31 still in the future. It was never expired; it was **editorially superseded** in Phase 3.1 by specific dated listings. The status vocabulary conflated "the date passed" with "we replaced this on judgement." Added a distinct `superseded` status, corrected the record, taught the validator the new value, and added a test requiring every superseded record to explain itself.

**Suite went 12/14 → 17/17.** Two of those new tests exist specifically to stop these classes of bug recurring.

## 2. Test results

| | Before | After |
|---|---|---|
| `scripts/run_tests.sh` | **12 passed / 2 failed** | **17 passed / 0 failed** |
| `scripts/check_editorial_preview.py` | 20 checks, all passed | **44 checks, all passed** |
| Internal links | 1,479 · 0 dead | 1,295 · 0 dead |
| Console errors | — | **0** |

The link count drop is fully explained by nav simplification: 4 fewer nav items × 46 pages = −184 links. No content was lost.

### New automated checks
Published video entries must carry `src`/`poster`/`posterAlt`/`textAlternative` and must not hotlink a third party · no blanket handcrafted/small-batch claim on any public page · house byline is config-driven · no house-byline page still declares a `Person` author · About retains real-entity disclosure · primary nav ≤6 items and has no Shop/Store item · no page explains its own file structure to visitors · scroll-reveal fails visible · archive/supersession invariants.

## 3. New homepage hierarchy

1. **Hero** — "The Delaware Life, Well Found."
2. **The Lead Story** (`#lead-story`) — flagship, dominant
3. **Watch DBF** — *hidden* (no assets)
4. **Departments** — the four pathways
5. **Field Notes** — 3 real guides
6. **Homes & Design** (`#homes-design`)
7. **This Week** — 5 real verified events
8. **The Edit** (`#the-edit`) — 3 real entries
9. Hidden Gem → 10. Explore by Town → 11. Latest Stories → 12. Series → 13. Shop

**Removed:** the old mid-page Towers hero (the flagship replaces it) and Coastal Moments (a duplicate submission promise with no content).

## 4. Populated vs. gated

**Populated with real content:** Flagship (Towers, from `stories.json`) · Field Notes (3 guides) · This Week (5 verified events, ≥2 threshold) · The Edit (3 real Etsy entries, ≥3 threshold) · Hidden Gem · Explore by Town · Latest Stories (6 of 11) · Shop (4 products).

**Correctly hidden:** Watch DBF (no video assets) · New on Instagram (no verified permalink) · Community (0 real submissions vs threshold 3).

Hidden modules contribute **exactly 0px** — verified, no ghost gaps — and reappear automatically when their data crosses threshold. Gating also hides the matching department panel *and* primary-nav link, so nav never advertises an empty destination.

## 5. Stories index

Already data-driven; verified rendering **all 11 published stories** from `stories.json`, every card with a working link and non-empty alt text. No hardcoded parallel list exists to drift.

## 6. Flagship treatment

Renders from real metadata: kicker, headline, hook, category, formatted date, read time, and one clear "Read the Story" action, in a two-column editorial card with hover elevation and image scale.

**A real bug fixed here:** alt text was just repeating the headline — claiming "The Towers on the Dunes" for a photo containing no towers. Added a `heroAlt` field and wrote accurate descriptions for four stories.

## 7. Video (Tier 3) — built, gated, honest

A full recursive search found **zero** `.mp4`/`.webm`/`.mov`/`.m4v`/`.avi` files, and `ffmpeg` is unavailable, so nothing could be transcoded either. Per the brief's fallback: the component and `data/watch-dbf.json` are built, the module stays hidden, and `automation/VIDEO_ASSET_REQUIREMENTS.md` specifies exactly what to supply — file paths, codec/resolution/size targets, an ffmpeg command, and the rule that **Instagram Reel audio cannot be self-hosted** (that licence covers playback on Instagram, not your domain).

When activated it will: render poster-first, load only near the viewport, stay muted + `playsinline`, pause when scrolled away, respect reduced-motion, and expose keyboard-reachable controls with a text alternative.

## 8. Commerce copy corrections

Removed the blanket claim **"handcrafted, small-batch coastal goods made right here on the Delaware shore"** — false for vintage and print-on-demand items — from the homepage, the shop page body, and its `description`/`og:description`/`twitter:description` metadata.

Replaced with: *"Delaware-inspired home goods, personalized pieces, and distinctive vintage finds — selected for life by the coast."*

The per-item *"handcrafted wooden porch sign"* was **kept**, because that item genuinely is handcrafted. The correction targets false blanket claims, not accurate per-item ones.

## 9. The Edit

Editorial-first: image, then why we selected it (`editorialNote`), with price secondary. Vintage identified as vintage, made-to-order as made-to-order, affiliate disclosure retained. No cart, checkout, or Shop-first nav — asserted by test.

## 10. Byline system

`data/site-editorial.json` holds one `houseByline` field. 8 article pages moved from "By Michael Schwander" to `Delaware Beach Finds Editorial`, with the static text as a no-JS fallback. Swapping to a pen name later is **one field**, not 8 edits.

**Consistency fix:** those pages still declared `"author": {"@type":"Person","name":"Michael Schwander"}` in JSON-LD — search engines would have shown a byline contradicting the page. Switched to `Organization`.

**Legal identity untouched:** About, Contact and Privacy retain real-entity disclosure, plus a new About paragraph explaining the house byline exists for presentation while ownership and contact details remain accurate.

## 11. Navigation

**10 items → 6**, applied uniformly across all 46 pages (verified: exactly 1 nav variant at each depth):

`Homes & Design · Delaware Stories · Field Notes · The Edit · Explore · About`

This Week, Hidden Gems, Events, Community, Shop, Archive and Search all remain reachable via footer. **No URLs changed.**

## 12. Responsive — verified at all three widths

| | 375px | 768px | 1280–1440px |
|---|---|---|---|
| Horizontal overflow | none | none | none |
| Flagship | 1 col, 16:9 | 1 col | 2 col |
| Departments | 1 col | 1 col + row stack | lead + stack |
| The Edit | 1 col | 2 col | 3 col |
| Nav | hamburger | hamburger | 6 items inline |

## 13. Accessibility

Logical heading order · meaningful alt text on every homepage image (asserted by test) · hidden modules use `display:none` so they leave the a11y tree entirely · `prefers-reduced-motion` honored in both CSS and JS · keyboard focus preserved · Instagram link labelled as leaving the site · video will carry a text alternative and keyboard controls.

**Robustness fix:** `.reveal` previously started at `opacity:0`, so a JS failure would have left real content permanently invisible. Now the hidden state only applies once JS confirms it can reverse it (`html.js-reveal`) — it fails *visible*.

## 14. Performance

No new framework or third-party embed. Video is poster-first, `preload="none"`, intersection-loaded. Images keep `loading="lazy"`/`decoding="async"`. Removing three empty modules cut DOM weight. Homepage went 15 sections → 12 visible + 3 gated.

## 15. Known limitations (honest)

1. **No video assets exist** — Watch DBF cannot be activated until real footage is supplied.
2. **No home/interior/garden photography exists.** Homes & Design uses the best available *streetscape* photo. This department cannot be more than an honest placeholder until real photography exists — and I did not fabricate articles to fill it.
3. **The flagship image is low-resolution** (`cape-henlopen-aerial-1.jpg`, 387×258) displayed in a ~1217px card, so it will look soft. It is kept because it is the only asset that actually depicts the Cape Henlopen coastline the story is about; substituting a sharper but unrelated dune photo would trade accuracy for polish. A higher-resolution photo of the same subject is the fix.
4. **Below-the-fold screenshots were unreliable** in this environment all session (scroll-then-capture returns blank frames). Verification below the fold was done by DOM/computed-style inspection instead, which is stricter — but I could not attach every screenshot the brief lists.
5. **Homes & Design has no landing page** — it is a homepage anchor, per the brief's instruction not to create empty public pages.
6. **`events.json` will drift stale again** in ~7 days; that is the designed weekly cadence, and `archive_expired.py` + the daily GitHub Action now handle it.

## 16. Local preview

```bash
cd /Users/michaelschwander/Desktop/delaware-beach-finds
git checkout dbf/editorial-expansion-preview
python3 -m http.server 8000
# open http://localhost:8000/
```

Return to the live-matching state with `git checkout main`.

To watch the gates work, temporarily trim `data/dbf-edit.json` to 2 entries and reload — The Edit section, its department panel, and its nav link all disappear together.

## 17. Files changed

```
NEW   data/site-editorial.json              byline + module thresholds
NEW   data/watch-dbf.json                   video feature data (gated)
NEW   automation/VIDEO_ASSET_REQUIREMENTS.md
NEW   scripts/archive_expired.py            expired-event maintenance
NEW   scripts/make_test_candidate.py        de-time-bombs the validator test
MOD   index.html                            hierarchy, flagship, watch, gating, shop copy
MOD   assets/js/site.js                     gateHide/gateShow, flagship, watch, byline, reveal
MOD   assets/css/styles.css                 .flagship, .watch-*, reveal fail-visible
MOD   data/stories.json                     heroAlt on 4 records
MOD   data/events.json / events-archive.json  4 archived, 1 superseded + note
MOD   scripts/run_tests.sh                  17 assertions
MOD   scripts/check_editorial_preview.py    44 checks
MOD   scripts/validate_candidate.py         + "superseded" status
MOD   shop.html, community.html, this-week.html, about.html
MOD   8 story pages                         house byline + JSON-LD author
MOD   46 pages                              simplified nav
```

---

**Confirmed: `main` untouched at `58ab4ee`. No PR, no merge, no deployment.**
