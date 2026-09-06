# `pooling`

Module `interlens.interp.pooling`

Pool a token-position axis down to one vector per span — the primitive under every span-level readout.

`span_pooled_residuals` pools one span per *message*; a theory-of-mind probe instead pools one vector per
*speaker* (many disjoint, non-contiguous spans per group) out of a single long forward pass, and a probe over
prefix-shared conversation turns pools many overlapping span sets out of that same pass. Both want the same
arithmetic, so it lives here once, as plain tensor math with no model, tokenizer, or conversation in sight.

Two entry points:

- :func:`span_pool` — one vector per `(start, end)` span, contiguous, the `span_pooled_residuals` shape.
- :func:`group_pool` — one vector per *group of spans*, for "everything this speaker said" reads where a group's
  spans are scattered through the sequence. `mean` is taken over the group's pooled tokens (token-weighted, so
  a long message counts more than a short one), `last` takes the final token of the group's last span.

Both are autograd-transparent (no `detach`, no in-place writes into the input), so they compose with
`forward_with_grad` when the pooled vectors feed a trainable head.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `Pool` |  |  |
| `Span` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`group_pool`](group_pool.md) | Pool each *group* of spans into one vector; returns `([len(groups), d_model], valid[len(groups)])`. |
| [`span_pool`](span_pool.md) | Pool `hidden[start:end]` for each span; returns `[len(spans), d_model]`. |
