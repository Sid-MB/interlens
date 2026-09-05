# `forward_with_grad`

One grad-connected forward pass over `input_ids` XOR `inputs_embeds`.

```python
forward_with_grad(
	model: 'PreTrainedModel',
	*,
	input_ids: torch.Tensor | None = None,
	inputs_embeds: torch.Tensor | None = None,
	attention_mask: torch.Tensor | None = None,
	capture: GradCaptureSpec | None = None,
	checkpoint: bool = False,
) -> GradForwardOutput
```

Defined in [`interlens.interp.grad`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/grad.py#L69-L140)

Exactly one of `input_ids` (`[batch, seq]` long) or `inputs_embeds` (`[batch, seq, d_model]` float,
typically the output of `bridge.soft_embed` or a learnable soft prompt) must be given. `attention_mask` is
optional (`[batch, seq]`). Returns `logits` and any requested hidden activations, all still attached to the
graph so `.backward()` flows back to `inputs_embeds` / soft-prompt params / an upstream model A.

`checkpoint=True` enables HF gradient checkpointing for this call (`use_reentrant=False`) and restores the
prior setting afterwards; it recomputes layer activations on the backward pass to trade compute for memory, and
produces identical gradients. Residual sites come from `output_hidden_states` (grad-connected); `attn`/`mlp`
sites come from non-detaching forward hooks on the submodules.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `'PreTrainedModel'` | *required* |  |
| `input_ids` | `torch.Tensor \| None` | `None` |  |
| `inputs_embeds` | `torch.Tensor \| None` | `None` |  |
| `attention_mask` | `torch.Tensor \| None` | `None` |  |
| `capture` | [GradCaptureSpec](GradCaptureSpec.md) \| None | `None` |  |
| `checkpoint` | `bool` | `False` |  |
