# `js_divergence`

Per-layer Jensen–Shannon divergence (symmetric, bounded by ln 2) → `[n_layers]`.

```python
js_divergence(p: torch.Tensor, q: torch.Tensor) -> torch.Tensor
```

Defined in [`interlens.interp.routing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/routing.py#L187-L190)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `p` | `torch.Tensor` | *required* |  |
| `q` | `torch.Tensor` | *required* |  |
