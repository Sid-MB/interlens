# `default_thinking`

The thinking mode a seat on this model starts in: the first of :data:`THINKING_PREFERENCE` the model accepts, falling back to its first declared mode if it accepts none of them (a provider free to invent mode names must still get a mode that model can take).

```python
default_thinking(model: Any) -> str
```

Defined in [`interlens.arena.live.provider`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/live/provider.py#L72-L80)

`model` is a :class:`ModelInfo` or its wire dict; a
missing model resolves to `"off"`, the only mode every backend has.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `Any` | *required* |  |
