# `normalized_utility`

`(utility, threshold, raw_utility)` for `sheet` over `deals_arr` (`(D, J)` option indices).

```python
normalized_utility(sheet, deals_arr: np.ndarray) -> tuple[np.ndarray, float, np.ndarray]
```

Defined in [`interlens.arena.negotiation.belief_accuracy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/belief_accuracy.py#L88-L104)

The first two are min-max normalized onto the type grid's `[0, 1]` scale (the additive sheet's span is
`sum_j (max_j - min_j)`, so this is the exact counterpart of the grid's construction); the third is the
raw points, which the accept set is defined on. A degenerate sheet (every deal worth the same) normalizes
to all-zeros with a threshold of `0.0` when it is met and `1.0` when it is not, so the accept set the
normalized pair implies still agrees with the raw one.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `sheet` |  | *required* |  |
| `deals_arr` | `np.ndarray` | *required* |  |
