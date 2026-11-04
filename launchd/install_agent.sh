#!/usr/bin/env bash
set -euo pipefail

TEMPLATE="${1:-}"
[[ -f "$TEMPLATE" ]] || { echo "Usage: $0 <path-to-plist>" >&2; exit 1; }

TARGET_DIR="$HOME/Library/LaunchAgents"
TARGET="$TARGET_DIR/$(basename "$TEMPLATE")"
mkdir -p "$TARGET_DIR"

TMPFILE="$(mktemp /tmp/launchd_install.XXXXXX)"
trap 'rm -f "$TMPFILE"' EXIT

sed "s/{{USER}}/$(id -un)/g" "$TEMPLATE" > "$TMPFILE"
mv "$TMPFILE" "$TARGET"
chmod 644 "$TARGET"

LABEL="$(/usr/libexec/PlistBuddy -c 'Print :Label' "$TARGET" 2>/dev/null || basename "$TARGET" .plist)"
UID_NUM="$(id -u)"

if launchctl print "gui/$UID_NUM/$LABEL" >/dev/null 2>&1; then
    launchctl bootout "gui/$UID_NUM/$LABEL" 2>/dev/null || true
    sleep 0.5
fi

launchctl bootstrap "gui/$UID_NUM" "$TARGET"
echo "Agent $LABEL successfully bootstrapped."
