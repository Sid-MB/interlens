# `normalized_surplus_matrix`

Per-deal per-party normalized surplus `z` of shape `(|D|, n)`: `clip(surplus, 0) / b_i`.

```python
normalized_surplus_matrix(tables: GameTables) -> np.ndarray
```

Defined in [`interlens.arena.negotiation.fairness`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/fairness.py#L68-L91)

`b_i` is party `i`'s largest surplus over the **individually rational** set (every party at or above
threshold) — the scale-invariant unit the whole fairness objective is expressed in, and the same
`game.scale` the analysis layer's `normalized_nash_welfare` divides by. Falls back to the max over all
deals when no deal is individually rational for everyone, and to `1.0` for a party whose best surplus is
non-positive (it can never be made better off, so dividing by its "ideal" is meaningless). Below-threshold
surpluses clip to 0 rather than going negative: they are not partial progress, they are unacceptable.

Values can exceed `1` *outside* the IR set — `b_i` is the best party `i` can do in a deal everyone
could sign, and a deal that tramples somebody else may pay `i` more than that. :func:`objective_from_normalized`
caps at 1 for exactly this reason; see its docstring.

Parameters
----------
tables : GameTables
    Precomputed dense game tables. Only `surplus` is read, so this works on any table whose surplus
    column is populated for the parties in question.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tables` | [GameTables](../oracle_context/GameTables.md) | *required* |  |
