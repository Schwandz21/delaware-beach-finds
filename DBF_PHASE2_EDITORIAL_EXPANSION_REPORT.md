# DBF Phase 2 — Editorial Expansion Preview

**Branch:** `dbf/editorial-expansion-preview`
**Commit:** `4bd2eb3`
**Base:** `main` @ `58ab4ee` (the completed visual-QA repair pass)
**Production status: NOT deployed. NOT pushed to origin. NOT merged.** This work exists only in this local branch/commit for Michael's review.

---

## 1. What changed, in one paragraph

The homepage no longer opens as a beach-guide landing page. The hero now reads "The Delaware Life, Well Found." over a real dusk-boardwalk photo with genuine streetscape character, and immediately below it a four-panel department navigator (Field Notes, Homes & Design, Delaware Stories, The Edit) frames the site as a broader Delaware lifestyle publication. Field Notes and Delaware Stories route straight to real, already-published content — nothing new was invented to fill them. Homes & Design is an honest "actively being built" panel, not a fake article grid. The Edit is a genuinely content-gated curation module that only appears because it currently has three real, real-URL Etsy entries — verified in both directions (with and without enough entries) against a disposable copy of the repo, not just asserted.

## 2. Homepage hierarchy (new → old)

1. **Hero** — reframed, same real-photo pattern as before
2. **Departments** (new) — the four-pathway navigator, asymmetric layout
3. **Field Notes preview** (renamed from "Guides") — same real `data-mount="guides"` component, unchanged data
4. **Homes & Design** (new) — single honest editorial panel, id="homes-design"
5. **The Edit** (new) — content-gated, id="the-edit"
6. Everything below this point is **unchanged**: this week's cover story, the "How Delaware Became Delaware" series module, the weekend calendar, Instagram panel, Coastal Moments, Community, Hidden Gem, Explore by Town, Delaware Stories (renamed kicker on the existing Latest Stories module, same real data), Coastal Shop.

Nothing below the new department block was restructured — Priority order in the brief was followed exactly, and I stopped adding new structure once the four-department milestone was solid rather than touching unrelated sections for their own sake.

## 3. Hero image: which asset, and why

**`assets/images/scenes/boardwalk-dusk-rehoboth-1.jpg`** (2048×1366, real photograph).

I inventoried every real (non-illustrated) photo in the repo before choosing:
`paddleboard-sunrise-1.jpg`, `dune-fence-sunset-1.jpg`, `dune-fence-sunset-2.jpg`, `rehoboth-boardwalk-day-1.jpg`, `cape-henlopen-aerial-1.jpg` (387×258, too low-res for hero use), `coastal-sunset-aerial-1.jpg`, and this one. None of them show a home, interior, garden, or porch — **that photography doesn't exist in the repo yet**, which is the honest limitation here, not a workaround. Of what does exist, `boardwalk-dusk-rehoboth-1.jpg` was the only one with real architectural/streetscape character (lit lamps receding in perspective, storefronts and awnings visible, a single figure walking) rather than beach-activity energy — closer to a quiet town-at-dusk editorial photo than a "come swim here" shot. That made it the right choice for "The Delaware Life, Well Found," where the previous paddleboard-sunrise photo (still excellent, still in the repo, untouched) was the right choice for the more beach-specific framing it originally served.

## 4. Modules live in the staged preview

- Hero (new copy + image)
- Department navigator, 4 panels, all real destinations or honest placeholders
- Field Notes preview grid (real guide data, unchanged)
- Homes & Design panel (real photo, honest "being built" copy — no fabricated articles)
- **The Edit** — live and rendering, because it currently has 3 real entries (see §5)

## 5. Content gating — proven, not just built

`data/dbf-edit.json` declares `minPublishCount: 3` and currently has exactly 3 valid entries (Antique Dome-Top Steamer Trunk, Personalized Address Planter Sign, Cape Henlopen Woven Throw Blanket — all real, already-verified Etsy listings pulled from `data/shop.json`, chosen specifically because they read as home/design objects rather than beach souvenirs). Each carries a real title, image, destination URL, description, and `affiliateDisclosure: true`.

`site.js`'s `dbf-edit` mount checks `entries.length >= minPublishCount` before rendering anything, and toggles **both** the `#the-edit` section and the department-nav's "The Edit" panel via a generic `.is-hidden{display:none}` rule.

I didn't just read this logic back and assume it worked — I copied the repo to `/tmp`, trimmed `dbf-edit.json` to 2 entries, and confirmed via computed-style checks in a live browser that **both** the section and the nav panel report `display:none`. Then restored 3 entries and confirmed both render. Both directions are real, not assumed.

## 6. Two regressions found and fixed during this session

1. **White-on-cream contrast bug, reintroduced by my own new code.** The new `.homes-copy` component (a light-background card, same pattern as `.gem-copy`) sits inside a `.section.bg-ink` on the homepage — the exact bug class fixed in the prior repair pass (`.section.bg-ink h2,h3{color:#fff}` leaking into nested light cards). I ran an automated contrast sweep across every text node on the rendered homepage rather than trusting a visual skim, caught `.homes-copy h3` rendering `rgb(255,255,255)` on `rgb(250,246,239)`, and fixed it with the same targeted-specificity pattern already established (`.homes-panel .homes-copy h3{color:var(--navy)}`).
2. **Gating class scoped too narrowly.** `.is-hidden` was originally written as `.dept-panel.is-hidden{display:none}` — it only worked on department panels. When the JS added `is-hidden` to the `#the-edit` `<section>` itself (not a `.dept-panel`), nothing happened — the section stayed visible with an empty grid. Caught by actually exercising the failure path (§5), not by reading the code. Fixed by making the rule generic: `.is-hidden{display:none}`.

Both are now covered by an explicit check in `scripts/check_editorial_preview.py` so they can't silently regress again.

## 7. Test results

Existing suite — unaffected, confirms the repaired baseline held:
```
$ ./scripts/run_tests.sh
Passed: 14   Failed: 0
```

New preview-specific suite (`scripts/check_editorial_preview.py`) — 19 checks: DBF Edit gate + per-entry disclosure/access_level, no cart/checkout files or nav links introduced, all `<img>` tags in `index.html` have real alt text, the gating CSS is generic (regression-tested per §6.2), site.js gate logic present, `prefers-reduced-motion` honored in both CSS and JS:
```
$ python3 scripts/check_editorial_preview.py
All editorial-preview checks passed.
```

Also verified directly in-browser (not just scripted):
- Zero console errors on the homepage
- Zero horizontal overflow at 375px, 768px, 1440px
- 1,480 internal links checked, zero dead
- Automated contrast sweep (real WCAG luminance/contrast-ratio math, not eyeballing) returns zero failures on the rendered homepage
- Department-nav asymmetric layout confirmed via computed `getBoundingClientRect()`: lead panel 675×644, three stacked panels 520×200 each on desktop; responsive stacking confirmed at tablet (full-width lead + 3-across row) and mobile (single column)

## 8. Known limitations (honest)

- **No home/architecture photography exists in the repo.** The Homes & Design panel and hero both reuse the strongest available *streetscape* photography — genuinely the best fit available, not a home-interior photo. This department cannot go further than an honest placeholder until real photography is sourced.
- **Homes & Design has no destination page** — by design, per the brief ("use safe homepage anchors... rather than creating empty public pages"). It's a homepage anchor (`#homes-design`), not a 404.
- **The department-nav top-level site nav was only relabeled on the homepage** (`Guides`→`Field Notes`, `Stories`→`Delaware Stories`), matching "update homepage navigation language *only where necessary*." Every other page's nav is untouched — a full sitewide rename would be a much larger, separate decision.
- **`.dept-panel` and `.edit-card` share hover/focus-visible styling** but I did not add a distinct focus *ring* color beyond what already exists sitewide — focus is visible (same treatment as hover: lift + shadow) but not a high-contrast outline. Worth a dedicated accessibility pass if this direction is approved.
- This entire report describes a **preview**. Nothing here is live. Approving it requires an explicit decision to merge and deploy — that was intentionally left undone.

## 9. Local preview instructions

```bash
cd /Users/michaelschwander/Desktop/delaware-beach-finds
git checkout dbf/editorial-expansion-preview
python3 -m http.server 8000
# open http://localhost:8000/ in a browser
```

To return to the live-matching state: `git checkout main`.

## 10. Exact files changed

```
 assets/css/styles.css              | department-nav, homes-panel, edit-card, .reveal, .is-hidden fix
 assets/js/site.js                  | dbf-edit gating mount + scroll-reveal observer
 data/dbf-edit.json                 | new — 3 real curated entries + minPublishCount
 data/content-index.json            | regenerated (timestamp only, no content change)
 index.html                         | hero, department nav, Homes & Design, The Edit, nav relabel
 scripts/check_editorial_preview.py | new — 19 targeted checks
```

---

**Production was not deployed. `main` and `origin/main` remain at `58ab4ee`, unchanged.** This report and the branch are the deliverable for review.
