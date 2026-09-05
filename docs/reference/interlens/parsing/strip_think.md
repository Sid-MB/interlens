# `strip_think`

Remove `<think>...</think>` blocks ANYWHERE in `text`; return `(visible, think)`.

```python
strip_think(text: str | None) -> tuple[str, str | None]
```

Defined in [`interlens.parsing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/parsing.py#L147-L161)

The defensive strip used before content reaches another seat's view: a generation truncated mid-`<think>`
leaves an *unterminated* block whose reasoning must not leak, so everything from an orphan `<think>` on is
treated as reasoning. `think` is the joined reasoning, or `None` when there was none.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str \| None` | *required* |  |
