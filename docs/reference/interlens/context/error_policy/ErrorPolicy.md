# `ErrorPolicy`

The safe default: raise if the view exceeds the context window rather than silently dropping content.

```python
ErrorPolicy()
```

Defined in [`interlens.context.error_policy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/context/error_policy.py#L22-L37)

**Inherits from:** [ContextPolicy](../context_policy/ContextPolicy.md)

Silent truncation reads as "everything fit" when it didn't, which is exactly the kind of quiet data loss this
harness avoids. Callers who want trimming opt into `DropOldestPolicy`/`SlidingWindowPolicy` explicitly.

## Methods {#methods}

## `fit` {#fit}

```python
fit(self, segments: list[ViewSegment], tokenizer, limit: int | None) -> list[ViewSegment]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/context/error_policy.py#L29-L37)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `segments` | list[[ViewSegment](../../view/ViewSegment.md)] | *required* |  |
| `tokenizer` |  | *required* |  |
| `limit` | `int \| None` | *required* |  |
