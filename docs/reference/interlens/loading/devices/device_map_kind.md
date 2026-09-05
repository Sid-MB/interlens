# `device_map_kind`

Interpret a `device` argument as a `device_map` when it names a sharding strategy, else `None`.

```python
device_map_kind(device) -> str | dict | None
```

Defined in [`interlens.loading.devices`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/loading/devices.py#L33-L45)

Accepts the strings transformers understands (`"auto"`, `"balanced"`, `"balanced_low_0"`,
`"sequential"`) and an explicit `{module: device}` dict. Anything else — `"cuda"`, `"cuda:1"`,
`"cpu"`, a `torch.device` — is an ordinary single-device placement and returns `None`, which is what
keeps the default load path unchanged.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `device` |  | *required* |  |
