#!/bin/bash
# Description: Syncs Obsidian Vault from iCloud to NAS
# Label: com.jarpex.obsidiansync
set -euo pipefail

# Paths
SOURCE="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents"
DEST="/Volumes/Asya/20_Knowledge"
# Lock
LOCK_DIR="/tmp/sync_obsidian.lock"
#Unison
UNISON_BIN=$(which unison || echo "/opt/homebrew/bin/unison")

# Flags
SKIP_POWER_CHECK=0

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-power-check|-s)
            SKIP_POWER_CHECK=1
            shift
            ;;
        --help|-h)
            echo "Usage: $(basename "$0") [--skip-power-check|-s]"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $(basename "$0") [--skip-power-check|-s]"
            exit 1
            ;;
    esac
done

# Acquire lock to prevent overlapping runs
if mkdir "$LOCK_DIR" 2>/dev/null; then
    trap 'rm -rf "$LOCK_DIR"' INT TERM EXIT
else
    echo "Another instance is running. Exiting."
    exit 0
fi

# Ensure source exists
if [[ ! -d "$SOURCE" ]]; then
    echo "Error: Source directory not found: $SOURCE"
    exit 1
fi

# 1. Check Power Source (skip if on Battery)
if [[ $SKIP_POWER_CHECK -eq 1 ]]; then
    echo "Skipping power source check (flag set)."
else
    if [[ $(pmset -g batt) != *"AC Power"* ]]; then
        echo "Running on Battery. Sync skipped to save energy."
        exit 0
    fi
fi

# 2. Check if NAS is mounted
if [ -d "$DEST" ]; then
    echo "NAS is mounted. Starting sync..."

    # Starting Unison (invoked as-is; use absolute path in plist if needed)
    "$UNISON_BIN" "$SOURCE" "$DEST" \
        -batch \
        -times \
        -perms 0 \
        -dontchmod \
        -rsrc false \
        -force "$SOURCE" \
        -ignore "Name .DS_Store" \
        -ignore "Name .Trashes" \
        -ignore "Name .DocumentRevisions-V100" \
        -ignore "Name .Spotlight-V100" \
        -ignore "Name .*.swp" \
        -ignore "Name Icon?" \
        -ignore "Path */.makemd" \
        -ignore "Path */.space"
    echo "------------------------------------"
    echo "Done!"
else
    echo "Error: NAS is not mounted at $DEST"
    exit 1
fi

# Cleanup lock (trap will also remove it)
rm -rf "$LOCK_DIR"
trap - INT TERM EXIT
