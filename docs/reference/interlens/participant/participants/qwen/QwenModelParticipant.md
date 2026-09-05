# `QwenModelParticipant`

A participant in a conversation that is a Qwen language model.

```python
QwenModelParticipant()
```

Defined in [`interlens.participant.participants.qwen`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/qwen.py#L20-L25)

**Inherits from:** [ModelParticipant](../model_participant/ModelParticipant.md)

Its tool-call format is the Hermes/base
`<tool_call>` JSON already handled by `ModelParticipant`, so this class adds no behavior — it exists so
Qwen models resolve to a distinct, statically-typed participant class.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `MODEL_TYPES` | `frozenset[str]` |  |
