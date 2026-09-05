# `summarize_turns`

Roll a list of turn annotations up into a `DivergenceSummary` (shared by `annotate.py` and the inline-rows reader so the summary math lives in one place).

```python
summarize_turns(
	episode_id: str,
	model: str,
	arm: str,
	outcome: dict,
	turn_anns: list[TurnAnnotation],
	threshold: float,
) -> DivergenceSummary
```

Defined in [`interlens.arena.negotiation.analysis.annotations`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/analysis/annotations.py#L116-L131)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `episode_id` | `str` | *required* |  |
| `model` | `str` | *required* |  |
| `arm` | `str` | *required* |  |
| `outcome` | `dict` | *required* |  |
| `turn_anns` | list[[TurnAnnotation](TurnAnnotation.md)] | *required* |  |
| `threshold` | `float` | *required* |  |
