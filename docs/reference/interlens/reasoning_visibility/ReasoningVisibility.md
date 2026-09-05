# `ReasoningVisibility`

Controls whether a participant's prior `<think>` reasoning is re-injected into views on later turns.

```python
ReasoningVisibility()
```

Defined in [`interlens.reasoning_visibility`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/reasoning_visibility.py#L21-L39)

**Inherits from:** `str`, `Enum`

Reasoning is always parsed out of `Message.content` into `metadata['parsed_think']` (so it is available
for interpretability regardless of this setting). This enum only governs *history re-injection*:

- `STRIP` (default): prior reasoning is dropped from all views — matches R1/Qwen3 chat templates, keeps
  reasoning a genuinely private scratchpad the other participant never sees, and is always template-safe.
- `SELF_RETAIN`: a participant sees its *own* prior reasoning re-injected into its view (visible-scratchpad
  self-continuation experiments).
- `SHARED`: all participants see all prior reasoning (shared-CoT collaboration/debate experiments).

Non-STRIP modes re-inject reasoning as tagged text at render time so templates that reject a native prior
`<think>` turn don't error.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `SELF_RETAIN` |  |  |
| `SHARED` |  |  |
| `STRIP` |  |  |
