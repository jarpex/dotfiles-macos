#!/bin/bash
set -euo pipefail

# Path to your dotfiles repository
DOTFILES_DIR="$HOME/Documents/Repos/dotfiles"
# Backup directory for existing files
BACKUP_DIR="$HOME/.dotfiles_backup_$(date +%Y%m%d_%H%M%S)"

# Create a symbolic link from $1 (source relative to DOTFILES_DIR)
# to $2 (absolute target path in home directory)
link_file() {
    local rel="$1"
    local source="$DOTFILES_DIR/$rel"
    local target="$HOME/$2"

    # Ensure the target's parent directory exists
    mkdir -p "$(dirname "$target")"

    # If the target exists
    if [ -L "$target" ]; then
        # If it's already the correct symlink
        if [ "$(readlink "$target")" = "$source" ]; then
            echo "✔ Symlink already exists: $target → $source"
            return
        else
            echo "⚠️ Conflicting symlink found. Backing up."
            mkdir -p "$BACKUP_DIR"
            mv "$target" "$BACKUP_DIR/"
        fi
    elif [ -e "$target" ]; then
        # If it's a regular file or directory
        echo "⚠️ File or directory exists at $target. Backing up."
        mkdir -p "$BACKUP_DIR"
        mv "$target" "$BACKUP_DIR/"
    fi

    # Create symbolic link
    ln -s "$source" "$target"
    echo "✅ Linked: $target → $source"

    # If this is a script (in bin/ or ends with .sh), ensure it's executable
    if [[ "$rel" == bin/* || "$rel" == *.sh ]]; then
        chmod +x "$source" || true
        echo "🔧 Ensured executable: $source"
    fi
}

# Copy a script from the repo into the user's home (useful for LaunchAgents)
install_script() {
    local rel="$1"
    local source="$DOTFILES_DIR/$rel"
    local target="$HOME/$2"

    # Ensure source exists
    if [[ ! -f "$source" ]]; then
        echo "Error: script source not found: $source"
        return 1
    fi

    # Ensure the target's parent directory exists
    mkdir -p "$(dirname "$target")"

    # If the target exists, back it up if different
    if [ -e "$target" ] || [ -L "$target" ]; then
        if cmp -s "$source" "$target"; then
            echo "✔ Script already installed and identical: $target → $source"
            return 0
        else
            echo "⚠️ Existing file at $target. Backing up."
            mkdir -p "$BACKUP_DIR"
            mv "$target" "$BACKUP_DIR/"
        fi
    fi

    # Copy the script and ensure it's executable
    cp "$source" "$target"
    chmod 755 "$target" || true
    echo "✅ Installed script: $target → $source"
}

# btop config
link_file ".config/btop/btop.conf" ".config/btop/btop.conf"
# ghostty config
link_file ".config/ghostty/config" ".config/ghostty/config"
# skhd config
link_file ".config/skhd/skhdrc" ".config/skhd/skhdrc"
# zsh config
link_file ".config/zsh" ".config/zsh"
link_file ".zshrc" ".zshrc"

# install sync script into ~/.local/bin (copy, not symlink, for launchd compatibility)
install_script "bin/sync_obsidian.sh" ".local/bin/sync_obsidian"