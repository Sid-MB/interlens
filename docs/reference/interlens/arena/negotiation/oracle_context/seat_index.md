# `seat_index`

Resolve `agent` to a seat index.

```python
seat_index(game, agent) -> int
```

Defined in [`interlens.arena.negotiation.oracle_context`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/oracle_context.py#L180-L198)

Accepts an int (returned as-is) or a seat *name* (str), which is
matched against `sheet.agent` on each score sheet, then against a `game.seats`/`seat_names`/
`agents` name list, then an int-like string. The real `Oracle` ABC types `agent` as `str` (the
seat name), so oracles call this first before indexing the seat-indexed utility tables.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `game` |  | *required* |  |
| `agent` |  | *required* |  |
