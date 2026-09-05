# `mnw_objective`

The full-information table objective of shape `(|D|,)` — what the **fairness oracle** maximizes.

```python
mnw_objective(tables: GameTables) -> np.ndarray
```

Defined in [`interlens.arena.negotiation.fairness`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/fairness.py#L122-L128)

Composition of :func:`normalized_surplus_matrix` and :func:`objective_from_normalized`. Its argmax is the
discrete NBS deal when some deal clears every threshold, and the Maximum-Nash-Welfare deal otherwise.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tables` | [GameTables](../oracle_context/GameTables.md) | *required* |  |
