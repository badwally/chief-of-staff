# Chief of Staff: Architecture Planning

## 1. Design Posture

The synthesized system inherits a constraint from both predecessors: Claude Code CLI is the runtime, the filesystem is the state layer, and prompts are the control plane. This is not a limitation to overcome prematurely — it is a deployment surface that works and that users understand. The architecture adds *structure* to this paradigm, not a new paradigm.

Three principles govern the design:

**Filesystem as database.** YAML and Markdown files remain the persistence layer. No embedded databases, no external services for core state. Files are human-readable, version-controllable, and debuggable with standard tools. The system earns the right to outgrow this only when file-based state demonstrably fails under real load.

**Convention over machinery.** The "workflow engine" is not a separate process. It is a file convention — workflow definitions, checkpoint files, typed schemas — that Claude Code follows when executing multi-step tasks. The "retrieval layer" is not a vector database. It is a set of maintained index files that Claude reads to assemble context. Sophistication comes from better organization, not more infrastructure.

**Governance through policy, not code.** CoS's 20 behavioral modules (P1–P20) are the system's most valuable innovation. They encode decision policy as natural-language rules that Claude applies during execution. The architecture preserves and extends this pattern rather than replacing it with programmatic enforcement.

---

## 2. Architecture Layers

Four layers, bottom to top. Each depends only on the layer below it.

```
┌─────────────────────────────────────────────────┐
│  L3  Interfaces                                 │
│      Voice input, text CLI, scheduled triggers, │
│      approval gates, notification delivery      │
├─────────────────────────────────────────────────┤
│  L2  Workflows                                  │
│      Multi-step definitions, checkpointing,     │
│      typed step interfaces, failure recovery    │
├─────────────────────────────────────────────────┤
│  L1  Retrieval                                  │
│      Index maintenance, context assembly,       │
│      structured queries, relevance ranking      │
├─────────────────────────────────────────────────┤
│  L0  State                                      │
│      Persistent memory, domain state, knowledge │
│      base, configuration, session journals      │
└─────────────────────────────────────────────────┘
```

Cross-cutting concern: **Governance policies** (adapted from P1–P20) are loaded into Claude's context at workflow execution time. They are not a layer but a set of context injections that the workflow layer manages.

---

## 3. L0: State Model

### 3.1 State Categories

The system maintains five categories of persistent state. Each has a distinct structure, update cadence, and retrieval pattern.

| Category | What it contains | Format | Update cadence | Location |
|---|---|---|---|---|
| **Working Memory** | Open questions, pending decisions, active threads, accumulated reasoning context | YAML | Per-session (read on start, write on end) | `state/memory/` |
| **Domain State** | Goals, tasks, contacts, schedules | YAML + MD | Per-command (structured mutations) | `state/domain/` |
| **Knowledge Base** | Notes, research, meeting records, captured content | Markdown (PARA) | Per-command (note creation/modification) | `vault/` |
| **Configuration** | User identity, company context, writing style, tool config, governance policies | YAML + MD | Infrequent (user-initiated changes) | `state/config/` |
| **Session Journals** | Execution logs, decision records, interaction transcripts | Markdown | Per-session (append-only) | `state/journals/` |

### 3.2 Working Memory (resolves Gap 1)

Working memory is the mechanism for cross-session continuity. It answers the question: *what should Claude know at the start of a session that it learned during previous sessions?*

Structure of `state/memory/memory.yaml`:

```yaml
entries:
  - id: mem_001
    content: "User decided to deprioritize the API integration project until Q3 funding is confirmed."
    scope: project:api-integration    # project:<name>, area:<name>, or global
    created: 2025-06-01
    source: session_2025-06-01_02     # session journal reference
    decay: persistent                 # persistent | 30d | 7d | session
    tags: [decision, api-integration, funding]

  - id: mem_002
    content: "When drafting messages to board members, user prefers bullet points over prose for status updates."
    scope: area:board-relations
    created: 2025-05-28
    source: session_2025-05-28_01
    decay: persistent
    tags: [writing-preference, board]

  - id: mem_003
    content: "Exploring whether to hire a second engineer or use contractors for the data pipeline work. No decision yet."
    scope: global
    created: 2025-06-02
    source: session_2025-06-02_01
    decay: 30d
    tags: [open-question, hiring, data-pipeline]
```

**Memory lifecycle:**

1. **Capture.** At session end (or when a significant decision/insight occurs mid-session), the system proposes memory entries. The user approves, edits, or rejects each. No automatic memory writes.
2. **Retrieval.** At session start, the retrieval layer (L1) selects relevant memory entries based on the session's initial context — the command being run, active projects, recent activity.
3. **Decay.** Entries with time-based decay are pruned during daily review. Entries with `session` decay live only until the next session start. Pruning proposals require user confirmation.
4. **Consolidation.** During weekly synthesis, related memory entries are merged or promoted. Three entries about the same decision thread become one summary entry. This prevents memory bloat.

**Capacity constraint.** Working memory is bounded: a soft limit of 50 active entries, with a hard warning at 100. This forces consolidation and prevents the memory file from becoming a second inbox.

### 3.3 Domain State

Subsumes Y1–Y4 from CoS and D1–D7 from Claudesidian, unified under `state/domain/`:

```
state/domain/
├── goals.yaml              # OKRs with progress tracking (from Y1)
├── tasks.yaml              # Task list with goal alignment (from Y2)
├── schedules.yaml          # Automation declarations (from Y3)
├── contacts/               # Per-person CRM files (from Y4)
│   ├── _index.yaml         # Contact registry: name, tier, last interaction
│   └── *.md                # Individual contact files
└── projects/               # Project metadata registry
    └── _index.yaml         # Active projects with status, links to vault folders
```

Key design decisions:

- **Goals are the root of the priority tree.** Tasks reference goals. Contacts reference projects. Scheduling decisions reference goals. This preserves CoS's most powerful pattern (P1 Goal Referencing) and extends it to knowledge management.
- **Contacts get an index file.** The `_index.yaml` enables structured queries (all Tier 1 contacts, all stale contacts) without reading every contact markdown file. The index is maintained as a side effect of contact enrichment (X4) and triage (X2).
- **Projects bridge domain state and the knowledge base.** A project entry in `_index.yaml` points to its vault folder, its goal alignment, its active tasks, and its key contacts. This is the join table between operations and knowledge.

### 3.4 Knowledge Base

The PARA vault structure (D1) is preserved with minor adjustments:

```
vault/
├── inbox/                  # Uncategorized captures
├── projects/               # Active project folders (linked from domain state)
├── areas/                  # Ongoing responsibility areas
├── resources/              # Reference material
├── archive/                # Completed/inactive material
└── attachments/            # Binary files, organized by type
```

Changes from Claudesidian's structure:

- Numeric prefixes (`00_`, `01_`, etc.) dropped. They add noise to paths without functional value; sort order is irrelevant in a system with an index.
- Templates and metadata move to `state/config/templates/` — they are configuration, not knowledge.
- The vault root is no longer the project root. The project root contains `state/`, `vault/`, `workflows/`, and `policies/`.

### 3.5 Configuration

```
state/config/
├── identity.yaml           # User: name, role, emails, constraints, energy patterns (from P6)
├── company.yaml            # Org context: description, stage, leadership, board (from P7)
├── voice.yaml              # Writing style model: tone, patterns, examples (from P8)
├── tools.yaml              # MCP servers, API keys, enabled integrations
├── tiers.yaml              # Triage + contact tier definitions and thresholds (from P9, P10)
├── modes.yaml              # Operating mode definitions and trigger conditions (from P11)
└── templates/              # Note, project, daily, research templates (from D5–D7)
```

### 3.6 Session Journals

Each Claude Code session produces a journal at `state/journals/YYYY-MM-DD_NN.md`:

```markdown
---
session: 2025-06-03_01
started: 2025-06-03T09:14:00
ended: 2025-06-03T10:42:00
mode: prioritize
commands_run: [morning-briefing, triage]
memory_additions: [mem_047, mem_048]
---

## Decisions
- Deferred investor update to Thursday; waiting on Q2 numbers.

## Actions Taken
- Triaged 14 emails. 3 Tier 1 responses sent. 2 Tier 2 drafts saved.
- Updated task T-089 status to in_progress.

## Open Threads
- Need to review contract from Acme Corp legal (forwarded to archive, not yet read).
```

Journals are append-only within a session, immutable after. They serve as the audit trail and as source material for memory capture.

### 3.7 Directory Structure (Complete)

```
chief-of-staff/
├── state/
│   ├── memory/
│   │   └── memory.yaml
│   ├── domain/
│   │   ├── goals.yaml
│   │   ├── tasks.yaml
│   │   ├── schedules.yaml
│   │   ├── contacts/
│   │   └── projects/
│   ├── config/
│   │   ├── identity.yaml
│   │   ├── company.yaml
│   │   ├── voice.yaml
│   │   ├── tools.yaml
│   │   ├── tiers.yaml
│   │   ├── modes.yaml
│   │   └── templates/
│   └── journals/
├── vault/
│   ├── inbox/
│   ├── projects/
│   ├── areas/
│   ├── resources/
│   ├── archive/
│   └── attachments/
├── workflows/
│   ├── definitions/          # Workflow YAML files
│   └── runs/                 # Checkpoint files for active/completed runs
├── policies/                 # Governance policy documents (from P1–P20)
├── indexes/                  # Maintained retrieval indexes
├── scripts/                  # Shell utilities (from S1–S6)
├── mcp/                      # Custom MCP server code (Gemini Vision)
├── skills/                   # Reference documents (from K1–K6)
├── CLAUDE.md                 # Bootstrap prompt: layer loading, session protocol
└── .claude/
    ├── commands/             # Slash command definitions
    ├── hooks/                # Session hooks
    └── settings.json         # Hook and command configuration
```

---

## 4. L1: Retrieval Layer (resolves Gap 2)

### 4.1 Problem Statement

The system must assemble relevant context for any given task without loading the full state into Claude's context window. Current approach (grep/find) fails for conceptual queries ("what have I decided about the hiring timeline?") and scales poorly beyond a few hundred files.

### 4.2 Approach: Maintained Indexes

Rather than introducing vector embeddings (which require an embedding service, a vector store, and a maintenance pipeline), the retrieval layer uses **maintained index files** — structured summaries of content that are updated as side effects of normal operations.

This is the pragmatic choice. It scales to thousands of files, requires no external dependencies, and degrades gracefully (worst case, the index is stale and Claude falls back to file search). The architecture leaves a clear upgrade path to embeddings if indexes prove insufficient.

### 4.3 Index Types

All indexes live in `indexes/` and are YAML files.

**Tag Index** (`indexes/tags.yaml`):
Maps tags to the files that contain them. Maintained by any command that creates or modifies notes.

```yaml
tags:
  hiring:
    - vault/projects/eng-hiring/brief.md
    - state/memory/memory.yaml#mem_003
    - state/journals/2025-06-02_01.md
  api-integration:
    - vault/projects/api-integration/spec.md
    - vault/projects/api-integration/research/vendor-comparison.md
    - state/domain/tasks.yaml#T-045
```

**Entity Index** (`indexes/entities.yaml`):
Maps people, companies, and projects to their mentions across the system. Enables queries like "everything related to Acme Corp."

```yaml
entities:
  acme-corp:
    type: company
    contact: state/domain/contacts/acme-corp.md
    mentions:
      - vault/projects/acme-partnership/notes.md
      - state/journals/2025-06-01_02.md
      - state/domain/tasks.yaml#T-072
  jane-doe:
    type: person
    contact: state/domain/contacts/jane-doe.md
    mentions:
      - vault/areas/board-relations/prep-notes.md
      - state/journals/2025-05-30_01.md
```

**Concept Index** (`indexes/concepts.yaml`):
Maps higher-level concepts to files. Unlike tags (which are explicit metadata), concepts are inferred from content during synthesis operations (C4 Weekly Synthesis, daily review). This is the closest analog to semantic search without embeddings.

```yaml
concepts:
  resource-allocation:
    description: "Decisions about how to allocate engineering time, budget, and attention across competing priorities."
    files:
      - vault/projects/eng-hiring/brief.md
      - vault/areas/budget/q2-plan.md
      - state/memory/memory.yaml#mem_003
    last_updated: 2025-06-01
```

**Chronological Index** (`indexes/recent.yaml`):
Rolling log of the last 30 days of file modifications. Enables time-scoped queries without scanning the filesystem.

```yaml
modifications:
  - file: vault/projects/api-integration/spec.md
    modified: 2025-06-03T14:22:00
    action: updated    # created | updated | archived
    summary: "Added vendor pricing comparison section."
```

### 4.4 Index Maintenance

Indexes are updated as **side effects**, not as separate maintenance tasks:

- When a command creates or modifies a note, it updates the tag index and chronological index.
- When triage or enrichment processes a contact interaction, it updates the entity index.
- When synthesis operations (daily review, weekly synthesis) run, they update the concept index.
- A `reindex` command exists for full rebuilds, but routine maintenance is incremental.

This means indexes can drift if commands are run without the index-update step. The workflow layer (L2) handles this: index updates are defined as steps in relevant workflows, so they execute as part of the normal command flow.

### 4.5 Context Assembly

When a workflow begins, the retrieval layer assembles a context package — the set of files and memory entries relevant to the task. The assembly follows a protocol:

1. **Identify scope.** From the command and user input, determine what the task is about (project, area, contact, topic).
2. **Query indexes.** Look up the scope in the tag, entity, and concept indexes. Collect file references.
3. **Filter by recency and relevance.** Prioritize recent modifications (chronological index) and high-relevance matches. Apply a budget: the context package should not exceed a configured token limit (default: 8,000 tokens of retrieved context).
4. **Load working memory.** Select memory entries whose scope matches the task scope.
5. **Load governance policies.** Based on the inferred operating mode (P11), select which policies to inject.
6. **Present the package.** The assembled context is written to a temporary file that the workflow reads as its starting context.

This protocol is defined in a policy document (`policies/context-assembly.md`) that Claude follows. It is not programmatic — Claude reads the protocol, reads the indexes, and applies judgment to assemble context. The protocol constrains that judgment.

---

## 5. L2: Workflow Engine (resolves Gap 3)

### 5.1 Problem Statement

Every command in both projects is a monolithic prompt — a single natural-language instruction that Claude executes end-to-end. This works for simple tasks but breaks for multi-step processes because there is no checkpointing (a failure at step 5 of 6 loses all progress), no typed handoffs (step 2's output is whatever Claude decides to produce), and no composition (morning briefing cannot reuse triage as a substep).

### 5.2 Approach: Declarative Workflow Definitions

A workflow is a YAML file that declares a sequence of named steps. Claude reads the definition and executes steps in order, writing checkpoint files between steps. There is no workflow runtime — Claude *is* the runtime. The YAML provides structure; Claude provides execution.

### 5.3 Workflow Definition Schema

```yaml
# workflows/definitions/morning-briefing.yaml
name: morning-briefing
description: "Daily operational review: time, calendar, tasks, goals, inbox."
trigger: manual                    # manual | session-start | scheduled
context:
  policies: [goal-referencing, time-focus, task-awareness, scheduling-guard]
  memory_scopes: [global]
  indexes: [recent, entities]

steps:
  - name: get-time
    executor: mcp
    tool: google-calendar.get-time
    output:
      type: timestamp
      key: current_time

  - name: review-calendar
    executor: prompt
    prompt: |
      Review today's calendar events. Flag conflicts, back-to-back meetings
      without breaks, and hard-constraint violations (per identity.yaml).
    input:
      current_time: ${get-time.current_time}
    reads: [state/config/identity.yaml]
    output:
      type: structured
      schema: calendar-review       # references a schema in workflows/schemas/
      key: calendar

  - name: review-tasks
    executor: prompt
    prompt: |
      Review tasks for overdue, due-today, and approaching items.
      Cross-reference against calendar for execution windows.
    input:
      calendar: ${review-calendar.calendar}
    reads: [state/domain/tasks.yaml]
    output:
      type: structured
      schema: task-review
      key: tasks

  - name: check-goals
    executor: prompt
    prompt: |
      Assess goal status. Identify stalled goals, check calendar-goal alignment.
      Flag if today's calendar serves no active goal.
    input:
      calendar: ${review-calendar.calendar}
      tasks: ${review-tasks.tasks}
    reads: [state/domain/goals.yaml]
    output:
      type: structured
      schema: goal-review
      key: goals

  - name: scan-inbox
    executor: prompt
    prompt: |
      Quick scan of last 12 hours of email for Tier 1 items only.
      Do not draft replies; flag items that need attention.
    input:
      current_time: ${get-time.current_time}
    reads: [state/config/tiers.yaml]
    tools: [gmail.search]
    output:
      type: structured
      schema: inbox-scan
      key: inbox

  - name: synthesize-briefing
    executor: prompt
    prompt: |
      Synthesize all inputs into a single-screen morning briefing.
      Lead with the top 1-3 focus items for the day.
      Include: calendar summary, critical tasks, goal status, urgent inbox items.
      End with a focus recommendation.
    input:
      calendar: ${review-calendar.calendar}
      tasks: ${review-tasks.tasks}
      goals: ${check-goals.goals}
      inbox: ${scan-inbox.inbox}
    output:
      type: text
      key: briefing
    gate: display                   # display | approve | send
```

### 5.4 Execution Model

When Claude runs a workflow:

1. **Load definition.** Read the YAML. Validate step references and input dependencies.
2. **Assemble context.** Run the context assembly protocol (L1) using the workflow's declared policies, memory scopes, and indexes.
3. **Execute steps sequentially.** For each step:
   a. Resolve input references from previous step outputs.
   b. Execute (prompt Claude, run MCP tool, or invoke script).
   c. Validate output against declared schema (if typed).
   d. Write checkpoint: `workflows/runs/{workflow}-{timestamp}/{step-name}.yaml` containing the step output.
   e. If a gate is declared, pause for user interaction.
4. **On failure:** Log the error in the checkpoint file. The workflow can be resumed from the failed step — Claude reads prior checkpoints and skips completed steps.
5. **On completion:** Write a summary checkpoint. Update session journal.

### 5.5 Step Executors

| Executor | What it does | Example |
|---|---|---|
| `prompt` | Claude executes a natural-language instruction with provided inputs | Most workflow steps |
| `mcp` | Calls a specific MCP tool with parameters | Calendar lookup, email search |
| `script` | Runs a shell script | Vault stats, Firecrawl scrape |
| `workflow` | Invokes another workflow as a substep | Morning briefing invoking inbox-scan |

The `workflow` executor enables composition. A triage workflow can be invoked as a step within the morning briefing, with its outputs flowing into the briefing's synthesis step.

### 5.6 Typed Interfaces

Step outputs declare a schema. Schemas are defined in `workflows/schemas/` as YAML:

```yaml
# workflows/schemas/calendar-review.yaml
name: calendar-review
fields:
  events:
    type: list
    items:
      fields:
        title: { type: string }
        start: { type: timestamp }
        end: { type: timestamp }
        attendees: { type: list, items: { type: string } }
  conflicts: { type: list, items: { type: string } }
  hard_constraint_violations: { type: list, items: { type: string } }
  available_blocks:
    type: list
    items:
      fields:
        start: { type: timestamp }
        end: { type: timestamp }
        duration_minutes: { type: integer }
```

Schemas serve two purposes: they tell Claude what structure to produce, and they enable the workflow engine (Claude) to validate that a step produced usable output before proceeding. Validation is Claude reading the output and checking it against the schema — not programmatic JSON schema validation.

### 5.7 Gates

Gates are explicit pause points where the workflow waits for user input:

| Gate type | Behavior |
|---|---|
| `display` | Show output to user, continue automatically |
| `approve` | Show output, wait for explicit approval before continuing |
| `send` | Show draft message, wait for per-message send approval (generalizes P4 Message Send Gate) |
| `edit` | Show output, allow user to modify before continuing |
| `confirm` | Ask a specific yes/no question before continuing |

The `send` gate preserves CoS's hard rule: no message is ever sent without explicit approval.

---

## 6. Governance Policies

CoS's 20 behavioral modules (P1–P20) are extracted from the monolithic CLAUDE.md into individual policy documents under `policies/`. Each policy is a markdown file that Claude loads into context when relevant.

### 6.1 Policy Loading

Not all policies apply to all tasks. The workflow definition declares which policies are needed. Additionally, some policies are **always-on** (loaded at session start regardless of task):

**Always-on policies:**
- `goal-referencing` (P1) — all work references goals
- `decision-posture` (P2) — clarity > focus > decision > action
- `anti-pattern-guards` (P3) — behavioral prohibitions
- `message-send-gate` (P4) — never send without approval
- `confidentiality-triggers` (P5) — sensitive topic handling
- `context-discipline` (P18) — minimize context bloat

**Task-specific policies (loaded per workflow):**
- `time-focus` (P12) — loaded for prioritization workflows
- `deep-work` (P13) — loaded for execution workflows
- `relationship-prep` (P14) — loaded for contact/meeting workflows
- `strategic-synthesis` (P15) — loaded for review/synthesis workflows
- `scheduling-guard` (P17) — loaded for calendar-modifying workflows

**Mode-derived policies:**
- `operating-mode` (P11) infers the current mode and may trigger additional policy loads.

### 6.2 Policy Document Structure

```markdown
# policies/goal-referencing.md
---
id: goal-referencing
scope: always-on
derived_from: P1
---

## Rule

Read `state/domain/goals.yaml` at the start of any session or workflow that involves
prioritization, scheduling, or task management.

When recommending actions, frame recommendations in terms of which goal they serve.
Push back when proposed work does not align with any active goal. Surface when goals
themselves need updating based on observed patterns.

## Exceptions

In Explore mode (per operating-mode policy), goal alignment is noted but not enforced.
```

### 6.3 New Policies (beyond P1–P20)

The synthesized system requires policies that neither project defined:

| Policy | Purpose |
|---|---|
| `memory-discipline` | When to propose memory entries, decay rules, consolidation triggers, capacity limits |
| `index-maintenance` | When and how to update indexes as side effects of operations |
| `workflow-recovery` | How to handle step failures, when to retry vs. escalate, checkpoint hygiene |
| `knowledge-capture` | When operational interactions (emails, meetings) should generate vault notes |
| `cross-domain-synthesis` | How to connect operational signals (task completion, contact interactions) with knowledge patterns (research findings, project evolution) |

---

## 7. Primitive Mapping

How the 84 existing primitives map onto the architecture.

### 7.1 Commands → Workflows

Each existing command becomes a workflow definition. Simple commands are single-step workflows. Complex commands decompose into multi-step workflows with typed interfaces.

| Primitive | Workflow | Steps | Notes |
|---|---|---|---|
| C1 Thinking Partner | `thinking-partner` | 3: scope, explore, synthesize | Adds memory capture at end |
| C2 Research Assistant | `research` | 3: search, deep-read, synthesize | Adds index updates |
| C3 Daily Review | `daily-review` | 5: gather, assess, capture-insights, set-priorities, update-memory | Merges with memory consolidation |
| C4 Weekly Synthesis | `weekly-synthesis` | 4: gather, patterns, energy-audit, intentions | Adds concept index update, memory consolidation |
| C5 Inbox Processor | `inbox-process` | 3: scan, categorize, execute-moves | Vault inbox only (distinct from email triage) |
| C6 Add Frontmatter | `add-frontmatter` | 1 | Simple, no decomposition needed |
| C7 De-AI-ify | `clean-prose` | 1 | Renamed for domain clarity |
| C8 Download Attachment | `capture-web` | 3: download, analyze, organize | Adds index update |
| C9 Pragmatic Review | `code-review` | 1–3 depending on mode | Deep mode becomes multi-step |
| C10 Pull Request | `pull-request` | 4: branch, stage, commit, push-pr | Already sequential |
| C11 Release | `release` | 4: analyze, bump, changelog, publish | Already sequential |
| C12 Upgrade | `self-upgrade` | 4: check, backup, diff, apply | Already sequential with review gate |
| C13 Create Command | `create-workflow` | 2: gather-requirements, scaffold | Renamed: creates workflows, not commands |
| C14 Init Bootstrap | `setup` | Multi-step wizard | Adapted for new directory structure |
| C15 Install Command | `install` | 1 | Shell alias setup |
| X1 Morning Briefing | `morning-briefing` | 6 | Defined in §5.3 above |
| X2 Inbox Triage | `triage` | 6: time, scan, classify, check-sent, draft, approve | Per-channel scanning, send gate |
| X3 Task Management | `tasks/*` | Subcommands become separate workflows | `tasks/add`, `tasks/list`, `tasks/execute`, `tasks/complete` |
| X4 Contact Enrichment | `enrich/*` | Subcommands become separate workflows | `enrich/all`, `enrich/stale`, `enrich/person` |

### 7.2 System Prompt Modules → Policies

P1–P20 map directly to policy documents under `policies/`. See §6.

### 7.3 Scripts → Utilities

S1–S6 move to `scripts/` unchanged. They are invocable as `script` executor steps within workflows.

### 7.4 Hooks → Session Protocol

H1–H3 and P16 (task awareness at session start) merge into a **session protocol** defined in CLAUDE.md:

```
On session start:
1. Read state/memory/memory.yaml — load entries scoped to active context
2. Read state/domain/tasks.yaml — surface overdue and due-today items (P16)
3. Check for first-run condition (H1)
4. Check for upstream updates (H2)
5. Scan user prompt for skill keywords (H3)
6. Infer operating mode (P11)
7. Load always-on policies
```

### 7.5 MCP Tools → Integrations

Custom MCP tools (M1–M4 Gemini Vision) move to `mcp/`. External MCP integrations (E1–E8) are declared in `state/config/tools.yaml` and referenced by workflows via the `mcp` executor.

### 7.6 Data Structures → State Model

D1–D7 and Y1–Y4 are subsumed by the state model defined in §3.

### 7.7 Skills and Config → Reference Material

K1–K6 move to `skills/`. G1–G5 are adapted for the new project structure.

---

## 8. New Primitives

Capabilities absent from both projects that the synthesized system requires.

### 8.1 Required (for core functionality)

| ID | Primitive | Type | Description |
|---|---|---|---|
| N1 | Memory Capture | Workflow step | Proposes memory entries at session end. Extracts decisions, open questions, and context worth preserving from the session journal. Requires user approval per entry. |
| N2 | Memory Retrieval | Workflow step | Selects relevant memory entries for a given task scope. Used during context assembly. |
| N3 | Memory Consolidation | Workflow | Runs during weekly synthesis. Merges related entries, prunes decayed entries, summarizes long-running threads. |
| N4 | Context Assembly | Protocol | Retrieval layer protocol: scope identification, index query, recency filter, memory load, policy load. Defined as a policy document. |
| N5 | Index Update | Workflow step | Updates relevant indexes after content creation/modification. Invoked as a step in content-modifying workflows. |
| N6 | Reindex | Workflow | Full index rebuild from filesystem scan. Recovery mechanism for stale indexes. |
| N7 | Workflow Resume | Protocol | Reads checkpoint files, identifies last successful step, resumes execution. |
| N8 | Session Start | Hook/Protocol | Combined session-start behavior: memory load, task surfacing, update check, mode inference, policy load. |
| N9 | Session End | Hook/Protocol | Session-end behavior: memory capture, journal finalization, index updates. |

### 8.2 Identified for Later (not in initial build)

| ID | Primitive | Type | Rationale for deferral |
|---|---|---|---|
| F1 | Voice Input | Interface | Requires speech-to-text integration. Valuable but not foundational. |
| F2 | Voice Output | Interface | Requires text-to-speech integration. Same rationale. |
| F3 | Notification Delivery | Interface | Push notifications for deadline alerts, stale contacts. Requires a delivery channel (email, SMS, system notification). |
| F4 | Scheduled Execution | Trigger | Cron-based workflow triggers (replace Y3 aspirational schedules). Requires a scheduler process outside Claude Code. |
| F5 | Analytics Dashboard | Interface | Visualization of goals, task completion, time allocation. Useful but not core. |
| F6 | Delegation Workflows | Workflow | Multi-user task assignment and tracking. Significant complexity increase. |
| F7 | Correction Learning | Policy | System adjusts behavior based on patterns of user corrections. Requires memory + pattern detection across sessions. |
| F8 | Proactive Initiative | Policy | System proposes actions without being asked (e.g., "you haven't contacted X in 30 days"). Requires scheduled execution (F4) + memory. |
| F9 | Embedding Retrieval | Retrieval | Vector embeddings for semantic search. Upgrade path from maintained indexes if/when they prove insufficient. |

---

## 9. Build Sequence

### 9.1 Dependency Graph

```
L0 State Model
  └── L1 Retrieval (depends on state structure)
        └── L2 Workflows (depends on retrieval for context assembly)
              └── L3 Interfaces (depends on workflows for execution)

Within L0:
  Directory structure → Domain state schemas → Working memory schema → Session journals

Within L1:
  Tag index → Entity index → Concept index → Context assembly protocol

Within L2:
  Workflow schema → Step executors → Checkpointing → Gates → Composition
```

### 9.2 Incremental Build Plan

Each phase produces a usable system. No phase depends on future phases for its utility.

**Phase 1: Foundation**
*Goal: State model exists, one workflow runs end-to-end.*

- Create directory structure (§3.7)
- Define domain state schemas (goals, tasks, contacts, schedules)
- Implement setup workflow (adapted C14) to initialize state from user input
- Implement one operational workflow end-to-end: `morning-briefing`
  - This forces the workflow definition schema, step executors (prompt + mcp), checkpointing, and the `display` gate to work
- Write CLAUDE.md with session-start protocol (N8, minimal version)
- Extract 6 always-on policies from CoS CLAUDE.md into `policies/`
- Test: run setup, run morning briefing, verify checkpoint files written

**Phase 2: Memory and Retrieval**
*Goal: Cross-session continuity works. Context assembly reduces manual context management.*

- Implement working memory schema and file
- Implement session journal format
- Implement session-end memory capture (N1, N9)
- Implement session-start memory retrieval (N2, N8 full version)
- Build tag index and chronological index with incremental maintenance (N5)
- Implement context assembly protocol (N4)
- Adapt `morning-briefing` to use context assembly
- Test: run two sessions in sequence, verify memory carries forward

**Phase 3: Operational Workflows**
*Goal: Core CoS functionality operational with workflow structure.*

- Implement `triage` workflow (X2) with send gate
- Implement `tasks/*` workflows (X3 subcommands)
- Implement `enrich/*` workflows (X4 subcommands)
- Implement `daily-review` workflow (merges C3 + goal/task review)
- Add entity index, maintained by triage and enrichment workflows
- Test: full operational day cycle (morning briefing → triage → task execution → daily review)

**Phase 4: Knowledge Workflows**
*Goal: Claudesidian's knowledge management integrated with operational layer.*

- Implement `thinking-partner` workflow (C1)
- Implement `research` workflow (C2)
- Implement `inbox-process` workflow (C5, vault inbox)
- Implement `weekly-synthesis` workflow (C4, with memory consolidation N3)
- Add concept index, maintained by synthesis workflows
- Implement `capture-web` workflow (C8, Firecrawl integration)
- Test: research session that produces notes, which appear in next day's briefing context

**Phase 5: Development Workflows**
*Goal: Code-oriented tooling available for users who need it.*

- Implement `code-review` workflow (C9)
- Implement `pull-request` workflow (C10)
- Implement `release` workflow (C11)
- Implement `self-upgrade` workflow (C12)
- Implement `clean-prose` workflow (C7)
- Test: code review → PR → release cycle

**Phase 6: Advanced Retrieval and Composition**
*Goal: Indexes are comprehensive, workflows compose cleanly.*

- Full `reindex` workflow (N6)
- Workflow composition (`workflow` executor invoking sub-workflows)
- Index coverage audit: verify all content-modifying workflows maintain indexes
- Memory consolidation as part of weekly synthesis
- Test: composite workflow (morning briefing that invokes triage as a substep)

---

## 10. Open Questions

Decisions deferred pending implementation experience:

1. **Context window budget.** The 8,000-token default for retrieved context is a guess. Real usage will reveal whether this is too tight (missing relevant context) or too loose (crowding out reasoning space). Needs empirical tuning.

2. **Memory entry granularity.** Should a single decision be one entry, or should a decision and its supporting reasoning be captured together? Too granular wastes capacity; too coarse loses retrievability.

3. **Index staleness tolerance.** How stale can an index be before it degrades retrieval quality enough to matter? This determines whether index updates must be synchronous (part of every workflow) or can be batched.

4. **Workflow definition authoring.** The YAML schema is designed for human readability, but authoring new workflows is still manual. The `create-workflow` meta-workflow (adapted from C13) needs to produce valid definitions without requiring the user to learn the schema.

5. **Policy interaction.** When multiple policies apply and their guidance conflicts (e.g., deep-work says "close loops now" but scheduling-guard says "don't book that meeting"), what is the resolution mechanism? Currently: Claude uses judgment. This may need explicit priority ordering.

6. **Obsidian compatibility.** The vault structure is designed for Obsidian use. Changes to path conventions, template locations, and frontmatter schemas need testing against Obsidian's expectations (wikilinks, graph view, search).

7. **MCP server availability.** The workflow definitions assume MCP tools are available and reliable. Real MCP servers fail, rate-limit, and return unexpected formats. The workflow recovery protocol needs to handle these gracefully.

---

## Appendix A: Primitive Traceability Matrix

Every original primitive has a home in the architecture. None are dropped.

| Source | Count | Destination |
|---|---|---|
| C1–C15 Commands | 15 | `workflows/definitions/` |
| S1–S6 Scripts | 6 | `scripts/` |
| H1–H3 Hooks | 3 | Session protocol in CLAUDE.md |
| M1–M4 MCP Tools | 4 | `mcp/` |
| K1–K6 Skills | 6 | `skills/` |
| D1–D7 Data Structures | 7 | `state/` + `vault/` |
| G1–G5 Config | 5 | Adapted for new structure |
| X1–X4 Commands | 4 | `workflows/definitions/` |
| P1–P20 Modules | 20 | `policies/` |
| Y1–Y4 Data Structures | 4 | `state/domain/` |
| I1 Install | 1 | `workflows/definitions/setup.yaml` |
| E1–E8 Integrations | 8 | `state/config/tools.yaml` |
| N1–N9 New primitives | 9 | Various (see §8.1) |
| **Total** | **93** | |
