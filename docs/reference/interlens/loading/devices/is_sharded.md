# `is_sharded`

True if `model` was placed by `device_map=` across more than one device (including cpu/disk offload).

```python
is_sharded(model) -> bool
```

Defined in [`interlens.loading.devices`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/loading/devices.py#L48-L56)

Reads accelerate's `hf_device_map`, which `from_pretrained(device_map=...)` stamps on the model. A
single-entry map (everything on one device) reads as NOT sharded, because in that case `model.device` is
already the right answer everywhere.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` |  | *required* |  |
