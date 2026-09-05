# `parse_negotiation_state`

The scenario-emitted `negotiation_state` block in `text` (the inner dict of the last fenced JSON object carrying that key), or `None`.

```python
parse_negotiation_state(text: str) -> dict | None
```

Defined in [`interlens.arena.negotiation.strategies`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/strategies.py#L190-L198)

This is the authoritative structured-state channel a scenario
embeds in a seat's view, so a `PolicyParticipant` reads canonical offer ids / round straight off it
instead of reconstructing the ledger from the transcript; :meth:`NegotiationState.from_block` turns the
result into a state. Reads through `parsing.last_json_with_key` — the library's one fenced-JSON reader.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | *required* |  |
