# `moe_num_experts`

Number of routed experts per MoE layer (`config.num_experts` — same field name in OLMoE/Qwen-MoE).

```python
moe_num_experts(model: 'PreTrainedModel') -> int
```

Defined in [`interlens.interp.routing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/routing.py#L43-L45)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `'PreTrainedModel'` | *required* |  |
