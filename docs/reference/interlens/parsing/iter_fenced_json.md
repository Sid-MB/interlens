# `iter_fenced_json`

Every parseable fenced JSON OBJECT in `text`, in order (malformed fences skipped, not fatal).

```python
iter_fenced_json(text: str | None) -> list[dict]
```

Defined in [`interlens.parsing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/parsing.py#L67-L77)

The fence
regex captures `{...}` only — structured actions are always objects — so a stray fenced list/number is
ignored, not mistaken for an action. Backs `MessagingPolicy.parse_json_actions`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str \| None` | *required* |  |
