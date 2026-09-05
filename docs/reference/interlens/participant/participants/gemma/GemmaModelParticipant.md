# `GemmaModelParticipant`

A Gemma-family participant.

```python
GemmaModelParticipant()
```

Defined in [`interlens.participant.participants.gemma`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/gemma.py#L26-L61)

**Inherits from:** [ModelParticipant](../model_participant/ModelParticipant.md)

The only thing that differs from base is the tool-call format
(```` ```tool_code ````); the chat-template flags (Gemma 2 rejects a standalone `system` role and requires
strict user/model alternation, Gemma 3 accepts a system role) are auto-derived from the tokenizer's own
template, so both generations use this one class.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `MODEL_TYPES` | `frozenset[str]` |  |

## Methods {#methods}

## `parse_tool_calls` {#parse_tool_calls}

```python
parse_tool_calls(self, text: str) -> list
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/gemma.py#L34-L61)

Parse Gemma's ```` ```tool_code ```` function-call blocks (best-effort).

Gemma emits calls like ```` ```tool_code
name(arg="x", n=2)
``` ```` rather than Hermes JSON. We extract
                the block, then the function name and simple keyword arguments. Falls back to `[]` (treat as final
                message) on anything it can't parse, matching the base contract of never misfiring silently.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | *required* |  |
