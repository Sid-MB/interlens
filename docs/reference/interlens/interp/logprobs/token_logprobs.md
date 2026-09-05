# `token_logprobs`

Compute per-token logprobs / surprisal / entropy for a generation.

```python
token_logprobs(scores: tuple[torch.Tensor, ...], generated_ids: torch.Tensor) -> dict
```

Defined in [`interlens.interp.logprobs`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/logprobs.py#L21-L45)

`scores` is the tuple of per-step logit tensors from `model.generate(..., output_scores=True,
return_dict_in_generate=True)` (one `[vocab]` per generated token); `generated_ids` are the sampled
token ids. Returns lists suitable to drop into `Message.metadata` — scalar-per-token, so they stay small
and don't violate the "no heavy tensors in metadata" invariant.

Surprisal = -logprob (nats); entropy is the full next-token distribution entropy at each step (a readout of
the model's uncertainty, distinct from the surprisal of the token it actually emitted).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `scores` | `tuple[torch.Tensor, ...]` | *required* |  |
| `generated_ids` | `torch.Tensor` | *required* |  |
