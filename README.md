# Chief of Staff

An AI-powered chief of staff for executive operations, built on Claude Code.

The filesystem is the database — YAML and Markdown files are the persistence layer, version-controlled with git, human-readable, and debuggable with standard tools. No external databases, no separate services, no infrastructure to deploy. Clone, configure, and run.

## Quick Start

```bash
git clone https://github.com/badwally/chief-of-staff.git
cd chief-of-staff
claude
```

On first run, Claude detects that `state/config/identity.yaml` is missing and walks you through an interactive setup: identity, company context, communication voice, and MCP tool integrations. See [docs/setup-guide.md](docs/setup-guide.md) for details.

## What It Does

Chief of Staff manages the operational surface area of an executive's day:

- **Morning briefings** — Calendar review, task triage, goal check-ins, inbox scan, synthesized into a single-screen daily focus recommendation
- **Task and goal management** — OKR tracking with key results, priority-ranked task lists with goal alignment, overdue/due-today surfacing
- **Message drafting** — Communications composed in your voice, with mandatory approval gates before any message is sent on any channel
- **Decision support** — Structured decision frameworks that drive toward action, not analysis paralysis
- **Contact and relationship management** — Tiered contact registry with staleness tracking to maintain your network
- **Knowledge capture** — PARA-structured vault (Projects, Areas, Resources, Archive) for notes, research, and meeting records
- **Cross-session memory** — Working memory that persists decisions, preferences, and open threads across sessions with controlled decay

## Design Philosophy

Three principles govern the architecture:

**Filesystem as database.** YAML and Markdown files are the persistence layer. No embedded databases, no external services for core state. Files are human-readable, version-controllable, and debuggable with `cat` and `grep`. The system earns the right to outgrow this only when file-based state demonstrably fails under real load.

**Convention over machinery.** The "workflow engine" is not a separate process — it's a file convention: workflow definitions, checkpoint files, and typed schemas that Claude follows. The "retrieval layer" is not a vector database — it's maintained index files that Claude reads to assemble context. Sophistication comes from better organization, not more infrastructure.

**Governance through policy, not code.** The system's most valuable innovation is its 6 always-on behavioral policies — natural-language rules that Claude applies during execution. Decision posture, confidentiality handling, anti-pattern guards, and message send gates are encoded as policy documents, not programmatic enforcement. They're extensible, auditable, and comprehensible.

## Architecture

Four layers, each depending only on the layer below:

```
┌─────────────────────────────────────────────────────┐
│  L3  Interfaces                                     │
│      Text CLI, approval gates, scheduled triggers   │
├─────────────────────────────────────────────────────┤
│  L2  Workflows                                      │
│      Declarative multi-step definitions,            │
│      checkpointing, typed schemas, failure recovery │
├─────────────────────────────────────────────────────┤
│  L1  Retrieval                                      │
│      Maintained indexes, context assembly,          │
│      structured queries, relevance ranking          │
├─────────────────────────────────────────────────────┤
│  L0  State                                          │
│      Memory, domain state, knowledge base,          │
│      configuration, session journals                │
└─────────────────────────────────────────────────────┘
```

Governance policies are a cross-cutting concern — loaded into Claude's context at session start and applied throughout execution.

### L0: State

Five categories of persistent state, all stored as flat files:

| Category | Location | Format | Purpose |
|----------|----------|--------|---------|
| Working Memory | `state/memory/` | YAML | Cross-session continuity — open questions, pending decisions, accumulated context |
| Domain State | `state/domain/` | YAML + MD | Goals (OKRs), tasks, contacts, schedules, projects |
| Knowledge Base | `vault/` | Markdown | PARA structure — notes, research, meeting records, captured content |
| Configuration | `state/config/` | YAML | User identity, company context, voice model, tool integrations, modes, tiers |
| Session Journals | `state/journals/` | Markdown | Append-only execution logs — decisions, actions, open threads |

#### Working Memory

Working memory solves the cross-session continuity problem. Each entry has:

- **Scope** — `global`, `project:<name>`, or `area:<name>` for targeted retrieval
- **Decay** — `persistent`, `30d`, `7d`, or `session` for automatic pruning
- **Source** — Reference to the session journal where the insight originated

Memory entries are never written automatically. At session end, the system proposes entries for user approval. During weekly synthesis, related entries consolidate to prevent bloat. Soft limit of 50 active entries, hard warning at 100.

#### Domain State

| File | Schema |
|------|--------|
| `goals.yaml` | OKRs with key results, progress tracking (0.0–1.0), quarterly scoping |
| `tasks.yaml` | Priority-ranked (1–4), due dates, goal alignment references, status tracking |
| `schedules.yaml` | Recurring automations — frequency, workflow reference, last/next run |
| `contacts/_index.yaml` | Tiered contact registry with staleness tracking, linked detail files |
| `projects/_index.yaml` | Project registry with vault folder links, goal alignment, contact references |

### L1: Retrieval

Four maintained indexes avoid the need for vector databases or full-text search infrastructure:

| Index | Purpose | Maintained By |
|-------|---------|---------------|
| `indexes/tags.yaml` | Maps tags to files containing them | Note creation/modification |
| `indexes/entities.yaml` | Maps people, companies, projects to mentions | Triage and enrichment workflows |
| `indexes/concepts.yaml` | Maps higher-level concepts to files | Synthesis operations (daily review, weekly synthesis) |
| `indexes/recent.yaml` | Rolling 30-day file modification log | All file operations |

Context assembly uses indexes to identify relevant files *before* loading them — preventing context bloat while maintaining comprehensive awareness.

### L2: Workflows

Declarative multi-step definitions stored as YAML in `workflows/definitions/`. Each workflow declares:

- **Context requirements** — which policies, memory scopes, and indexes to load
- **Steps** — ordered operations with typed inputs and outputs
- **Executors** — `prompt` (Claude reasoning), `mcp` (tool calls), `script` (shell), `workflow` (composition)
- **Schemas** — typed output validation per step (defined in `workflows/schemas/`)
- **Gates** — pause points requiring user interaction: `display`, `approve`, `send`, `edit`, `confirm`
- **Checkpoints** — per-step state saved to `workflows/runs/` for failure recovery and resumability

Steps chain via `${step.key}` references. Optional steps degrade gracefully when their executor is unavailable.

**Included workflows:**

| Workflow | Steps | Description |
|----------|-------|-------------|
| `morning-briefing` | 6 | Calendar → tasks → goals → inbox → synthesized briefing with focus recommendation |
| `setup` | 8 | Interactive first-run: identity → company → voice → tools → state initialization → journal |

**Output schemas** (in `workflows/schemas/`):

| Schema | Fields |
|--------|--------|
| `calendar-review` | Events, conflicts, hard-constraint violations, available time blocks |
| `task-review` | Overdue, due-today, and approaching tasks with priority and goal references |
| `goal-review` | Goal progress, stalled goals, alignment gaps |
| `inbox-scan` | Tier-1 urgent items, count-by-tier aggregation |

## Operating Modes

Six modes, automatically inferred from the user's prompt. Each activates specific policies:

| Mode | Purpose | Example Triggers |
|------|---------|-----------------|
| **Prioritize** | Assess, rank, and sequence work | "what should I focus on", "prioritize", "what's most important" |
| **Decide** | Structure and support a specific decision | "should I", "help me decide", "trade-offs" |
| **Draft** | Compose messages and documents | "draft", "write", "compose", "reply to" |
| **Coach** | Provide perspective, challenge assumptions | "what do you think", "push back on", "challenge" |
| **Synthesize** | Combine information, find patterns | "summarize", "what's the pattern", "review" |
| **Explore** | Open-ended research and brainstorming | "explore", "brainstorm", "what if", "ideas" |

## Always-On Policies

Six governance policies loaded at every session start. These are the system's behavioral core — natural-language rules that shape how Claude thinks and acts:

### Goal Referencing (P1)
Frame all work in terms of active goals. Recommend actions only when aligned. Push back on misaligned work. Surface when goals need updating. *Exception: in Explore mode, alignment is noted but not enforced.*

### Decision Posture (P2)
Apply a strict hierarchy: **Clarity → Focus → Decision → Action → Improve.** Resist analysis without deciding. Every interaction should move toward a concrete decision with specific next actions, owners, and deadlines. *No exceptions.*

### Anti-Pattern Guards (P3)
Prohibit five harmful patterns in all outputs:
1. **Verbosity** — no filler, hedging, or excessive caveats
2. **Neutral summaries** — every summary includes a recommendation or insight
3. **Empty frameworks** — only introduce frameworks that help decide the matter at hand
4. **Batch questions** — ask one question at a time
5. **Scope creep** — stay within bounds of what was asked

### Message Send Gate (P4)
Never send any message on any channel without explicit user approval. Draft → present full draft (recipient, subject, body) → wait for explicit confirmation → only then send. **Absolute rule — urgency, automation, and prior approval do not override.**

### Confidentiality Triggers (P5)
Activate heightened awareness when content involves: compensation, termination/PIPs, board materials, legal/litigation, M&A, personnel changes. Flag sensitivity, check channel appropriateness, restrict to minimum necessary audience.

### Context Discipline (P18)
Minimize context window bloat. Targeted queries over broad reads. Summarize retrieved information. Batch related reads. State rationale before loading additional context. Prune aggressively.

## Voice Interface (Optional)

Voice input and output are available as a supplement to the text CLI when VoiceMode is enabled. Voice is never required — the system functions identically without it.

### How It Works

**Input:** VoiceMode uses Whisper for speech-to-text. Spoken input is transcribed and treated identically to typed input — all workflows, mode inference, and policies apply unchanged. Users can speak "yes" or "approved" at approval gates instead of typing.

**Output:** Claude selectively speaks responses per `policies/voice-output.md`. Voice always supplements text — it never replaces it. Text output is always displayed regardless of voice state.

| Context | Voice | Text |
|---------|-------|------|
| Briefing synthesis and summaries | Speak | Also display |
| Task review overviews | Speak | Also display |
| Short confirmations | Speak | Also display |
| Drafted messages at `send` gates | Speak summary only | Display full draft |
| Confidential content | Silent | Text only |
| Code, YAML, structured data | Silent | Text only |
| Content at `edit` gates | Silent | Text only |

### Setup

VoiceMode requires system dependencies and a Claude Code plugin:

```bash
brew install portaudio ffmpeg
claude plugin marketplace add mbailey/voicemode
claude plugin install voicemode@voicemode
```

Then enable in `state/config/tools.yaml`:

```yaml
voicemode:
  type: mcp
  server: voicemode
  enabled: true
```

Activate in a session with `/voicemode:converse`.

### mcp-tts (Deferred)

[mcp-tts](https://github.com/blacktop/mcp-tts) is declared in `tools.yaml` as a secondary TTS provider with additional backends (macOS `say`, ElevenLabs, Google, OpenAI). It's disabled by default and intended for evaluation after VoiceMode is established.

## Triage Tiers

Incoming work is classified into three response tiers:

| Tier | Label | Response Target | Criteria |
|------|-------|-----------------|----------|
| 1 | Respond now | < 1 hour | Direct leadership/board request, time-sensitive decisions, blocking issues |
| 2 | Handle today | Same business day | Team requests, stakeholder updates, scheduled deliverables |
| 3 | FYI / Queue | Within 3 business days | Newsletters, non-urgent updates, reference material |

Contacts are similarly tiered for relationship maintenance:

| Tier | Label | Staleness Threshold |
|------|-------|---------------------|
| 1 | Inner circle | 14 days |
| 2 | Active network | 30 days |
| 3 | Extended network | 60 days |

## Session Lifecycle

### Session Start (7 steps)

1. Load working memory — surface entries scoped to active context
2. Surface tasks — flag overdue and due-today items
3. Check first-run — if `identity.yaml` missing, prompt for setup workflow
4. Check upstream updates — surface changes to workflows, policies, or config
5. Scan for skill keywords — match prompt against workflow triggers
6. Infer operating mode — announce which of the 6 modes applies
7. Load always-on policies — read and apply all 6 policy documents

### Session End (2 steps)

1. Memory capture — propose entries for decisions, open questions, and preferences discovered during the session (never written without explicit approval)
2. Journal finalization — close the session journal with decisions, actions taken, and open threads

## Project Structure

```
chief-of-staff/
├── state/
│   ├── config/                    # Configuration
│   │   ├── identity.template.yaml #   Identity template (tracked)
│   │   ├── company.template.yaml  #   Company template (tracked)
│   │   ├── voice.template.yaml    #   Voice template (tracked)
│   │   ├── tools.template.yaml    #   Tools template (tracked)
│   │   ├── modes.yaml             #   6 operating modes (tracked)
│   │   └── tiers.yaml             #   Triage + contact tiers (tracked)
│   ├── domain/                    # Domain state (personal)
│   │   ├── goals.yaml             #   OKRs with key results
│   │   ├── tasks.yaml             #   Priority-ranked task list
│   │   ├── schedules.yaml         #   Recurring automations
│   │   ├── contacts/              #   Contact registry + detail files
│   │   └── projects/              #   Project registry + detail files
│   ├── memory/
│   │   └── memory.yaml            #   Working memory (personal)
│   └── journals/                  #   Session logs (personal)
├── vault/                         # Knowledge base — PARA structure
│   ├── inbox/                     #   Unprocessed captures
│   ├── projects/                  #   Active project notes
│   ├── areas/                     #   Ongoing area-of-responsibility notes
│   ├── resources/                 #   Reference material
│   ├── archive/                   #   Completed/inactive material
│   └── attachments/               #   Binary files
├── workflows/
│   ├── definitions/               #   Workflow YAML files
│   │   ├── morning-briefing.yaml  #   Daily operational review
│   │   └── setup.yaml             #   First-run configuration
│   ├── schemas/                   #   Typed output schemas
│   └── runs/                      #   Checkpoint files
├── policies/                      #   6 always-on governance policies
├── indexes/                       #   Retrieval indexes (tags, entities, concepts, recent)
├── docs/                          #   Architecture spec + setup guide
├── scripts/                       #   Shell utilities
├── mcp/                           #   Custom MCP server code
│   └── imessage/                  #     iMessage read/search/send (macOS)
└── skills/                        #   Reference documents
```

**Tracked vs personal:** Templates (`*.template.yaml`), modes, tiers, workflows, schemas, policies, and docs are tracked in git and shared across all users. Config files, domain state, memory, journals, vault contents, and indexes are gitignored — created during setup and personal to each user.

## MCP Integrations

Chief of Staff supports optional MCP server integrations. All are disabled by default and enabled during setup:

| Integration | Server | Capabilities |
|-------------|--------|-------------|
| Gmail | `gmail` | Inbox scanning, message drafting and sending |
| Google Calendar | `google-calendar` | Calendar review, event management, time queries |
| Slack | `slack` | Channel and DM messaging |
| Linear | `linear` | Issue tracking integration |
| Notion | `notion` | Knowledge base bridging |
| Firecrawl | `firecrawl` | Web content capture |
| GitHub | `github` | Repository access |
| Gemini Vision | Custom (`mcp/gemini-vision`) | Image analysis |
| iMessage | Custom (`mcp/imessage`) | Read, search, send messages, contact lookup, file attachments. Requires Full Disk Access. |
| VoiceMode | `voicemode` | Voice input (Whisper STT) and output (Kokoro/OpenAI TTS) |
| mcp-tts | `mcp-tts` | Multi-backend TTS: macOS `say`, ElevenLabs, Google, OpenAI (deferred) |

Workflows degrade gracefully when an integration is unavailable — optional steps are skipped with fallback notes for downstream steps.

## Extending

### Adding a workflow

Create a new YAML file in `workflows/definitions/` following the convention established in `morning-briefing.yaml`:

```yaml
name: my-workflow
description: "What this workflow does."
trigger: manual
context:
  policies: [goal-referencing, context-discipline]
  memory_scopes: [global]
  indexes: [recent]

steps:
  - name: step-one
    executor: prompt
    prompt: |
      Instructions for Claude...
    output:
      type: structured
      schema: my-schema
      key: result
    gate: display
```

### Adding a policy

Create a Markdown file in `policies/`. To make it always-on, add it to the policy loading step in `CLAUDE.md`. To make it mode-specific, reference it in the relevant mode's `policies` list in `state/config/modes.yaml`.

### Adding an output schema

Create a YAML file in `workflows/schemas/` defining the typed fields that a workflow step must produce. Schemas are referenced by name in step definitions.

## Prerequisites

- [Claude Code](https://claude.ai/download) CLI
- Git
- (Optional) MCP servers for integrations you want to use

## Documentation

- [Setup Guide](docs/setup-guide.md) — First-run configuration, re-running setup, tracked vs personal files
- [Architecture Specification](docs/arch-planning.md) — Full 4-layer architecture, state model, workflow engine, retrieval layer, governance policies, primitive mapping, build sequence
- [Planning Prompt](docs/chief-of-staff-planning-prompt.md) — Original design analysis and primitive inventory

## License

Private repository. All rights reserved.
