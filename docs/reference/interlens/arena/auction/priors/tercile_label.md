# `tercile_label`

Which of :data:`TERCILE_LABELS` the realization `x` falls in, against the public boundaries of `N(0, sigma^2)`.

```python
tercile_label(x: float, sigma: float) -> str
```

Defined in [`interlens.arena.auction.priors`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/auction/priors.py#L82-L89)

This is the whole content of the "unusually strong capital position this cycle"
private fact: the label is private, the boundaries are public.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `x` | `float` | *required* |  |
| `sigma` | `float` | *required* |  |
