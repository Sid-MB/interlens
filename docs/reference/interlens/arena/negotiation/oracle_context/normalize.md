# `normalize`

Return a probability vector from nonnegative weights, optionally mixed with `floor` uniform mass.

```python
normalize(w: np.ndarray, floor: float = 0.0) -> np.ndarray
```

Defined in [`interlens.arena.negotiation.oracle_context`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/oracle_context.py#L169-L177)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `w` | `np.ndarray` | *required* |  |
| `floor` | `float` | `0.0` |  |
