# `bridge`

Module `interlens.interp.bridge`

Differentiable bridges for feeding one model's output into another's input.

Text is a non-differentiable bottleneck: sampling a discrete token from model A kills the gradient before it can
reach B. These utilities replace the sampled token with a *continuous relaxation* that B can consume as soft
embeddings, so a loss on B backpropagates all the way into A. Two regimes:

- **Shared tokenizer (vocab mixture):** `soft_embed` turns a distribution over A's vocab (optionally relaxed via
  `gumbel_softmax_tokens`) into an embedding in B's space by mixing B's embedding rows. Exact when the tokenizers
  match; `soft_embed(B, one_hot(ids))` equals `B`'s ordinary token embedding of `ids`.
- **Different tokenizers (learned adapter):** `LinearBridge` maps A's hidden state (`d_a`) into B's embedding
  space (`d_b`), sidestepping the vocab mismatch — the same shape of cross-model linear map used in the
  Procrustes/CKA analyses, but here trained jointly against B's downstream loss.

Pair these with `grad.forward_with_grad` / `grad.continuation_logprob` (which accept `inputs_embeds`) to close
the A -> B loop.

## Classes

| Name | Summary |
|---|---|
| [`LinearBridge`](LinearBridge.md) | Learned linear map from model A's hidden width `d_a` to model B's embedding width `d_b`. |

## Functions

| Name | Summary |
|---|---|
| [`gumbel_softmax_tokens`](gumbel_softmax_tokens.md) | Relaxed (Gumbel-softmax) sample over the last (vocab) dim of `logits`, differentiable in `logits`. |
| [`soft_embed`](soft_embed.md) | Mix `model`'s input-embedding rows by a per-position distribution: `[..., V] @ E[V, d] -> [..., d]`. |
