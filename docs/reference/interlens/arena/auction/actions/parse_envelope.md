# `parse_envelope`

Split a turn's fenced JSON object into its four channels WITHOUT validating the binding move.

```python
parse_envelope(text: str | None) -> TurnEnvelope
```

Defined in [`interlens.arena.auction.actions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/actions.py#L567-L597)

Kept separate from :func:`parse_auction_action` so a seat that produced a legal message but an illegal
bid still has its message published on the retry — the same separation `scorable.py` maintains between
the chat channel and the formal move.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str \| None` | *required* |  |
