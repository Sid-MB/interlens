# `LinearBridge`

Learned linear map from model A's hidden width `d_a` to model B's embedding width `d_b`.

```python
LinearBridge(d_a: int, d_b: int, bias: bool = False)
```

Defined in [`interlens.interp.bridge`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/bridge.py#L69-L85)

**Inherits from:** `nn.Module`

For heterogeneous (different-tokenizer) pairs where a vocab mixture is undefined: take A's last-layer hidden
states (via `forward_with_grad(..., capture=GradCaptureSpec(sites=('residual',), layers=(last,)))`), map them
into B's embedding space, and pass the result as `inputs_embeds` to B. Trained jointly with A against B's loss.
`bias=False` by default to match the (linear, origin-preserving) cross-model maps used in the Procrustes work.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `d_a` | `int` | *required* |  |
| `d_b` | `int` | *required* |  |
| `bias` | `bool` | `False` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `proj` |  |  |

## Methods {#methods}

## `forward` {#forward}

```python
forward(self, hidden: torch.Tensor) -> torch.Tensor
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/bridge.py#L82-L85)

`[batch, seq, d_a] -> [batch, seq, d_b]` soft embeddings in B's input space.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `hidden` | `torch.Tensor` | *required* |  |
