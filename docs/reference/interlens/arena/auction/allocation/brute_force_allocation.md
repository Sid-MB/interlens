# `brute_force_allocation`

The exhaustive optimum over every assignment of items to seats-or-unsold.

```python
brute_force_allocation(vm: ValueModel) -> tuple[Allocation, float]
```

Defined in [`interlens.arena.auction.allocation`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L316-L327)

Exponential
(`(n+1)^n_items`) and used ONLY to verify :meth:`ValueModel.efficient_allocation` in the tests — the
exactness claim is what every efficiency number rests on, so it is checked rather than asserted.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `vm` | [ValueModel](ValueModel.md) | *required* |  |
