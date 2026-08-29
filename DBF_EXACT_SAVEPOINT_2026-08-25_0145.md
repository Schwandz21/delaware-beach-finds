# DELAWARE BEACH FINDS — EXACT SAVE POINT

**Captured:** August 25, 2026, 1:45 AM ET  
**Use:** Upload this file to ChatGPT in this chat or a new Delaware Beach Finds chat and say: **“Resume from this exact DBF save point.”**

## 1. Project phase
DBF is officially in the **audience acquisition + retention + monetization** phase. Backend-only work is deprioritized unless it directly enables measurable acquisition, retention, monetization, or an immediately visible reader-facing improvement. Nearly every substantive Claude Code/Codex sprint should visibly improve the production product.

The product goal is no longer a late-2010s/early-2020s coastal newsletter/blog. The target is a premium **2026/2027 Delaware coastal media/discovery product** with strong mobile browsing, live/current utility, visual storytelling, repeat-use loops, and commercially valuable audience behavior. Long-form stories and archives remain a core depth/search asset and may support future premium/paywall strategy.

## 2. Latest production state
### Latest commit: `e640ac8`
Latest Claude sprint transformed mobile homepage density and article sharing.

Reported before → after homepage metrics:
- **25,284px / 30 mobile screens / 18 vertical modules / 0 horizontal rails**
- → **15,823px / 18.7 mobile screens / 13 vertical + 5 horizontal surfaces**
- 9,461px removed without deleting content.
- Five swipe rails: **Explore by Town, Stories, Guides, The Edit, Shop**.
- Desktop/tablet revert to grids.

Article acquisition feature:
- Native `navigator.share` path on supported phones.
- Fallbacks: clipboard / selection copy / inline URL.
- Analytics event: `content_share` with `content_id`, `content_type`, `method`, `source_page`.

### Previous key commit: `98b17c2`
Delaware Coast Live transformed from links/static cards into functioning live-feed embeds.
- Live embeds attach reliably.
- Featured feed attaches immediately; lazy/fallback behavior for others.
- Analytics: `live_feed_view` with `feed_id`, `feed_type`, `location`, `operator`, `placement`.
- Live is intended as a repeat-use/sponsorable surface.

### Previous key commit: `abeb75a`
DBF Weekend restored after being hidden for 12 days by stale legacy `events.json`.
- Rewired to current ingested event pipeline.
- Public-event editorial filter added.
- Civic meetings remain available/labeled on full events calendar.
- Weekend is now a visible recurring retention/sponsor surface.

## 3. Technical baseline
Latest reported QA:
- **26/26** test suites
- **2,380 links, 0 dead**
- DBF Weekend intact
- Delaware Coast Live intact
- events ingest/classification intact
- sitemap intact
- favicon/social previews intact
- GA4 intact
- stable production URLs intact

Technical stability is the **floor**, not the main accomplishment going forward.

## 4. Current highest-value gap
The biggest visible constraint is now **real media**.

Claude reports:
- **10 of 34 homepage images are illustrations**.
- The new swipe rails expose the illustration problem more, not less.
- The town rail still leads with an illustrated Lewes tile.

However, Michael has previously supplied/owns real DBF photography, so do **not** automatically tell him to go shoot new images until the existing media has been reconciled. Possible problem: photos live in ChatGPT, Photos/iCloud, Desktop/downloads, external storage, or a local DBF folder but were never copied/tagged into the media paths Claude actually inspects.

The immediate human task is therefore a **2-hour media intake/reconciliation block on Wednesday, August 26, 2026**.

## 5. Exact next human task
Create:
`DBF_MEDIA_TO_UPLOAD_2026-08-26.zip`

Ideal contents:
- `TOP_12/` — Michael's strongest 12 DBF photos
- `PHOTOS/` — another 10-30 strong original/full-res assets
- `VIDEO/` — up to 5 clean short original clips
- `NOTES/media_notes.txt` — exact place/subject, rights/source, must-use/do-not-use notes

Priority places/content:
1. Lewes waterfront/canal/harbor
2. Rehoboth boardwalk/beach/downtown/Grove Park
3. Cape Henlopen tower/dunes/trails/wildlife
4. Dewey / Indian River Inlet / Delaware Seashore
5. Bethany / Fenwick
6. Homes & Design (real coastal property/design frames)
7. Atmospheric Delaware details and human-scale moments

Use original/full-resolution files when possible. Do not use screenshots when the original exists. Preserve originals. Do not guess location or rights.

## 6. Next code sprint AFTER media packet is uploaded
The next Claude Code/Codex prompt should be a **real-media reconciliation + visual deployment sprint**, not generic backend work.

Expected visible outcomes:
- replace appropriate illustration-heavy homepage/town surfaces with real DBF photography;
- use multiple relevant photos inside strong long-form stories when a real photo editor would reasonably place them;
- increase real visual reward in the first five mobile screens;
- strengthen homepage lead/supporting visual hierarchy;
- use short clean original video where it creates genuine motion;
- preserve Live/Weekend/share/rails;
- optimize derivatives but preserve source originals;
- track meaningful content selections where useful;
- quantify real-photo vs illustration changes before/after.

Do not add stock or AI-generated Delaware photography. Do not invent locations. Do not tell Michael to reshoot a place until the uploaded inventory has been fully reconciled.

## 7. Deferred product items
- **Recently Viewed** via local browser storage was evaluated and deferred. It remains a promising cheap retention experiment after photography.
- Persistent mobile bottom navigation was intentionally deferred pending more behavior data. Do not add it merely to imitate an app.
- Native app development is NOT underway. The mobile website remains the prototype. Serious iOS + Android app consideration is planned after enough real behavior data is collected in September 2026.

## 8. Product operating rule
Articles are the depth layer, not the entire product. DBF should build loops such as:

**Home → Now/Weekend → Live → Town → Story → Event → Story/Archive → return tomorrow**

The desired reader reactions are:
- first-time visitor: “There is a lot happening here.”
- returning visitor: “There is something new/useful for me.”
- local: “This is worth checking.”
- advertiser: “People spend real attention here.”

## 9. Monetization context
DBF is entering monetization. Near-term revenue paths include:
- DBF-owned Etsy commerce;
- direct/founding local sponsors, especially DBF Weekend/Live/current utility surfaces;
- legitimate affiliate programs once actually enrolled/configured.

Do not fabricate affiliate links or revenue. Audience acquisition and retention are now prerequisites for valuable sponsorship inventory.

## 10. Resume instruction for future assistant
Read this save point first. Do NOT restart DBF strategy from scratch. The immediate next dependency is the August 26 media packet. If it has been uploaded, inspect it and map the real media to production surfaces before writing the next Claude prompt. If it has not been uploaded, help Michael complete the two-hour media intake with minimal friction.
