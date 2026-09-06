# `model_cache`

Module `interlens.loading.model_cache`

## Functions

| Name | Summary |
|---|---|
| [`cached_model`](cached_model.md) | Return the cached model for `key`, running `loader()` at most once even under concurrent callers. |
| [`cached_tokenizer`](cached_tokenizer.md) | Return the cached tokenizer for `tok_id`, running `loader()` at most once even under concurrent callers (same double-checked per-key locking as :func:`cached_model`). |
| [`free`](free.md) | Drop both caches and reclaim GPU memory. |
