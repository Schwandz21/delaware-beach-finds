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
