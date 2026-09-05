# `GradCaptureSpec`

What grad-connected activations to pull from `forward_with_grad` (mirrors `CaptureSpec` minus offload).

```python
GradCaptureSpec(
	sites: tuple[Site, ...] = ('residual',),
	layers: tuple[int, ...] | None = None,
)
```

Defined in [`interlens.interp.grad`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/grad.py#L47-L57)

`sites` is any of `"residual"`/`"attn"`/`"mlp"`; `layers` selects decoder-layer indices (`None` =
all). Unlike `CaptureSpec` there is no `offload` — the whole point is to keep tensors on-device and in the
autograd graph, so an intermediate-layer objective (e.g. project onto a concept direction) can be backpropagated.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `sites` | `tuple[Site, ...]` | `('residual',)` |  |
| `layers` | `tuple[int, ...] \| None` | `None` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `layers` | `tuple[int, ...] \| None` |  |
| `sites` | `tuple[Site, ...]` |  |
