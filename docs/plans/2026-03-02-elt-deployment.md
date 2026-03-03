# ELT Deployment: Project Brief

**Date:** 2026-03-02
**Status:** Draft
**Scope:** 3–5 ELT members, single-tenant architecture preserved

---

## Problem Statement

The chief-of-staff tool delivers value as a single-user, single-repo system with Claude Code as its runtime and the filesystem as its database. Extending that value to other ELT members requires solving a provisioning and operations problem without abandoning the architecture that makes the tool work.

The current onboarding path — install Claude Code, clone the repo, manually configure MCP servers, run OAuth flows, execute the setup workflow — assumes a technical user comfortable maintaining a developer tool environment. That assumption holds for the tool's author. It does not hold for 3–5 executives who should be operating the tool, not administering it.

This project scopes the work required to make each ELT member's instance reliably provisioned, maintainable without ongoing technical support, and connected to shared organizational context where appropriate.

## Architecture Constraints

These are not up for debate in this project. They define the solution space.

1. **Single-tenant, single-repo.** Each ELT member gets their own instance. No shared runtime, no multi-user backend, no platform.
2. **Filesystem as database.** YAML and Markdown remain the persistence layer. No database introduction.
3. **Claude Code as runtime.** The tool runs inside Claude Code. No custom execution engine.
4. **Git as version control and distribution mechanism.** Upstream updates (workflows, policies, schemas) flow via git pull. Personal state is gitignored.

## Workstreams

Three workstreams, each with distinct deliverables. They are partially sequential: WS1 must be substantially complete before WS2 matters, and WS3's sync model needs to be designed before WS1's bootstrap can know which files to provision as shared vs. personal.

| # | Workstream | Core Question |
|---|-----------|---------------|
| WS1 | Environment Provisioning | How does an ELT member go from zero to running instance? |
| WS2 | Ongoing Maintenance and Reliability | What breaks after day one, and who fixes it? |
| WS3 | Shared Organizational Context | Which state is personal, which is shared, and how does it sync? |

**Dependency note:** WS3's design decisions feed back into WS1 (the bootstrap needs to know the shared/personal boundary) and WS2 (the maintenance model depends on which state is shared). WS3 design should be resolved first, even though WS1 is the most visible deliverable.

---

## WS1: Environment Provisioning

### Current State

Onboarding today requires a user to:

1. Install Claude Code CLI
2. Install git (if not present)
3. Clone the chief-of-staff repository
4. Configure MCP servers in Claude Code's global config (`~/.claude/`) for each desired integration (Gmail, Google Calendar, Slack, etc.)
5. Run OAuth authorization flows for each enabled MCP server — typically browser-based, per-service
6. Launch Claude Code in the repo directory
7. Complete the interactive setup workflow (identity, company, voice, tools)

Steps 1–3 are standard developer tooling. Step 7 is already well-designed — the setup workflow handles it. The problem is steps 4–6: MCP server configuration is manual, lives outside the project repository, requires editing JSON config files, and the OAuth flows are per-service browser interactions that can't be fully scripted.

### Target State

A bootstrap process that reduces onboarding to:

1. Run a single setup command (or a short script)
2. Complete browser-based OAuth flows for chosen integrations (irreducible — OAuth requires browser interaction)
3. Answer the setup workflow's interactive prompts

Everything between "I want to use this tool" and "answer these questions about your identity and preferences" should be automated.

### What the Bootstrap Must Do

**Environment prerequisites:**

- Verify Claude Code is installed (or install it)
- Verify git is available
- Clone the repo to a standard location (or accept a user-specified path)

**MCP server configuration:**

This is the hardest part of the bootstrap, and the part most likely to break across Claude Code versions. MCP server configuration lives in `~/.claude/settings.json` (or equivalent per-platform path), not in the project repo. The bootstrap must:

- Read the user's existing Claude Code config without clobbering other projects' MCP settings
- Add MCP server entries for each integration the user wants to enable
- Each entry requires: server name, command to start the server, and any environment variables (API keys, OAuth tokens)
- Handle the case where MCP servers are already partially configured

**OAuth credential provisioning:**

For each enabled integration (Gmail, Calendar, Slack, etc.), the user needs OAuth tokens. The bootstrap should:

- Launch the OAuth flow for each enabled service
- Store resulting tokens where the MCP server expects them
- Verify the tokens work (make a test API call)

This step is inherently interactive — OAuth requires browser consent. The bootstrap's job is to orchestrate the sequence and verify success, not eliminate the browser interaction.

**Shared state initialization (depends on WS3):**

- Configure the shared git remote (if using git-based sync)
- Pull shared organizational state (company.yaml, team goals, shared contacts)
- Set up the appropriate gitignore rules for the shared/personal boundary

**Handoff to setup workflow:**

- Launch Claude Code in the project directory
- The existing first-run detection (`identity.yaml` missing) triggers the setup workflow automatically
- Shared state (company.yaml) is already populated from the shared remote, so the setup workflow can skip or pre-fill the company step

### Deliverables

1. **Bootstrap script** (`scripts/bootstrap.sh` or equivalent): Automates steps 1–6 of the current onboarding path. Idempotent — safe to re-run. Scoped to macOS initially.
2. **Claude Code version detection** (`scripts/detect-claude-version.sh`): Queries the installed Claude Code version and validates that its MCP config format matches what the bootstrap expects. Exits with clear instructions on mismatch. Documents the supported version range.
3. **MCP config templates**: Per-integration JSON snippets that the bootstrap merges into the user's Claude Code config. Maintained alongside `tools.template.yaml`. Initial scope: 2–3 integrations (Gmail, Calendar, and one other).
4. **OAuth orchestration script**: Walks through OAuth flows for enabled integrations, stores tokens, verifies connectivity with a test API call per service.
5. **Bootstrap documentation**: Plain-language guide for non-technical users. Includes per-step screenshots, an OAuth troubleshooting section covering common failures (denied permission, API not enabled, browser timeout), and post-bootstrap verification steps.
6. **OAuth troubleshooting guide**: Separate reference for diagnosing and resolving OAuth failures after initial setup. Covers token expiry symptoms, re-authorization steps, and "how to tell if your integration is broken."

### Open Questions — WS1

1. **Claude Code config stability.** The MCP configuration format in `~/.claude/` is not a stable API. If Anthropic changes it, the bootstrap breaks. Mitigation: version-pin the config format, detect mismatches, fail gracefully with instructions.
2. **Per-platform differences.** Claude Code runs on macOS, Linux, and (partially) Windows. MCP config paths and shell environments differ. Scope the bootstrap to macOS initially (likely platform for all ELT members), note Linux as a secondary target.
3. **MCP server installation.** The bootstrap configures MCP servers but assumes they're installed. Some MCP servers are npm packages, some are standalone binaries, some are hosted. The bootstrap needs either to install them or to document the prerequisite clearly.
4. **Credential rotation.** OAuth tokens have expiry. The bootstrap provisions them once; WS2 handles renewal. But the bootstrap's storage choice constrains WS2's options.

### Estimated Effort

- Bootstrap script (environment + clone + config merge): 2–3 days
- MCP config templates and OAuth orchestration: 3–5 days (varies by number of integrations)
- Documentation: 1 day
- Testing across 3–5 actual ELT setups: 2–3 days

**Total: 8–12 days**, with variance driven primarily by the number of MCP integrations and per-platform edge cases.

---

## WS2: Ongoing Maintenance and Reliability

### Problem

The setup workflow handles day one. This workstream handles day thirty. MCP servers lose connectivity, OAuth tokens expire, Claude Code updates may introduce breaking changes, and upstream repo updates to workflows or policies need to reach each instance without disrupting personal state.

Without a maintenance model, each broken integration becomes a support ticket to whoever built the tool. At 3–5 users, that's manageable but annoying. The goal is to make routine maintenance self-service and surface failures before users notice them.

### Failure Modes

These are the things that will actually break, ordered by likelihood:

**OAuth token expiry.** Google OAuth tokens expire and require re-authorization. This is the most common failure. The user's morning briefing silently skips the inbox scan (because Gmail is `optional: true` in the workflow), and they don't realize they've been missing email triage for two weeks. This is a quiet failure — the system degrades gracefully by design, which means failures are invisible.

**MCP server unavailability.** An MCP server process crashes, a dependency updates and breaks it, or the user's machine restarts and the server doesn't come back. Same silent degradation pattern.

**Claude Code version changes.** Anthropic updates Claude Code. MCP config format changes, hook behavior changes, or tool availability changes. The chief-of-staff repo's CLAUDE.md and workflow definitions may reference behavior that no longer works as expected.

**Upstream repo drift.** New workflows, updated policies, or schema changes are pushed to the shared repo. Users who don't pull regularly fall behind. Users who pull at the wrong time get merge conflicts (unlikely given gitignore rules, but possible if the shared/personal boundary shifts).

**State corruption.** A malformed YAML edit (by Claude or by the user) breaks a state file. The next session fails to parse goals.yaml or memory.yaml and the session-start protocol errors.

### Maintenance Components

**Health check workflow.**

A new workflow (`workflows/definitions/health-check.yaml`) that runs on demand or on a schedule. Steps:

1. **Verify MCP connectivity.** For each enabled integration in `tools.yaml`, attempt a lightweight API call (e.g., Gmail: list labels; Calendar: get current time; Slack: auth test). Report pass/fail per integration.
2. **Check token freshness.** For integrations with known token expiry patterns, check token age or attempt a refresh. Flag tokens approaching expiry before they fail.
3. **Validate state files.** Parse all YAML state files. Report any that fail to parse or violate expected schema (missing required fields, wrong types).
4. **Check upstream status.** `git fetch` and compare local HEAD to remote. Report if the user is behind, and by how many commits. Surface a summary of what changed (new workflows, updated policies).
5. **Report.** Single-screen summary: green/yellow/red per component. Actionable next steps for any yellow or red items.

This workflow is the primary self-service maintenance tool. If something breaks, "run the health check" is the first instruction.

**Re-authorization script.**

A targeted script (or workflow step) for re-authorizing a specific MCP integration. The user runs it, completes the OAuth flow in the browser, and the script updates the stored token. This is the remediation path for the most common failure mode.

**Upstream update protocol.**

Documented procedure (and optionally a script) for pulling upstream changes:

1. Run `git stash` (in case of uncommitted personal state changes — shouldn't happen given gitignore, but defensive)
2. `git pull origin main`
3. Compare template files against personal configs: `diff state/config/identity.yaml state/config/identity.template.yaml` (etc.) to detect new fields
4. Run health check to verify nothing broke

**State backup.**

Personal state files (memory, goals, tasks, journals, vault) are not version-controlled by default (gitignored). They should be backed up. Options:

- **Git branch per user:** Personal state is committed to a user-specific branch, never pushed to main. Simple, uses existing tools, but conflates the shared-infrastructure repo with personal data.
- **Separate backup repo or location:** A cron job copies state files to a backup directory, cloud folder, or separate repo. Cleaner separation, but more moving parts.
- **Manual:** The user's machine backup (Time Machine, etc.) captures the directory. Simplest, least reliable.

Recommendation: start with manual (document that the directory should be included in system backups), add git-branch backup as an option for users who want it.

### Monitoring and Alerting

For 3–5 users, a full monitoring stack is overkill. The minimum viable approach:

- **Scheduled health check.** If scheduled execution (F4 from the architecture doc) is implemented, run the health check daily or weekly. Until then, the morning briefing workflow could include a lightweight connectivity check as an optional first step.
- **Failure surfacing in session.** When a session starts and an MCP tool fails, surface a clear message: "Gmail integration is unavailable. Run the health check for details." Currently, optional step failures are silently skipped. This needs to change — silent degradation is appropriate for workflow resilience, but the user should be informed.

### Deliverables

1. **Health check workflow** (`workflows/definitions/health-check.yaml`): MCP connectivity, token freshness, state validation, upstream status.
2. **Re-authorization script** (`scripts/reauth.sh`): Per-integration OAuth re-authorization.
3. **Upstream update script** (`scripts/update.sh`): Git pull with template diff and post-update health check.
4. **Failure surfacing in session protocol**: Modify session-start behavior to report MCP failures visibly rather than silently skipping.
5. **Maintenance documentation**: Non-technical guide covering common failure modes and their resolution.

### Open Questions — WS2

1. **Scheduled execution dependency.** The health check is most valuable when it runs automatically. The architecture doc identifies scheduled execution (F4) as deferred. Should this project include a minimal scheduler (cron job that launches Claude Code with a specific command), or remain manual-trigger only?
2. **Token storage visibility.** Can the health check script inspect token expiry without a full OAuth client? Depends on how each MCP server stores tokens. May need per-server inspection logic.
3. **Claude Code update notifications.** There's no mechanism to detect that Claude Code itself has updated. The health check can't distinguish "MCP config format changed" from "MCP server crashed." Mitigation: version-pin Claude Code where possible, document the update procedure.

### Estimated Effort

- Health check workflow: 2–3 days
- Re-authorization script: 1–2 days per integration (reuses bootstrap OAuth logic)
- Upstream update script: 1 day
- Session-start failure surfacing: 1 day
- Documentation: 1 day

**Total: 6–10 days**, with variance driven by the number of integrations that need health-check and re-auth logic.

---

## WS3: Shared Organizational Context

### Problem

Five ELT members running independent instances will immediately diverge on organizational state. The CEO updates company context — new board member, revised operating principles, updated leadership team — and that change exists only in their instance. The CTO adds a strategic goal for the quarter; the other four instances don't reflect it. A key contact changes roles; each instance maintains a stale record independently.

Some state is inherently personal (my identity, my voice, my memory, my tasks). Some state is inherently organizational (company context, team-level goals, the contact registry, governance policies, workflow definitions). The current architecture doesn't distinguish between them because it was designed for one user.

### State Classification

Every file in the system falls into one of three categories:

**Shared infrastructure (already tracked in git):**

- `workflows/definitions/` — workflow YAML files
- `workflows/schemas/` — typed output schemas
- `policies/` — governance policy documents
- `state/config/modes.yaml` — operating mode definitions
- `state/config/tiers.yaml` — triage tier definitions
- `state/config/templates/` — note and project templates
- `*.template.yaml` files — config schema references
- `scripts/`, `mcp/`, `skills/`, `docs/`
- `CLAUDE.md`, `.claude/`

These already sync via `git pull`. No design change needed.

**Shared organizational state (currently gitignored, needs to become shared):**

- `state/config/company.yaml` — company description, stage, leadership, board
- A subset of `state/domain/goals.yaml` — team-level or company-level OKRs (distinct from personal goals)
- A subset of `state/domain/contacts/` — shared contact registry (the organizational CRM, not personal relationship notes)
- Potentially: shared project definitions in `state/domain/projects/`

These files are currently generated during each user's setup workflow and gitignored. For multi-user, they need a shared source of truth and a sync mechanism.

**Personal state (remains gitignored, per-user):**

- `state/config/identity.yaml` — name, role, constraints, energy patterns
- `state/config/voice.yaml` — communication style
- `state/config/tools.yaml` — which MCP integrations are enabled (per-user)
- `state/memory/memory.yaml` — personal working memory
- `state/domain/tasks.yaml` — personal task list
- `state/domain/schedules.yaml` — personal automation schedules
- `state/journals/` — session journals
- `vault/` — personal knowledge base
- `indexes/` — retrieval indexes (derived from personal + shared state)
- Personal goals within goals.yaml
- Personal notes on contacts

### The Core Design Decision: How to Handle Mixed Files

The clean cases are easy: `identity.yaml` is personal, `company.yaml` is shared, workflow definitions are shared infrastructure. The hard cases are files that contain both shared and personal content:

**Goals.** An ELT member has both personal goals ("improve my presentation skills") and team goals ("ship v2 by end of Q2"). The current `goals.yaml` doesn't distinguish between them. Options:

- **Split the file:** `state/domain/goals-personal.yaml` (gitignored) and `state/domain/goals-shared.yaml` (tracked or synced). Clean separation, but requires updating every workflow and policy that reads `goals.yaml`.
- **Tag within the file:** Each goal gets a `scope: personal | team | company` field. The shared sync mechanism extracts and merges scoped entries. More flexible, more complex sync logic.
- **Separate directory:** `state/domain/goals/personal.yaml` and `state/domain/goals/shared.yaml`. Same as file split but cleaner directory structure.

Recommendation: **split into separate files.** The tagging approach makes the sync mechanism responsible for parsing YAML and merging entries, which is fragile. Separate files let git handle the boundary.

**Contacts.** The contact registry (`contacts/_index.yaml` + per-contact `.md` files) contains both organizational contacts (shared) and personal relationship context (notes, last-interaction, communication preferences — personal). Options:

- **Shared index, personal overlays.** The shared `_index.yaml` contains the organizational directory (name, role, tier, company). Each user has a personal directory (`contacts/personal/`) for relationship notes, interaction history, and communication preferences. Workflows merge both at read time.
- **Fully shared contacts.** All contact data is shared. Loses personal relationship context.
- **Fully personal contacts.** Each user maintains their own. Loses organizational consistency.

Recommendation: **shared index with personal overlays.** The organizational directory (who is this person, what's their role, what tier are they) is shared. Personal notes on the relationship are private. This matches how a real organization works — the CRM is shared, your personal notes are yours.

### Sync Mechanism

Given the constraints (git-based, no platform, single-tenant), the sync mechanism should use git. Three options:

**Option A: Shared files tracked on main branch.**

Move shared organizational state from gitignored to tracked. `company.yaml`, `goals-shared.yaml`, and the shared contact index are committed to the repo. Users pull to get updates, and designated individuals push changes.

- Pro: Simplest. Uses existing git workflow. No new tooling.
- Con: Every user's repo now contains other users' commits to shared state. Merge conflicts are possible if two people update company.yaml simultaneously (unlikely for 3–5 users but possible). The repo becomes a mix of infrastructure and live organizational data.

**Option B: Git submodule for shared state.**

Create a separate repo (`chief-of-staff-shared`) containing only organizational state. Mount it as a git submodule in each user's instance at a path like `state/shared/`. Workflows read from `state/shared/company.yaml` instead of `state/config/company.yaml`.

- Pro: Clean separation between infrastructure, shared state, and personal state. Each repo has a single concern.
- Con: Git submodules are notoriously awkward. Non-technical users will not manage submodule updates correctly. Adds complexity to the bootstrap and update scripts.

**Option C: Shared git remote with branch-per-user.**

One repo, but shared state lives on a `shared` branch that users merge into their local branch. Each user works on a personal branch.

- Pro: Single repo. Branch model is conceptually clean.
- Con: Branch management is error-prone for non-technical users. Merge conflicts between shared and personal branches. Operationally fragile.

**Recommendation: Option A** — track shared state on main, with clear conventions.

The submodule and branch approaches add operational complexity that exceeds their benefit for 3–5 users. Option A works if:

- The shared/personal boundary is enforced by file-level separation (separate files, not entries within files)
- A convention designates who is authoritative for shared state (e.g., one person is the "org admin" who pushes shared state changes)
- The update script (`scripts/update.sh` from WS2) handles the pull cleanly
- Shared state changes are infrequent (company.yaml changes quarterly, not daily)

### Authority Model

Who can update shared state?

**Single authority:** One person (likely the CEO or whoever initiated the tool) is the canonical editor of shared organizational state. They update company.yaml, shared goals, and the shared contact index. They push to the remote. Others pull. Changes to shared state by other users are proposed (via a message, a PR, or a manual request) and applied by the authority.

This is operationally simple and matches the likely reality: the CEO defines company context, strategic goals, and the leadership team. Other ELT members consume that context and maintain their own personal state.

**Shared authority with conventions:** Any ELT member can push shared state changes, with the convention that changes are announced (via Slack, email, or a commit message convention) and that conflicts are resolved by the most senior stakeholder. This is faster but riskier — silent overwrites are possible.

Recommendation: **single authority initially**, with the option to relax to shared authority once the team is comfortable with the tool and the update workflow.

### File Structure Changes

The current structure needs modification to support the shared/personal split:

```
state/
├── config/
│   ├── company.yaml              # SHARED (move from gitignored to tracked)
│   ├── identity.yaml             # PERSONAL (remains gitignored)
│   ├── voice.yaml                # PERSONAL (remains gitignored)
│   ├── tools.yaml                # PERSONAL (remains gitignored)
│   ├── modes.yaml                # SHARED INFRASTRUCTURE (already tracked)
│   └── tiers.yaml                # SHARED INFRASTRUCTURE (already tracked)
├── domain/
│   ├── goals-shared.yaml         # SHARED (new file, tracked)
│   ├── goals-personal.yaml       # PERSONAL (new file, gitignored)
│   ├── tasks.yaml                # PERSONAL (remains gitignored)
│   ├── schedules.yaml            # PERSONAL (remains gitignored)
│   ├── contacts/
│   │   ├── _index.yaml           # SHARED (move to tracked)
│   │   ├── *.md                  # SHARED (base contact files, tracked)
│   │   └── personal/             # PERSONAL (new directory, gitignored)
│   │       └── *.md              # Personal notes on contacts
│   └── projects/
│       └── _index.yaml           # SHARED (move to tracked)
├── memory/
│   └── memory.yaml               # PERSONAL (remains gitignored)
└── journals/                     # PERSONAL (remains gitignored)
```

### Impact on Existing Components

**Setup workflow.** The company setup step (`setup-company` in `setup.yaml`) changes behavior: instead of collecting company info from scratch, it checks whether `company.yaml` already exists (pulled from shared remote). If it does, the step displays the existing context for confirmation rather than prompting from zero. The setup workflow still creates `identity.yaml` and `voice.yaml` from scratch.

**Goals workflow.** Any workflow that reads `goals.yaml` now reads both `goals-shared.yaml` and `goals-personal.yaml` and merges them. The goal-referencing policy (P1) applies to both. Personal goals reference personal tasks; shared goals provide strategic context.

**Contact workflows.** Enrichment and triage workflows read the shared contact index and overlay personal notes. When updating a contact's organizational data (role change, tier change), the update goes to the shared file. When adding personal relationship notes, the update goes to `contacts/personal/`.

**Context assembly.** The retrieval layer's scope-matching logic needs to distinguish shared and personal state. A query scoped to "project X" should pull from both shared project definitions and personal task lists. The token budget may need adjustment since there's more state to potentially include.

**Index maintenance.** Indexes are per-user (they reflect the user's combined view of shared + personal state). The index files remain gitignored. Each user's indexes are rebuilt from their merged view.

### Deliverables

1. **State classification document:** Definitive list of which files are shared, personal, or infrastructure. Reference for all other workstreams. Must be finalized in Phase 0 before any implementation begins.
2. **Contact merge specification:** Explicit schema defining which contact fields are shared (org data: name, role, tier, company) vs. personal (relationship notes, interaction history, communication preferences). Pseudo-code for the merge logic that workflows use at read time. A helper script or convention that workflows call to "get merged contact view."
3. **File structure migration:** Split `goals.yaml` into shared and personal. Restructure contacts directory. Update `.gitignore`. Commit `.gitignore` changes and initial shared state atomically to avoid sequencing issues for users pulling updates.
4. **Goal ID namespacing convention:** Shared goals use `SG-*` prefix, personal goals use `PG-*` prefix (or equivalent). Document the convention; update goal-creating workflows to enforce it.
5. **Workflow updates:** Modify all workflows that read goals, contacts, or company config to handle the split-file model. Update health-check schemas for the new split-file structure (do not defer to WS2).
6. **Setup workflow modification:** Company step reads existing shared state instead of prompting from scratch. Define behavior for incomplete shared state (missing fields) and for non-authority users who attempt edits — display as read-only with a note to request changes from the authority.
7. **Authority model documentation:** Who updates shared state, how changes are communicated, conflict resolution procedure.
8. **Gitignore and git tracking changes:** Move shared state files from gitignored to tracked. Ensure personal state remains gitignored.

### Open Questions — WS3

1. **Shared projects.** Should `projects/_index.yaml` be shared? Projects often span multiple ELT members' domains. But project-specific tasks, notes, and vault folders are personal. The index could be shared while project detail files remain personal — same pattern as contacts.
2. **Shared schedules.** Are there team-level scheduled workflows (e.g., a weekly team synthesis that all instances run)? Or are schedules purely personal? If shared, `schedules.yaml` needs the same split treatment as goals.
3. **Goal ID namespacing.** If shared goals use IDs like `G-001` and personal goals also use `G-001`, there's a collision. Convention needed: shared goals use `SG-*`, personal goals use `PG-*`, or a single namespace with range allocation.
4. **Contact overlay merge strategy.** When the shared index updates a contact's tier and the user has personal notes on that contact, how does the merge work at read time? Straightforward if the fields don't overlap (shared has org data, personal has relationship data), but needs explicit definition.

### Estimated Effort

- State classification and file structure design (Phase 0): 3–4 days
- Contact merge specification and helper logic: 2–3 days
- File structure migration, gitignore changes, ID namespacing: 2–3 days
- Workflow updates (goals, contacts, company, health-check schemas): 4–6 days
- Setup workflow modification (including read-only/incomplete-state handling): 1–2 days
- Authority model and documentation: 1 day
- Testing (verify shared state syncs correctly across two instances): 2–3 days

**Total: 15–22 days**, reflecting the contact merge specification (previously unscoped), health-check schema updates (previously deferred to WS2), and the Phase 0 design work that is a hard prerequisite. The original 10–14 day estimate understated the complexity of the contact overlay and goal-splitting patterns.

---

## Execution Sequence

Given the dependency between workstreams (WS3 design feeds WS1 bootstrap, WS2 depends on both):

**Phase 0: WS3 Design (3–4 days). Hard gate — no implementation begins until sign-off.** Resolve the shared/personal boundary. Produce the state classification document. Decide on goal splitting, contact overlay merge logic, authority model, and goal ID namespacing. Specify which `company.yaml` fields are read-only for non-authority users. Define the contact merge schema (which fields are shared, which are personal, how workflows combine them). This is design work, not implementation — but the decisions here are load-bearing for all three workstreams and cannot be made in parallel with implementation.

**Phase 1: WS3 Implementation + WS1 Bootstrap (parallel, 2–3 weeks).** Implement the file structure migration (WS3) while building the bootstrap script (WS1). These can proceed in parallel once the design decisions from Phase 0 are locked. WS1 should scope the initial bootstrap to 2–3 MCP integrations (Gmail, Calendar, and one other) rather than all eight; additional integrations are added during Phase 3 as per-user needs emerge. WS3 must deliver updated health-check schemas for split files alongside the file structure changes — not deferred to WS2.

**Phase 2: WS2 Maintenance Tooling (1–2 weeks).** Build the health check workflow, re-auth script, update script, and failure surfacing. This phase depends on WS1 (the health check needs to know what was provisioned) and WS3 (the update script needs to handle shared state pulls). The update script must include a post-pull step that either re-timestamps pulled files to match their git commit date or excludes shared files from the chronological index — preventing git pull from corrupting the retrieval layer's recency data.

**Phase 3: Rollout (2–3 weeks).** Provision one ELT member as a beta tester. Budget 3–5 days for that user's onboarding, debugging, and documentation iteration. Once the first user is stable, provision one more. Then the remaining members. Do not onboard all users in parallel — each onboarding surfaces per-environment issues (macOS version, existing Claude Code config, shell environment, network/proxy constraints) that require bootstrap iteration. The tool's author should be explicitly available as support during this phase with a 2-hour response commitment for critical issues (broken bootstrap, corrupted state, failed OAuth).

**Total estimated duration: 7–10 weeks**, including rollout iteration. The original 5–8 week estimate did not adequately account for the Phase 0 hard gate, the per-user debugging overhead in Phase 3, or the OAuth/MCP integration complexity at the edges.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Claude Code MCP config format changes | Medium | High — breaks all bootstraps | Add `scripts/detect-claude-version.sh` to bootstrap; check config format before mutation; document supported Claude Code version range; fail with manual instructions on mismatch |
| OAuth token expiry goes undetected | High | Medium — silent degradation of integrations | Health check workflow with MCP connectivity test; modify session-start to surface MCP failures visibly rather than silently skipping optional steps |
| Non-technical users can't complete OAuth flows | Medium | High — blocks onboarding entirely | Bootstrap documentation with per-step screenshots; OAuth troubleshooting section covering common failures (denied permission, API not enabled in GCP, browser timeout); fallback to paired setup session |
| Shared state merge conflicts | Low | Medium — blocks git pull for affected user | Single authority model reduces conflict probability; `.gitignore` and shared state changes committed atomically; document manual resolution for non-technical users |
| MCP server installation varies by platform | Medium | Medium — delays onboarding | Scope bootstrap to macOS initially with 2–3 integrations; document prerequisites per platform; budget 1–2 days per additional integration in Phase 3 |
| Workflow updates for split-file model introduce regressions | Medium | Medium — broken briefings or triage | Test each modified workflow against both empty and populated state files; WS3 delivers updated health-check schemas alongside split files |
| Adoption stalls — ELT members don't use the tool regularly | Medium | High — wasted project effort | Rollout one user at a time; validate value with first user before expanding; explicit support commitment during Phase 3 |
| Git pull corrupts chronological index | Medium | Low — stale retrieval context | Post-pull index repair in update script; or exclude shared files from chronological index |
| Concurrent Claude sessions corrupt state files | Low | High — unrecoverable data loss | Document that only one Claude session should access an instance at a time; health check validates YAML integrity |

---

## Appendix: Pressure-Test Findings

This brief was subjected to a structured review after initial drafting. The following findings were identified and integrated into the workstream descriptions, deliverables, execution sequence, and estimates above. They are preserved here for traceability.

**Findings integrated (material changes to the brief):**

1. **WS3 design must be a hard gate.** The original execution sequence showed Phase 0 and Phase 1 as partially parallel. WS3 design decisions (shared/personal boundary, contact merge schema, goal namespacing, authority model field-level specifics) are prerequisites for both the WS1 bootstrap and the WS3 implementation. Phase 0 is now a hard gate.

2. **Claude Code version detection is a missing dependency.** The bootstrap writes to `~/.claude/` config without verifying the expected format. Added `scripts/detect-claude-version.sh` to WS1 deliverables.

3. **Contact merge logic was unspecified.** The brief recommended "shared index with personal overlays" but did not define the merge schema, which fields belong to each layer, or how workflows combine them at read time. Added contact merge specification as a WS3 deliverable.

4. **Health-check schemas for split files were deferred to WS2.** Splitting `goals.yaml` creates new files that the health check must validate, but no schema was specified. Moved health-check schema updates to WS3 deliverables so they ship alongside the file structure changes.

5. **OAuth token storage varies per MCP server.** Each MCP server stores tokens differently. The bootstrap must discover storage locations per server, and the health check must be able to inspect them. Scoped WS1 to 2–3 integrations initially rather than all eight.

6. **Phase 3 rollout was underestimated.** Testing with real ELT users on varied environments (macOS versions, existing Claude Code installs, shell environments, network constraints) requires more than 1 week. Extended to 2–3 weeks with sequential onboarding and explicit support commitment.

7. **Git pull can corrupt the chronological index.** Pulling shared state from origin updates file timestamps, causing the retrieval layer to treat pulled files as "recently modified." Added post-pull index repair to WS2 update script requirements.

8. **Setup workflow behavior with pre-existing shared state was underspecified.** What happens when `company.yaml` exists but is incomplete? When a non-authority user wants to edit it? Added explicit handling to WS3 setup workflow modification deliverable.

**Findings noted but not integrated (accepted risks or deferred):**

- Git-based sync for shared state introduces the possibility of merge conflicts during simultaneous pushes. Accepted as low-probability for 3–5 users with single-authority model; documented manual resolution in bootstrap docs.
- OAuth documentation will go stale as Google/Slack change their UIs. Accepted; plan for 1–2 days of documentation updates per quarter.
- Concurrent Claude sessions on the same instance can corrupt state files. Accepted; documented as a usage constraint rather than building file locking.

**Net effect on estimates:** Original total was 5–8 weeks. Revised to 7–10 weeks, driven primarily by the Phase 0 hard gate, expanded WS3 scope (contact merge spec, health-check schemas), and a more realistic Phase 3 rollout timeline.

---

## What This Project Is Not

This project does not build a product. It does not introduce multi-tenancy, a web interface, a mobile client, a shared database, or a platform. It makes a single-user tool reproducible for a small, known set of users within a single organization, using the existing architecture and distribution mechanism (git).

If the result is that 3–5 people can independently run and maintain their own chief-of-staff instance with shared organizational context, the project is done. If the result reveals that the architecture cannot support even this modest expansion without fundamental changes, that is also a valuable outcome — it defines the boundary of the current design.
