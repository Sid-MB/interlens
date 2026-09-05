# `split_leading_think`

Split a raw completion into `(visible_content, parsed_think)` on a LEADING `<think>...</think>` block only (the participant-level convention).

```python
split_leading_think(text: str) -> tuple[str, str | None]
```

Defined in [`interlens.parsing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/parsing.py#L164-L171)

No leading block → `(text.strip(), None)`. Backs the base
`ModelParticipant.split_reasoning`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | *required* |  |
