# `cached_model`

Return the cached model for `key`, running `loader()` at most once even under concurrent callers.

```python
cached_model(key: tuple, loader)
```

Defined in [`interlens.loading.model_cache`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/loading/model_cache.py#L55-L69)

Double-checked locking: the fast path is a lock-free `dict.get` (atomic under the GIL) once the model is
cached; a miss takes the per-key lock and re-checks, so the loader runs exactly once and every caller gets
the same fully-materialized object. The key is published only AFTER `loader()` returns, so no thread ever
observes a partially-`.to()`'d model.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `key` | `tuple` | *required* |  |
| `loader` |  | *required* |  |
