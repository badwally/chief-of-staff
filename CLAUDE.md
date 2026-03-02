# Chief of Staff

An AI-powered chief of staff for executive operations. The filesystem is the database — YAML and Markdown files are the persistence layer, version-controlled with git, human-readable, and debuggable with standard tools.

## Project Structure

| Directory | Purpose |
|-----------|---------|
| `state/memory/` | Working memory — cross-session continuity |
| `state/domain/` | Goals, tasks, contacts, schedules, projects |
| `state/config/` | User identity, company context, voice, tools, tiers, modes — personal config generated from `*.template.yaml` during setup |
| `state/journals/` | Session execution logs (append-only) |
| `vault/` | Knowledge base (PARA: inbox, projects, areas, resources, archive) |
| `workflows/definitions/` | Declarative workflow YAML files |
| `workflows/schemas/` | Typed output schemas for workflow steps |
| `workflows/runs/` | Checkpoint files for active/completed runs |
| `policies/` | Governance policy documents (always-on + task-specific) |
| `indexes/` | Maintained retrieval indexes (tags, entities, concepts, recent) |
| `scripts/` | Shell utilities |
| `mcp/` | Custom MCP server code |
| `skills/` | Reference documents |

## Getting Started

New user? After cloning the repository, start Claude in this directory and the session-start protocol will detect that `state/config/identity.yaml` is missing. It will prompt you to run the setup workflow, which walks you through:

1. Configuring your identity, company context, communication voice, and MCP tools
2. Initializing all state files (goals, tasks, memory, etc.)
3. Creating your first session journal

Template files (`*.template.yaml`) in `state/config/` show the expected schema for each config file. The setup workflow uses these as a reference. For details, see `docs/setup-guide.md`.

## Session-Start Protocol

On every session start, execute these steps in order:

1. **Load working memory.** Read `state/memory/memory.yaml`. Surface entries scoped to the active context.

2. **Surface tasks.** Read `state/domain/tasks.yaml`. Identify and flag overdue and due-today items.

3. **Check first-run condition.** If `state/config/identity.yaml` does not exist, this is a first-run. Prompt the user to run the setup workflow (`workflows/definitions/setup.yaml`) to configure identity, company, voice, tools, and initialize state files.

4. **Check for upstream updates.** If the project is connected to a remote git repo, check for new commits. Surface any changes to workflows, policies, or config.

5. **Scan user prompt for skill keywords.** Match the user's initial message against known workflow triggers (see `state/config/modes.yaml` for keyword lists). If a workflow match is found, suggest running it.

6. **Infer operating mode.** Based on the user's prompt, infer which of the 6 operating modes applies (prioritize, decide, draft, coach, synthesize, explore). Announce the inferred mode.

7. **Load always-on policies.** Read all 6 policy files from `policies/`:
   - `policies/goal-referencing.md` (P1)
   - `policies/decision-posture.md` (P2)
   - `policies/anti-pattern-guards.md` (P3)
   - `policies/message-send-gate.md` (P4)
   - `policies/confidentiality-triggers.md` (P5)
   - `policies/context-discipline.md` (P18)

   Apply these policies throughout the session.

## Session-End Protocol

Before ending a session:

1. **Memory capture.** Review the session for decisions made, open questions discovered, preferences expressed, and context worth preserving. Propose memory entries for user approval. Never write memory entries without explicit approval.

2. **Journal finalization.** If a session journal was started (`state/journals/YYYY-MM-DD_NN.md`), finalize it with decisions, actions taken, and open threads.

## Always-On Policies

These 6 policies are loaded at session start and apply to ALL interactions:

| Policy | File | Core Rule |
|--------|------|-----------|
| Goal Referencing | `policies/goal-referencing.md` | Frame all work in terms of active goals |
| Decision Posture | `policies/decision-posture.md` | Clarity > Focus > Decision > Action > Improve |
| Anti-Pattern Guards | `policies/anti-pattern-guards.md` | No verbosity, neutral summaries, empty frameworks, batch questions, scope creep |
| Message Send Gate | `policies/message-send-gate.md` | Never send any message without explicit approval |
| Confidentiality Triggers | `policies/confidentiality-triggers.md` | Flag sensitive content, check channel appropriateness |
| Context Discipline | `policies/context-discipline.md` | Minimize context bloat, targeted queries, summarize results |

## Voice Interface (Optional)

When VoiceMode is enabled in `state/config/tools.yaml`, voice input and output are available as a supplement to the text CLI. Voice is never required — the system functions identically without it.

**Activation:** User invokes `/voicemode:converse` to enter voice conversation mode.

**Input:** Spoken input is transcribed to text via Whisper. Treat it identically to typed input. All workflows, mode inference, and policies apply unchanged.

**Output:** Use voice output selectively per `policies/voice-output.md`. Always display text alongside speech. Never speak confidential content, code, or structured data.

**Policy loading:** When VoiceMode is enabled, load `policies/voice-output.md` alongside the 6 always-on policies at session start.

## Workflow Execution Protocol

When running a workflow:

1. **Load definition.** Read the workflow YAML from `workflows/definitions/`. Validate step references and input dependencies.

2. **Assemble context.** Load the policies, memory scopes, and indexes declared in the workflow's `context` block.

3. **Execute steps sequentially.** For each step:
   - Resolve `${step.key}` input references from previous step outputs
   - Execute based on `executor` type (`prompt`, `mcp`, `script`, `workflow`)
   - Validate output against declared `schema` (if typed)
   - Write checkpoint to `workflows/runs/{workflow}-{timestamp}/{step-name}.yaml`
   - If a `gate` is declared, pause for user interaction

4. **Handle optional steps.** If a step has `optional: true` and its executor is unavailable (e.g., MCP server not configured), skip it gracefully. Use the `fallback` note if provided. Downstream steps should handle missing optional inputs.

5. **On failure.** Log the error in the checkpoint file. The workflow can be resumed from the failed step by reading prior checkpoints.

6. **On completion.** Write a summary checkpoint. Update session journal if one exists.

## Architecture Reference

Full architecture specification: `docs/arch-planning.md`
Planning analysis: `docs/chief-of-staff-planning-prompt.md`
