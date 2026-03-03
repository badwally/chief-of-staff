---
name: substack-digest
description: "Run when user says 'substack digest', 'newsletters', 'what did I miss in my newsletters', or 'substack'. Produces a topic-grouped digest of Substack newsletters from the last 24 hours."
---

# Substack Daily Digest

## Prerequisites

Before running, verify Gmail is available:
1. Check `state/config/tools.yaml` — gmail must be `enabled: true`
2. Attempt `mcp__claude_ai_Gmail__gmail_get_profile` to confirm authorization
3. If Gmail is not authorized, inform the user:
   > Gmail integration is not yet authorized. Go to Claude Settings > Integrations > Gmail to connect your Google account, then retry.

## Execution

Load and execute `workflows/definitions/substack-digest.yaml`:

1. **fetch-newsletters**: Search Gmail for `from:substack.com newer_than:1d`, extract publication/headline/summary, group by topic
2. **display-digest**: Format and display the topic-grouped digest
3. **save-to-obsidian**: Write the digest to `/Users/andrewgrant/obsidian/Substack/{YYYY-MM-DD}.md` with YAML frontmatter and [[wikilinked]] publication names

## On-Demand Read

After displaying the digest, the user may ask to read a specific article (e.g., "read the Stratechery piece"). When this happens:

1. Match the user's request to a newsletter in the digest by publication name
2. Use the stored `message_id` to fetch the full message via `gmail_read_message`
3. Execute the **on-demand-read** step: produce core argument, key claims, and goal relevance

## Notes

- This workflow is also embedded as a lightweight step in `workflows/definitions/morning-briefing.yaml`
- The standalone version provides deeper summaries and the on-demand read capability
- Topic grouping uses 4-6 broad labels: Tech/AI, Geopolitics, Finance, Culture, Science, Business Strategy
- Every run saves a daily note to the Obsidian vault at `/Users/andrewgrant/obsidian/Substack/`
- Publication names are [[wikilinked]] so repeated mentions across days auto-link in Obsidian's graph view
