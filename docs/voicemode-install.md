# VoiceMode Installation Guide

A step-by-step guide to adding voice input and output to Chief of Staff. Written for someone comfortable with computers but not necessarily with terminal commands — every step includes the exact command to run and what to expect.

## What You're Installing

VoiceMode adds two capabilities to Chief of Staff:

- **Voice input** — speak to Claude instead of typing (powered by Whisper speech-to-text)
- **Voice output** — Claude speaks responses back to you (powered by Kokoro text-to-speech)

Both run locally on your machine. No audio leaves your computer. No paid API keys required.

## Before You Start

You need:

- **A Mac** (Apple Silicon or Intel) — this guide covers macOS; see the end for Linux notes
- **Claude Code** installed and working (`claude` command works in Terminal)
- **Homebrew** installed — if running `brew --version` in Terminal prints a version number, you're set. If not, install it first: https://brew.sh
- **A working microphone and speakers** — built-in is fine

Open **Terminal** (search for "Terminal" in Spotlight, or find it in Applications > Utilities). All commands below are typed into Terminal.

---

## Step 1: Install System Audio Libraries

These libraries let VoiceMode access your microphone and process audio.

**Run this command:**

```bash
brew install portaudio ffmpeg
```

**What you'll see:** Homebrew downloads and installs two packages. This may take 1–2 minutes. If either is already installed, Homebrew will say "already installed" — that's fine.

**Verify it worked:**

```bash
brew list portaudio && brew list ffmpeg && echo "Both installed successfully"
```

**Expected output:** A list of files for each package, ending with `Both installed successfully`.

**If it fails:** If you see an Xcode license error, run `sudo xcodebuild -license accept` (you'll need to enter your Mac password and type "agree"), then re-run the brew install command.

---

## Step 2: Install the UV Package Manager

UV is a fast Python package manager that VoiceMode uses to install its dependencies.

**Run this command:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**What you'll see:** A short download and install. UV installs to `~/.local/bin/`.

**Then reload your shell so the `uv` command is available:**

```bash
source ~/.zshrc
```

**Verify it worked:**

```bash
uv --version
```

**Expected output:** A version number like `uv 0.6.x`. If you see "command not found", close Terminal and open a new window, then try again.

---

## Step 3: Install the VoiceMode Plugin

This registers VoiceMode with Claude Code.

**Run these two commands, one at a time:**

```bash
claude plugin marketplace add mbailey/voicemode
```

```bash
claude plugin install voicemode@voicemode
```

**What you'll see:** Each command runs silently or prints a brief confirmation. No output is normal — it means success.

**Verify it worked:**

```bash
claude plugin list 2>&1 | grep voicemode || echo "Check: voicemode should appear in plugin list"
```

---

## Step 4: Install the VoiceMode Runtime

This installs the actual voice processing software on your machine.

**Run this command:**

```bash
uvx voice-mode-install --yes
```

**What you'll see:** A progress display as it downloads and installs the VoiceMode package. It will:
- Install the `voicemode` command-line tool
- Create a `~/.voicemode/` configuration directory
- Generate a default config file at `~/.voicemode/voicemode.env`

This takes 1–2 minutes depending on your internet connection.

**Verify it worked:**

```bash
voicemode --version
```

**Expected output:** A version number. If you see "command not found", run `source ~/.zshrc` and try again.

---

## Step 5: Install Whisper (Speech-to-Text)

Whisper converts your spoken words into text. It runs locally — no internet needed after installation.

**Run this command:**

```bash
voicemode service install whisper
```

**What you'll see:** It downloads the Whisper model (~150 MB for the default "base" model) and compiles the whisper.cpp server. This may take 2–5 minutes. You may see compiler output — that's normal.

**Verify it worked:**

```bash
voicemode service status whisper
```

**Expected output:** Should indicate the service is available or running.

### Choosing a Whisper Model (Optional)

The default "base" model is a good balance of speed and accuracy. If you want better accuracy and have a newer Mac with 16 GB+ RAM:

```bash
voicemode whisper install --model large-v3-turbo
```

| Model | Download Size | RAM Used | Accuracy | Speed |
|-------|--------------|----------|----------|-------|
| tiny | ~40 MB | ~50 MB | Basic | Fastest |
| base | ~150 MB | ~300 MB | Good (default) | Fast |
| small | ~460 MB | ~1 GB | Better | Moderate |
| large-v3-turbo | ~3 GB | ~5 GB | Best | Slower |

For daily use, `base` or `small` is recommended. The `large` model is noticeably slower but more accurate with accents and technical terms.

---

## Step 6: Install Kokoro (Text-to-Speech)

Kokoro converts Claude's text responses into spoken audio. It also runs locally.

**Run this command:**

```bash
voicemode service install kokoro
```

**What you'll see:** It downloads the Kokoro model (~350 MB) and sets up the TTS server. Takes 2–5 minutes.

**Verify it worked:**

```bash
voicemode service status kokoro
```

**Expected output:** Should indicate the service is available or running.

---

## Step 7: Enable VoiceMode in Chief of Staff

Open the tools configuration file in a text editor. You can use any editor — here's how with the built-in `nano` editor:

```bash
nano ~/chief-of-staff/state/config/tools.yaml
```

Find the `voicemode` section (near the bottom) and change `enabled: false` to `enabled: true`:

```yaml
  voicemode:
    type: mcp
    server: voicemode
    enabled: true    # ← change false to true
```

**Save the file:** Press `Ctrl+O` (that's the letter O, not zero), then `Enter` to confirm, then `Ctrl+X` to exit nano.

---

## Step 8: Start a Voice Session

You need to start a **new** Claude Code session for VoiceMode to load. If you have Claude running, exit it first (`Ctrl+C` or type `/exit`).

**Start a fresh session:**

```bash
cd ~/chief-of-staff
claude
```

**Once inside Claude Code, start a voice conversation:**

```
/voicemode:converse
```

**What happens:**
1. You'll hear a chime (if your speakers are on)
2. VoiceMode starts listening through your microphone
3. Speak naturally — say something like "What's on my schedule today?"
4. When you stop speaking, it automatically detects the silence and sends your words to Claude
5. Claude responds in text AND speaks the response aloud

**To stop voice mode**, just type normally or press `Ctrl+C`.

---

## Troubleshooting

### "Microphone not working" or "No audio input detected"

**macOS microphone permissions:** Your Mac may need to grant Terminal (or your terminal app) access to the microphone.

1. Open **System Settings** (Apple menu > System Settings)
2. Go to **Privacy & Security** > **Microphone**
3. Find **Terminal** (or iTerm, Warp, etc.) in the list and make sure it's toggled **on**
4. Restart Terminal and try again

### "Command not found: voicemode"

The `voicemode` command isn't in your shell's PATH. Try:

```bash
source ~/.zshrc
```

If that doesn't work, the binary may be at `~/.local/bin/voicemode`. Add it to your PATH:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### "Service won't start" or "Port already in use"

Another process may be using the port. Check and fix:

```bash
# Check what's on Whisper's port (2022)
lsof -i :2022

# Check what's on Kokoro's port (8880)
lsof -i :8880

# If you see a stuck process, restart the services
voicemode service restart whisper
voicemode service restart kokoro
```

### Words consistently misrecognized

If Whisper keeps getting specific words wrong (company names, technical terms, people's names), you can teach it:

```bash
nano ~/.voicemode/voicemode.env
```

Add or edit this line with comma-separated terms:

```
VOICEMODE_STT_PROMPT="YourCompany, Acme Corp, kubectl, your colleague's name"
```

Save (`Ctrl+O`, `Enter`, `Ctrl+X`) and restart the Whisper service:

```bash
voicemode service restart whisper
```

### Voice output sounds wrong or is missing

Try a different voice. Edit `~/.voicemode/voicemode.env`:

```
VOICEMODE_KOKORO_DEFAULT_VOICE=af_sky
```

Some good voice options:
- `af_sky` — female, natural (default)
- `af_nova` — female, warm
- `af_bella` — female, clear
- `am_adam` — male, natural
- `am_michael` — male, clear

### Bluetooth audio cutting off the beginning of speech

Bluetooth speakers sometimes clip the first moment of audio. Add a brief silence buffer:

Edit `~/.voicemode/voicemode.env`:

```
VOICEMODE_CHIME_LEADING_SILENCE=1.0
VOICEMODE_CHIME_TRAILING_SILENCE=0.5
```

### Everything is slow

Switch to a smaller Whisper model:

```bash
voicemode whisper install --model tiny
voicemode service restart whisper
```

The `tiny` model is much faster but less accurate. Good for quick commands, less good for longer dictation.

---

## Disabling VoiceMode

To turn off voice without uninstalling anything:

```bash
nano ~/chief-of-staff/state/config/tools.yaml
```

Change `enabled: true` back to `enabled: false` under the `voicemode` entry. Save and restart Claude.

---

## Summary of What Was Installed

| Component | Location | Purpose |
|-----------|----------|---------|
| portaudio | `/opt/homebrew/` (via Homebrew) | Microphone access library |
| ffmpeg | `/opt/homebrew/` (via Homebrew) | Audio format conversion |
| uv | `~/.local/bin/uv` | Python package manager |
| VoiceMode plugin | `~/.claude/plugins/` | Claude Code integration |
| voicemode CLI | `~/.local/bin/voicemode` | Voice processing runtime |
| Whisper model | `~/.voicemode/services/whisper/models/` | Speech-to-text model |
| Kokoro model | `~/.voicemode/models/kokoro/` | Text-to-speech model |
| Config | `~/.voicemode/voicemode.env` | All voice settings |

Total disk space: ~500 MB–3 GB depending on Whisper model choice.

---

## Linux Notes

If you're on Ubuntu/Debian instead of macOS, replace the Homebrew step (Step 1) with:

```bash
sudo apt install -y python3-dev gcc libasound2-dev libportaudio2 portaudio19-dev ffmpeg
```

If you're on WSL2 (Windows Subsystem for Linux), you also need PulseAudio for microphone access:

```bash
sudo apt install -y pulseaudio pulseaudio-utils libasound2-plugins
pulseaudio --start
```

All other steps are identical.
