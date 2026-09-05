# `extract_json`

The last fenced JSON object in `text`, else the last balanced top-level `{...}` that parses.

```python
extract_json(text: str) -> Any | None
```

Defined in [`interlens.arena.views`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/views.py#L69-L72)

Thin alias for :func:`interlens.parsing.last_json`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | *required* |  |
