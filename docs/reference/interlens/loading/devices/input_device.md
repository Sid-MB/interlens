# `input_device`

The device to place `input_ids` on for `model`: its input embedding's device.

```python
input_device(model) -> torch.device
```

Defined in [`interlens.loading.devices`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/loading/devices.py#L59-L85)

Resolution order, each step falling through on failure so this never raises on an exotic model:

1. `model.get_input_embeddings()`'s first parameter/buffer — correct under any `device_map`, and equal
   to the model's single device when there is no sharding.
2. `model.device` — the historical answer, kept for models that expose no input embedding (mocks, some
   wrappers).
3. the first parameter's device.

Returns a `torch.device` (never a string), so callers can compare and `.to()` it directly.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` |  | *required* |  |
