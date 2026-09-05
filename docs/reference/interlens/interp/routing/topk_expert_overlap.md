# `topk_expert_overlap`

Per-layer fraction of overlap between the `k` most-used experts of `p` and of `q` → `[n_layers]`.

```python
topk_expert_overlap(p: torch.Tensor, q: torch.Tensor, k: int = 8) -> torch.Tensor
```

Defined in [`interlens.interp.routing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/routing.py#L193-L200)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `p` | `torch.Tensor` | *required* |  |
| `q` | `torch.Tensor` | *required* |  |
| `k` | `int` | `8` |  |
