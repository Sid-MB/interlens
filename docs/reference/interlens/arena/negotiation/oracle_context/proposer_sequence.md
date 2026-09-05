# `proposer_sequence`

Per-round proposer seat indices.

```python
proposer_sequence(game) -> list
```

Defined in [`interlens.arena.negotiation.oracle_context`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/oracle_context.py#L297-L305)

Uses `game.proposer_sequence` if present; else a rotation starting
at `game.proposer` (default 0) over `range(n)` — the rotating-proposer default.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
