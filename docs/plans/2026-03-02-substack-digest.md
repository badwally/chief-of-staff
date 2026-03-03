# Substack Daily Digest — Implementation Plan

**Date:** 2026-03-02
**Status:** Implemented

## Problem

25+ Substack newsletters arrive daily to Gmail. No consolidated view exists — checking them requires scrolling through Gmail manually. A topic-grouped daily digest with 1-line summaries would save time during morning briefings and enable on-demand deep reads.

## Design

### Standalone Workflow (`substack-digest.yaml`)
- **fetch-newsletters**: Gmail search `from:substack.com newer_than:1d`, extract metadata, group by 4-6 topic labels
- **display-digest**: Format topic-grouped headlines with summaries
- **on-demand-read**: User requests full article read — fetches via message_id, produces core argument + goal relevance

### Morning Briefing Integration
- Lightweight `review-newsletters` step inserted between `scan-inbox` and `synthesize-briefing`
- Quick headline scan only (no deep summaries)
- Synthesize step adds "Reading Queue" section with top 3-4 goal-relevant headlines

### Skill
- `skills/substack-digest/SKILL.md` triggers on "substack digest", "newsletters", "what did I miss", etc.
- Checks Gmail prerequisite before execution

## Files Created
- `workflows/schemas/newsletter-digest.yaml` — typed output schema
- `workflows/definitions/substack-digest.yaml` — standalone 3-step workflow
- `skills/substack-digest/SKILL.md` — skill definition
- `docs/plans/2026-03-02-substack-digest.md` — this file

## Files Modified
- `workflows/definitions/morning-briefing.yaml` — added review-newsletters step, updated synthesize-briefing
- `state/config/tools.yaml` — updated gmail entry to claude_integration type
- `state/config/modes.yaml` — added synthesize triggers and skills registry

## Prerequisites
- Gmail must be authorized in Claude Settings > Integrations > Gmail
- `mcp__claude_ai_Gmail` tools become available after authorization
