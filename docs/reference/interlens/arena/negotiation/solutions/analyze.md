# `analyze`

The precomputed per-instance analysis dict every generated game ships with.

```python
analyze(
	space: DealSpace,
	sheets: tuple[ScoreSheet, ...] | list[ScoreSheet],
	acceptable_mask: np.ndarray | None = None,
) -> dict
```

Defined in [`interlens.arena.negotiation.solutions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L388-L432)

Contains: `deal_space_size` |D|, `n_parties`, `pareto_count`, `ir_count` |IR|, `ir_pareto_count`
|IR∩Pareto|, `ir_pareto_fraction` |IR∩Pareto|/|IR| (how near-zero-sum the acceptable set is),
`dominated_acceptable_fraction` = 1 - that (the central score-sheet-repair target [reproA2025]),
`empty_ir`, `ideal_surplus` (over IR), the score-sheet descriptors `sparsity` and `pairwise_iou`
[reproB_tmlr], and every solution point under `solutions`. Pass `acceptable_mask` to score the fraction
against a custom agreement rule (e.g. `GameSpec.feasible_mask`); default is unanimity IR (all surplus >=
0). Fully JSON-serializable.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `space` | [DealSpace](../space/DealSpace.md) | *required* |  |
| `sheets` | tuple[[ScoreSheet](../sheets/ScoreSheet.md), ...] \| list[[ScoreSheet](../sheets/ScoreSheet.md)] | *required* |  |
| `acceptable_mask` | `np.ndarray \| None` | `None` |  |
