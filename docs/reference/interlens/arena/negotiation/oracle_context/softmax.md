# `softmax`

Tempered softmax; `temperature -> 0` approaches a hard argmax (used to break equilibrium cycles).

```python
softmax(a: np.ndarray, temperature: float = 1.0, axis=-1) -> np.ndarray
```

Defined in [`interlens.arena.negotiation.oracle_context`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/oracle_context.py#L161-L166)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `a` | `np.ndarray` | *required* |  |
| `temperature` | `float` | `1.0` |  |
| `axis` |  | `-1` |  |
