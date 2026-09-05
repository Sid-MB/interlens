# `ir_mask`

Boolean `(|D|,)` mask of individually rational (acceptable) deals: every party's surplus is `>= 0` (`strict=True` requires `> 0`, the domain of the product solutions).

```python
ir_mask(U: np.ndarray, tau: np.ndarray, strict: bool = False) -> np.ndarray
```

Defined in [`interlens.arena.negotiation.solutions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L154-L159)

An empty mask means "no deal" is the
rational outcome (Nash 1950 p.158 -- the disagreement point) [nash1950].

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `U` | `np.ndarray` | *required* |  |
| `tau` | `np.ndarray` | *required* |  |
| `strict` | `bool` | `False` |  |
