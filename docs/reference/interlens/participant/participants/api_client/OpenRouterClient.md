# `OpenRouterClient`

OpenRouter (https://openrouter.ai) via the OpenAI-compatible `openai` SDK — one endpoint proxying many providers' models (e.g. `anthropic/claude-sonnet-5`, `openai/gpt-5`, `meta-llama/llama-3.1-70b-instruct`).

```python
OpenRouterClient()
```

Defined in [`interlens.participant.participants.api_client`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/participant/participants/api_client.py#L443-L451)

**Inherits from:** `_OpenAICompatClient`

Reads `OPENROUTER_API_KEY`. OpenRouter has **no batch API**, so `submit_batch` inherits the base's raise —
requesting batch mode on an OpenRouter participant fails loudly.
