# `all_solutions`

Compute every solution concept for a game, returning `{concept_name: SolutionPoint}`.

```python
all_solutions(
	space: DealSpace,
	sheets: tuple[ScoreSheet, ...] | list[ScoreSheet],
) -> dict[str, SolutionPoint]
```

Defined in [`interlens.arena.negotiation.solutions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L380-L385)

Builds the utility
matrix once and reuses it.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `space` | [DealSpace](../space/DealSpace.md) | *required* |  |
| `sheets` | tuple[[ScoreSheet](../sheets/ScoreSheet.md), ...] \| list[[ScoreSheet](../sheets/ScoreSheet.md)] | *required* |  |
