# `RoutingCapture`

Per-token routing at one MoE layer, from one `capture_router_logits` pass.

```python
RoutingCapture()
```

Defined in [`interlens.interp.routing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/routing.py#L71-L82)

**Inherits from:** `NamedTuple`

`router_logits` is the raw pre-softmax gate output `[seq, n_experts]` (cpu fp32), or `None` when the
capture was compacted with `top_k_only=True`. `topk_experts` / `topk_probs` are always present: the
`k` selected expert ids (int16) and their softmax router probabilities (fp16), `[seq, k]` each.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `layer` | `int` |  |
| `router_logits` | `torch.Tensor \| None` |  |
| `topk_experts` | `torch.Tensor` |  |
| `topk_probs` | `torch.Tensor` |  |
