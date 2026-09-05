# `conversation_from_ids`

Deprecated thin alias for :func:`conversation_from_models` / :meth:`Conversation.from_models`, kept for back-compat.

```python
conversation_from_ids(ids: tuple[ModelLike, ...], **kwargs: Any = {}) -> Conversation
```

Defined in [`interlens.factories`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/factories.py#L141-L146)

Prefer `Conversation.from_models(models=..., ...)`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `ids` | `tuple[ModelLike, ...]` | *required* |  |
| `kwargs` | `Any` | `{}` |  |
