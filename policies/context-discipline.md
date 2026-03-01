---
id: context-discipline
scope: always-on
derived_from: P18
---

## Rule

Minimize context window bloat through disciplined information retrieval:

1. **Targeted queries** — Read specific files and sections, not entire directories. Use indexes to identify relevant files before loading them.
2. **Summarize results** — When retrieving information, summarize what was found rather than dumping raw content into context.
3. **Batch related reads** — Group related file reads together rather than interleaving with other operations.
4. **State rationale** — Before loading additional context, briefly state why it is needed for the current task.
5. **Prune aggressively** — If retrieved information turns out to be irrelevant, do not carry it forward in reasoning.

The goal is to maintain a high signal-to-noise ratio in the context window, preserving space for reasoning.

## Exceptions

During Explore mode or initial codebase familiarization, broader reading is permitted, but summarization discipline still applies.
