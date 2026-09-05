# `continuation_logprob`

Differentiable teacher-forced logprob of `target_ids` continuing a prefix, under `model`.

```python
continuation_logprob(
	model: 'PreTrainedModel',
	*,
	target_ids: torch.Tensor,
	prefix_ids: torch.Tensor | None = None,
	prefix_embeds: torch.Tensor | None = None,
	attention_mask: torch.Tensor | None = None,
	reduction: str = 'mean',
	checkpoint: bool = False,
) -> torch.Tensor
```

Defined in [`interlens.interp.grad`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/grad.py#L143-L201)

The grad-enabled analog of `train_to_steer/rl_elicit.py::cont_logprob` (which is `@torch.no_grad` and returns
a float). Supply the prefix as `prefix_ids` (`[batch, P]` long) OR `prefix_embeds` (`[batch, P, d_model]`
float — e.g. a learnable soft prompt, or soft embeddings bridged from model A). `target_ids` is `[batch, T]`
long (or `[T]` broadcast to batch 1). The prefix and target are embedded via `model.get_input_embeddings()`
and run in one forward; the returned scalar (or per-example vector, see `reduction`) is the logprob the model
assigns to the exact target tokens, still attached to the graph.

`reduction`: `"mean"` (mean over target tokens, mean over batch -> scalar; the reward used by rl_elicit),
`"sum"` (sum over target tokens, mean over batch), or `"none"` (`[batch, T]` per-token logprobs). Use
`"mean"` as a length-normalized elicitation reward, `"sum"` when total sequence likelihood matters, `"none"`
for custom weighting. `checkpoint` is forwarded to save memory when backpropagating through a large frozen B.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `'PreTrainedModel'` | *required* |  |
| `target_ids` | `torch.Tensor` | *required* |  |
| `prefix_ids` | `torch.Tensor \| None` | `None` |  |
| `prefix_embeds` | `torch.Tensor \| None` | `None` |  |
| `attention_mask` | `torch.Tensor \| None` | `None` |  |
| `reduction` | `str` | `'mean'` |  |
| `checkpoint` | `bool` | `False` |  |
