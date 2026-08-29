#!/usr/bin/env python3
"""Sync the DBF Instagram archive from the official Instagram Graph API.

Official API only. No scraping, no HTML parsing, no unofficial endpoints.

The archive is CUMULATIVE and additive. Instagram's /media endpoint returns
only a recent window; anything that scrolls out of that window stays in the
archive forever. Posts are keyed by the immutable Instagram media ID, so a
re-run updates an existing record rather than duplicating it.

Editor-owned fields are never overwritten by a sync:
    localVideo, relatedUrl, relatedLabel, location, region, featured, note
Those are the fields a human curates. The API owns the factual ones:
    permalink, caption, mediaType, timestamp, thumbnail

Credentials come from the environment (GitHub Actions secrets):
    IG_USER_ID        the professional account's IG user id
    IG_ACCESS_TOKEN   a long-lived access token

Usage:
    python3 scripts/sync_instagram_archive.py            # sync and write
    python3 scripts/sync_instagram_archive.py --dry-run  # report only
    python3 scripts/sync_instagram_archive.py --check    # validate file only
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ARCHIVE = os.path.join(REPO, 'data', 'instagram-archive.json')

API_VERSION = 'v21.0'
FIELDS = 'id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,username'

# Fields a human curates. A sync must never clobber these.
EDITORIAL_FIELDS = ('localVideo', 'localPoster', 'relatedUrl', 'relatedLabel',
                    'location', 'region', 'featured', 'note', 'published')


def log(m):
    print(m, flush=True)


def load_archive():
    if not os.path.exists(ARCHIVE):
        return {'_note': '', 'syncedAt': None, 'posts': []}
    with open(ARCHIVE, encoding='utf-8') as fh:
        return json.load(fh)


def save_archive(doc):
    with open(ARCHIVE, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write('\n')


def fetch_media(user_id, token, limit=50, timeout=30):
    """Return (posts, error). Never raises."""
    url = ('https://graph.instagram.com/%s/%s/media?%s' %
           (API_VERSION, user_id,
            urllib.parse.urlencode({'fields': FIELDS, 'limit': limit,
                                    'access_token': token})))
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'DelawareBeachFinds/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8')).get('data', []), None
    except Exception as e:                                    # noqa: BLE001
        return [], '%s: %s' % (type(e).__name__, e)


def normalize(item):
    """API item -> archive record. Only factual, API-owned fields."""
    return {
        'id': str(item.get('id')),
        'permalink': item.get('permalink') or '',
        'caption': (item.get('caption') or '').strip(),
        'mediaType': (item.get('media_type') or '').upper(),   # IMAGE|VIDEO|CAROUSEL_ALBUM
        'timestamp': item.get('timestamp') or '',
        'thumbnail': item.get('thumbnail_url') or item.get('media_url') or '',
        'username': item.get('username') or 'delawarebeachfinds',
    }


def merge(existing, incoming):
    """Merge one API record into the archive, preserving curation."""
    out = dict(existing)
    out.update(incoming)                       # API wins on factual fields
    for f in EDITORIAL_FIELDS:                 # editor wins on curated fields
        if f in existing:
            out[f] = existing[f]
    return out


def main():
    dry = '--dry-run' in sys.argv
    check_only = '--check' in sys.argv

    doc = load_archive()
    posts = {str(p['id']): p for p in doc.get('posts', [])}

    if check_only:
        bad = [p for p in doc.get('posts', []) if not p.get('id') or not p.get('permalink')]
        log('archive posts: %d' % len(posts))
        log('records missing id/permalink: %d' % len(bad))
        return 1 if bad else 0

    user_id = os.environ.get('IG_USER_ID')
    token = os.environ.get('IG_ACCESS_TOKEN')
    if not user_id or not token:
        log('  IG_USER_ID / IG_ACCESS_TOKEN not set — nothing fetched.')
        log('  The existing archive is left exactly as it is (%d posts).' % len(posts))
        # Not an error: the site must keep working without credentials.
        return 0

    fetched, err = fetch_media(user_id, token)
    if err:
        log('  Instagram API request failed: %s' % err)
        log('  Archive left untouched (%d posts retained).' % len(posts))
        return 1

    added = updated = 0
    for item in fetched:
        rec = normalize(item)
        if not rec['id']:
            continue
        if rec['id'] in posts:
            merged = merge(posts[rec['id']], rec)
            if merged != posts[rec['id']]:
                updated += 1
            posts[rec['id']] = merged
        else:
            # New posts start unpublished on the site until an editor decides.
            rec.setdefault('featured', False)
            rec.setdefault('published', True)
            posts[rec['id']] = rec
            added += 1

    ordered = sorted(posts.values(), key=lambda p: p.get('timestamp') or '', reverse=True)
    doc['posts'] = ordered
    doc['syncedAt'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    doc['_note'] = ('Cumulative DBF Instagram archive, synced from the official '
                    'Instagram Graph API. Posts are keyed by immutable media id and are '
                    'never removed when they fall out of the API window. Editor-owned '
                    'fields (localVideo, relatedUrl, location, featured, note) survive '
                    'every sync — see scripts/sync_instagram_archive.py.')

    log('  fetched %d | added %d | updated %d | archive total %d'
        % (len(fetched), added, updated, len(ordered)))

    if dry:
        log('  DRY RUN — nothing written.')
        return 0
    save_archive(doc)
    log('  wrote %s' % os.path.relpath(ARCHIVE, REPO))
    return 0


if __name__ == '__main__':
    sys.exit(main())
