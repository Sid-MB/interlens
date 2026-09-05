# `expected_objective`

The table objective under a posterior over the other seats' hidden sheets — what the **fairness algorithmic** agent maximizes.

```python
expected_objective(
	tables: GameTables,
	seat: int,
	expected_z: dict[int, np.ndarray],
) -> np.ndarray
```

Defined in [`interlens.arena.negotiation.fairness`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/fairness.py#L131-L166)

The acting seat's own column is exact (it holds its own sheet, so its normalized surplus is known); every
other seat's column is the posterior-expected normalized surplus supplied in `expected_z`. Any seat
missing from `expected_z` and not the acting seat is treated as fully satisfied (`z = 1`), which is the
only neutral choice: scoring it 0 would make every deal look like it satisfies nobody and would collapse
the objective to a constant.

Parameters
----------
tables : GameTables
    Tables whose `surplus` column for `seat` is populated. Under private information the other columns
    are padding (the caller's `_tables` fills them with zeros) and are deliberately never read here.
seat : int
    The acting seat, whose own normalized surplus is computed exactly from its own sheet.
expected_z : dict[int, np.ndarray]
    `{opponent_seat: (|D|,) posterior-expected normalized surplus}`, e.g. from
    :meth:`~interlens.arena.negotiation.beliefs.BeliefState.expected_normalized_surplus_matrix`.

Returns the `(|D|,)` expected objective. See the module docstring on the plug-in (Jensen) bias.

One further deviation from the full-information case, forced by the information condition: the acting
seat's normalizer is its best surplus over ALL deals, not over the IR set, because identifying the IR set
requires the thresholds it does not have. This cannot move the ranking within its own column (a positive
constant), but it does shift how its own gains trade against the opponents' in the geometric mean.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tables` | [GameTables](../oracle_context/GameTables.md) | *required* |  |
| `seat` | `int` | *required* |  |
| `expected_z` | `dict[int, np.ndarray]` | *required* |  |
