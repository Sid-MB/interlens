# `sheet_json`

A seat's private score sheet as the dock renders it: `{agent, values, threshold}`.

```python
sheet_json(sheet: Any) -> dict
```

Defined in [`interlens.arena.live.human`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/human.py#L173-L178)

Sent to exactly one
browser — the person playing this seat — which is the whole point of a private sheet.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `sheet` | `Any` | *required* |  |
