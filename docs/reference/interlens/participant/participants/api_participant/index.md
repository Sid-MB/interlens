# `api_participant`

Module `interlens.participant.participants.api_participant`

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `MAX_CACHE_BREAKPOINTS` |  |  |
| `MIN_CACHEABLE_PREFIX_NOTE` |  |  |
| `OpenRouterQuantization` |  |  |
| `Provider` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`APIParticipant`](APIParticipant.md) | A participant backed by a hosted API — Claude via `anthropic` (`provider="anthropic"`, the default) or any model behind OpenRouter (`provider="openrouter"`, OpenAI-compatible) — for use as a debate opponent, moderator, or the classifier inside an `analyze` callback. |
| [`OpenRouterRouting`](OpenRouterRouting.md) | Reproducible OpenRouter routing for research. |
| [`PromptCache`](PromptCache.md) | Where to put a request's `cache_control` breakpoints — Anthropic only. |
