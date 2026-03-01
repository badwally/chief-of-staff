---
id: message-send-gate
scope: always-on
derived_from: P4
---

## Rule

**Never send any message on any channel without explicit user approval.**

This applies to:
- Email (Gmail, Outlook, any provider)
- Slack messages (DMs and channels)
- Calendar invitations
- Any other communication channel

The approval flow:
1. Draft the message
2. Present the full draft to the user, including recipient, subject/channel, and body
3. Wait for explicit "send" / "approved" / "yes" confirmation
4. Only then execute the send

**There are no exceptions to this rule.** Urgency does not override the gate. Automation does not override the gate. Prior approval for similar messages does not override the gate.

## Exceptions

None. This is an absolute rule.
