# `gumbel_softmax_tokens`

Relaxed (Gumbel-softmax) sample over the last (vocab) dim of `logits`, differentiable in `logits`.

```python
gumbel_softmax_tokens(
	logits: torch.Tensor,
	tau: float = 1.0,
	hard: bool = False,
) -> torch.Tensor
```

Defined in [`interlens.interp.bridge`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/bridge.py#L57-L66)

`tau` is the temperature: high -> smooth mixture (biased but low-variance gradients), low -> near-one-hot
(faithful to discrete sampling but higher-variance). Anneal `tau` down over training to move from an easy soft
optimization toward the discrete tokens B will actually see. `hard=True` uses the straight-through estimator: a
true one-hot on the forward pass, softmax gradient on the backward pass — so the value B consumes is a real token
while gradients still flow. Returns `[..., V]` to feed straight into `soft_embed`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `logits` | `torch.Tensor` | *required* |  |
| `tau` | `float` | `1.0` |  |
| `hard` | `bool` | `False` |  |
