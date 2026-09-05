# `routing_stats`

Pool per-token routing into per-layer expert-usage distributions.

```python
routing_stats(
	captures: list[RoutingCapture],
	n_experts: int,
	spans: list[tuple[int, int]] | None = None,
) -> RoutingStats
```

Defined in [`interlens.interp.routing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/routing.py#L142-L175)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `captures` | list[[RoutingCapture](RoutingCapture.md)] | *required* | output of `capture_router_logits` (all layers share one token sequence). |
| `n_experts` | `int` | *required* | total routed experts (`moe_num_experts(model)`) — needed to size the histogram since a span may never touch some experts. |
| `spans` | `list[tuple[int, int]] \| None` | `None` | optional `[(start, end), ...]` token windows to restrict to (e.g. only the MoE's own generated messages, from `message_token_spans`). Default: all positions. |
