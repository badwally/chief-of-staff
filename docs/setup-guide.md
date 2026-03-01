# Setup Guide

## Prerequisites

- [Claude Code](https://claude.com/claude-code) CLI installed
- Git
- (Optional) MCP servers configured for integrations you want to use (Gmail, Google Calendar, Slack, etc.)

## Quick Start

```bash
git clone <repo-url> chief-of-staff
cd chief-of-staff
claude
```

On first run, Claude detects that `state/config/identity.yaml` is missing and prompts you to run the setup workflow. Follow the interactive prompts to configure:

1. **Identity** — your name, role, meeting constraints, energy patterns
2. **Company** — organization name, stage, industry, leadership team
3. **Voice** — communication tone, formality, stylistic patterns
4. **Tools** — which MCP integrations to enable

The workflow then initializes all state files and creates your first session journal.

## What Gets Configured

| File | Purpose |
|------|---------|
| `state/config/identity.yaml` | Your name, role, constraints, energy patterns |
| `state/config/company.yaml` | Organization context, leadership, principles |
| `state/config/voice.yaml` | Writing style and communication preferences |
| `state/config/tools.yaml` | MCP integrations (Gmail, Calendar, Slack, etc.) |

These files are generated from the `*.template.yaml` files in the same directory. Templates are tracked in git; your personal config files are not.

## Re-Running Setup

To re-run setup from scratch, delete `state/config/identity.yaml`:

```bash
rm state/config/identity.yaml
```

The next session will detect the missing file and prompt you to run setup again.

To update a single config file, edit it directly — no need to re-run the full workflow.

## Tracked vs Personal Files

**Tracked in git** (shared across all users):
- Workflow definitions, schemas, and policies
- Operating modes and triage tiers (`modes.yaml`, `tiers.yaml`)
- Template files (`*.template.yaml`)
- Documentation and architecture specs

**Personal** (gitignored, created during setup):
- Config files: `identity.yaml`, `company.yaml`, `voice.yaml`, `tools.yaml`
- Working memory: `state/memory/memory.yaml`
- Domain state: goals, tasks, schedules, contacts, projects
- Session journals
- Vault contents
- Index data (tags, entities, concepts, recent)

## Updating from Upstream

Pull new changes without losing your personal state:

```bash
git pull origin main
```

Since personal files are gitignored, `git pull` will only update shared infrastructure (workflows, policies, templates, docs). Your config, state, and vault content are untouched.

If a template file changes upstream, compare it with your config to see if new fields were added:

```bash
diff state/config/identity.yaml state/config/identity.template.yaml
```
