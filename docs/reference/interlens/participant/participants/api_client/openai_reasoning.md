# `openai_reasoning`

Extract the reasoning record from an OpenAI-schema `choices[0].message` (+ `usage`): `(reasoning_text, provenance)`.

```python
openai_reasoning(message, usage) -> tuple[str | None, str]
```

Defined in [`interlens.participant.participants.api_client`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_client.py#L110-L127)

Works with SDK objects and plain dicts (the batch-API path).

OpenRouter/DeepSeek-style `reasoning` / `reasoning_content` fields carry the model's raw reasoning
stream → `full`. OpenAI's own reasoning models withhold the stream but count it in
`usage.completion_tokens_details.reasoning_tokens` → `withheld_or_summarized` with no text.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `message` |  | *required* |  |
| `usage` |  | *required* |  |
