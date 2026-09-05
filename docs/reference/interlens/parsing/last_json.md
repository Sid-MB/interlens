# `last_json`

The LAST fenced JSON object in `text`, else the last balanced top-level `{...}` that parses, else `None`. "Last wins" because a model's final fenced block is its committed action when it revised mid-turn.

```python
last_json(text: str | None) -> Any | None
```

Defined in [`interlens.parsing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/parsing.py#L80-L107)

Backs the arena's `extract_json`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str \| None` | *required* |  |
