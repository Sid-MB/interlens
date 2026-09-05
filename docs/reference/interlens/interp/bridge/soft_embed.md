# `soft_embed`

Mix `model`'s input-embedding rows by a per-position distribution: `[..., V] @ E[V, d] -> [..., d]`.

```python
soft_embed(model: 'PreTrainedModel', probs: torch.Tensor) -> torch.Tensor
```

Defined in [`interlens.interp.bridge`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/bridge.py#L45-L54)

`probs` is a (relaxed or one-hot) distribution over `model`'s vocab for each position — e.g. a softmax /
`gumbel_softmax_tokens` output of an upstream model. Returns grad-connected soft embeddings suitable to pass as
`inputs_embeds` to `forward_with_grad` / `continuation_logprob`. This is exact for hard one-hots: feeding
`one_hot(ids)` reproduces `model.get_input_embeddings()(ids)`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `'PreTrainedModel'` | *required* |  |
| `probs` | `torch.Tensor` | *required* |  |
