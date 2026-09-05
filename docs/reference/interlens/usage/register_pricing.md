# `register_pricing`

Register (or override) the $/Mtok pricing for `model_id`, process-wide.

```python
register_pricing(model_id: str, *, input_per_mtok: float, output_per_mtok: float) -> None
```

Defined in [`interlens.usage`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/usage.py#L78-L81)

Meters constructed afterwards
pick it up; a meter-local `pricing=` table still wins for that meter.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model_id` | `str` | *required* |  |
| `input_per_mtok` | `float` | *required* |  |
| `output_per_mtok` | `float` | *required* |  |
