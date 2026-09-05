# `CaptureSpec`

What to capture during a generation: which `sites` at which `layers`, and where to keep the tensors.

```python
CaptureSpec(
	sites: tuple[Site, ...] = ('residual',),
	layers: tuple[int, ...] | None = None,
	offload: OffloadLocation = 'cpu',
)
```

Defined in [`interlens.interp.activation_cache`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/activation_cache.py#L56-L67)

Capture defaults to a *narrow* set — you pass the layers/sites you actually want — because capturing all
layers × all tokens × many rollouts OOMs fast. `offload='cpu'` moves captured tensors off-GPU as they are
recorded (essential for large sweeps); `offload=None` keeps them on-device.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `sites` | `tuple[Site, ...]` | `('residual',)` |  |
| `layers` | `tuple[int, ...] \| None` | `None` |  |
| `offload` | `OffloadLocation` | `'cpu'` |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `layers` | `tuple[int, ...] \| None` |  |
| `offload` | `OffloadLocation` |  |
| `sites` | `tuple[Site, ...]` |  |
