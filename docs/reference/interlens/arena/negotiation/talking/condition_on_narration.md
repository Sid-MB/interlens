# `condition_on_narration`

Fold "this package is above/below my bar" into the posterior — exactly the accept/reject evidence `observe_response` implements, with the claim's truth value playing the vote.

```python
condition_on_narration(
	bst: BeliefState,
	deal,
	above: bool,
	*,
	reliability: float = 0.85,
	strength: float = 0.6,
) -> None
```

Defined in [`interlens.arena.negotiation.talking`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/talking.py#L219-L224)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `bst` | [BeliefState](../beliefs/BeliefState.md) | *required* |  |
| `deal` |  | *required* |  |
| `above` | `bool` | *required* |  |
| `reliability` | `float` | `0.85` |  |
| `strength` | `float` | `0.6` |  |
