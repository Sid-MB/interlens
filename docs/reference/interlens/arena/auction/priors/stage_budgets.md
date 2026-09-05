# `stage_budgets`

Per-stage whole-number budgets: `budget_i = round(budget_mult_i * sum of bidder i's top-k_i values)`.

```python
stage_budgets(
	values: np.ndarray,
	capacities: np.ndarray,
	budget_mults: np.ndarray,
) -> np.ndarray
```

Defined in [`interlens.arena.auction.priors`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L288-L301)

Deterministic given the realized values, so the budget carries no information the seat does not already
have from its own value table, and a `budget_mult` below 1 makes the constraint genuinely bind on the
seat's own preferred bundle (the Che-Gale subject). Budgets are replenished each stage and never carried
(design.md §2.4).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `values` | `np.ndarray` | *required* |  |
| `capacities` | `np.ndarray` | *required* |  |
| `budget_mults` | `np.ndarray` | *required* |  |
