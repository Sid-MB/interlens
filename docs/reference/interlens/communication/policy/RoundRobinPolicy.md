# `RoundRobinPolicy`

The shared-transcript default, as an explicit policy: speakers cycle through `participants` order and everyone sees every committed turn.

```python
RoundRobinPolicy(first: str | None = None)
```

Defined in [`interlens.communication.policy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/policy.py#L81-L99)

**Inherits from:** [CommunicationPolicy](CommunicationPolicy.md)

`first` (a name) shifts the starting speaker.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `first` | `str \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `first` |  |  |

## Methods {#methods}

## `next_speaker` {#next_speaker}

```python
next_speaker(self, conversation: 'Conversation') -> 'Participant | None'
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/policy.py#L89-L96)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `conversation` | `'Conversation'` | *required* |  |

## `reset` {#reset}

```python
reset(self) -> None
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/policy.py#L98-L99)
