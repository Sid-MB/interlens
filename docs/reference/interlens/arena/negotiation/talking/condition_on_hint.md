# `condition_on_hint`

Fold declared per-issue top options into the posterior: types whose evaluator peaks at the declared option on that issue match the claim (likelihood `reliability`), the rest `1 - reliability`, tempered by `strength` and the state's own damping `lam`.

```python
condition_on_hint(
	bst: BeliefState,
	tops: dict,
	*,
	reliability: float = 0.85,
	strength: float = 0.6,
) -> None
```

Defined in [`interlens.arena.negotiation.talking`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L227-L237)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `bst` | [BeliefState](../beliefs/BeliefState.md) | *required* |  |
| `tops` | `dict` | *required* |  |
| `reliability` | `float` | `0.85` |  |
| `strength` | `float` | `0.6` |  |
