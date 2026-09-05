# `nash_welfare`

Nash social welfare `NSW = prod x_i` when every surplus is strictly positive, else `0.0`.

```python
nash_welfare(x: 'Sequence[float]') -> float
```

Defined in [`interlens.arena.negotiation.solutions`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/solutions.py#L80-L93)

The Nash objective is `argmax prod x_i` over strictly-IR deals, so a party at or below its threshold is by
convention outside the Nash set and contributes zero rather than a negative or spurious product — matching
the discrete-NBS convention in :func:`max_nash_welfare_index`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `x` | `'Sequence[float]'` | *required* |  |
