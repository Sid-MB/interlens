# `LlamaModelParticipant`

A Llama-family participant.

```python
LlamaModelParticipant()
```

Defined in [`interlens.participant.participants.llama`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/llama.py#L26-L60)

**Inherits from:** [ModelParticipant](../model_participant/ModelParticipant.md)

Chat-template flags are auto-derived from the tokenizer; only the tool-call
format differs from base: Llama 3 emits calls as `<|python_tag|>{json}` rather than Hermes/Qwen
`<tool_call>` blocks.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `MODEL_TYPES` | `frozenset[str]` |  |

## Methods {#methods}

## `parse_tool_calls` {#parse_tool_calls}

```python
parse_tool_calls(self, text: str) -> list
```

[source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/llama.py#L33-L60)

Parse Llama-3's `<|python_tag|>{json}` function-call format (best-effort).

Everything after `<|python_tag|>` is one or more JSON objects (separated by newlines or semicolons),
each `{"name": ..., "arguments"/"parameters": {...}}`. Anything unparseable is skipped, so a malformed
call yields `[]` (treated as a final message), matching the base contract of never misfiring.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | *required* |  |
