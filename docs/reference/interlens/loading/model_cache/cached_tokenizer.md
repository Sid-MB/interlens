# `cached_tokenizer`

Return the cached tokenizer for `tok_id`, running `loader()` at most once even under concurrent callers (same double-checked per-key locking as :func:`cached_model`).

```python
cached_tokenizer(tok_id: str, loader)
```

Defined in [`interlens.loading.model_cache`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/loading/model_cache.py#L72-L82)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `tok_id` | `str` | *required* |  |
| `loader` |  | *required* |  |
