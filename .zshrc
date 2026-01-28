##########################################################
# 🧰 Ruby via Homebrew
##########################################################

if [ -d "/opt/homebrew/opt/ruby/bin" ]; then
  export PATH="/opt/homebrew/opt/ruby/bin:$PATH"
  export PATH="$(gem environment gemdir)/bin:$PATH"
fi

##########################################################
# 🍺 Homebrew Settings
##########################################################

# Disable automatic update to speed up `brew` commands
export HOMEBREW_NO_AUTO_UPDATE=1

##########################################################
# 🕸️ Node Version Manager
##########################################################

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion


##########################################################
# ⚙️ Zsh Options and Completion Setup
# (Generated via compinstall + manual extensions)
##########################################################

# Enable extended completion features
zstyle ':completion:*' completer _expand _complete _ignored _approximate
zstyle ':completion:*' list-colors ''
zstyle ':completion:*' matcher-list ''
zstyle ':completion:*' menu select=long
zstyle ':completion:*' select-prompt %SScrolling active: current selection at %p%s
zstyle ':completion::complete:*' gain-privileges 1

# File where compinstall stores its configuration
zstyle :compinstall filename '~/.zshrc'

# Enable completion for aliases
setopt COMPLETE_ALIASES

# History settings
setopt HIST_IGNORE_DUPS      # Don't record duplicates
setopt SHARE_HISTORY         # Share history between sessions
setopt APPEND_HISTORY        # Append to history file (not overwrite)
setopt INC_APPEND_HISTORY    # Save commands immediately

# Other shell behavior options
setopt NO_BEEP               # Disable terminal bell
setopt CORRECT               # Enable command autocorrection
setopt AUTO_CD               # Allow `cd` without typing the command

# Keybindings for cursor movement
bindkey "^[[H"   beginning-of-line
bindkey "^[[F"   end-of-line
bindkey "^[[3~"  delete-char

# Enable and set prompt
autoload -Uz promptinit
promptinit
PROMPT="%2~ %(?.%F{120}❯.%F{161}❯)%f "

# Load and initialize completion system
autoload -Uz compinit
compinit

##########################################################
# 📜 History Configuration
##########################################################

HISTFILE=~/.histfile
HISTSIZE=1000
SAVEHIST=1000

##########################################################
# 🎨 Themes and UI Styling
##########################################################

# FZF (fuzzy finder) theme: Rose Pine
export FZF_DEFAULT_OPTS="
  --color=fg:#908caa,bg:#191724,hl:#ebbcba
  --color=fg+:#e0def4,bg+:#26233a,hl+:#ebbcba
  --color=border:#403d52,header:#31748f,gutter:#191724
  --color=spinner:#f6c177,info:#9ccfd8
  --color=pointer:#c4a7e7,marker:#eb6f92,prompt:#908caa"

# Stylized man pages (requires rose-pine-man.zsh script)
source ~/.config/zsh/rose-pine-man/rose-pine-man.zsh
colorize_man rose-pine

# Enable zsh-autosuggestions (gray ghost text for predicted input)
source "$(brew --prefix)/share/zsh-autosuggestions/zsh-autosuggestions.zsh"

##########################################################
# 📦 Extraction Helper Function
##########################################################

# Usage: extract archive.tar.gz
extract() {
  if [ -f "$1" ]; then
    case "$1" in
      *.tar.bz2)   tar xjf "$1"    ;;
      *.tar.gz)    tar xzf "$1"    ;;
      *.bz2)       bunzip2 "$1"    ;;
      *.rar)       unrar x "$1"    ;;
      *.gz)        gunzip "$1"     ;;
      *.tar)       tar xf "$1"     ;;
      *.tbz2)      tar xjf "$1"    ;;
      *.tgz)       tar xzf "$1"    ;;
      *.zip)       unzip "$1"      ;;
      *.Z)         uncompress "$1" ;;
      *.7z)        7z x "$1"       ;;
      *)           echo "'$1' cannot be extracted" ;;
    esac
  else
    echo "'$1' is not a valid file"
  fi
}

##########################################################
# 🧾 Aliases
##########################################################

alias ...="cd ../.."
alias ..="cd .."
#alias cat="bat"                                  # Better cat
alias cfv="nvim ~/.config/nvim/init.vim"         # Edit init.vim
alias cfvp="nvim ~/.config/nvim/vim-plug/plugins.vim"  # Edit vim-plug plugins
alias cfz="nvim ~/.zshrc"                        # Edit this file
alias dcd="iconv -f WINDOWS-1251 -t UTF-8 -o"    # Convert encoding
alias du="dust"                                  # Better disk usage
alias find="fd"                                  # Better find
alias grep="rg"                                  # Better grep with ripgrep
alias ls="eza -la"                               # Better ls with full details
alias mp3="yt-dlp -x --audio-format mp3"         # Download audio
alias rep="cd ~/Documents/Repos/ && eza -la"     # Go to repos dir and list
alias v="nvim"                                   # Short nvim