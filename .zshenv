# Sourced by every zsh instance (including non-interactive ones, e.g. skhd/sxhkd).
# Keep this file minimal and free of side effects.

# Rust toolchain
[ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"

# User-local binaries (~/.local/bin) so scripts like aerolaunch are found
if [ -d "$HOME/.local/bin" ]; then
  export PATH="$HOME/.local/bin:$PATH"
fi

# Homebrew binaries (aerospace, skhd, ...)
if [ -d "/opt/homebrew/bin" ]; then
  export PATH="/opt/homebrew/bin:$PATH"
fi
