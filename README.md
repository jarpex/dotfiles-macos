# dotfiles

My personal macOS dotfiles for configuring and managing system and developer tool settings across multiple machines.

This repository contains symbolic link mappings for configuration files like `skhd`, and will be extended to support additional tools soon.

## 📦 Supported tools

- aerospace
- btop
- ghostty
- skhd
- zsh

## 🔁 Obsidian iCloud → NAS sync

This repo includes a small sync helper that mirrors an Obsidian vault from iCloud to a mounted NAS using `unison`.

- Script: `bin/sync_obsidian.sh` (installed/copied to `~/.local/bin/sync_obsidian` by the installer)
- Usage: run manually or via `launchd`; the script supports `--skip-power-check` (or `-s`) to bypass the AC-power check.
- Install: run `bash dotfiles-install.sh` to copy the script into `~/.local/bin` and make it executable.
- LaunchAgent: a plist template is provided at `launchd/com.jarpex.obsidiansync.plist` and an installer script at `launchd/install_launchd_plist.sh` which will patch the `{{USER}}` placeholder and load the agent into `~/Library/LaunchAgents`.

Notes:

- `launchd` agents should run non-symlinked executables (copying the script into `~/.local/bin` avoids permission issues when the repo is stored in `~/Documents`).
- The template uses `StartInterval` (default in the template is 3600);
- Ensure `unison` is available in the runtime PATH for `launchd` (you can use an absolute path in the plist's `ProgramArguments` if needed).
