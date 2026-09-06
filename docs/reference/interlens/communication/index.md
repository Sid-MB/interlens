# `communication`

Package `interlens.communication`

Pluggable communication topologies: who speaks next, and who sees what. See `policy.py`.

## Modules

- [`messaging`](messaging/index.md) — Tool-mediated asynchronous messaging between autonomous agents.
- [`policy`](policy/index.md) — Communication topology as a pluggable policy.

## Re-exported

| Name | Defined in | Summary |
|---|---|---|
| [`CommunicationPolicy`](policy/CommunicationPolicy.md) | `interlens.communication.policy` | Who speaks next, and who sees what. |
| [`DirectPipingPolicy`](policy/DirectPipingPolicy.md) | `interlens.communication.policy` | A fixed pipeline: each participant sees only its **predecessor's** output (plus moderator/system framing and its own past turns), and speaking order follows the chain — A → B → C → A → … |
| [`Mail`](messaging/Mail.md) | `interlens.communication.messaging` | One mailbox item. |
| [`MessagingPolicy`](messaging/MessagingPolicy.md) | `interlens.communication.messaging` | Asynchronous point-to-point messaging with per-agent mailboxes and a ping-driven scheduler. |
| [`ReadMessageTool`](messaging/ReadMessageTool.md) | `interlens.communication.messaging` | Native-tool surface for reading: `read_message()` returns and marks-read the caller's unread mail. |
| [`RoundRobinPolicy`](policy/RoundRobinPolicy.md) | `interlens.communication.policy` | The shared-transcript default, as an explicit policy: speakers cycle through `participants` order and everyone sees every committed turn. |
| [`SendMessageTool`](messaging/SendMessageTool.md) | `interlens.communication.messaging` | Native-tool surface for sending: `send_message(content, recipient, priority)`. |
| [`parse_json_actions`](messaging/parse_json_actions.md) | `interlens.communication.messaging` | All fenced JSON objects in `text`, parsed (malformed fences are skipped, not fatal). |
