# `is_refusal`

Did this completion come back declined rather than generated?

```python
is_refusal(message) -> bool
```

Defined in [`interlens.arena.refusal`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/refusal.py#L75-L88)

True when the participant stamped `metadata["refusal"]` (`APIParticipant` sets it from the native stop
reason), when the stop reason is one of :data:`REFUSAL_STOPS`, or when the visible content is empty and the
stop reason is *not* a truncation — an empty non-truncated completion is the same "the seat wrote nothing"
failure, whatever the provider called it.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `message` |  | *required* |  |
