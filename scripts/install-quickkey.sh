#!/bin/bash
# install-quickkey.sh — Set up the VoiceMode Quick Key (Ctrl+Shift+V)
#
# This script guides you through creating a macOS Shortcut that triggers
# VoiceMode in your "Chief of Staff" terminal session from any app.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APPLESCRIPT_PATH="$SCRIPT_DIR/voicemode-quickkey.applescript"

cat <<'HEADER'
╔══════════════════════════════════════════════════════════════╗
║           VoiceMode Quick Key — Installation Guide          ║
╚══════════════════════════════════════════════════════════════╝

This sets up a global Ctrl+Shift+V hotkey that activates VoiceMode
in your "Chief of Staff" terminal window from any application.

HEADER

# ── Step 0: Verify files exist ──────────────────────────────
echo "Checking prerequisites..."
if [ ! -f "$APPLESCRIPT_PATH" ]; then
    echo "ERROR: AppleScript not found at $APPLESCRIPT_PATH"
    exit 1
fi
if [ ! -f "$SCRIPT_DIR/cos-launch.sh" ]; then
    echo "ERROR: Launch script not found at $SCRIPT_DIR/cos-launch.sh"
    exit 1
fi
echo "  ✓ AppleScript found"
echo "  ✓ Launch script found"
echo ""

# ── Step 1: Test AppleScript compiles ───────────────────────
echo "Compiling AppleScript to verify syntax..."
if osacompile -o /dev/null "$APPLESCRIPT_PATH" 2>/dev/null; then
    echo "  ✓ AppleScript compiles successfully"
else
    echo "  ✗ AppleScript has syntax errors. Please fix before continuing."
    exit 1
fi
echo ""

# ── Step 2: Permissions check ───────────────────────────────
cat <<'PERMS'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1: Enable Accessibility Permissions

The hotkey uses System Events to type into Terminal.app.
You must grant permission to the Shortcuts app (and Terminal.app
if you run this script from the terminal).

  1. Open System Settings > Privacy & Security > Accessibility
  2. Enable these apps (add with + if not listed):
     • Shortcuts
     • Terminal

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERMS

# ── Step 3: Create the Shortcut ─────────────────────────────
cat <<SHORTCUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2: Create a macOS Shortcut

  1. Open the Shortcuts app (Cmd+Space → "Shortcuts")
  2. Click  +  to create a new Shortcut
  3. Name it: VoiceMode Quick Key
  4. In the search bar on the right, search: "Run AppleScript"
  5. Drag "Run AppleScript" into the workflow
  6. Replace the placeholder AppleScript with the contents of:

     $APPLESCRIPT_PATH

     (The script is printed below for easy copy-paste.)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SHORTCUT

echo "── AppleScript contents (copy everything between the lines) ──"
echo "────────────────────────────────────────────────────────────────"
cat "$APPLESCRIPT_PATH"
echo ""
echo "────────────────────────────────────────────────────────────────"
echo ""

# ── Step 4: Assign the hotkey ───────────────────────────────
cat <<'HOTKEY'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3: Assign the Keyboard Shortcut

  1. In the Shortcuts app, right-click "VoiceMode Quick Key"
  2. Select the ⓘ (info) icon or "Get Info"
  3. Click "Add Keyboard Shortcut"
  4. Press: Ctrl + Shift + V
  5. Close the info panel

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOTKEY

# ── Step 5: Usage ───────────────────────────────────────────
cat <<'END_USAGE'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO USE

  1. Start Chief of Staff in a terminal:
     ./scripts/cos-launch.sh

  2. From any app, press Ctrl+Shift+V
     → VoiceMode activates in your Chief of Staff session
     → Focus returns to your previous app

  3. Speak naturally. Say "stop" or "goodbye" to end.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

END_USAGE

echo "Setup guide complete. Follow the steps above to finish installation."
