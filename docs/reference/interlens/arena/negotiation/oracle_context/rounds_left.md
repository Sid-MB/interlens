# `rounds_left`

Rounds remaining (this turn inclusive).

```python
rounds_left(game, history) -> int
```

Defined in [`interlens.arena.negotiation.oracle_context`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/oracle_context.py#L264-L273)

Uses `game.rounds` and completed rounds when discoverable;
defaults to `game.rounds` (or 1).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
| `history` |  | *required* |  |
