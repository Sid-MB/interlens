# `anthropic_reasoning`

Extract the reasoning record from an Anthropic `content` block list: `(reasoning_text, provenance)`.

```python
anthropic_reasoning(content_blocks) -> tuple[str | None, str]
```

Defined in [`interlens.participant.participants.api_client`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_client.py#L94-L107)

`thinking` blocks are persisted verbatim as returned — but current Claude models return **summarized**
thinking over the API, and `redacted_thinking` blocks carry no readable text at all, so any
thinking-bearing response is marked `withheld_or_summarized` rather than `full`: the model's actual
reasoning stream is longer than what the provider hands back. No thinking blocks → `none`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `content_blocks` |  | *required* |  |
