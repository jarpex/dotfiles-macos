#!/usr/bin/env bash
set -euo pipefail

# Installs or updates the plist template into ~/Library/LaunchAgents,
# replaces {{USER}} with the current username, and (re)loads it via launchctl.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="$SCRIPT_DIR/com.jarpex.obsidiansync.plist"
TARGET_DIR="$HOME/Library/LaunchAgents"
TARGET="$TARGET_DIR/$(basename "$TEMPLATE")"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "Template not found: $TEMPLATE" >&2
  exit 1
fi

USERNAME="$(id -un)"

TMPFILE="$(mktemp /tmp/launchd_install.XXXXXX)"
trap 'rm -f "$TMPFILE"' EXIT

# Replace placeholder
sed "s/{{USER}}/${USERNAME}/g" "$TEMPLATE" > "$TMPFILE"

# Ensure target dir exists
mkdir -p "$TARGET_DIR"

if [[ -f "$TARGET" ]]; then
  if cmp -s "$TMPFILE" "$TARGET"; then
    echo "No changes in $TARGET; leaving existing agent intact."
    exit 0
  else
    echo "Updating existing plist at $TARGET"
  fi
else
  echo "Installing plist to $TARGET"
fi

# Move into place
mv "$TMPFILE" "$TARGET"
chmod 644 "$TARGET"

# Determine label from plist (fallback to filename without .plist)
LABEL="$(/usr/libexec/PlistBuddy -c 'Print :Label' "$TARGET" 2>/dev/null || true)"
if [[ -z "$LABEL" ]]; then
  LABEL="$(basename "$TARGET" .plist)"
fi

# If agent is already loaded, unload it first
if launchctl list | grep -Fq "$LABEL"; then
  echo "Unloading existing launch agent: $LABEL"
  launchctl unload "$TARGET" || true
fi

echo "Loading launch agent: $TARGET"
launchctl load "$TARGET"

echo "Done."
