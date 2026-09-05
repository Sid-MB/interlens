# `resolve_pricing`

The effective pricing table: bundled defaults, overlaid with `register_pricing` entries, overlaid with the caller's `pricing` dict (each value `{"in": $/Mtok, "out": $/Mtok}`).

```python
resolve_pricing(pricing: dict | None = None) -> dict[str, dict[str, float]]
```

Defined in [`interlens.usage`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/usage.py#L84-L91)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `pricing` | `dict \| None` | `None` |  |
