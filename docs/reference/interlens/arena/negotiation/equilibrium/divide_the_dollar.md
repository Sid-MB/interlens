# `divide_the_dollar`

A discrete divide-the-dollar TU game as `GameTables`: deals = integer allocations of `steps` units among `n` players (compositions), `u_i = share_i = units_i / steps`, `tau = 0`.

```python
divide_the_dollar(n: int, steps: int) -> GameTables
```

Defined in [`interlens.arena.negotiation.equilibrium`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/equilibrium.py#L153-L163)

Used as the Okada
unanimity sanity anchor for the equilibrium solver.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `n` | `int` | *required* |  |
| `steps` | `int` | *required* |  |
