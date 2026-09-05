# `DropOldestPolicy`

Drop the oldest `turn` segments (preserving system/moderator/private_context) until the view fits.

```python
DropOldestPolicy()
```

Defined in [`interlens.context.drop_oldest_policy`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/context/drop_oldest_policy.py#L22-L47)

**Inherits from:** [ContextPolicy](../context_policy/ContextPolicy.md)

## Methods {#methods}

## `fit` {#fit}

```python
fit(self, segments: list[ViewSegment], tokenizer, limit: int | None) -> list[ViewSegment]
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/context/drop_oldest_policy.py#L25-L47)

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `segments` | list[[ViewSegment](../../view/ViewSegment.md)] | *required* |  |
| `tokenizer` |  | *required* |  |
| `limit` | `int \| None` | *required* |  |
