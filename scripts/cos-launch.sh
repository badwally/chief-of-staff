#!/bin/bash
# cos-launch.sh — Launch Claude Code with a recognizable window title.
# The title "Chief of Staff" is used by the VoiceMode quick key to find this window.

# Set Terminal.app window title
printf '\033]0;Chief of Staff\007'

# Navigate to project directory
cd "$(dirname "$0")/.." || exit 1

# Start Claude Code
claude
