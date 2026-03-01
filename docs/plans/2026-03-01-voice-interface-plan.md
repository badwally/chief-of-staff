# Voice Interface Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add VoiceMode as an optional voice interface for Chief of Staff, with mcp-tts as a deferred secondary TTS provider.

**Architecture:** Voice is an MCP integration alongside existing ones (Gmail, Calendar, etc.). Claude controls when to listen and speak. All voice features are optional — the system functions identically without audio. See `docs/plans/2026-03-01-voice-interface-design.md` for the full design.

**Tech Stack:** VoiceMode MCP plugin (Python, Whisper, Kokoro/OpenAI TTS), mcp-tts (Go, multi-backend TTS), Homebrew (portaudio, ffmpeg)

---

### Task 1: Install System Dependencies

**Files:**
- None (system-level install)

**Step 1: Install portaudio and ffmpeg via Homebrew**

```bash
brew install portaudio ffmpeg
```

Expected: Both packages install successfully. If already installed, Homebrew reports "already installed."

**Step 2: Verify installations**

```bash
brew list portaudio && brew list ffmpeg
```

Expected: Both list their installed files without error.

**Step 3: Commit**

No files changed — nothing to commit. Proceed to next task.

---

### Task 2: Install VoiceMode Plugin

**Files:**
- None (Claude Code plugin system manages this)

**Step 1: Install VoiceMode from marketplace**

```bash
claude plugin marketplace add mbailey/voicemode
claude plugin install voicemode@voicemode
```

Expected: Plugin installs and registers as an MCP server.

**Step 2: Verify VoiceMode is available**

```bash
claude mcp list
```

Expected: `voicemode` appears in the MCP server list.

**Step 3: Commit**

No project files changed — nothing to commit. Proceed to next task.

---

### Task 3: Add Voice Integrations to tools.yaml

**Files:**
- Modify: `state/config/tools.yaml`

**Step 1: Add voicemode and mcp_tts entries to tools.yaml**

Append after the `gemini_vision` entry in `state/config/tools.yaml`:

```yaml
  voicemode:
    type: mcp
    server: voicemode
    enabled: false
    notes: "Voice input (Whisper STT) and output (Kokoro/OpenAI TTS). Install plugin first: claude plugin marketplace add mbailey/voicemode"

  mcp_tts:
    type: mcp
    server: mcp-tts
    enabled: false
    notes: "Multi-backend TTS (macOS say, ElevenLabs, Google, OpenAI). Install: go install github.com/blacktop/mcp-tts@latest"
```

**Step 2: Verify the file is valid YAML**

```bash
python3 -c "import yaml; yaml.safe_load(open('state/config/tools.yaml'))" && echo "valid"
```

Expected: `valid`

**Step 3: Commit**

```bash
git add state/config/tools.yaml
git commit -m "Add voicemode and mcp-tts to tools.yaml (disabled by default)"
```

---

### Task 4: Create Voice Output Policy

**Files:**
- Create: `policies/voice-output.md`

**Step 1: Create the policy file**

Write `policies/voice-output.md` with the following content:

```markdown
---
id: voice-output
scope: conditional
condition: voicemode.enabled == true
derived_from: design/2026-03-01-voice-interface
---

## Rule

When VoiceMode is enabled, use voice output selectively. Voice supplements text — it never replaces it. Always display text output alongside any speech.

**Speak:**
- Briefing synthesis and summaries
- Task review overviews
- Short confirmations and status updates
- Workflow `display` gate outputs

**Do not speak:**
- Confidential content (see P5 confidentiality-triggers for keyword list)
- Code blocks, YAML, or structured data
- Markdown formatting, headers, or tables
- Policy warnings and meta-information
- Content at `edit` gates (editing requires visual context)

**At `send` gates:**
- Speak a brief summary of the drafted message
- Display the full draft text for visual review before approval

**Conciseness:**
- Keep spoken output concise
- Summarize rather than reading verbatim when content exceeds a few sentences
- Prefer natural phrasing over reading structured output literally

## Exceptions

If the user explicitly requests that specific content be spoken (e.g., "read me the full draft"), comply regardless of the above rules. The override applies only to that specific instance.

When VoiceMode is not enabled in tools.yaml, this policy is inactive and has no effect.
```

**Step 2: Verify the frontmatter is valid YAML**

```bash
python3 -c "
import yaml
content = open('policies/voice-output.md').read()
fm = content.split('---')[1]
yaml.safe_load(fm)
print('valid')
"
```

Expected: `valid`

**Step 3: Commit**

```bash
git add policies/voice-output.md
git commit -m "Add voice output policy (conditional on voicemode enabled)"
```

---

### Task 5: Update Setup Workflow

**Files:**
- Modify: `workflows/definitions/setup.yaml`

**Step 1: Update the setup-tools step prompt**

In `workflows/definitions/setup.yaml`, update the `setup-tools` step's prompt to include VoiceMode and mcp-tts in the available integrations list. Replace the prompt text inside the `setup-tools` step with:

```yaml
  - name: setup-tools
    executor: prompt
    prompt: |
      Let's configure your MCP tool integrations. I'll write the results to
      state/config/tools.yaml.

      Available integrations:
        - Gmail (email access)
        - Google Calendar (calendar management)
        - Slack (team messaging)
        - Linear (issue tracking)
        - Notion (knowledge base)
        - Firecrawl (web scraping)
        - GitHub (repository access)
        - Gemini Vision (image analysis — custom MCP)
        - VoiceMode (voice input via Whisper + voice output via Kokoro/OpenAI TTS — requires: claude plugin marketplace add mbailey/voicemode, brew install portaudio ffmpeg)
        - mcp-tts (multi-backend text-to-speech: macOS say, ElevenLabs, Google, OpenAI — requires: go install github.com/blacktop/mcp-tts@latest)

      For each integration you want to use, you'll need the corresponding MCP
      server configured in your Claude settings. Which integrations do you have
      set up and want to enable?

      Use the template at state/config/tools.template.yaml for the full schema.
      After collecting answers, write state/config/tools.yaml with enabled: true
      for confirmed integrations.
    reads: [state/config/tools.template.yaml]
    output:
      type: file
      path: state/config/tools.yaml
      key: tools
    gate: edit
```

**Step 2: Verify the workflow YAML is valid**

```bash
python3 -c "import yaml; yaml.safe_load(open('workflows/definitions/setup.yaml'))" && echo "valid"
```

Expected: `valid`

**Step 3: Commit**

```bash
git add workflows/definitions/setup.yaml
git commit -m "Add VoiceMode and mcp-tts to setup workflow tool selection"
```

---

### Task 6: Update CLAUDE.md with Voice Guidance

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add voice interface section to CLAUDE.md**

Append the following section after the "Always-On Policies" section (after the policy table, before "## Workflow Execution Protocol"):

```markdown
## Voice Interface (Optional)

When VoiceMode is enabled in `state/config/tools.yaml`, voice input and output are available as a supplement to the text CLI. Voice is never required — the system functions identically without it.

**Activation:** User invokes `/voicemode:converse` to enter voice conversation mode.

**Input:** Spoken input is transcribed to text via Whisper. Treat it identically to typed input. All workflows, mode inference, and policies apply unchanged.

**Output:** Use voice output selectively per `policies/voice-output.md`. Always display text alongside speech. Never speak confidential content, code, or structured data.

**Policy loading:** When VoiceMode is enabled, load `policies/voice-output.md` alongside the 6 always-on policies at session start.
```

**Step 2: Verify CLAUDE.md is well-formed**

Read the file and confirm the new section is placed correctly between "Always-On Policies" and "Workflow Execution Protocol."

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "Add voice interface guidance to CLAUDE.md"
```

---

### Task 7: Smoke Test — Verify Voice-Off Baseline

**Files:**
- None (verification only)

**Step 1: Confirm voicemode is disabled in tools.yaml**

```bash
python3 -c "
import yaml
config = yaml.safe_load(open('state/config/tools.yaml'))
vm = config['integrations']['voicemode']
assert vm['enabled'] == False, f'Expected disabled, got {vm[\"enabled\"]}'
print('voicemode disabled: OK')
"
```

Expected: `voicemode disabled: OK`

**Step 2: Confirm all existing YAML files still parse**

```bash
python3 -c "
import yaml, glob
for f in glob.glob('state/config/*.yaml') + glob.glob('workflows/definitions/*.yaml'):
    yaml.safe_load(open(f))
    print(f'OK: {f}')
print('All YAML valid')
"
```

Expected: All files report OK, ending with `All YAML valid`

**Step 3: Confirm policy file has valid frontmatter**

```bash
python3 -c "
import yaml
content = open('policies/voice-output.md').read()
fm = content.split('---')[1]
data = yaml.safe_load(fm)
assert data['id'] == 'voice-output'
assert data['scope'] == 'conditional'
print('Policy frontmatter: OK')
"
```

Expected: `Policy frontmatter: OK`

**Step 4: No commit needed — this is verification only**

---

### Task 8: Manual VoiceMode Test (User-Driven)

**Files:**
- Modify: `state/config/tools.yaml` (temporarily enable voicemode)

**Step 1: Enable voicemode in tools.yaml**

Set `enabled: true` for the voicemode entry in `state/config/tools.yaml`.

**Step 2: Start a voice conversation**

In a Claude Code session in the chief-of-staff directory, run:

```
/voicemode:converse
```

Speak a simple command like "What tasks are overdue?" and verify:
- Speech is captured and transcribed
- Claude responds with text AND spoken output
- The response follows voice-output policy (summaries spoken, not raw YAML)

**Step 3: Test voice-off fallback**

Set `enabled: false` for voicemode in tools.yaml. Verify the system works identically to before — no errors, no audio references.

**Step 4: Commit final state**

Leave voicemode `enabled` set to the user's preference (true if keeping it on, false if not).

```bash
git add state/config/tools.yaml
git commit -m "Configure voicemode enabled state after testing"
```
