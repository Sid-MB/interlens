# `MessagingPolicy`

Asynchronous point-to-point messaging with per-agent mailboxes and a ping-driven scheduler.

```python
MessagingPolicy(agents: list[str] | None = None, *, fairness_every: int = 3)
```

Defined in [`interlens.communication.messaging`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/messaging.py#L128-L274)

**Inherits from:** [CommunicationPolicy](../policy/CommunicationPolicy.md)

`fairness_every` bounds starvation: after that many consecutive ping-driven grants, the
least-recently-active unpinged agent gets a turn regardless. The protocol text each agent needs is injected
automatically as a system-block view segment (`PROTOCOL`), so no manual prompt plumbing is required.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `agents` | `list[str] \| None` | `None` |  |
| `fairness_every` | `int` | `3` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `PROTOCOL` |  |  |
| `agents` |  |  |
| `events` | `list[dict]` |  |
| `fairness_every` |  |  |
| `mailboxes` | dict[str, list[[Mail](Mail.md)]] |  |

## Methods {#methods}

## `extra_segments` {#extra_segments}

```python
extra_segments(
	self,
	conversation: 'Conversation',
	participant: 'Participant',
) -> list[ViewSegment]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/messaging.py#L227-L244)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversation` | `'Conversation'` | *required* |  |
| `participant` | `'Participant'` | *required* |  |

## `next_speaker` {#next_speaker}

```python
next_speaker(self, conversation: 'Conversation') -> 'Participant | None'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/messaging.py#L197-L212)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversation` | `'Conversation'` | *required* |  |

## `on_commit` {#on_commit}

```python
on_commit(self, message: 'Message', conversation: 'Conversation') -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/messaging.py#L246-L265)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `message` | `'Message'` | *required* |  |
| `conversation` | `'Conversation'` | *required* |  |

## `read` {#read}

```python
read(self, reader: str, sender: str | None = None) -> list[Mail]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/messaging.py#L169-L182)

Mark `reader`'s unread mail (optionally from one `sender`) as read and schedule it for delivery into the reader's view.

Returns the newly delivered items.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `reader` | `str` | *required* |  |
| `sender` | `str \| None` | `None` |  |

## `reset` {#reset}

```python
reset(self) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/messaging.py#L267-L274)

## `send` {#send}

```python
send(self, sender: str, recipient: str, content: str, priority: str = 'normal') -> str
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/messaging.py#L160-L167)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `sender` | `str` | *required* |  |
| `recipient` | `str` | *required* |  |
| `content` | `str` | *required* |  |
| `priority` | `str` | `'normal'` |  |

## `tools_for` {#tools_for}

```python
tools_for(self, agent: str) -> tuple[Tool, Tool]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/messaging.py#L187-L190)

Native `send_message`/`read_message` tools bound to `agent`, for participants with a tool-calling family (attach via `tools=`).

The fenced-JSON path needs no setup.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `agent` | `str` | *required* |  |

## `unread` {#unread}

```python
unread(self, agent: str) -> list[Mail]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/messaging.py#L184-L185)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `agent` | `str` | *required* |  |

## `visible` {#visible}

```python
visible(
	self,
	message: 'Message',
	pov: 'Participant',
	conversation: 'Conversation',
) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/messaging.py#L220-L225)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `message` | `'Message'` | *required* |  |
| `pov` | `'Participant'` | *required* |  |
| `conversation` | `'Conversation'` | *required* |  |
