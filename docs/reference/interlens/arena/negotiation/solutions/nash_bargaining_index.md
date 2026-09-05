# `nash_bargaining_index`

Discrete **Nash Bargaining Solution**: `argmax_{d: x_i(d) > 0 for all i} prod_i x_i(d)`, computed as `argmax sum_i log x_i(d)` for overflow safety [nash1950] (solution statement p.159; the non-convex/finite axiomatization is [mariotti1998]; the symmetric n-player product is [harsanyi1963]).

```python
nash_bargaining_index(U: np.ndarray, tau: np.ndarray) -> tuple[int, tuple[int, ...], str]
```

Defined in [`interlens.arena.negotiation.solutions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L204-L219)

**Exactly scale
invariant** -- `u_i -> a_i u_i + c_i` (with `tau_i` moved likewise) multiplies the product by `prod a_i`
and leaves the argmax unchanged. If the strict-IR set is empty, falls back to Maximum Nash Welfare
(:func:`max_nash_welfare_index`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `U` | `np.ndarray` | *required* |  |
| `tau` | `np.ndarray` | *required* |  |
