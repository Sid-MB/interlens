# `interlens.interp.grad`

Gradient-enabled forward passes for backprop *through* a model.

The rest of interp is read-only: `capture_activations` runs under `torch.inference_mode` and detaches, which
is right for logit-lens / probe readouts but throws away the graph. This module is the escape hatch for
optimization *through* a (usually frozen) model: differentiable soft-prompt tuning into a target, and end-to-end
backprop across two stacked models (model A's relaxed tokens feed model B via `bridge.soft_embed`). Nothing here
touches `ModelParticipant.generate` — these are standalone functions on the raw `.model`, matching the style of
`token_logprobs`/`decoder_layers`.

Two design points:
- Accept `inputs_embeds` (soft embeddings) as a first-class input, not just `input_ids` — that is how a
  continuous, differentiable signal enters a transformer. Residual-stream capture is grad-connected (via
  `output_hidden_states` on the *same* forward, not the separate detached pass `capture_activations` uses).
- `checkpoint=True` turns on HF gradient checkpointing for the pass, so backprop through a frozen B recomputes
  activations instead of storing them — the memory lever that lets a 0.5B+1.5B two-model stack fit one GPU.

## Classes

| Name | Summary |
|---|---|
| [`GradCaptureSpec`](GradCaptureSpec.md) | What grad-connected activations to pull from `forward_with_grad` (mirrors `CaptureSpec` minus offload). |
| [`GradForwardOutput`](GradForwardOutput.md) | Result of `forward_with_grad`: grad-connected `logits` (`[batch, seq, vocab]`) and, if a `GradCaptureSpec` was passed, `hidden` mapping `(site, layer) -> tensor[batch, seq, d_model]` (also grad-connected). |

## Functions

| Name | Summary |
|---|---|
| [`continuation_logprob`](continuation_logprob.md) | Differentiable teacher-forced logprob of `target_ids` continuing a prefix, under `model`. |
| [`forward_with_grad`](forward_with_grad.md) | One grad-connected forward pass over `input_ids` XOR `inputs_embeds`. |
