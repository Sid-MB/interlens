# `first_think_block`

The first complete `<think>...</think>` block's inner reasoning, or `None`.

```python
first_think_block(text: str | None) -> str | None
```

Defined in [`interlens.parsing`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/parsing.py#L174-L178)

A detection helper for
leak gates that need the fragment itself (`arena.gates.check_reasoning_leak`).

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str \| None` | *required* |  |
