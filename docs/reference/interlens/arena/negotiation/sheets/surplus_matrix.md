# `surplus_matrix`

The `|D| x n` surplus matrix `U - tau`.

```python
surplus_matrix(
	space: DealSpace,
	sheets: tuple[ScoreSheet, ...] | list[ScoreSheet],
) -> np.ndarray
```

Defined in [`interlens.arena.negotiation.sheets`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/sheets.py#L351-L354)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `space` | [DealSpace](../space/DealSpace.md) | *required* |  |
| `sheets` | tuple[[ScoreSheet](ScoreSheet.md), ...] \| list[[ScoreSheet](ScoreSheet.md)] | *required* |  |
