# `moe_layer_indices`

Decoder-layer indices that carry a sparse MoE block.

```python
moe_layer_indices(model: 'PreTrainedModel') -> tuple[int, ...]
```

Defined in [`interlens.interp.routing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/routing.py#L53-L68)

HF MoE models return `router_logits` only for the *sparse* layers, in layer order, with no index
attached. This maps that tuple back to real decoder-layer indices by checking each layer's `mlp` for a
router `gate` submodule — which handles mixed stacks (e.g. Qwen-MoE `decoder_sparse_step` /
`mlp_only_layers` leaving some layers dense) as well as fully-sparse stacks like OLMoE.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `'PreTrainedModel'` | *required* |  |
