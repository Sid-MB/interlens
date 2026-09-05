# `capture_activations`

Run one clean forward pass over `input_ids` and return `[(layer, site, tensor[seq, d_model])]`.

```python
capture_activations(
	model: 'PreTrainedModel',
	input_ids: torch.Tensor,
	spec: CaptureSpec,
) -> list[CapturedSite]
```

Defined in [`interlens.interp.capture`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/capture.py#L51-L100)

Design choice: capture is a *separate forward pass* over the full (prompt + generated) sequence rather than
accumulating hooks across the multi-step decode loop. This is simpler and provably complete — every position
is present in one pass — at the cost of one extra forward. Residual-stream activations come from
`output_hidden_states` (no hooks needed); `attn`/`mlp` sublayer outputs come from forward hooks on the
corresponding submodules.

Note: `attn` captures the attention *sublayer output* (post-o_proj), which is available under any attention
backend. Attention *weights/patterns* are NOT captured here — those require `attn_implementation='eager'` +
`output_attentions` and are out of scope for the default kernel.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `'PreTrainedModel'` | *required* |  |
| `input_ids` | `torch.Tensor` | *required* |  |
| `spec` | [CaptureSpec](../activation_cache/CaptureSpec.md) | *required* |  |
