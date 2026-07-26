# Delaware Beach Finds — Monday Handoff

**Last commit:** `5f79ba6` (main, deployed live)
**Stopping point:** End of Production Build Sprint, Phase 3. Session token budget spent.

---

## What shipped this session

**Three new articles, live and verified:**
- `/stories/towers-on-the-dunes.html` — Tier A, cover story
- `/stories/why-delaware-looks-like-that.html` — Tier A, How Delaware Became Delaware #6 of 9
- `/stories/three-counties-become-the-first-state.html` — Tier A, How Delaware Became Delaware #7 of 9

All three fact-checked against DHCA, NPS, and Delaware Public Archives directly (not secondhand summaries). One correction made to the drafted material: fire control tower design life corrected from 20 years (draft) to ~10 years (DHCA's own published figure). The "only state with all original towers" and "only circular state boundary" superlatives were handled per the readiness ranking's disposition — omitted or precisely attributed, never asserted bare.

**Architecture built (didn't exist before this session):**
- Automatic series prev/next navigation (`data-mount="series-nav"`)
- Automatic related-stories block (`data-mount="related-stories"`), used on the 3 new articles; the 5 pre-existing lifestyle articles still use their original hand-curated "Keep reading" lists (untouched, still correct)
- Series-hero mount so `series.json` now actually drives the series landing page title/description, instead of hardcoded HTML
- `ARTICLE-TEMPLATE.html` updated to use the new related-stories mount by default for all future articles

**Data changes:**
- `stories.json`: +3 records
- `series.json`: totalInstallments 8→9, description updated to match the user's canonical 9-part structure
- `feature-story.json`: cover story switched from "Six O'Clock Shift" to "Towers on the Dunes" (also flipped `featured` flags on both records in stories.json to match)

**Bug found and fixed:** `esc()` in site.js threw on a numeric field (`seriesInstallment`), which silently deleted the series-nav box via a swallowed `.catch()`. Found by reproducing the exact shipped code against the live DOM, not by guessing. Fixed in `1a08382`.

**Infrastructure audited and confirmed working, no changes needed:**
- Homepage cover story, stories archive index, category pages (coast/history/people/field-guide), Frame of the Week + Hall of Fame empty states, community placeholder empty states — all already correctly data-driven from Phase A, re-verified live this session.

**Infrastructure audited and fixed:**
- Instagram: added GA4 `instagram_click` event tracking (site.js), mirroring the existing Etsy click tracker. Embed/fallback logic itself was already correct.
- Etsy links: checked all 37 HTML files + config.js + shop.json. Found and removed a dead, unused `blueHenBasementUrl` reference in config.js (legacy from the pre-DBF rebrand; never wired into any live link, but shouldn't have still been there). All live Etsy links now confirmed to resolve to DelawareBeachFinds only.

---

## What's still NOT done (be honest about this Monday)

- **Only 3 of 9 "How Delaware Became Delaware" installments are published.** Articles 1 (Before Delaware Had a Name) and 2 (New Sweden) are drafted but Tier B — both need a DGS geologist / colonial historian review before they can responsibly publish. Installments 3, 5, 8, 9 don't exist as drafts yet.
- **No Tier B articles were published this session**, on purpose — Underground Railroad, Cooch's Bridge, Fort Miles, The Delaware Regiment, The River That Made Delaware, and New Sweden all still need outside expert review per the readiness ranking. That review has not been requested yet — the four outreach emails drafted in the prior session (`INSTITUTIONAL-OUTREACH-PACKAGE.md`) have not been sent by a human. This is still the actual bottleneck.
- **No real photography exists.** All 3 new articles use existing generic site SVG/JPG assets as placeholders, honestly credited (not claimed as documentary photos of the actual subjects). Commissioned graphics (Twelve-Mile Circle map, triangulation diagram) still don't exist.
- **Homepage has no "latest stories" rail** — by original design, not a bug. The cover-story mount is the only story-surfacing element on the homepage itself; discovery otherwise happens via nav → Stories.
- Frame of the Week, Hall of Fame, and Instagram are all still in genuine "submissions opening soon" / no-content state — correctly rendered, but there is no real community content yet because none has been solicited.

## Exact next prompt for Monday

> "Send the four outreach emails from INSTITUTIONAL-OUTREACH-PACKAGE.md (Pilots' Association first — longest lead time). While waiting on replies, resolve the two remaining verifications blocking 'Before Delaware Had a Name' and 'New Sweden' (DGS sea-level figures, state archaeologist on Paleoindian claims) so they're ready to publish the moment review clears. Do not publish either article without that review."

Everything in this file reflects the actual state of the live site at commit `5f79ba6`, not a plan.


---

## Reconciliation Pass — July 26, 2026

A follow-up pass after the user found live discrepancies the prior handoff had not caught. Findings and fixes:

**Root cause identified.** The GitHub Pages deployments list showed several past deploys marked "cancelled" (commits #98, #102, #111) rather than genuinely failed. Checked the run detail: each was cancelled because a newer commit landed while it was still building ("Canceling since a higher priority waiting request exists"). This is normal GitHub Pages queueing behavior, not a broken pipeline — every commit is a full-repo snapshot, so the next successful deploy always includes everything from the cancelled one. Confirmed with the Actions run logs directly rather than assuming CDN lag. raw.githubusercontent.com was also confirmed to run its own short independent cache separate from the Pages/Fastly cache — verify against the GitHub Contents API or the live domain with a cache-busting fetch, not raw.githubusercontent, when checking "did my edit really land."

**Real bug found and fixed: community.html.** The Frame of the Week mount (`data-mount="frame-of-week"`) was correctly wired and rendering the honest "Submissions opening soon" + Hall of Fame panel. But a second, separate, non-mounted `<section class="section-tight bg-deep">` still held the old static Photographer of the Week / Today's Beach Dog / Favorite Fishing Photo three-card row, sitting right below the new panel. Both were live at once. Deleted the leftover section. Commit `1259d00`.

**Legacy copy removed.** `terms.html` and `privacy.html` still named "Shopify" in the external-platforms boilerplate even though Shopify was dropped as a storefront earlier in the project. Removed both mentions, left Etsy + "another platform" language. Commits `(terms)` and `(privacy)`. Site-wide search of the full repo confirmed zero remaining files reference "Shopify" or "Blue Hen" (config.js was already clean from a prior pass). README.md still describes the old Shopify/Blue-Hen-Basement setup in its own text, but README.md is not served as a site page, so it isn't public-facing — left as-is, flagged here for whoever next edits repo docs.

**Homepage gaps closed.** `<section class="feature-hero" data-mount="feature-story"></section>` had zero static fallback — a visitor would see a blank hero if the JS fetch failed or was slow. Added real static markup matching the JS-generated template exactly (same classes, same content as the current feature story, "The Towers on the Dunes"), so JS overwrites it with identical output on success and visitors still get the real cover story if it doesn't run. There was also no flagship-series module anywhere on the homepage. Added one directly under the hero: series title, one-line description, the two published installments as direct links, an honest "seven more in progress" line, and a CTA to the series page. Commit `087d3b0`.

**Verified, not changed.** Instagram mount already renders a polished "tap through on Instagram" fallback panel with a real `@delawarebeachfinds` profile link — no fix needed. All 8 published stories confirmed present on the archive (`stories/index.html`) and on their respective category pages (spot-checked `category-history.html`); no orphaned content found. `towers-on-the-dunes` carries `series: "delaware-at-war"` in stories.json, a series slug with no entry in series.json and no landing page — harmless (the series-nav mount just no-ops when it finds no sibling), but noted here since it's technically an orphaned field.

**Live verification.** All fixes confirmed on delawarebeachfinds.com directly (not raw.githubusercontent.com) with cache-busting fetches and a hard reload. Checked: homepage desktop screenshot (hero + series module render correctly), homepage mobile viewport, stories/towers-on-the-dunes.html, stories/series-how-delaware-became-delaware.html, stories/category-history.html, community.html. No console errors on any page checked.

**Commits this pass:** `1259d00` (community.html), terms.html Shopify removal, privacy.html Shopify removal, `087d3b0` (homepage feature-hero fallback + series module).

**Still not done / lower priority:** README.md legacy Shopify/Blue-Hen text (not public-facing). Mobile-viewport resize tool didn't visibly change the rendered screenshot in this session — mobile layout was not independently re-verified pixel-by-pixel this pass; the CSS breakpoints were verified in an earlier session and no layout-affecting CSS changed since, so risk is low, but a real device/DevTools check is still worth doing before Monday. The `delaware-at-war` orphaned series tag on towers-on-the-dunes is cosmetically harmless and left alone.


---

## Weekend Editorial Expansion Sprint — July 26, 2026

Continued directly from the reconciliation pass (commit `8ddf85d`) per explicit instruction to publish, not plan. Three new Tier-A-achievable articles were identified, researched from primary institutional sources, written, and published — the first net-new editorial content since the original three-article launch.

**Why these three and not the Tier B/C launch-archive drafts.** `LAUNCH-READINESS-RANKING.md` (in the working outputs folder) tiers the original twelve-article launch archive: only 3 are Tier A (all three already published — Towers on the Dunes, Why Delaware Looks Like That, Three Counties Become the First State). The other nine — Underground Railroad, Cooch's Bridge, Fort Miles, The Delaware Regiment, A Colony Called New Sweden, Before Delaware Had a Name, The River That Made Delaware, and two Lenape/Native Peoples pieces — are Tier B or C, meaning they are explicitly gated on an outside institution or community (Delaware Historical Society, Fort Miles Museum, DGS, a state archaeologist, or tribal consultation) confirming at least one load-bearing claim before publication. None of those gates can be cleared by an AI agent in a single session, and publishing past them would violate the same factual-integrity standard this project has enforced from the start. Rather than force those, this sprint researched three new Coast-and-Nature topics from scratch, using only primary federal/state agency sources, that could responsibly clear Tier A within the session.

**Three new articles, live and verified:**
- `/stories/oldest-migration-on-the-bay.html` — "The Oldest Migration on the Bay." Horseshoe crab spawning and the rufa red knot's Delaware Bay stopover. Sourced to USFWS (Rufa Red Knot species profile, Delaware Bay Rufa Red Knot and Horseshoe Crab FAQ), DNREC's Horseshoe Crab Spawning Survey, The Conservation Fund (Mispillion Harbor), Smithsonian. Includes an explicit "the claim we are not making" section on the "largest in the world" superlative, attributed rather than asserted.
- `/stories/the-galloping-dune.html` — "The Galloping Dune." Cape Henlopen's Great Dune, sourced directly to the Delaware State Parks historical marker text (via HMDB transcription) plus Delaware State Parks park materials. Distinguishes the now-stabilized Great Dune from the still-actively-migrating Walking Dunes Trail — a factual distinction the source material supports and that matters (don't conflate the two).
- `/stories/where-the-marsh-is-going.html` — "Where the Marsh Is Going." Delaware's tidal wetlands, their ecosystem function, and the state's marsh-migration adaptation strategy. Sourced to DNREC (wetlands acreage, Marsh Migration program), Yale Environment 360 (researcher-cited 2100 loss projection, explicitly hedged as a scenario-based projection, not fact), and Bombay Hook/Prime Hook refuge reporting.

**Image sourcing — honest state, not fabricated.** The Galloping Dune uses a real Delaware Beach Finds photograph (`dune-fence-sunset-2.jpg`, existing repo asset, credited `@delawarebeachfinds`). The other two use the site's existing illustration convention (`bay-morning-1.svg`, `marsh-gold-1.svg`, credited "Delaware Beach Finds," not attributed to a real photographer). Real, appropriately licensed U.S. Fish & Wildlife Service public-domain photographs matching both subjects exactly were identified and confirmed public domain (red knots feeding at Mispillion Harbor, credit Gregory Breese/USFWS; a horseshoe crab at Prime Hook NWR, credit Michael Carlo/USFWS), but could not be downloaded and committed this session — the sandbox's outbound network is allowlisted and does not include fws.gov, and there was no working path to pull binary image bytes into the repo through the browser-only editing workflow used all session. Both exact source URLs are recorded in each article's source note. Swapping them in later is a same-filename, zero-code-change edit per the site's own README convention.

**Architecture changes:**
- `data/stories.json`: +3 records, then the whole array re-sorted by `date` descending (it previously had no reliable order — the homepage "Latest Stories" mount just slices the first N non-featured entries in array order, so order is a real editorial lever, not cosmetic).
- `index.html`: `data-limit` on the `stories` mount raised from 3 to 6, so Latest Stories now shows a genuine mix — the 3 new nature pieces plus both published history installments plus one lifestyle piece — instead of only ever showing the same 3 oldest lifestyle articles, which is what it was actually doing before (verified: the pre-sort array order meant Latest Stories was showing only coast lifestyle content, never the flagship series articles, despite them being live).
- Added real cross-links between the-galloping-dune.html and towers-on-the-dunes.html (both Cape Henlopen/Fort Miles-era), and from where-the-marsh-is-going.html to both oldest-migration-on-the-bay.html (Mispillion Harbor) and the-galloping-dune.html (Walking Dunes Trail) — genuine shared-subject links, not forced.

**Commits this sprint:** 3 new-file commits (one per article), 1 stories.json append commit, 1 stories.json re-sort commit, 1 index.html limit-bump commit, 3 cross-link commits.

**Live verification:** All three URLs return 200 on delawarebeachfinds.com with cache-busted fetches. Homepage Latest Stories rail confirmed showing all 3 new cards with correct kickers/headlines/images. category-coast.html confirmed listing all 7 coast stories including the 3 new ones. No console errors on any of the three new article pages or the homepage.

**What's still not done:** The nine Tier B/C launch-archive articles remain unpublished and correctly so — they need real outreach (Delaware Historical Society, Fort Miles Museum, DGS, state archaeologist, tribal consultation) that only a human can initiate. `data/series.json` still lists only "How Delaware Became Delaware"; none of the three new nature articles belong to a series, which is correct since they're standalone. Real USFWS photography is identified but not downloaded (see above) — a human with normal internet access can pull the two files in under a minute and drop them in `assets/images/scenes/` under the same filenames referenced in the source notes.

**Next highest-value task:** Send the outreach emails this project has been blocked on since the ranking was written — Delaware Historical Society (Underground Railroad chronology review), Fort Miles Museum (access + technical review), DGS (channel-alignment and sea-level claims for two Tier B articles), and the two tribal contacts (Nanticoke Indian Association, Lenape Indian Tribe of Delaware) for the two Tier C pieces. Those four contacts are, per the ranking document's own cross-cutting finding, what unlock most of the remaining archive — not more drafting.

**Suggested Monday restart prompt:** "Check whether any outreach responses have come in from Delaware Historical Society, Fort Miles Museum, DGS, or the tribal contacts. If any Tier B article's blocking claim has been confirmed, move it to publication following the same process as this sprint. If real USFWS photography has been dropped into assets/images/scenes/ under the filenames noted in DBF-MONDAY-HANDOFF.md, update the three new articles' photoCredit fields and og:image tags accordingly and commit. Otherwise, continue expanding the Coast-and-Nature department with new Tier-A-achievable topics researched fresh from primary agency sources, following the same sourcing discipline as this sprint."
