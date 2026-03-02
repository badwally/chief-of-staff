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
