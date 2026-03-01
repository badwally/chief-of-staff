# Voice Interface Design

## Summary

Add voice input/output to Chief of Staff as a supplementary interface alongside the existing text CLI. Adopt existing MCP servers (VoiceMode for STT+TTS, optionally mcp-tts for additional TTS backends) rather than building custom voice infrastructure.

## Decisions

- **VoiceMode** (github.com/mbailey/voicemode) as primary voice interface — handles STT (Whisper) and TTS (Kokoro/OpenAI), purpose-built for Claude Code
- **mcp-tts** (github.com/blacktop/mcp-tts) as optional secondary TTS — adds macOS `say`, ElevenLabs, Google TTS backends. Install after evaluating VoiceMode.
- Voice is always optional. No audio dependencies. System functions identically without it.

## Architecture

Voice is an MCP integration — the same pattern as Gmail, Calendar, Slack. Not a new architectural layer.

```
Claude Code CLI
    │
    ├── voicemode MCP (STT + TTS)    ◄── New, optional
    ├── mcp-tts MCP (TTS only)       ◄── New, optional, deferred
    ├── gmail MCP                     ◄── Existing
    ├── google-calendar MCP           ◄── Existing
    └── ...other integrations
```

Claude controls when to listen (`/voicemode:converse`) and when to speak (selective tool calls). Voice does not take over the conversation loop.

## Workflow Integration

### Input (STT)

Spoken input is transcribed to text. From Claude's perspective, it is identical to typed input. All workflows, mode inference, policy enforcement, and gates work unchanged.

### Output (TTS)

Claude selectively calls VoiceMode's speak tool. Not everything is spoken.

| Context | Voice | Text |
|---------|-------|------|
| Briefing synthesis | Speak | Also display |
| Task review summary | Speak | Also display |
| Drafted messages for review | Speak summary only | Display full draft |
| Confidentiality warnings | No | Text only |
| Code/YAML output | No | Text only |
| Short confirmations | Speak | Also display |

Voice always supplements text — never replaces it. Text output is always present regardless of voice state.

### Gates

Workflow gates work unchanged:
- `display` — Natural speak point. Speak the output, also display.
- `approve` / `confirm` — User can speak "yes" or "approved" instead of typing.
- `send` — Speak a summary of the draft. Display the full draft for visual review before approval.
- `edit` — Text-only. Editing requires visual context.

## Optionality

Voice follows the same pattern as all other integrations:

1. **tools.yaml** — `enabled: false` by default for both voicemode and mcp-tts
2. **Workflow steps** — Any step that speaks uses `optional: true` with graceful fallback to text display
3. **Setup workflow** — VoiceMode listed in tool selection step alongside other integrations
4. **Runtime** — Not invoking `/voicemode:converse` means no audio occurs. Users can disable in tools.yaml at any time.
5. **No code dependencies on audio** — All outputs are text-first. Voice is a layer on top.

## Implementation Scope

### Files to modify

1. **`state/config/tools.yaml`** — Add voicemode and mcp-tts integration entries (disabled by default)
2. **`workflows/definitions/setup.yaml`** — Add VoiceMode to tool selection step
3. **`CLAUDE.md`** — Add voice output guidance section (when to speak vs. text-only, conditional on voicemode enabled)
4. **`policies/voice-output.md`** (new) — Policy governing voice output behavior. Loaded only when voice is enabled.

### Installation steps

1. Install VoiceMode: `claude plugin marketplace add mbailey/voicemode`
2. Install Homebrew deps: `brew install portaudio ffmpeg`
3. Optionally install mcp-tts: `go install github.com/blacktop/mcp-tts@latest`

### Not in scope

- No custom voice code
- No new workflow executor types
- No changes to existing workflow definitions
- No changes to state model, indexes, or retrieval layer
- No new output schemas

## Voice Output Policy (policies/voice-output.md)

Loaded only when `voicemode.enabled: true` in tools.yaml.

Rules:
- Always display text output alongside speech. Voice supplements, never replaces.
- Speak: briefing summaries, task overviews, confirmations, short status updates.
- Do not speak: confidential content, code blocks, YAML, markdown formatting, policy warnings, edit-gate content.
- At `send` gates, speak a brief summary but display the full draft for visual review.
- Keep spoken output concise. Summarize rather than reading verbatim when content exceeds a few sentences.

## Future Considerations

- **mcp-tts evaluation** — After testing VoiceMode's TTS, assess whether additional backends (ElevenLabs for voice quality, macOS `say` for zero-latency) add value
- **Wake word** — VoiceMode or a future extension could support always-on listening with a trigger phrase. Not needed for v1.
- **Workflow-level voice hints** — Workflow steps could declare `voice: true/false` to explicitly control speech. Not needed while the policy-based approach works.
