# `participants`

Package `interlens.participant.participants`

## Modules

- [`api_client`](api_client/index.md)
- [`api_participant`](api_participant/index.md)
- [`gemma`](gemma/index.md)
- [`llama`](llama/index.md)
- [`model_participant`](model_participant/index.md)
- [`qwen`](qwen/index.md)
- [`scripted_participant`](scripted_participant/index.md)

## Re-exported

| Name | Defined in | Summary |
|---|---|---|
| [`APIParticipant`](api_participant/APIParticipant.md) | `interlens.participant.participants.api_participant` | A participant backed by a hosted API — Claude via `anthropic` (`provider="anthropic"`, the default) or any model behind OpenRouter (`provider="openrouter"`, OpenAI-compatible) — for use as a debate opponent, moderator, or the classifier inside an `analyze` callback. |
| [`GemmaModelParticipant`](gemma/GemmaModelParticipant.md) | `interlens.participant.participants.gemma` | A Gemma-family participant. |
| [`LlamaModelParticipant`](llama/LlamaModelParticipant.md) | `interlens.participant.participants.llama` | A Llama-family participant. |
| [`ModelParticipant`](model_participant/ModelParticipant.md) | `interlens.participant.participants.model_participant` | A conversation participant backed by a local HuggingFace causal LM. |
| [`QwenModelParticipant`](qwen/QwenModelParticipant.md) | `interlens.participant.participants.qwen` | A participant in a conversation that is a Qwen language model. |
