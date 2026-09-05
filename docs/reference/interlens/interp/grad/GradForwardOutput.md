# `GradForwardOutput`

Result of `forward_with_grad`: grad-connected `logits` (`[batch, seq, vocab]`) and, if a `GradCaptureSpec` was passed, `hidden` mapping `(site, layer) -> tensor[batch, seq, d_model]` (also grad-connected).

```python
GradForwardOutput()
```

Defined in [`interlens.interp.grad`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/grad.py#L60-L66)

**Inherits from:** `NamedTuple`

`hidden` is empty when no capture was requested.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `hidden` | `dict[tuple[Site, int], torch.Tensor]` |  |
| `logits` | `torch.Tensor` |  |
