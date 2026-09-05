# `max_nash_welfare_index`

**Maximum Nash Welfare** with the two-stage empty-product rule [caragiannis2019] (Def. 3.1 + Algorithm 1, pp.12:7-12:8): first find the largest number of parties that can be made simultaneously positive-surplus by a single deal, then, among deals achieving that count, maximize the product of the positive surpluses (via `sum log` over the satisfied parties).

```python
max_nash_welfare_index(U: np.ndarray, tau: np.ndarray) -> tuple[int, tuple[int, ...], str]
```

Defined in [`interlens.arena.negotiation.solutions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L272-L291)

When some deal clears every party's threshold this coincides exactly
with the Nash Bargaining Solution; otherwise it is the least-bad diagnostic point for an empty strict-IR
game. Scale-free [caragiannis2019] p.12:2.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `U` | `np.ndarray` | *required* |  |
| `tau` | `np.ndarray` | *required* |  |
