# `capture_router_logits`

One clean forward pass over `input_ids` (`[1, seq]`); return per-MoE-layer `RoutingCapture`.

```python
capture_router_logits(
	model: 'PreTrainedModel',
	input_ids: torch.Tensor,
	layers: tuple[int, ...] | None = None,
	top_k_only: bool = False,
	offload: str = 'cpu',
) -> list[RoutingCapture]
```

Defined in [`interlens.interp.routing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/routing.py#L85-L122)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `'PreTrainedModel'` | *required* | an HF MoE causal LM whose `forward` accepts `output_router_logits=True` (OLMoE, Qwen-MoE, Mixtral, ...). |
| `input_ids` | `torch.Tensor` | *required* | full token sequence to route, shape `[1, seq]` (batch of 1 — replay one view at a time). |
| `layers` | `tuple[int, ...] \| None` | `None` | decoder-layer indices to keep (default: all sparse layers, per `moe_layer_indices`). |
| `top_k_only` | `bool` | `False` | drop the full `[seq, n_experts]` logits and keep only top-k ids/probs (int16/fp16, ~8x smaller — use for long-sequence sweeps over large MoEs like Qwen3-30B-A3B). |
| `offload` | `str` | `'cpu'` | device for the returned tensors (default `"cpu"` so GPU memory is freed immediately). |
