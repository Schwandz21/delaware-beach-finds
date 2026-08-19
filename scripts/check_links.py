#!/usr/bin/env python3
"""Check every relative internal href across the site resolves to a real file.

Usage: python3 scripts/check_links.py
Exit code 0 = clean, 1 = dead links found.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "node_modules", "backups", ".github",
             # Local-only material that is gitignored and must never be validated
             # as if it were production: a stale July-15 snapshot, savepoints, media.
             "dbf-rebuild-tmp", ".claude", "Instagram reels",
             # Renderer inputs, not deployed pages. templates/ hrefs are
             # {{PLACEHOLDER}} tokens; content/ holds body fragments whose
             # relative links resolve from stories/, where they are checked
             # once rendered.
             "templates", "content"}


def main():
    missing = []
    checked = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(".html"):
                continue
            path = os.path.join(dirpath, fn)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            # strip inline <script> blocks so JS string concatenation like
            # `href="'+esc(r.url)+'"` never gets mistaken for a real href
            content = re.sub(r"<script\b[^>]*>.*?</script>", "", content, flags=re.S)
            base_dir = os.path.dirname(path)
            for m in re.finditer(r'href="([^"]+)"', content):
                href = m.group(1)
                if href.startswith(("http://", "https://", "mailto:", "#", "tel:")):
                    continue
                # Strip both fragment and query string. Cache-busted asset
                # references like favicon.svg?v=2 resolve to the file itself.
                href_path = href.split("#")[0].split("?")[0]
                if not href_path:
                    continue
                checked += 1
                target = os.path.normpath(os.path.join(base_dir, href_path))
                if not os.path.exists(target):
                    missing.append((os.path.relpath(path, ROOT), href))

    print(f"Checked {checked} internal links")
    if missing:
        print("MISSING:")
        for p, h in missing:
            print(f"  {p} -> {h}")
        return 1
    print("No dead internal links found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
