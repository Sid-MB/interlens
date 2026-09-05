# `span_pooled_residuals`

One pooled activation vector **per message** of `view`, at each requested site/layer.

```python
span_pooled_residuals(
	model: 'PreTrainedModel',
	tokenizer: 'PreTrainedTokenizerBase',
	view: list[dict],
	*,
	layers: int | Iterable[int] | None,
	sites: tuple[Site, ...] = ('residual',),
	pool: Pool = 'mean',
	grad: bool = False,
) -> dict[tuple[Site, int], torch.Tensor]
```

Defined in [`interlens.interp.softtokens`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/softtokens.py#L234-L283)

Renders `view` once with the chat template, locates each message's token span with
`routing.message_token_spans` (prefix-diffing the rendered strings, so spans include each message's role
markup), runs a single forward pass, and pools each span down to one vector. Returns
`{(site, layer): tensor[n_messages, d_model]}` — keyed like `forward_with_grad`'s `hidden`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `'PreTrainedModel'` | *required* | the model to read; must accept `input_ids` (no generation happens here). |
| `tokenizer` | `'PreTrainedTokenizerBase'` | *required* | supplies the chat template used for both the render and the spans. |
| `view` | `list[dict]` | *required* | the conversation as chat-template dicts (`[{"role": ..., "content": ...}, ...]`). |
| `layers` | `int \| Iterable[int] \| None` | *required* | decoder-layer index, iterable of indices, or `None` for every layer. Negative indices count from the end (`-1` = last layer), so `layers=(-1,)` is "the usual readout layer" without knowing depth. |
| `sites` | `tuple[Site, ...]` | `('residual',)` | any of `"residual"`/`"attn"`/`"mlp"`. `"residual"` is the probe default; the sublayer sites are there when you want to attribute a readout to attention vs MLP. |
| `pool` | `Pool` | `'mean'` | `"mean"` or `"last"`, forwarded to :func:`~interlens.interp.pooling.span_pool` — mean averages the span's tokens (stable, order-insensitive; the probe default), last takes the span's final token (the position that causally sees the whole message, and what a next-token readout conditions on). |
| `grad` | `bool` | `False` | `False` runs the detached `capture_activations` pass (cheap, inference-mode) — right for fitting a probe on frozen features. `True` routes through `forward_with_grad` so the pooled vectors stay in the autograd graph — required when they feed a trainable bridge/soft prompt that is optimized end to end. |
