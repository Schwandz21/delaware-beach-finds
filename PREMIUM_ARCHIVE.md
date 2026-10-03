# Premium archive access

**Status: disabled.** `data/premium-archive.json` has `"enabled": false` with the
reason "Protected premium-content backend is not yet configured." Every archived
story is free to read, and the archive page says so. **No paywall exists.**

## Why it cannot simply be switched on

The site is a static GitHub Pages build of a public repository. Today the full
text of every archived story is public in three places:

1. `content/stories/<slug>.html` holds the canonical prose in the public repo.
2. `stories/<slug>.html` is the rendered public page.
3. `data/stories.json` has an inline `body` that the browser fetches.

Hiding any of these with JavaScript is cosmetic. Anyone can read the file
directly. So `scripts/premium_archive.py` refuses `"enabled": true` while any
premium-eligible story's full text is still exposed. That check runs in three
places:

- `scripts/validate_editorial.py`, so the hourly publisher refuses to run;
- `scripts/test_story_archive.py`, as part of `run_tests.sh`;
- `python3 scripts/premium_archive.py`, which reports how many exposures remain.

## What enabling it requires

1. **A real backend with authentication and payments.** It must offer:
   - `GET <fullTextEndpoint>/<slug>`, which returns `{slug, html}` to an
     entitled, signed-in subscriber, `401` to anyone not signed in and `403` to
     anyone not entitled;
   - `GET <accessStateEndpoint>`, which returns
     `{signedIn, entitled, plan, expiresAt}`.
2. **The premium prose moved behind that backend.** Remove it from the public
   repository, from the public static HTML and from `data/stories.json`. The
   private archive export (`scripts/export_story_archive.py`) is the owner's
   checksummed source copy to load into the backend.
3. **Public teasers only on the static site.** Serve metadata plus the hook:
   headline, kicker, hook, date, issue, category, author desk, hero image and
   word count. All of these are already in `data/story-archive.json` or the
   story record.
4. **The config.** Set `"enabled": true` and add `"fullTextEndpoint"` and
   `"accessStateEndpoint"` to `data/premium-archive.json`.

The validator and the tests pass only once steps 1–4 are all true. Until then,
nothing on the site may say that paid access works.
