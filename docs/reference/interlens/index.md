# `interlens`

Package `interlens`

The public `interlens` API, exported **lazily**.

Every name below still resolves with a plain `from interlens import X`; the only thing that changed is *when*
the defining module is imported. Eagerly importing the whole API pulled in `torch` and `transformers` (~7 s
warm, far worse on a cold NFS mount) even for the many CPU-only entry points that never touch a model —
`interlens.arena.viz` (reads JSON, writes HTML), `interlens.arena.negotiation.analysis`, audit scripts. The
table below is the single source of truth: it maps each defining module to the names it exports, `__getattr__`
(PEP 562) imports that module on **first attribute access** and caches the value in module globals, and
`__all__` is derived from it. To add an export, add it here and nowhere else.

## Modules

- [`arena`](arena/index.md) — Scoreable multi-agent evaluations on interlens: scenarios, episode drivers, and exact scoring.
- [`communication`](communication/index.md) — Pluggable communication topologies: who speaks next, and who sees what.
- [`context`](context/index.md)
- [`context_item`](context_item/index.md)
- [`conversation`](conversation/index.md)
- [`execution_mode`](execution_mode/index.md)
- [`factories`](factories/index.md)
- [`functional`](functional/index.md) — Copy-on-write functional-update support shared by `Participant` and `Conversation`.
- [`hooks`](hooks/index.md)
- [`integrations`](integrations/index.md) — Optional adapters that connect Interlens participants to external runtimes.
- [`interp`](interp/index.md) — First-class interpretability layer.
- [`loading`](loading/index.md)
- [`message`](message/index.md)
- [`parsing`](parsing/index.md) — One home for structured-action parsing and reasoning stripping.
- [`participant`](participant/index.md)
- [`reasoning_visibility`](reasoning_visibility/index.md)
- [`runner`](runner/index.md)
- [`stop`](stop/index.md)
- [`templating`](templating/index.md) — Per-row templating for data-driven rollouts.
- [`tools`](tools/index.md)
- [`transcript`](transcript/index.md)
- [`usage`](usage/index.md) — Usage accounting: token/cost metering for hosted-API participants.
- [`view`](view/index.md)

## Re-exported

| Name | Defined in | Summary |
|---|---|---|
| [`APIParticipant`](participant/participants/api_participant/APIParticipant.md) | `interlens.participant.participants.api_participant` | A participant backed by a hosted API — Claude via `anthropic` (`provider="anthropic"`, the default) or any model behind OpenRouter (`provider="openrouter"`, OpenAI-compatible) — for use as a debate opponent, moderator, or the classifier inside an `analyze` callback. |
| [`ActivationCache`](interp/activation_cache/ActivationCache.md) | `interlens.interp.activation_cache` | A queryable store of captured activations, tagged by conversation structure. |
| [`AnyStopCondition`](stop/stop_condition/AnyStopCondition.md) | `interlens.stop.stop_condition` | Fires when *any* member condition fires. |
| [`AutoModelParticipant`](factories/AutoModelParticipant.md) | `interlens.factories` | Resolver for creating `Participant` instances automatically from HuggingFace model identifiers, local model paths, or already-loaded `PreTrainedModel`s. |
| [`CaptureSpec`](interp/activation_cache/CaptureSpec.md) | `interlens.interp.activation_cache` | What to capture during a generation: which `sites` at which `layers`, and where to keep the tensors. |
| [`CommunicationPolicy`](communication/policy/CommunicationPolicy.md) | `interlens.communication.policy` | Who speaks next, and who sees what. |
| [`ContextItem`](context_item/ContextItem.md) | `interlens.context_item` | A single item of *private* asymmetric knowledge given to one participant (a briefing, a document, a fact). |
| [`ContextPolicy`](context/context_policy/ContextPolicy.md) | `interlens.context.context_policy` | Decides how to fit a participant's view within its model's context window. |
| [`Conversation`](conversation/Conversation.md) | `interlens.conversation` | A multi-agent conversation: the recipe, the live dialogue, AND the benchmark-rollout driver, all in one lightweight object. |
| [`CostBudget`](usage/CostBudget.md) | `interlens.usage` | A per-conversation **dollar** budget — the cost-denominated sibling of `TokenBudget`. |
| [`DEFAULT_REGISTRY`](tools/registry/index.md#attributes) | `interlens.tools.registry` |  |
| [`DatasetField`](templating/DatasetField.md) | `interlens.templating` | A placeholder for `row[name]` in a templated field, created by :func:`dataset_field`. |
| [`DirectPipingPolicy`](communication/policy/DirectPipingPolicy.md) | `interlens.communication.policy` | A fixed pipeline: each participant sees only its **predecessor's** output (plus moderator/system framing and its own past turns), and speaking order follows the chain — A → B → C → A → … |
| [`DropOldestPolicy`](context/drop_oldest_policy/DropOldestPolicy.md) | `interlens.context.drop_oldest_policy` | Drop the oldest `turn` segments (preserving system/moderator/private_context) until the view fits. |
| [`ElapsedTimeStopCondition`](stop/conditions/ElapsedTimeStopCondition.md) | `interlens.stop.conditions` | Stop once `seconds` of wall-clock have elapsed since the run started (monotonic clock). |
| [`ErrorPolicy`](context/error_policy/ErrorPolicy.md) | `interlens.context.error_policy` | The safe default: raise if the view exceeds the context window rather than silently dropping content. |
| [`ExecutionMode`](execution_mode/ExecutionMode.md) | `interlens.execution_mode` | Names the deterministic-vs-throughput tension explicitly rather than pretending it doesn't exist. |
| [`Functional`](functional/Functional.md) | `interlens.functional` | Mixin giving a dataclass copy-on-write updates via `set(**changes)`. |
| [`GemmaModelParticipant`](participant/participants/gemma/GemmaModelParticipant.md) | `interlens.participant.participants.gemma` | A Gemma-family participant. |
| [`GradCaptureSpec`](interp/grad/GradCaptureSpec.md) | `interlens.interp.grad` | What grad-connected activations to pull from `forward_with_grad` (mirrors `CaptureSpec` minus offload). |
| [`GradForwardOutput`](interp/grad/GradForwardOutput.md) | `interlens.interp.grad` | Result of `forward_with_grad`: grad-connected `logits` (`[batch, seq, vocab]`) and, if a `GradCaptureSpec` was passed, `hidden` mapping `(site, layer) -> tensor[batch, seq, d_model]` (also grad-connected). |
| [`HookAction`](hooks/message_hook/HookAction.md) | `interlens.hooks.message_hook` |  |
| [`LinearBridge`](interp/bridge/LinearBridge.md) | `interlens.interp.bridge` | Learned linear map from model A's hidden width `d_a` to model B's embedding width `d_b`. |
| [`LlamaModelParticipant`](participant/participants/llama/LlamaModelParticipant.md) | `interlens.participant.participants.llama` | A Llama-family participant. |
| [`Message`](message/Message.md) | `interlens.message` | A single committed turn in a conversation. |
| [`MessageHook`](hooks/message_hook/MessageHook.md) | `interlens.hooks.message_hook` | Middleware that inspects each freshly generated message *before* it is committed to the transcript, and may approve / deny / edit it. |
| [`MessageHookResult`](hooks/message_hook/MessageHookResult.md) | `interlens.hooks.message_hook` |  |
| [`MessagingPolicy`](communication/messaging/MessagingPolicy.md) | `interlens.communication.messaging` | Asynchronous point-to-point messaging with per-agent mailboxes and a ping-driven scheduler. |
| [`ModelLike`](factories/index.md#attributes) | `interlens.factories` |  |
| [`ModelParticipant`](participant/participants/model_participant/ModelParticipant.md) | `interlens.participant.participants.model_participant` | A conversation participant backed by a local HuggingFace causal LM. |
| [`OpenRouterRouting`](participant/participants/api_participant/OpenRouterRouting.md) | `interlens.participant.participants.api_participant` | Reproducible OpenRouter routing for research. |
| [`Participant`](participant/participant/Participant.md) | `interlens.participant.participant` | A participant in a conversation, either a model or a person. |
| [`Patch`](interp/patching/Patch.md) | `interlens.interp.patching` | Activation patching: overwrite a decoder layer's residual at specific token `positions` with saved `activations` (captured from another run/branch). |
| [`Provider`](participant/participants/api_participant/index.md#attributes) | `interlens.participant.participants.api_participant` |  |
| [`QwenModelParticipant`](participant/participants/qwen/QwenModelParticipant.md) | `interlens.participant.participants.qwen` | A participant in a conversation that is a Qwen language model. |
| [`ReasoningVisibility`](reasoning_visibility/ReasoningVisibility.md) | `interlens.reasoning_visibility` | Controls whether a participant's prior `<think>` reasoning is re-injected into views on later turns. |
| [`RoundRobinPolicy`](communication/policy/RoundRobinPolicy.md) | `interlens.communication.policy` | The shared-transcript default, as an explicit policy: speakers cycle through `participants` order and everyone sees every committed turn. |
| [`RunReport`](runner/pool/RunReport.md) | `interlens.runner.pool` | Aggregate outcome of a run. |
| [`RunResult`](runner/pool/RunResult.md) | `interlens.runner.pool` | Outcome of one job: the finished `conversation` (weightless participants + completed transcript), its `transcript` and (serializable) `analysis`, or an `error` string if it failed. |
| [`ScriptedParticipant`](participant/participants/scripted_participant/ScriptedParticipant.md) | `interlens.participant.participants.scripted_participant` | A non-model participant that replies with **pre-written (scripted) messages**, cycled in order — its turns are fixed, NOT generated from the conversation. |
| [`SlidingWindowPolicy`](context/sliding_window_policy/SlidingWindowPolicy.md) | `interlens.context.sliding_window_policy` | Keep the preserved framing plus the most recent `keep_last` turns; drop older turns. |
| [`SteeringSpec`](interp/steering/SteeringSpec.md) | `interlens.interp.steering` | A residual-stream intervention applied during generation via forward hooks on decoder layers. |
| [`StopCondition`](stop/stop_condition/StopCondition.md) | `interlens.stop.stop_condition` | A stateful predicate that ends a `Conversation.run` early. |
| [`StopStringCondition`](stop/conditions/StopStringCondition.md) | `interlens.stop.conditions` | Stop when a committed message's visible `content` contains any of the given strings (a done-signal). |
| [`SummarizePolicy`](context/summarize_policy/SummarizePolicy.md) | `interlens.context.summarize_policy` | Compress older turns into a single summary segment instead of dropping them outright (the heaviest policy). |
| [`TokenBudget`](stop/conditions/TokenBudget.md) | `interlens.stop.conditions` | A per-conversation compute budget — the matched-compute primitive for fair solo-vs-pair comparisons. |
| [`TokenStopCondition`](stop/conditions/TokenStopCondition.md) | `interlens.stop.conditions` | Stop once the total generated tokens across turns reach `max_tokens`. |
| [`Tool`](tools/tool/Tool.md) | `interlens.tools.tool` | A capability a participant can invoke during its turn. |
| [`ToolCall`](tools/tool_call/ToolCall.md) | `interlens.tools.tool_call` | A parsed request from the model to invoke a tool: the tool `name` and its `arguments`. |
| [`ToolRegistry`](tools/registry/ToolRegistry.md) | `interlens.tools.registry` | Resolves tool *names* (which serialize) to live `Tool` instances (which don't). |
| [`ToolResult`](tools/tool_call/ToolResult.md) | `interlens.tools.tool_call` | The outcome of executing a `ToolCall`: the tool `name` and its string `output` (or error text). |
| [`Transcript`](transcript/Transcript.md) | `interlens.transcript` | The canonical, perspective-neutral record of a conversation, plus the logic to render it *from* a given participant's perspective. |
| [`TurnStopCondition`](stop/conditions/TurnStopCondition.md) | `interlens.stop.conditions` | Stop after `max_turns` committed turns. |
| [`UsageMeter`](usage/UsageMeter.md) | `interlens.usage` | A cumulative, thread-safe dollar ledger shared by every metered participant in a run. |
| [`available_devices`](runner/devices/available_devices.md) | `interlens.runner.devices` | List the devices to spread conversations across: every CUDA GPU, else a single mps/cpu fallback. |
| [`continuation_logprob`](interp/grad/continuation_logprob.md) | `interlens.interp.grad` | Differentiable teacher-forced logprob of `target_ids` continuing a prefix, under `model`. |
| [`conversation_from_ids`](factories/conversation_from_ids.md) | `interlens.factories` | Deprecated thin alias for :func:`conversation_from_models` / :meth:`Conversation.from_models`, kept for back-compat. |
| [`conversation_from_models`](factories/conversation_from_models.md) | `interlens.factories` | Scaffold a conversation from a tuple of `models` — each an HF id (str) or an already-loaded `PreTrainedModel` (see `ModelLike`). |
| [`dataset_field`](templating/dataset_field.md) | `interlens.templating` | Reference a dataset column in a templated field: `shared_context=("Solve:\n\n", dataset_field("question"))` resolves `row["question"]` for each row at rollout expansion. |
| [`decoder_layers`](interp/layers/decoder_layers.md) | `interlens.interp.layers` | Return the list of transformer decoder layer modules, across common HF architectures. |
| [`forward_with_grad`](interp/grad/forward_with_grad.md) | `interlens.interp.grad` | One grad-connected forward pass over `input_ids` XOR `inputs_embeds`. |
| [`gumbel_softmax_tokens`](interp/bridge/gumbel_softmax_tokens.md) | `interlens.interp.bridge` | Relaxed (Gumbel-softmax) sample over the last (vocab) dim of `logits`, differentiable in `logits`. |
| [`register_analyzer`](runner/analyzer_registry/register_analyzer.md) | `interlens.runner.analyzer_registry` |  |
| [`register_pricing`](usage/register_pricing.md) | `interlens.usage` | Register (or override) the $/Mtok pricing for `model_id`, process-wide. |
| [`register_worker_init`](runner/worker_init/register_worker_init.md) | `interlens.runner.worker_init` | Register a zero-arg callable to run once at worker startup (e.g. to populate the tool/analyzer registries). |
| [`run`](runner/pool/run.md) | `interlens.runner.pool` | Run several conversation lineups in ONE pool — the multi-lineup entry point (e.g. a ladder of model pairs × conditions in one overnight job). |
| [`run_jobs`](runner/pool/run_jobs.md) | `interlens.runner.pool` | Run `(job_id, Conversation)` jobs across devices, with checkpointing, resume, and per-job failure isolation. |
| [`soft_embed`](interp/bridge/soft_embed.md) | `interlens.interp.bridge` | Mix `model`'s input-embedding rows by a per-position distribution: `[..., V] @ E[V, d] -> [..., d]`. |
| [`token_logprobs`](interp/logprobs/token_logprobs.md) | `interlens.interp.logprobs` | Compute per-token logprobs / surprisal / entropy for a generation. |
| [`transcript_usage`](usage/transcript_usage.md) | `interlens.usage` | Aggregate the recorded usage of one transcript: total generated/input tokens, dollar cost, and a per-author breakdown — read from each committed message's metadata (`n_tokens` / `n_tokens_in` / `cost_usd`), the same source of truth `TokenBudget` and `CostBudget` use. |
