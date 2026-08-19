# Delaware Beach Finds — Checkpoint

**Last verified in production:** 2026-08-19
**Purpose:** resume the next session without rediscovering the project.

---

## LIVE STATE

| | |
| --- | --- |
| Published stories | **22** |
| Departments | Coast 10 · History 6 · Field Guide 4 · People 2 |
| Real photography | **14 of 22** heroes are photographs; the rest use the house illustrated treatment |
| Cover story | `where-the-marsh-is-going` — 2400px marsh photograph, deliberately preserved |
| Latest published | `what-the-dunes-were-for` (Fort Miles), `three-hundred-dollars`, `the-patience-of-herons`, `the-refuge-loop` |
| Today | Live at `/today.html` — NWS forecast + alerts, NOAA tides + water temp, DNREC link-out, 5 towns |
| Live | Live at `/live.html` — 2 embedded YouTube feeds (Cape Henlopen osprey + nature centre), 3 link-out cards |
| Events | **102** ingested from 3 first-party sources (Rehoboth, Lewes Historical Society, Bethany) |
| Automation | **Healthy.** `refresh-coast.yml` ran unattended 4× on 2026-08-19 (09:52, 14:00, 17:44, 21:43 UTC) |
| Tests | **25/25 suites** |
| Links | **2,380 internal, 0 dead** |
| Etsy | DelawareBeachFinds only; no Blue Hen Basement references anywhere |
| Sponsored | **0** — and the renderer forces `sponsored:false` even if an override tries to set it |
| Audience metrics | **0 published** — `data/audience-metrics.json` is filled but every value is null by design |

### Deploy
GitHub Pages from `main`, CNAME `delawarebeachfinds.com`. Remote is **SSH**
(`git@github.com:Schwandz21/...`) because the HTTPS keychain token expired.
Push may need `git pull --rebase` first — the refresh workflow commits on its own.

---

## EDITORIAL STATE

### Just published
**What the Dunes Were For** — Fort Miles and Delaware's WWII coast. Why the bay
mouth was worth closing, the fort that closed it, the U-boat war that actually
arrived, and the surrender of *U-858* at Lewes on 14 May 1945. Joins
`delaware-at-war` alongside *The Towers on the Dunes* and resolves the
tower-count ambiguity that piece flagged (15 concrete towers system-wide: 11 in
Delaware, 4 in New Jersey).

### Strongest remaining backlog candidates
`editorial/STORY-BACKLOG.md` holds 30 pitches with sources and visual notes.
The three best right now:
1. **The Wedge** — the sliver Delaware and Pennsylvania both claimed until 1921.
2. **Thomas Garrett** — the Wilmington merchant fined into bankruptcy for helping
   freedom seekers. Would also open the proposed **Freedom Routes** series.
3. **The Delaware Bay pilots follow-up / lifesaving service** — maritime is proven
   territory and under-served.

### Deliberately deferred — do not publish without better grounding
**The Indigenous history feature** (backlog pitch 8, and installment 1 of
*How Delaware Became Delaware*). Every research pass so far has been
colonial-side. It must not be drafted from secondary material alone. Route:
Nanticoke Indian Association, Delaware Tribe of Indians, Smithsonian NMAI.

### How Delaware Became Delaware — incomplete, honestly
Published: **2, 6, 7, 8, 9**. Missing: **1, 3, 4, 5**.
The series page states this itself: *"5 of 9 installments published · still to
come: 1, 3, 4, 5"*, and the renderer refuses to say "complete" while any
numbered installment is missing. Installment 2 ends exactly where 3 must begin.

### Known visual gaps (real, not cosmetic)
- **No Cape Henlopen / Fort Miles photograph above 387px.** The Fort Miles
  flagship runs a 1200px coastal aerial, honestly captioned, because nothing
  better exists in the library.
- **No verified Lewes frame** — the pilots story, tide station, osprey cam and
  marsh cover all point at Lewes.
- **No archival/historical imagery pipeline.** Every history piece uses the house
  illustration. Library of Congress, NARA and Delaware Public Archives hold
  public-domain material but rights need checking item by item.
- **No Homes & Design photography** — that department has no stories and cannot
  be illustrated today.

---

## NEXT SESSION — three editorial moves

1. **Publish The Wedge.** Genuinely strange, well documented, works standalone,
   and strengthens the borders material without needing new photography.
2. **Publish Thomas Garrett and open Freedom Routes.** Grows People to three,
   opens a serious series, and is the most consequential Delaware story still
   unwritten.
3. **Get one Cape Henlopen and one Lewes photograph.** A single afternoon with a
   camera unblocks the Fort Miles hero, the pilots piece and the towers story —
   the largest visible constraint on the archive right now.

Everything else is working. Leave the automation alone.
