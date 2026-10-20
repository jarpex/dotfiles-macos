# dotfiles

My personal macOS dotfiles for configuring and managing system and developer tool settings across multiple machines.

This repository contains symbolic link mappings for configuration files like `skhd`, and will be extended to support additional tools soon.

## Supported tools

- aerospace
- btop
- ghostty
- skhd
- tmux
- zsh

## AeroSpace: returning to the previous workspace

AeroSpace's `on-window-detected` callbacks can move a freshly opened window to
another workspace. When
that window is later closed, macOS moves focus to the previously focused app -
but AeroSpace then _bounces_ the focused workspace back to the now-empty desk
the closed window lived on. You end up staring at an empty workspace while
macOS believes the other app is focused, so clicking it in the Dock does
nothing.

`bin/aerospace-workspace-return` fixes that. It runs as a `launchd` agent and:

1. subscribes to AeroSpace's event stream over its Unix socket
   (`window-detected`, `focus-changed`, `focused-workspace-changed`),
2. remembers the workspace each window was opened on (the "origin"),
3. watches the _process_ of every automatically moved window directly
   (kqueue's `NOTE_EXIT`, no socket round trip),
4. moves the dying window back to its origin **before** AeroSpace collects it.

- Script: `bin/aerospace-workspace-return` (copied to
  `~/.local/bin/aerospace-workspace-return` by the installer)
- LaunchAgent: `launchd/com.jarpex.aerospace-workspace-return.plist`, installed
  with `bash launchd/install_aerospace_workspace_return.sh`
- Log: `/tmp/aerospace-workspace-return.log`
  (set `AEROSPACE_RETURN_DEBUG=1` for verbose output)

## Launching apps with `aerolaunch`

`bin/aerolaunch` launches an app and returns to the origin workspace when it
exits. It works from the shell and from `skhd` hotkeys:

```bash
aerolaunch open -a "Telegram"
aerolaunch code .
```

It injects `-W` for `open` and `-w` for `code` so the command blocks until the
app quits, then switches back to the workspace it was launched from.

Note: `aerolaunch` returns you to the origin when the app **quits**, not when
you close its last window. For apps that linger in the menu bar use `Cmd+Q`
rather than `Cmd+W`.

## 🔁 Obsidian iCloud → NAS sync

This repo includes a small sync helper that mirrors an Obsidian vault from iCloud to a mounted NAS using `unison`.

- Script: `bin/sync_obsidian.sh` (installed/copied to `~/.local/bin/sync_obsidian` by the installer)
- Usage: run manually or via `launchd`; the script supports `--skip-power-check` (or `-s`) to bypass the AC-power check.
- Install: run `bash dotfiles-install.sh` to copy the script into `~/.local/bin` and make it executable.
- LaunchAgent: a plist template is provided at `launchd/com.jarpex.obsidiansync.plist` and an installer script at `launchd/install_obsidian_sync.sh` which will patch the `{{USER}}` placeholder and load the agent into `~/Library/LaunchAgents`.

Notes:

- `launchd` agents should run non-symlinked executables (copying the script into `~/.local/bin` avoids permission issues when the repo is stored in `~/Documents`).
- The template uses `StartInterval` (default in the template is 3600);
- Ensure `unison` is available in the runtime PATH for `launchd` (you can use an absolute path in the plist's `ProgramArguments` if needed).
