# `round_ledger_card`

The per-round, all-seats view, or `""` on an episode that advises fewer than two seats.

```python
round_ledger_card(payload: dict) -> str
```

Defined in [`interlens.arena.viz.advice`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/advice.py#L255-L300)

Rendered server-side, one block per round, so the picture reads with scripting off and every number on it is
in the page rather than computed in the browser. Omitted entirely on a single-advised-seat arm, where five
columns would be four empty ones.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict` | *required* |  |
