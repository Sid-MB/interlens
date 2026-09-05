# `slot_name`

Display name of slot `j` — `"Lot 1"`..`"Lot n"`, the token the action grammar's `item` field carries (design.md §3.2).

```python
slot_name(j: int, n_items: int) -> str
```

Defined in [`interlens.arena.auction.priors`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L182-L185)

Uniform across single- and multi-item stages so one parser serves both.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `j` | `int` | *required* |  |
| `n_items` | `int` | *required* |  |
