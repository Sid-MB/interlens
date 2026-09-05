# `interlens.interp.softtokens`

Virtual (soft) tokens inside ordinary text prompts, plus the message-span read path that pairs with them.

Two utilities that together make a *continuous* channel into an otherwise text-only chat harness:

- :class:`VirtualTokenInjector` — write soft tokens into a prompt **without** an `inputs_embeds` code path. The
  harness's batched generation (`ModelParticipant.generate_batch`) chat-templates strings and calls
  `model.generate(input_ids=...)`; it cannot accept embeddings. So the injector hands you a *placeholder text
  snippet* (a run of one existing rare vocab token, repeated `n_soft` times — no new tokens, no embedding resize)
  to render into the prompt like any other text, and a context manager that swaps the embeddings at exactly those
  positions for caller-supplied vectors. The swap is a forward-pre-hook (to see `input_ids`) plus a forward hook
  (to edit the embedding output) on `model.get_input_embeddings()`, so it works identically under
  `model.generate` (placeholders live in the prefill only; cached decode steps pass through untouched) and under a
  plain `model(...)` training forward, and it is autograd-transparent: gradients flow back into the vectors, so
  the vectors can come from a trainable :class:`~interlens.interp.bridge.LinearBridge`.

- :func:`span_pooled_residuals` — the matching read path: one pooled residual vector *per message* of a rendered
  conversation, by combining `capture_activations` / `forward_with_grad` with `routing.message_token_spans`
  and `pooling.span_pool` (which owns the pooling arithmetic). This is what a theory-of-mind probe head reads.

Worked example (bridge a partner's hidden state into a listener's prompt as 4 soft tokens):

```python
from interlens.interp import VirtualTokenInjector, span_pooled_residuals, LinearBridge

inj = VirtualTokenInjector(tok_b, n_soft=4)
pooled = span_pooled_residuals(model_a, tok_a, view, layers=(-1,), grad=True)   # [n_messages, d_a]
vectors = bridge(pooled[("residual", -1)][-1:].unsqueeze(0))                    # [1, 4, d_b] (after a reshape)
prompt = f"Partner state: {inj.text}
```
What do they want?"
        with inj.inject(model_b, vectors):
                out = model_b.generate(**tok_b(prompt, return_tensors="pt"), max_new_tokens=16)

## Classes

| Name | Summary |
|---|---|
| [`VirtualTokenInjector`](VirtualTokenInjector.md) | Reserve `n_soft` positions in a *text* prompt and substitute their input embeddings at forward time. |

## Functions

| Name | Summary |
|---|---|
| [`span_pooled_residuals`](span_pooled_residuals.md) | One pooled activation vector **per message** of `view`, at each requested site/layer. |
