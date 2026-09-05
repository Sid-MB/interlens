# `iter_tagged_json`

Every `<tag>{json}</tag>` block in `text` as `(parsed_object, raw_match)` pairs (malformed JSON skipped).

```python
iter_tagged_json(text: str | None, tag: str) -> list[tuple[dict, str]]
```

Defined in [`interlens.parsing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/parsing.py#L130-L142)

`raw_match` is the whole matched `<tag>...</tag>` substring, for provenance. Backs the base
`ModelParticipant.parse_tool_calls` (Hermes/Qwen `<tool_call>` format).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str \| None` | *required* |  |
| `tag` | `str` | *required* |  |
