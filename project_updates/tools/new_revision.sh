#!/usr/bin/env bash
set -euo pipefail

# Portable revision helper. Assumes this script lives at:
#   <repo>/project_updates/tools/new_revision.sh
# and that <repo>/project_updates/README.md exists.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

usage() {
  cat <<'EOF'
Usage:
  bash project_updates/tools/new_revision.sh workflow-standards
  bash project_updates/tools/new_revision.sh project-upgrade-prompt

Creates a new same-day revision (e.g. __r3.md) by copying the current "Latest"
file referenced in project_updates/README.md, then updates the README to point
to the new file. You still edit the new file to add the actual learnings.
EOF
}

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

KIND="$1"
case "$KIND" in
  workflow-standards)
    README_KEY="Workflow standards"
    ;;
  project-upgrade-prompt)
    README_KEY="Upgrade prompt"
    ;;
  *)
    echo "Unknown kind: $KIND" >&2
    usage
    exit 2
    ;;
esac

README_PATH="project_updates/README.md"
if [[ ! -f "$README_PATH" ]]; then
  echo "Missing: $README_PATH" >&2
  exit 1
fi

if command -v rg >/dev/null 2>&1; then
  LATEST_LINE="$(rg -n "^- ${README_KEY}: " "$README_PATH" | head -n 1 || true)"
else
  LATEST_LINE="$(grep -nE "^- ${README_KEY}: " "$README_PATH" | head -n 1 || true)"
fi
if [[ -z "$LATEST_LINE" ]]; then
  echo "Could not find '- ${README_KEY}: `...`' in $README_PATH" >&2
  exit 1
fi

LATEST_FILE="$(echo "$LATEST_LINE" | sed -n 's/.*`\([^`]*\)`.*/\1/p')"
if [[ -z "$LATEST_FILE" || ! -f "$LATEST_FILE" ]]; then
  echo "Parsed latest file is missing: $LATEST_FILE" >&2
  exit 1
fi

DATE_UTC="$(date -u +%F)"
BASE="project_updates/${DATE_UTC}__langhero__${KIND}"

max_r=1
for f in ${BASE}__r*.md; do
  [[ -e "$f" ]] || continue
  r="$(echo "$f" | sed -n 's/.*__r\([0-9][0-9]*\)\.md/\1/p')"
  if [[ -n "$r" && "$r" -gt "$max_r" ]]; then
    max_r="$r"
  fi
done

next_r=$((max_r + 1))
NEW_FILE="${BASE}__r${next_r}.md"

cp "$LATEST_FILE" "$NEW_FILE"

# Ensure the new file references the previous latest in "Previous versions".
has_rg=0
if command -v rg >/dev/null 2>&1; then
  has_rg=1
fi

if (( has_rg )); then
  has_prev_versions="$(rg -n "^## Previous versions" "$NEW_FILE" >/dev/null 2>&1 && echo 1 || echo 0)"
else
  has_prev_versions="$(grep -nE "^## Previous versions" "$NEW_FILE" >/dev/null 2>&1 && echo 1 || echo 0)"
fi

if [[ "$has_prev_versions" == "1" ]]; then
  escaped_latest="$(printf '%s' "$LATEST_FILE" | sed 's/[.[\\^$*+?(){|]/\\\\&/g')"
  if (( has_rg )); then
    has_link="$(rg -n "$escaped_latest" "$NEW_FILE" >/dev/null 2>&1 && echo 1 || echo 0)"
  else
    has_link="$(grep -nE "$escaped_latest" "$NEW_FILE" >/dev/null 2>&1 && echo 1 || echo 0)"
  fi
  if [[ "$has_link" != "1" ]]; then
    tmp="$(mktemp)"
    awk -v prev="$LATEST_FILE" '
      BEGIN { inserted = 0 }
      { print }
      $0 ~ /^## Previous versions/ && inserted == 0 {
        print ""
        print "- `" prev "`"
        inserted = 1
      }
    ' "$NEW_FILE" > "$tmp"
    mv "$tmp" "$NEW_FILE"
  fi
fi

tmp="$(mktemp)"
awk -v key="$README_KEY" -v newfile="$NEW_FILE" '
  {
    if ($0 ~ ("^- " key ": ")) {
      print "- " key ": `" newfile "`"
    } else {
      print
    }
  }
' "$README_PATH" > "$tmp"
mv "$tmp" "$README_PATH"

chmod +x "$NEW_FILE" 2>/dev/null || true

echo "Created: $NEW_FILE"
echo "Updated: $README_PATH"
echo "Next: edit $NEW_FILE and add your learnings; then commit both files."
