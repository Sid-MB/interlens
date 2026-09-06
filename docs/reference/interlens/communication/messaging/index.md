# `messaging`

Module `interlens.communication.messaging`

Tool-mediated asynchronous messaging between autonomous agents.

Under `MessagingPolicy` there is **no shared conversation**: each agent sees only the moderator framing and
its own past turns. Communication is explicit — an agent *sends* a message to a named recipient
(`send_message`: content, `normal`/`high` priority), the recipient gets a **ping** (a lightweight notice
in its next view: how many unread, from whom, at what priority), and *reads* its mailbox (`read_message`),
after which the mail is delivered into its view. The activation scheduler grants turns ping-first (high
priority ahead of normal), with a **fairness tick** so agents nobody has pinged still act regularly, and lets a
reader act on freshly delivered mail immediately.

Both invocation surfaces feed the same mailboxes:

- **Fenced-JSON actions** (family-agnostic, works for every participant type — API, local, scripted): an agent
  ends its turn with `{"send_message": {"recipient": ..., "content": ..., "priority": ...}}` or
  `{"read_message": {}}`; the policy parses committed turns in `on_commit`.
- **Native tools** (local model participants with a tool-calling family): `policy.tools_for(name)` returns
  `Tool` objects to attach via `tools=` — `read_message` then resolves *within* the turn (the model reads
  and reacts in one generation), and the call/result trail lands in `metadata['tool_trail']` as usual.

Everything is recorded first-class for scoring and replay: each send/read/delivery appends a structured event
to `policy.events` (JSON-serializable) *and* annotates the committed message's metadata
(`comm_sends` / `comm_read`), so a saved transcript carries the full message traffic.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `PRIORITIES` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`Mail`](Mail.md) | One mailbox item. |
| [`MessagingPolicy`](MessagingPolicy.md) | Asynchronous point-to-point messaging with per-agent mailboxes and a ping-driven scheduler. |
| [`ReadMessageTool`](ReadMessageTool.md) | Native-tool surface for reading: `read_message()` returns and marks-read the caller's unread mail. |
| [`SendMessageTool`](SendMessageTool.md) | Native-tool surface for sending: `send_message(content, recipient, priority)`. |

## Functions

| Name | Summary |
|---|---|
| [`parse_json_actions`](parse_json_actions.md) | All fenced JSON objects in `text`, parsed (malformed fences are skipped, not fatal). |
