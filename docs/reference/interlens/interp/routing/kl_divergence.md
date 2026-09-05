# `kl_divergence`

Per-layer KL(p || q) between expert distributions `[n_layers, n_experts]` → `[n_layers]`.

```python
kl_divergence(p: torch.Tensor, q: torch.Tensor, eps: float = 1e-08) -> torch.Tensor
```

Defined in [`interlens.interp.routing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/routing.py#L178-L184)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `p` | `torch.Tensor` | *required* |  |
| `q` | `torch.Tensor` | *required* |  |
| `eps` | `float` | `1e-08` |  |
