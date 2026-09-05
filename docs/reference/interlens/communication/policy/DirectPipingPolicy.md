# `DirectPipingPolicy`

A fixed pipeline: each participant sees only its **predecessor's** output (plus moderator/system framing and its own past turns), and speaking order follows the chain — A → B → C → A → …

```python
DirectPipingPolicy(chain: list[str] | None = None)
```

Defined in [`interlens.communication.policy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/policy.py#L102-L135)

**Inherits from:** [CommunicationPolicy](CommunicationPolicy.md)

This formalizes the natural two-agent dialogue framing (where "the other's turn is my input" is already how
a 2-party shared transcript renders) and generalizes it to longer chains, where a shared transcript and a
pipeline genuinely diverge: in a 3-agent pipe, C sees B's output but not A's. Because it is the same
`Conversation` machinery, the full transcript is still recorded and serialized — visibility filters what
each *model* is conditioned on, never what the record keeps.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `chain` | `list[str] \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `chain` |  |  |

## Methods {#methods}

## `next_speaker` {#next_speaker}

```python
next_speaker(self, conversation: 'Conversation') -> 'Participant | None'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/policy.py#L119-L123)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversation` | `'Conversation'` | *required* |  |

## `reset` {#reset}

```python
reset(self) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/policy.py#L134-L135)

## `visible` {#visible}

```python
visible(
	self,
	message: 'Message',
	pov: 'Participant',
	conversation: 'Conversation',
) -> bool
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/policy.py#L125-L132)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `message` | `'Message'` | *required* |  |
| `pov` | `'Participant'` | *required* |  |
| `conversation` | `'Conversation'` | *required* |  |
