#!/usr/bin/env python3
"""Focused checks for the DBF editorial-expansion preview (dbf/editorial-expansion-preview).
Run: python3 scripts/check_editorial_preview.py
"""
import glob
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


# 7. Publication-activation checks
edit_min = edit_data.get("minPublishCount", 3)

# Watch DBF: a published entry must be fully specified, or it must stay unpublished.
watch = json.load(open(os.path.join(ROOT, "data", "watch-dbf.json")))
for e in watch.get("entries", []):
    if e.get("published"):
        for field in ("src", "poster", "posterAlt", "textAlternative"):
            check(f"published video '{e.get('id')}' has {field}", bool(e.get(field)))
        check(f"published video '{e.get('id')}' is not hotlinking a third party",
              not str(e.get("src", "")).startswith("http"))
published_video = [e for e in watch.get("entries", []) if e.get("published")]
check("video module hidden when no publishable entry exists (or renders when one does)",
      True if published_video else 'data-gate-hide' in index_html)

# No blanket manufacturing claims anywhere public.
BANNED = ["small-batch", "handcrafted goods", "made right here", "made on the Delaware shore", "Hand-blocked"]
offenders = []
for path in glob.glob(os.path.join(ROOT, "*.html")) + glob.glob(os.path.join(ROOT, "stories", "*.html")):
    body = open(path).read()
    for phrase in BANNED:
        if phrase in body:
            offenders.append(f"{os.path.basename(path)}: {phrase}")
check(f"no blanket handcrafted/small-batch claim remains ({len(offenders)} found)", not offenders)
for o in offenders[:5]:
    print("        ", o)

# House byline renders and is config-driven.
cfg = json.load(open(os.path.join(ROOT, "data", "site-editorial.json")))
check("site-editorial.json defines a house byline",
      bool(cfg.get("byline", {}).get("houseByline")))
byline_pages = [p for p in glob.glob(os.path.join(ROOT, "stories", "*.html"))
                if 'data-byline' in open(p).read()]
check(f"article pages use the house-byline hook ({len(byline_pages)} pages)", len(byline_pages) >= 8)
mismatch = [os.path.basename(p) for p in byline_pages
            if '"@type": "Person"' in open(p).read()]
check("no house-byline page still declares a Person author in structured data", not mismatch)

# Real-entity disclosure must survive the byline change.
about = open(os.path.join(ROOT, "about.html")).read()
check("About still discloses the real responsible entity", "rentdelawarebeaches" in about or "Schwander" in about)
check("About explains the desk byline system", "editorial desk bylines" in about)
# The disclosure has to do more than name the desks: it must say plainly that
# they are not individual people, which is the whole point of the guard.
check("About states desks are not individual reporters",
      "not pen names" in about and "does not exist" in about)

# Navigation must not be Shop-first and must stay simplified.
nav = re.search(r'<nav class="nav-links".*?</nav>', index_html, re.S)
nav_html = nav.group(0) if nav else ""
nav_items = re.findall(r"<a\b[^>]*>(.*?)</a>", nav_html)
check(f"primary nav is simplified to <=6 items ({len(nav_items)} found)", 0 < len(nav_items) <= 6)
check("primary nav has no Shop/Store item",
      not any("shop" in i.lower() or "store" in i.lower() for i in nav_items))

# Public pages must not explain their own implementation to readers.
impl_leak = []
for path in glob.glob(os.path.join(ROOT, "*.html")):
    body = open(path).read()
    for phrase in ["one small file", "without anyone touching layout code"]:
        if phrase in body:
            impl_leak.append(f"{os.path.basename(path)}: {phrase}")
check("no page explains its own file/layout implementation to visitors", not impl_leak)
for o in impl_leak[:3]:
    print("        ", o)

# Reveal animation must fail visible, not fail hidden.
check("scroll-reveal only hides content once JS confirms it can reveal it",
      "html.js-reveal .reveal{opacity:0" in styles_css and "js-reveal" in site_js)

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
