#!/usr/bin/env python3
"""Build data/content-index.json from stories.json, guides.json and towns.json.

Deterministic and idempotent: re-run any time editorial content changes.
Only public, published content is indexed. Coming-soon / paused / non-public
records are deliberately excluded so they can never surface as finished
articles in search or the archive.

Usage: python3 scripts/build_content_index.py
"""
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def load(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build():
    stories = load("stories.json") or []
    guides = load("guides.json") or []
    towns = load("towns.json") or []

    index = []

    for s in stories:
        if s.get("status") != "published":
            continue
        if s.get("access_level", "public") != "public":
            continue
        index.append({
            "id": "story-" + s["slug"],
            "type": "story",
            "title": s.get("headline", ""),
            "excerpt": s.get("hook", ""),
            "url": "stories/" + s["slug"] + ".html",
            "town": s.get("kicker", ""),
            "category": s.get("category", ""),
            "tags": [t for t in [s.get("category"), s.get("series")] if t],
            "publishedDate": s.get("date"),
            "updatedDate": s.get("date"),
            "status": "current",
            "access_level": s.get("access_level", "public"),
            "scene": s.get("scene"),
        })

    for g in guides:
        if g.get("status") != "published":
            continue
        if g.get("access_level", "public") != "public":
            continue
        index.append({
            "id": "guide-" + g["slug"],
            "type": "guide",
            "title": g.get("title", ""),
            "excerpt": g.get("dek", ""),
            "url": g.get("href", ""),
            "town": (g.get("meta", "").split("·")[0].strip() if g.get("meta") else ""),
            "category": "guide",
            "tags": ["guide"],
            "publishedDate": None,
            "updatedDate": None,
            "status": "current",
            "access_level": g.get("access_level", "public"),
            "scene": g.get("scene"),
        })

    for t in towns:
        index.append({
            "id": "town-" + t["slug"],
            "type": "town",
            "title": t.get("name", ""),
            "excerpt": t.get("dek", ""),
            "url": "towns/" + t["slug"] + ".html",
            "town": t.get("name", ""),
            "category": "town",
            "tags": ["town", t.get("state", "")],
            "publishedDate": None,
            "updatedDate": None,
            "status": "current",
            "access_level": "public",
            "scene": t.get("tileScene"),
        })

    out = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "recordCount": len(index),
        "records": index,
    }
    out_path = os.path.join(DATA, "content-index.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(index)} records to {out_path}")
    return out


if __name__ == "__main__":
    build()
