#!/usr/bin/env python3
"""Focused checks for the DBF editorial-expansion preview (dbf/editorial-expansion-preview).
Run: python3 scripts/check_editorial_preview.py
"""
import json, re, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
failures = []


def fail(msg):
    failures.append(msg)


def check(desc, ok):
    print(("  ok  - " if ok else "FAIL  - ") + desc)
    if not ok:
        fail(desc)


# 1. DBF Edit minimum-entry publishing gate
edit_path = os.path.join(ROOT, "data", "dbf-edit.json")
with open(edit_path) as f:
    edit_data = json.load(f)
min_count = edit_data.get("minPublishCount", 3)
entries = edit_data.get("entries", [])
valid_entries = [e for e in entries if e.get("title") and e.get("image") and e.get("url") and e.get("description")]
check("dbf-edit.json declares a minPublishCount", "minPublishCount" in edit_data)
check(f"dbf-edit.json has >= {min_count} valid entries ({len(valid_entries)} found)", len(valid_entries) >= min_count)
for e in valid_entries:
    check(f"  entry '{e.get('id')}' has affiliateDisclosure field set", "affiliateDisclosure" in e)
    check(f"  entry '{e.get('id')}' is access_level public", e.get("access_level") == "public")

# 2. No accidental Shop/checkout build
suspicious_files = ["cart.html", "checkout.html", "cart.js", "checkout.js"]
for fn in suspicious_files:
    check(f"no {fn} file was introduced", not os.path.exists(os.path.join(ROOT, fn)))

index_html = open(os.path.join(ROOT, "index.html")).read()
check("homepage nav has no new Cart/Checkout link", "cart" not in index_html.lower() and "checkout" not in index_html.lower())

# 3. Every <img> in index.html has non-empty alt text
imgs = re.findall(r"<img\s+[^>]*>", index_html)
missing_alt = [i for i in imgs if not re.search(r'alt="[^"]+"', i)]
check(f"all {len(imgs)} <img> tags in index.html have non-empty alt text", len(missing_alt) == 0)
if missing_alt:
    for m in missing_alt[:5]:
        print("        missing alt:", m[:100])

# 4. Empty-module suppression mechanism present and CSS-backed
styles_css = open(os.path.join(ROOT, "assets", "css", "styles.css")).read()
check("data-dept-panel=\"the-edit\" hook exists in index.html", 'data-dept-panel="the-edit"' in index_html)
check(".is-hidden is a generic rule (not scoped to one component) so it hides any element",
      bool(re.search(r"(^|[\s,}])\.is-hidden\s*\{\s*display\s*:\s*none", styles_css)))
check("#the-edit section starts with a gating mount (data-mount=\"dbf-edit\")", 'data-mount="dbf-edit"' in index_html)

# 5. site.js contains the gating logic, not just static markup
site_js = open(os.path.join(ROOT, "assets", "js", "site.js")).read()
check("site.js checks entries against minPublishCount before rendering",
      "minPublishCount" in site_js and "valid.length < minCount" in site_js)
check("site.js hides the section AND its nav panel on gate failure",
      "editSection.classList.add('is-hidden')" in site_js and "editNavPanel.classList.add('is-hidden')" in site_js)

# 6. Reduced-motion respected
check("prefers-reduced-motion is honored for .reveal", "prefers-reduced-motion" in styles_css and "prefers-reduced-motion" in site_js)

print()
print("================================")
if failures:
    print(f"{len(failures)} check(s) failed:")
    for f in failures:
        print("  -", f)
    sys.exit(1)
else:
    print("All editorial-preview checks passed.")
    sys.exit(0)
