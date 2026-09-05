# `CommunicationPolicy`

Who speaks next, and who sees what.

```python
CommunicationPolicy()
```

Defined in [`interlens.communication.policy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/policy.py#L49-L78)

**Inherits from:** `ABC`

Four hooks, all consulted by the `Conversation` core:

- `next_speaker(conversation)` — the participant due to speak now, or `None` when no one is due (which
  ends a `run` exactly like a stop condition).
- `visible(message, pov, conversation)` — whether a committed transcript message enters `pov`'s view.
  Default: everything is visible (the shared-transcript semantics).
- `extra_segments(conversation, participant)` — additional view segments appended after the transcript
  (delivered mail, pending-message notices, protocol instructions). Default: none.
- `on_commit(message, conversation)` — bookkeeping after a turn is committed (parse message-passing
  actions, deliver mail, advance scheduling state). Default: no-op.

## Methods {#methods}

## `extra_segments` {#extra_segments}

```python
extra_segments(
	self,
	conversation: 'Conversation',
	participant: 'Participant',
) -> 'list[ViewSegment]'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/policy.py#L71-L72)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversation` | `'Conversation'` | *required* |  |
| `participant` | `'Participant'` | *required* |  |

## `next_speaker` {#next_speaker}

```python
next_speaker(self, conversation: 'Conversation') -> 'Participant | None'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/policy.py#L64-L66)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversation` | `'Conversation'` | *required* |  |

## `on_commit` {#on_commit}

```python
on_commit(self, message: 'Message', conversation: 'Conversation') -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/policy.py#L74-L75)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `message` | `'Message'` | *required* |  |
| `conversation` | `'Conversation'` | *required* |  |

## `reset` {#reset}

```python
reset(self) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/policy.py#L77-L78)

Clear accumulated scheduling/delivery state so one policy instance can drive a fresh conversation.

## `visible` {#visible}

```python
visible(
	self,
	message: 'Message',
	pov: 'Participant',
	conversation: 'Conversation',
) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/policy.py#L68-L69)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `message` | `'Message'` | *required* |  |
| `pov` | `'Participant'` | *required* |  |
| `conversation` | `'Conversation'` | *required* |  |
