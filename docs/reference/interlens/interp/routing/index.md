# `routing`

Module `interlens.interp.routing`

Mixture-of-Experts routing capture and statistics.

Reads *which experts an MoE model routes each token to* — the discrete, cheap-to-interpret counterpart of
residual-stream capture. Like `capture_activations`, capture is a single clean forward pass over the full
token sequence (provably complete, one extra forward) rather than hooks accumulated across a decode loop: both
`OlmoeForCausalLM` and `Qwen3MoeForCausalLM` (and other HF MoE families) return per-MoE-layer router logits
natively via `output_router_logits=True`, so no module hooks are needed at all.

Typical use: replay a saved conversation view through the MoE, get per-token routing with
`capture_router_logits`, compute per-message expert-usage distributions with `routing_stats` restricted to
`message_token_spans`, and compare conditions with `js_divergence` / `topk_expert_overlap`.

## Classes

| Name | Summary |
|---|---|
| [`RouterSteeringSpec`](RouterSteeringSpec.md) | A causal intervention on MoE routing: add a per-expert bias to the gate logits during generation, nudging which experts fire. |
| [`RoutingCapture`](RoutingCapture.md) | Per-token routing at one MoE layer, from one `capture_router_logits` pass. |
| [`RoutingStats`](RoutingStats.md) | Aggregate expert-usage distributions over a set of token positions. |

## Functions

| Name | Summary |
|---|---|
| [`capture_router_logits`](capture_router_logits.md) | One clean forward pass over `input_ids` (`[1, seq]`); return per-MoE-layer `RoutingCapture`. |
| [`js_divergence`](js_divergence.md) | Per-layer Jensen–Shannon divergence (symmetric, bounded by ln 2) → `[n_layers]`. |
| [`kl_divergence`](kl_divergence.md) | Per-layer KL(p \|\| q) between expert distributions `[n_layers, n_experts]` → `[n_layers]`. |
| [`message_token_spans`](message_token_spans.md) | Token span `(start, end)` of each message of `view` in the fully-rendered chat-template sequence. |
| [`moe_layer_indices`](moe_layer_indices.md) | Decoder-layer indices that carry a sparse MoE block. |
| [`moe_num_experts`](moe_num_experts.md) | Number of routed experts per MoE layer (`config.num_experts` — same field name in OLMoE/Qwen-MoE). |
| [`moe_topk`](moe_topk.md) | Experts selected per token (`config.num_experts_per_tok`). |
| [`routing_stats`](routing_stats.md) | Pool per-token routing into per-layer expert-usage distributions. |
| [`topk_expert_overlap`](topk_expert_overlap.md) | Per-layer fraction of overlap between the `k` most-used experts of `p` and of `q` → `[n_layers]`. |
