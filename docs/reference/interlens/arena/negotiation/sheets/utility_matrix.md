# `utility_matrix`

Build the dense `|D| x n` utility matrix `U[k, i] = u_i(space.deal_at(k))`.

```python
utility_matrix(
	space: DealSpace,
	sheets: tuple[ScoreSheet, ...] | list[ScoreSheet],
) -> np.ndarray
```

Defined in [`interlens.arena.negotiation.sheets`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L330-L348)

This is the array every solution concept in `solutions.py` consumes. It is built without a Python loop over
the `|D|` deals: for each issue `j` the per-option, per-party value block (shape `(|options_j|, n)`) is
gathered by the mixed-radix option-index pattern `(arange(|D|) // stride_j) % |options_j|` and added in, so
the cost is `O(J * |D| * n)` vectorized. Row order matches :meth:`DealSpace.deal_at` /
:meth:`DealSpace.enumerate`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `space` | [DealSpace](../space/DealSpace.md) | *required* |  |
| `sheets` | tuple[[ScoreSheet](ScoreSheet.md), ...] \| list[[ScoreSheet](ScoreSheet.md)] | *required* |  |
