# `interlens.interp`

First-class interpretability layer.

All four tools hook into the *same* generation path (real turns, `sample`, and every generation inside the
future tool loop) and are tagged to conversation structure, so downstream consumers (logit lens, SAEs, probes,
CKA/Procrustes) read the `ActivationCache` via the raw-model escape hatch without any harness change.

## Modules

- [`activation_cache`](activation_cache/index.md)
- [`bridge`](bridge/index.md) — Differentiable bridges for feeding one model's output into another's input.
- [`capture`](capture/index.md)
- [`grad`](grad/index.md) — Gradient-enabled forward passes for backprop *through* a model.
- [`layers`](layers/index.md)
- [`logprobs`](logprobs/index.md)
- [`patching`](patching/index.md)
- [`pooling`](pooling/index.md) — Pool a token-position axis down to one vector per span — the primitive under every span-level readout.
- [`routing`](routing/index.md) — Mixture-of-Experts routing capture and statistics.
- [`softtokens`](softtokens/index.md) — Virtual (soft) tokens inside ordinary text prompts, plus the message-span read path that pairs with them.
- [`steering`](steering/index.md)

## Re-exported

| Name | Defined in | Summary |
|---|---|---|
| [`ActivationCache`](activation_cache/ActivationCache.md) | `interlens.interp.activation_cache` | A queryable store of captured activations, tagged by conversation structure. |
| [`ActivationRecord`](activation_cache/ActivationRecord.md) | `interlens.interp.activation_cache` | One captured tensor plus everything needed to know *what it is*. |
| [`CaptureRequest`](capture/CaptureRequest.md) | `interlens.interp.capture` | A pending capture handed to `generate`: where to store records (`cache`) and what to grab (`spec`). |
| [`CaptureSpec`](activation_cache/CaptureSpec.md) | `interlens.interp.activation_cache` | What to capture during a generation: which `sites` at which `layers`, and where to keep the tensors. |
| [`CapturedSite`](capture/CapturedSite.md) | `interlens.interp.capture` | One activation captured by `capture_activations`: the `tensor` (`[seq, d_model]`) at a given `layer` and `site`. |
| [`GradCaptureSpec`](grad/GradCaptureSpec.md) | `interlens.interp.grad` | What grad-connected activations to pull from `forward_with_grad` (mirrors `CaptureSpec` minus offload). |
| [`GradForwardOutput`](grad/GradForwardOutput.md) | `interlens.interp.grad` | Result of `forward_with_grad`: grad-connected `logits` (`[batch, seq, vocab]`) and, if a `GradCaptureSpec` was passed, `hidden` mapping `(site, layer) -> tensor[batch, seq, d_model]` (also grad-connected). |
| [`LinearBridge`](bridge/LinearBridge.md) | `interlens.interp.bridge` | Learned linear map from model A's hidden width `d_a` to model B's embedding width `d_b`. |
| [`OffloadLocation`](activation_cache/index.md#attributes) | `interlens.interp.activation_cache` |  |
| [`Patch`](patching/Patch.md) | `interlens.interp.patching` | Activation patching: overwrite a decoder layer's residual at specific token `positions` with saved `activations` (captured from another run/branch). |
| [`Phase`](activation_cache/index.md#attributes) | `interlens.interp.activation_cache` |  |
| [`Pool`](pooling/index.md#attributes) | `interlens.interp.pooling` |  |
| [`RouterSteeringSpec`](routing/RouterSteeringSpec.md) | `interlens.interp.routing` | A causal intervention on MoE routing: add a per-expert bias to the gate logits during generation, nudging which experts fire. |
| [`RoutingCapture`](routing/RoutingCapture.md) | `interlens.interp.routing` | Per-token routing at one MoE layer, from one `capture_router_logits` pass. |
| [`RoutingStats`](routing/RoutingStats.md) | `interlens.interp.routing` | Aggregate expert-usage distributions over a set of token positions. |
| [`Site`](activation_cache/index.md#attributes) | `interlens.interp.activation_cache` |  |
| [`Span`](pooling/index.md#attributes) | `interlens.interp.pooling` |  |
| [`SteeringSpec`](steering/SteeringSpec.md) | `interlens.interp.steering` | A residual-stream intervention applied during generation via forward hooks on decoder layers. |
| [`VirtualTokenInjector`](softtokens/VirtualTokenInjector.md) | `interlens.interp.softtokens` | Reserve `n_soft` positions in a *text* prompt and substitute their input embeddings at forward time. |
| [`capture_activations`](capture/capture_activations.md) | `interlens.interp.capture` | Run one clean forward pass over `input_ids` and return `[(layer, site, tensor[seq, d_model])]`. |
| [`capture_router_logits`](routing/capture_router_logits.md) | `interlens.interp.routing` | One clean forward pass over `input_ids` (`[1, seq]`); return per-MoE-layer `RoutingCapture`. |
| [`continuation_logprob`](grad/continuation_logprob.md) | `interlens.interp.grad` | Differentiable teacher-forced logprob of `target_ids` continuing a prefix, under `model`. |
| [`decoder_layers`](layers/decoder_layers.md) | `interlens.interp.layers` | Return the list of transformer decoder layer modules, across common HF architectures. |
| [`forward_with_grad`](grad/forward_with_grad.md) | `interlens.interp.grad` | One grad-connected forward pass over `input_ids` XOR `inputs_embeds`. |
| [`group_pool`](pooling/group_pool.md) | `interlens.interp.pooling` | Pool each *group* of spans into one vector; returns `([len(groups), d_model], valid[len(groups)])`. |
| [`gumbel_softmax_tokens`](bridge/gumbel_softmax_tokens.md) | `interlens.interp.bridge` | Relaxed (Gumbel-softmax) sample over the last (vocab) dim of `logits`, differentiable in `logits`. |
| [`js_divergence`](routing/js_divergence.md) | `interlens.interp.routing` | Per-layer Jensen–Shannon divergence (symmetric, bounded by ln 2) → `[n_layers]`. |
| [`kl_divergence`](routing/kl_divergence.md) | `interlens.interp.routing` | Per-layer KL(p \|\| q) between expert distributions `[n_layers, n_experts]` → `[n_layers]`. |
| [`message_token_spans`](routing/message_token_spans.md) | `interlens.interp.routing` | Token span `(start, end)` of each message of `view` in the fully-rendered chat-template sequence. |
| [`moe_layer_indices`](routing/moe_layer_indices.md) | `interlens.interp.routing` | Decoder-layer indices that carry a sparse MoE block. |
| [`moe_num_experts`](routing/moe_num_experts.md) | `interlens.interp.routing` | Number of routed experts per MoE layer (`config.num_experts` — same field name in OLMoE/Qwen-MoE). |
| [`moe_topk`](routing/moe_topk.md) | `interlens.interp.routing` | Experts selected per token (`config.num_experts_per_tok`). |
| [`routing_stats`](routing/routing_stats.md) | `interlens.interp.routing` | Pool per-token routing into per-layer expert-usage distributions. |
| [`soft_embed`](bridge/soft_embed.md) | `interlens.interp.bridge` | Mix `model`'s input-embedding rows by a per-position distribution: `[..., V] @ E[V, d] -> [..., d]`. |
| [`span_pool`](pooling/span_pool.md) | `interlens.interp.pooling` | Pool `hidden[start:end]` for each span; returns `[len(spans), d_model]`. |
| [`span_pooled_residuals`](softtokens/span_pooled_residuals.md) | `interlens.interp.softtokens` | One pooled activation vector **per message** of `view`, at each requested site/layer. |
| [`token_logprobs`](logprobs/token_logprobs.md) | `interlens.interp.logprobs` | Compute per-token logprobs / surprisal / entropy for a generation. |
| [`topk_expert_overlap`](routing/topk_expert_overlap.md) | `interlens.interp.routing` | Per-layer fraction of overlap between the `k` most-used experts of `p` and of `q` → `[n_layers]`. |
