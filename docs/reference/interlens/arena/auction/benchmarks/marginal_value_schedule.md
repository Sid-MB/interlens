# `marginal_value_schedule`

A seat's TRUE marginal value for each successive identical unit: `v_i * d_i^(r-1)` for `r = 1..min(k_i, n_units)`, zero beyond capacity.

```python
marginal_value_schedule(vm: ValueModel, seat: int, n_units: int) -> np.ndarray
```

Defined in [`interlens.arena.auction.benchmarks`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/benchmarks.py#L406-L413)

This is the demand-reduction-free schedule, and the
reference the demand-reduction gradient is measured against [ausubel_cramton2014].

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `vm` | [ValueModel](../allocation/ValueModel.md) | *required* |  |
| `seat` | `int` | *required* |  |
| `n_units` | `int` | *required* |  |
