# `api_client`

Module `interlens.participant.participants.api_client`

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `REASONING_FULL` |  |  |
| `REASONING_NONE` |  |  |
| `REASONING_WITHHELD` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`AnthropicClient`](AnthropicClient.md) | Claude via the `anthropic` SDK (the default provider). |
| [`Completion`](Completion.md) | A completion string that also carries the call's **usage telemetry** as attributes: `input_tokens` / `output_tokens` (0 when the provider reported none), `stop_reason` (the provider's native stop/finish reason, `None` when unreported), `batched` (served via a provider batch API at discount pricing), `cache_read_tokens` / `cache_write_tokens` (Anthropic prompt-cache accounting: tokens served from a cache entry, and tokens written into one — both EXCLUDED from `input_tokens`, which is the full-price remainder), and the call's **reasoning record**: `reasoning` (whatever reasoning text the provider returned — Anthropic thinking blocks including summarized ones, OpenAI-compatible `reasoning`/`reasoning_content` fields — or `None`) with `reasoning_provenance` marking how complete that record is (see the marker constants above). |
| [`OpenAIClient`](OpenAIClient.md) | OpenAI directly via the `openai` SDK (`provider="openai"`). |
| [`OpenRouterClient`](OpenRouterClient.md) | OpenRouter (https://openrouter.ai) via the OpenAI-compatible `openai` SDK — one endpoint proxying many providers' models (e.g. `anthropic/claude-sonnet-5`, `openai/gpt-5`, `meta-llama/llama-3.1-70b-instruct`). |

## Functions

| Name | Summary |
|---|---|
| [`anthropic_reasoning`](anthropic_reasoning.md) | Extract the reasoning record from an Anthropic `content` block list: `(reasoning_text, provenance)`. |
| [`openai_reasoning`](openai_reasoning.md) | Extract the reasoning record from an OpenAI-schema `choices[0].message` (+ `usage`): `(reasoning_text, provenance)`. |
