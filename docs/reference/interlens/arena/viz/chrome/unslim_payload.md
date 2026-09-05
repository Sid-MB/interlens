# `unslim_payload`

The inverse of :func:`slim_payload`: pooled view indices back to full `{role, content}` messages.

```python
unslim_payload(payload: dict) -> dict
```

Defined in [`interlens.arena.viz.chrome`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/viz/chrome.py#L99-L118)

A published page embeds the SLIMMED payload, so this is what makes an already-written page re-renderable — the
only way to refresh a page whose original run directory is gone. A payload that carries no `msgpool` is
already inflated and is returned unchanged, so the call is safe to make unconditionally.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict` | *required* |  |
