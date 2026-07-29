#!/bin/bash
# UPDATE_DBF_FRESHNESS.command
#
# Double-click this in Finder to review and apply a weekly freshness
# candidate (produced by the scheduled Claude research task) to
# Delaware Beach Finds — validate, preview, back up, apply, test,
# commit, push, and verify. Every destructive step requires your
# explicit yes. Nothing is force-pushed or destructively reset.
#
# Can also be run from a terminal: ./UPDATE_DBF_FRESHNESS.command

set -u
cd "$(dirname "$0")" || exit 1
REPO_ROOT="$(pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'

say()  { echo -e "$1"; }
fail() { echo -e "${RED}✗ $1${NC}"; exit 1; }
ok()   { echo -e "${GREEN}✓ $1${NC}"; }

confirm() {
  # $1 = prompt. Returns 0 for yes, 1 for no/cancel.
  local reply
  read -r -p "$1 [y/N] " reply
  case "$reply" in
    [yY][eE][sS]|[yY]) return 0 ;;
    *) return 1 ;;
  esac
}

say "${BOLD}Delaware Beach Finds — Freshness Updater${NC}"
say "Repo: $REPO_ROOT"
say ""

command -v python3 >/dev/null 2>&1 || fail "python3 is required and was not found on this Mac."
command -v git >/dev/null 2>&1 || fail "git is required and was not found on this Mac."

# ---------------------------------------------------------------------------
# 1. Locate the candidate file
# ---------------------------------------------------------------------------
CANDIDATE=""
if [ "${1:-}" != "" ]; then
  CANDIDATE="$1"
elif command -v osascript >/dev/null 2>&1; then
  CANDIDATE=$(osascript -e 'POSIX path of (choose file with prompt "Select the DBF freshness candidate JSON file" of type {"json","public.json"})' 2>/dev/null)
fi
if [ -z "$CANDIDATE" ]; then
  read -r -p "Path to candidate JSON file: " CANDIDATE
fi
if [ -z "$CANDIDATE" ] || [ ! -f "$CANDIDATE" ]; then
  fail "No candidate file selected. Nothing was changed. Run this again when you have a candidate to review."
fi
say "Candidate: $CANDIDATE"
say ""

# ---------------------------------------------------------------------------
# 2. Validate
# ---------------------------------------------------------------------------
say "${BOLD}Step 1 — Validating candidate${NC}"
if ! python3 scripts/validate_candidate.py "$CANDIDATE"; then
  fail "Candidate failed validation (see errors above). Nothing was changed. Fix the candidate and run this again."
fi
ok "Candidate is valid"
say ""

# ---------------------------------------------------------------------------
# 3. Preview (dry run)
# ---------------------------------------------------------------------------
say "${BOLD}Step 2 — Proposed changes${NC}"
python3 scripts/apply_candidate.py "$CANDIDATE"
say ""

if ! confirm "Apply these changes to your local data files?"; then
  say "${YELLOW}Cancelled — nothing was changed.${NC}"
  exit 0
fi

# ---------------------------------------------------------------------------
# 4. Backup
# ---------------------------------------------------------------------------
say ""
say "${BOLD}Step 3 — Backing up current data${NC}"
STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="backups/$STAMP"
mkdir -p "$BACKUP_DIR"
for f in data/events.json data/events-archive.json data/guides.json data/content-index.json; do
  [ -f "$f" ] && cp "$f" "$BACKUP_DIR/$(basename "$f")"
done
ok "Backed up to $BACKUP_DIR"
say ""

# ---------------------------------------------------------------------------
# 5. Apply
# ---------------------------------------------------------------------------
say "${BOLD}Step 4 — Applying changes${NC}"
if ! python3 scripts/apply_candidate.py "$CANDIDATE" --apply; then
  fail "Apply failed. Your data files were not modified beyond this point — restore from $BACKUP_DIR if anything looks wrong."
fi
ok "Data files updated"
say ""

# ---------------------------------------------------------------------------
# 6. Rebuild search index
# ---------------------------------------------------------------------------
say "${BOLD}Step 5 — Refreshing search index${NC}"
python3 scripts/build_content_index.py || fail "Failed to rebuild content-index.json."
ok "Search index refreshed"
say ""

# ---------------------------------------------------------------------------
# 7. Run checks
# ---------------------------------------------------------------------------
say "${BOLD}Step 6 — Running checks${NC}"
CHECKS_OK=1

for f in data/events.json data/events-archive.json data/guides.json data/content-index.json; do
  python3 -c "import json,sys; json.load(open('$f'))" || { say "${RED}Invalid JSON: $f${NC}"; CHECKS_OK=0; }
done

python3 scripts/check_links.py || CHECKS_OK=0
python3 scripts/freshness_report.py || say "${YELLOW}(freshness report flags items to review — see above; not necessarily blocking)${NC}"

if [ "$CHECKS_OK" != "1" ]; then
  say ""
  fail "Checks failed. Restore from $BACKUP_DIR if you want to undo:  for f in $BACKUP_DIR/*; do cp \"\$f\" data/\$(basename \"\$f\"); done"
fi
ok "All checks passed"
say ""

# ---------------------------------------------------------------------------
# 8. Commit
# ---------------------------------------------------------------------------
say "${BOLD}Step 7 — Git status${NC}"
git status --short -- data/events.json data/events-archive.json data/guides.json data/content-index.json
say ""
if ! confirm "Commit these changes to your local main branch?"; then
  say "${YELLOW}Cancelled before commit — your data files ARE updated locally but not committed or pushed.${NC}"
  say "Restore the previous version any time with: for f in $BACKUP_DIR/*; do cp \"\$f\" data/\$(basename \"\$f\"); done"
  exit 0
fi

COMMIT_MSG="Weekly freshness update: $(basename "$CANDIDATE")"
git add data/events.json data/events-archive.json data/guides.json data/content-index.json
git commit -m "$COMMIT_MSG" || fail "Commit failed."
ok "Committed: $COMMIT_MSG"
say ""

# ---------------------------------------------------------------------------
# 9. Push
# ---------------------------------------------------------------------------
if ! confirm "Push to origin/main now? This deploys live to delawarebeachfinds.com."; then
  say "${YELLOW}Cancelled before push — committed locally only. Push later with: git push origin main${NC}"
  exit 0
fi

git push origin main || fail "Push failed. Your commit is still local — resolve the git error and push manually."
ok "Pushed to origin/main"
say ""

# ---------------------------------------------------------------------------
# 10. Verify live
# ---------------------------------------------------------------------------
say "${BOLD}Step 8 — Verifying live deployment${NC}"
say "Waiting for GitHub Pages to redeploy (this can take a minute)..."
ATTEMPTS=0
DEPLOYED=0
while [ $ATTEMPTS -lt 24 ]; do
  if curl -s "https://delawarebeachfinds.com/data/events.json?cb=$(date +%s)" | grep -q "$(python3 -c "import json; print(json.load(open('data/events.json'))['verifiedAt'])")"; then
    DEPLOYED=1
    break
  fi
  ATTEMPTS=$((ATTEMPTS+1))
  sleep 5
done

if [ "$DEPLOYED" = "1" ]; then
  ok "Live site confirmed updated."
  for url in "https://delawarebeachfinds.com/" "https://delawarebeachfinds.com/this-week.html" "https://delawarebeachfinds.com/events.html" "https://delawarebeachfinds.com/guides.html"; do
    CODE=$(curl -s -o /dev/null -w "%{http_code}" "$url?cb=$(date +%s)")
    say "  $CODE  $url"
  done
  say ""
  say "${GREEN}${BOLD}Done. This week's update is live.${NC}"
else
  say "${YELLOW}Pushed successfully, but couldn't confirm the live deploy within 2 minutes.${NC}"
  say "GitHub Pages can occasionally take longer — check https://delawarebeachfinds.com manually in a few minutes,"
  say "or check the Actions/Pages tab on GitHub for deploy status."
fi
