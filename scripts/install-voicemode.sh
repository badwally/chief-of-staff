#!/bin/bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────
# install-voicemode.sh — One-command VoiceMode installer
#
# Usage:  ./scripts/install-voicemode.sh [--large]
#
# Flags:
#   --large   Install the large-v3-turbo Whisper model (needs 16GB+ RAM)
#             Default is the "base" model (~150 MB)
#
# Idempotent: safe to re-run. Skips already-installed components.
# macOS only. No sudo required (except Xcode license if prompted).
# ─────────────────────────────────────────────────────────────

# ── Parse flags ──────────────────────────────────────────────

WHISPER_MODEL="base"

for arg in "$@"; do
  case "$arg" in
    --large) WHISPER_MODEL="large-v3-turbo" ;;
    --help|-h)
      echo "Usage: $0 [--large]"
      echo "  --large  Use large-v3-turbo Whisper model (16GB+ RAM recommended)"
      exit 0
      ;;
    *)
      echo "Unknown flag: $arg"
      echo "Usage: $0 [--large]"
      exit 1
      ;;
  esac
done

# ── Resolve paths ────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Helper functions ─────────────────────────────────────────

info()  { printf '\033[1;32m▸\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m▸\033[0m %s\n' "$*"; }
fail()  { printf '\033[1;31m✗\033[0m %s\n' "$*"; exit 1; }
check() { printf '\033[1;32m✔\033[0m %s\n' "$*"; }

# Track what happened for the summary
declare -a SUMMARY=()
installed() { SUMMARY+=("installed  $1"); }
skipped()   { SUMMARY+=("skipped    $1"); }

# ── Step 1: Check prerequisites ──────────────────────────────

info "Step 1/8: Checking prerequisites…"

if [[ "$(uname)" != "Darwin" ]]; then
  fail "This script only supports macOS. Detected: $(uname)"
fi

if ! command -v brew &>/dev/null; then
  fail "Homebrew not found. Install it first: https://brew.sh"
fi

if ! command -v claude &>/dev/null; then
  fail "Claude CLI not found. Install it first: https://docs.anthropic.com/en/docs/claude-code"
fi

check "macOS, Homebrew, and Claude CLI detected"

# ── Step 2: Install system audio libraries ───────────────────

info "Step 2/8: Checking audio libraries (portaudio, ffmpeg)…"

NEED_AUDIO=()
if brew list portaudio &>/dev/null; then
  skipped "portaudio"
else
  NEED_AUDIO+=(portaudio)
fi

if brew list ffmpeg &>/dev/null; then
  skipped "ffmpeg"
else
  NEED_AUDIO+=(ffmpeg)
fi

if [[ ${#NEED_AUDIO[@]} -gt 0 ]]; then
  info "Installing: ${NEED_AUDIO[*]}"
  brew install "${NEED_AUDIO[@]}"
  for pkg in "${NEED_AUDIO[@]}"; do
    installed "$pkg"
  done
fi

# Verify both present
brew list portaudio &>/dev/null || fail "portaudio install failed"
brew list ffmpeg &>/dev/null    || fail "ffmpeg install failed"
check "Audio libraries ready"

# ── Step 3: Install UV package manager ───────────────────────

info "Step 3/8: Checking UV package manager…"

if command -v uv &>/dev/null; then
  skipped "uv"
else
  info "Installing UV…"
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # Make uv available in this session
  export PATH="$HOME/.local/bin:$PATH"
  if [[ -f "$HOME/.zshrc" ]]; then
    # shellcheck disable=SC1091
    source "$HOME/.zshrc" 2>/dev/null || true
  fi

  installed "uv"
fi

command -v uv &>/dev/null || fail "UV not found after install. Close terminal, reopen, and re-run this script."
check "UV ready ($(uv --version 2>/dev/null || echo 'installed'))"

# ── Step 4: Install VoiceMode plugin ─────────────────────────

info "Step 4/8: Checking VoiceMode plugin…"

PLUGIN_INSTALLED=false

# Check installed_plugins.json for voicemode
PLUGINS_FILE="$HOME/.claude/plugins/installed_plugins.json"
if [[ -f "$PLUGINS_FILE" ]]; then
  if python3 -c "
import json, sys
with open('$PLUGINS_FILE') as f:
    data = json.load(f)
# v2 format: {version: 2, plugins: {'voicemode@voicemode': [...]}}
plugins = data.get('plugins', data) if isinstance(data, dict) else data
if isinstance(plugins, dict):
    for k in plugins:
        if 'voicemode' in k.lower():
            sys.exit(0)
elif isinstance(plugins, list):
    for p in plugins:
        name = p.get('name','') if isinstance(p, dict) else str(p)
        if 'voicemode' in name.lower():
            sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    PLUGIN_INSTALLED=true
  fi
fi

if $PLUGIN_INSTALLED; then
  skipped "voicemode plugin"
else
  info "Registering VoiceMode plugin…"
  claude plugin marketplace add mbailey/voicemode || true
  claude plugin install voicemode@voicemode || true
  installed "voicemode plugin"
fi

check "VoiceMode plugin registered"

# ── Step 5: Install VoiceMode runtime ────────────────────────

info "Step 5/8: Checking VoiceMode runtime…"

if command -v voicemode &>/dev/null; then
  skipped "voicemode runtime"
else
  info "Installing VoiceMode runtime (this takes 1-2 minutes)…"
  uvx voice-mode-install --yes

  # Make voicemode available in this session
  export PATH="$HOME/.local/bin:$PATH"
  if [[ -f "$HOME/.zshrc" ]]; then
    # shellcheck disable=SC1091
    source "$HOME/.zshrc" 2>/dev/null || true
  fi

  installed "voicemode runtime"
fi

command -v voicemode &>/dev/null || fail "voicemode not found after install. Close terminal, reopen, and re-run this script."
check "VoiceMode runtime ready"

# ── Step 6: Install Whisper (STT) ────────────────────────────

info "Step 6/8: Checking Whisper (speech-to-text)…"

if [[ -d "$HOME/.voicemode/services/whisper" ]]; then
  skipped "whisper service"
else
  info "Installing Whisper service (this takes 2-5 minutes)…"
  voicemode service install whisper
  installed "whisper service"
fi

# If --large was requested, install the large model regardless
if [[ "$WHISPER_MODEL" == "large-v3-turbo" ]]; then
  info "Installing large-v3-turbo Whisper model (needs 16GB+ RAM, ~3 GB download)…"
  voicemode whisper install --model large-v3-turbo
  installed "whisper model (large-v3-turbo)"
fi

check "Whisper ready (model: $WHISPER_MODEL)"

# ── Step 7: Install Kokoro (TTS) ────────────────────────────

info "Step 7/8: Checking Kokoro (text-to-speech)…"

if [[ -d "$HOME/.voicemode/services/kokoro" ]]; then
  skipped "kokoro service"
else
  info "Installing Kokoro service (this takes 2-5 minutes)…"
  voicemode service install kokoro
  installed "kokoro service"
fi

check "Kokoro ready"

# ── Step 8: Enable in tools.yaml ─────────────────────────────

info "Step 8/8: Enabling VoiceMode in tools.yaml…"

TOOLS_YAML="$PROJECT_ROOT/state/config/tools.yaml"

if [[ -f "$TOOLS_YAML" ]]; then
  if grep -q 'voicemode:' "$TOOLS_YAML"; then
    # Use awk to target only the voicemode block's enabled line
    if grep -A2 'voicemode:' "$TOOLS_YAML" | grep -q 'enabled: false'; then
      # Replace enabled: false with enabled: true only in the voicemode block
      awk '
        /voicemode:/ { in_vm=1 }
        in_vm && /enabled: false/ { sub(/enabled: false/, "enabled: true"); in_vm=0 }
        /^  [a-z]/ && !/voicemode:/ { in_vm=0 }
        { print }
      ' "$TOOLS_YAML" > "${TOOLS_YAML}.tmp" && mv "${TOOLS_YAML}.tmp" "$TOOLS_YAML"
      installed "voicemode enabled in tools.yaml"
    else
      skipped "tools.yaml (voicemode already enabled)"
    fi
  else
    warn "No voicemode entry found in tools.yaml — the setup workflow will add it"
  fi
else
  warn "tools.yaml not found at $TOOLS_YAML — the setup workflow will create it"
fi

check "Configuration complete"

# ── Summary ──────────────────────────────────────────────────

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
info "VoiceMode installation complete!"
echo ""

for line in "${SUMMARY[@]}"; do
  echo "  $line"
done

echo ""
echo "Next steps:"
echo "  1. Restart Claude Code (exit and re-run 'claude')"
echo "  2. Start a voice session with: /voicemode:converse"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
