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

If the window was collected first, the bounce is recognised from the event
stream - focus landing on an empty workspace - and undone immediately.

Every command to AeroSpace's socket makes it lay out all its workspaces, so
the helper reads the window list only when a window appears, and every 15
seconds as a safety net. An earlier version polled the socket 10 times a
second and cost AeroSpace about 37% CPU; the current one costs under 1%.

A lock file keeps a second instance from running, so a duplicated launchd
agent cannot double the load.

- Script: `bin/aerospace-workspace-return` (copied to
  `~/.local/bin/aerospace-workspace-return` by the installer)
- LaunchAgent: `launchd/com.jarpex.aerospace-workspace-return.plist`, installed
  with `bash launchd/install_aerospace_workspace_return.sh`
- Log: `/tmp/aerospace-workspace-return.log`
  (set `AEROSPACE_RETURN_DEBUG=1` for verbose output)
- Tests: `python3 tests/test_aerospace_workspace_return.py`,
  `python3 tests/test_integration.py`, `python3 tests/test_daemon_e2e.py`

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

## Obsidian iCloud to NAS sync

This repo includes a sync helper that mirrors an Obsidian vault from iCloud to
a mounted NAS using `unison`.

- Script: `bin/sync_obsidian.sh` (installed/copied to `~/.local/bin/sync_obsidian` by the installer)
- Usage: run manually or via `launchd`; the script supports `--skip-power-check` (or `-s`) to bypass the AC-power check.
- Install: run `bash dotfiles-install.sh` to copy the script into `~/.local/bin` and make it executable.
- LaunchAgent: `launchd/com.jarpex.obsidiansync.plist`, installed by
  `launchd/install_obsidian_sync.sh`, which patches the `{{USER}}` placeholder
  and loads the agent into `~/Library/LaunchAgents`.

Notes:

- `launchd` agents run non-symlinked executables. Copying the script into
  `~/.local/bin` avoids permission issues when the repo sits in `~/Documents`.
- The template uses `StartInterval` (3600 seconds in the template).
- `unison` must be in the runtime PATH for `launchd`. An absolute path in the
  plist's `ProgramArguments` also works.
