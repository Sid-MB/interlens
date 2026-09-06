# `policy`

Module `interlens.communication.policy`

Communication topology as a pluggable policy.

A `Conversation` has always answered two questions implicitly: *who speaks next* (round-robin over
`participants` order) and *who sees what* (everyone sees the whole shared transcript). A
`CommunicationPolicy` makes both answers explicit and swappable, so the same participants, scoring, and
persistence compose with different communication styles:

- `RoundRobinPolicy` — the classic shared transcript (the default behavior, now nameable).
- `DirectPipingPolicy` — one participant's output becomes the next one's input along a fixed chain,
  formalizing what a 2-party `Conversation` already does implicitly and generalizing it to longer pipelines.
- `MessagingPolicy` (see `messaging.py`) — no shared transcript at all: autonomous agents exchange
  point-to-point messages through per-agent mailboxes via `send_message`/`read_message`, with a
  ping-driven scheduler.

Custom topologies (private sub-group channels, hub-and-spoke, dynamic floor-passing) subclass
`CommunicationPolicy` and override the same four hooks — no core changes needed. Install a policy via
`Conversation(communication=...)` (or `conv.set(communication=...)`); `run` consults it for turn order
and the view pipeline consults it for visibility. Policies are conversation-state: a copy-on-write clone /
branch gets an independent deep copy, and they are runtime-only (not persisted by `save`), like
`message_hooks`.

## Classes

| Name | Summary |
|---|---|
| [`CommunicationPolicy`](CommunicationPolicy.md) | Who speaks next, and who sees what. |
| [`DirectPipingPolicy`](DirectPipingPolicy.md) | A fixed pipeline: each participant sees only its **predecessor's** output (plus moderator/system framing and its own past turns), and speaking order follows the chain — A → B → C → A → … |
| [`RoundRobinPolicy`](RoundRobinPolicy.md) | The shared-transcript default, as an explicit policy: speakers cycle through `participants` order and everyone sees every committed turn. |
