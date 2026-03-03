# VoiceMode Quick Key — Design

**Date:** 2026-03-03
**Status:** Implemented

## Problem

The user works primarily in other apps (e.g., Chrome) while chief-of-staff runs in a separate Claude Code terminal. Activating VoiceMode currently requires switching to the terminal and typing `/voicemode:converse`. This friction discourages voice interaction.

## Goal

Press a single global macOS hotkey from any app to activate VoiceMode in the chief-of-staff session. Voice-based stopping ("stop" / "goodbye") ends the conversation — no second hotkey needed.

## Design

### Component 1: Launch Script

**File:** `scripts/cos-launch.sh`

A shell script that starts Claude Code in the project directory:

- Sets the terminal window title via ANSI escape sequence (note: Terminal.app overrides this with its own format)
- `cd`s into the chief-of-staff project directory
- Runs `claude`

**Window identification:** Terminal.app displays the working directory name (`chief-of-staff`) in its title bar, ignoring the ANSI escape title. The AppleScript matches on this directory name.

### Component 2: macOS Shortcut + AppleScript

A macOS Shortcut (built-in Shortcuts app) containing an AppleScript that:

1. Records the currently active app (to restore focus later)
2. Finds the terminal window containing "chief-of-staff" in its title
3. Activates that window (brief ~0.5s focus flash)
4. Types `/voicemode:converse` and presses Enter via System Events
5. Waits briefly, then re-activates the previously active app

If no matching window is found, shows a macOS notification.

**Important:** The AppleScript must be wrapped in an `on run {input, parameters}` handler — this is required by the macOS Shortcuts runtime.

### Component 3: Keyboard Shortcut Assignment

The macOS Shortcut is assigned a global keyboard shortcut. Suggested: **Ctrl+Shift+V** (V for voice — low conflict risk with other apps).

Assigned via one of:
- Shortcuts app > shortcut settings > "Add Keyboard Shortcut"
- System Settings > Keyboard > Keyboard Shortcuts > Services

### User Flow

```
User in Chrome → presses Ctrl+Shift+V
  → macOS Shortcut fires
  → AppleScript finds "chief-of-staff" terminal window
  → Activates window (~0.5s flash)
  → Types /voicemode:converse + Enter
  → VoiceMode starts listening via system mic
  → User speaks (from any app — audio I/O is system-level)
  → User says "stop" or "goodbye" to end voice mode
```

## Deliverables

| File | Purpose |
|------|---------|
| `scripts/cos-launch.sh` | Launch script that sets window title + starts Claude Code |
| `scripts/install-quickkey.sh` | Automated installer that creates the macOS Shortcut (or manual instructions if Shortcuts scripting is limited) |
| `docs/plans/2026-03-03-voicemode-quickkey-design.md` | This design doc |

## Constraints & Assumptions

- **Terminal app:** Terminal.app (macOS built-in).
- **VoiceMode plugin:** Must be installed (`claude plugin marketplace add mbailey/voicemode`) and working before the hotkey is useful.
- **macOS permissions:** Shortcuts requires Automation permissions for Terminal and System Events (System Settings > Privacy & Security > Automation). Accessibility permissions may also be needed.
- **Window title:** Terminal.app ignores ANSI escape titles and uses its own format (`directory — process info`). The AppleScript matches on the directory name `chief-of-staff`.
- **Single session:** Assumes only one "chief-of-staff" titled window exists. If multiple exist, targets the first match.

## Not In Scope

- Stop hotkey (voice-based stopping is sufficient and consistent)
- System-wide voice mode outside Claude Code
- Auto-launching chief-of-staff if not already running
