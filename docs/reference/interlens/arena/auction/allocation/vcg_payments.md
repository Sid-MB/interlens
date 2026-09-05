# `vcg_payments`

Clarke-Groves pivot payments for a multi-item allocation [clarke1971_groves1973].

```python
vcg_payments(
	vm: ValueModel,
	alloc: Allocation | None = None,
) -> tuple[np.ndarray, Allocation]
```

Defined in [`interlens.arena.auction.allocation`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/allocation.py#L333-L353)

`p_i = W_{-i} - (W - V_i(S_i))`: the welfare the others would have obtained without `i`, minus the
welfare they actually obtain. A seat that wins nothing pays 0, and no payment exceeds the winner's own
bundle value. `alloc` defaults to the efficient allocation (the only allocation for which the pivot rule
is incentive compatible); passing a different one prices THAT allocation under the same rule, which is how
the clinching benchmark is cross-checked.

Returns `(payments, alloc)` with `payments` a `(n_bidders,)` float array.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `vm` | [ValueModel](ValueModel.md) | *required* |  |
| `alloc` | [Allocation](Allocation.md) \| None | `None` |  |
