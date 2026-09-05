# `CaptureRequest`

A pending capture handed to `generate`: where to store records (`cache`) and what to grab (`spec`).

```python
CaptureRequest(cache: ActivationCache, spec: CaptureSpec)
```

Defined in [`interlens.interp.capture`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/interp/capture.py#L40-L48)

The `Conversation` builds this (via `conv.capture(...)`) and the participant fills the cache with records
tagged by participant + turn, so the caller ends up with structurally-tagged activations.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `cache` | [ActivationCache](../activation_cache/ActivationCache.md) | *required* |  |
| `spec` | [CaptureSpec](../activation_cache/CaptureSpec.md) | *required* |  |

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `cache` | [ActivationCache](../activation_cache/ActivationCache.md) |  |
| `spec` | [CaptureSpec](../activation_cache/CaptureSpec.md) |  |
