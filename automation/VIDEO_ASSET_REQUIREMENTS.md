# Watch DBF — exact assets needed to turn the video module on

**Current status: the module is built and hidden.** It is hidden because the
repository contains **zero video files**. A full recursive search for `.mp4`,
`.webm`, `.mov`, `.m4v` and `.avi` returned nothing, and `ffmpeg` is not
installed in the build environment, so nothing could be transcoded either.

Nothing fake is shown to visitors in the meantime — the section does not render
at all, and its department-navigator panel stays hidden with it.

---

## What to drop in

Put the files here:

```
assets/video/towers-on-the-dunes.mp4      <- required
assets/video/towers-on-the-dunes.webm     <- optional but recommended
assets/images/video-posters/towers-on-the-dunes.jpg   <- required
```

### Video file

| Property | Target | Why |
|---|---|---|
| Container / codec | MP4, H.264 (High profile), AAC or no audio track | Widest browser support |
| Second format | WebM / VP9 (optional) | Smaller on Chrome/Firefox |
| Resolution | **1920×1080 max**, 1280×720 is fine | A phone master (4K) is far too heavy for a homepage |
| Duration | **8–25 seconds** | This is an editorial loop, not a film |
| Target size | **under 3 MB**, ideally ~1.5 MB | Homepage must stay fast |
| Frame rate | 24–30 fps | |
| Audio | **Strip it, or ensure it is original/licensed** | See rights below |

If you have ffmpeg available, this produces a correctly-sized web file from a
phone master:

```bash
ffmpeg -i INPUT.mov -vf "scale='min(1920,iw)':-2" -c:v libx264 -profile:v high \
  -crf 24 -preset slow -movflags +faststart -an assets/video/towers-on-the-dunes.mp4
```

`-an` strips audio entirely (simplest rights position). `-movflags +faststart`
lets playback begin before the whole file downloads.

### Poster image

- Same aspect ratio as the video (avoids layout shift)
- 1600px wide max, JPG, under ~250 KB
- Must be a real frame from the clip, not a different scene

---

## Rights rules — these are not optional

The module will happily play whatever you give it, so the rules live here:

- ✅ **Original DBF footage you shot.** This is the intended source.
- ✅ **Silent / muted footage.** Simplest and safest.
- ✅ **Original ambient audio** you recorded on location.
- ✅ **Audio you hold a documented website license for.**
- ❌ **Never** the audio from an Instagram Reel. Instagram's music licensing
  covers playback *on Instagram*, not self-hosting on your own domain. Rip the
  audio out before it goes in `assets/video/`.
- ❌ **Never** download media from Instagram (yours or anyone's) to self-host —
  export from the original source file instead.
- ❌ **Never** third-party footage without a written license.

`data/watch-dbf.json` records `rights` and `audio` per entry so this stays
auditable later.

---

## Activating it

1. Add the files above.
2. In `data/watch-dbf.json`, fill in on the entry:
   - `src` → `assets/video/towers-on-the-dunes.mp4`
   - `srcWebm` → the WebM path, or leave `""`
   - `poster` → the poster path
   - `posterAlt` → a real description of the frame
   - `textAlternative` → a sentence describing what happens in the clip, for
     anyone who cannot see or play it
   - `durationSeconds` → actual length
   - `published` → `true`
3. Reload. The section and its nav panel appear automatically.

Run `python3 scripts/check_editorial_preview.py` afterwards — it asserts that a
published entry has all of `src`, `poster`, `posterAlt` and `textAlternative`,
so a half-filled entry fails loudly instead of shipping a broken player.

---

## Behaviour once live

- Poster renders first; the video file is only fetched when the module scrolls
  near the viewport
- Muted + `playsinline`; a short loop may autoplay **only** if the browser
  allows it and the visitor has not asked for reduced motion
- Otherwise: poster + a clear play button
- Playback pauses automatically when scrolled out of view
- Visible, keyboard-reachable controls; focus is never trapped
- Explicit `width`/`height` so nothing shifts as it loads
