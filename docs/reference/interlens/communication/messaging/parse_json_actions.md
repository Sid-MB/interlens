# `parse_json_actions`

All fenced JSON objects in `text`, parsed (malformed fences are skipped, not fatal).

```python
parse_json_actions(text: str) -> list[dict]
```

Defined in [`interlens.communication.messaging`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/communication/messaging.py#L57-L60)

Thin alias for
:func:`interlens.parsing.iter_fenced_json`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | *required* |  |
