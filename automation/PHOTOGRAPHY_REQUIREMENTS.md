# Photography requirements — front-page art direction

The Phase 2 front page is built to carry real documentary photography. Two slots
are currently limited by the assets that exist, and **CSS cannot fix either**.
Nothing here was faked or AI-generated to paper over the gap.

---

## 1. Cover story slot — the one that matters

**Current:** `assets/images/scenes/cape-henlopen-aerial-1.jpg` — **387 × 258 px**,
displayed at roughly **714 × 446** on desktop. That is a ~1.85× upscale, so it
renders visibly soft in the most important position on the site.

It is used because it is the only asset that genuinely depicts the Cape Henlopen
coastline the cover story is about. Substituting a sharper but unrelated photo
(a dune fence, a boardwalk) would look better and be less true — so it wasn't done.

**Needed:**

| Property | Target |
|---|---|
| Subject | The WWII fire-control towers at Cape Henlopen, or the Cape Henlopen coastline they overlook |
| Min width | **2400 px** (the slot renders ~714 px at 1×, so 2× for retina plus crop headroom) |
| Aspect | Shoot wide; the slot crops to **16:10** |
| Format | JPG, quality ~80, under ~500 KB after export |
| Filename | Replace in place: `assets/images/scenes/cape-henlopen-aerial-1.jpg` |

Same filename = zero code changes. `data/stories.json` already carries an accurate
`heroAlt` for it.

## 2. Homes & Design

**The repo contains no home, interior, porch, or garden photography at all.** That
department currently uses `rehoboth-boardwalk-day-1.jpg` (a streetscape) and is
written as an honest "being built" panel rather than pretending to be published.

**Needed before it can launch:** 4–6 images at 2000 px+ — a historic Lewes or
Rehoboth exterior, one interior, one porch/architectural detail, one garden.
Owned or properly licensed. Until those exist the department should stay a
placeholder.

---

## Slots already carrying strong real photography

These are fine and were deliberately positioned where the assets are strongest:

| Asset | Size | Used for |
|---|---|---|
| `rehoboth-boardwalk-day-1.jpg` | 3024×2268 | Boardwalk story, Homes placeholder |
| `paddleboard-sunrise-1.jpg` | 2640×1980 | Six O'Clock Shift |
| `dune-fence-sunset-2.jpg` | 2048×1315 | Galloping Dune, surf guide |
| `boardwalk-dusk-rehoboth-1.jpg` | 2048×1366 | Rehoboth town page |
| `dune-fence-sunset-1.jpg` | 1600×1100 | Gordon's Pond guide, Field Notes |
| `coastal-sunset-aerial-1.jpg` | 1200×674 | Sunset Spots guide |

## Rules

- No AI-generated imagery standing in for documentary Delaware photography.
- Preserve `photoCredit` / `heroAlt` on every record.
- Illustrated SVG scenes remain legitimate for conceptual/nature pieces; they are
  credited as illustration, never as photographs.

---

## Blocking asset need — homepage cover (recorded 2026-08-14)

`assets/images/scenes/cape-henlopen-aerial-1.jpg` is **387 × 258**. It is the
image for the current cover story (`towers-on-the-dunes`), and it is the only
low-resolution raster in the library — every other asset is 1200–3024px wide:

| Asset | Pixels |
| --- | --- |
| rehoboth-boardwalk-day-1.jpg | 3024 × 2268 |
| paddleboard-sunrise-1.jpg | 2640 × 1980 |
| dune-fence-sunset-2.jpg | 2048 × 1315 |
| boardwalk-dusk-rehoboth-1.jpg | 2048 × 1366 |
| dune-fence-sunset-1.jpg | 1600 × 1100 |
| coastal-sunset-aerial-1.jpg | 1200 × 674 |
| **cape-henlopen-aerial-1.jpg** | **387 × 258** |

Because of this the homepage cover is deliberately **type-led**: the headline
carries the page and the picture is capped at 387px so it is never upscaled.
This is a graceful treatment, not the intended design.

**Replace with:** a Cape Henlopen / fire-control-tower image, **minimum
2000px wide**, landscape, shot at or after golden hour, showing either the
tower itself against the dune line or the coastline with a tower visible.

**On replacement:** drop the file into `assets/images/scenes/`, set
`heroImage` on `towers-on-the-dunes` in `data/stories.json`, run
`python3 scripts/render_story.py`, then delete the `max-width:387px` cap in the
ITERATION 3 block of `assets/css/styles.css`. The cover scales up with no other
change.

**Also wanted, in priority order:** a vertical (4:5) coastal portrait for
cover-package variety; a detail/texture frame (dune fence, marsh grass, boardwalk
plank) for quieter transitions; one interior/architectural frame for
Homes & Design.
