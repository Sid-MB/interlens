# `usage`

Module `interlens.usage`

Usage accounting: token/cost metering for hosted-API participants.

Hosted-API turns cost real money, and a large rollout can outrun a budget *while it is running* — the failure
mode this module exists to prevent is N concurrent conversations each individually under budget that together
blow past the cap before any of them finishes. Three pieces:

- **Per-turn usage** is recorded by `APIParticipant` into `Message.metadata` (`n_tokens`, `n_tokens_in`,
  `cost_usd`, `stop_reason`) — the same convention `ModelParticipant` uses for `n_tokens`, so
  `TokenBudget` and transcript-level aggregation work identically for local and hosted turns.
- **`UsageMeter`** is the live, run-level ledger: every metered participant reports each API call into one
  shared meter, which tracks cumulative dollars per model, supports **reservation-style gating** (claim an
  estimated cost *before* launching work, so concurrent conversations cannot collectively overrun the cap),
  and optionally persists to disk after every add (crash-safe: a restarted run resumes the ledger).
- **`CostBudget`** is the dollar-denominated `StopCondition`: the per-conversation analogue of
  `TokenBudget`, reading each committed turn's recorded `metadata['cost_usd']`.

Pricing is a $/Mtok table keyed by model id. The bundled defaults are deliberately conservative (high) so the
meter over- rather than under-counts; register exact prices with `register_pricing` or pass a table to the
meter. An unknown model uses `FALLBACK_PRICING` (higher than any bundled entry) rather than silently costing $0.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `CACHE_READ_MULTIPLIER` |  |  |
| `CACHE_WRITE_MULTIPLIERS` |  |  |
| `DEFAULT_PRICING` | `dict[str, dict[str, float]]` |  |
| `FALLBACK_PRICING` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`CostBudget`](CostBudget.md) | A per-conversation **dollar** budget — the cost-denominated sibling of `TokenBudget`. |
| [`UsageMeter`](UsageMeter.md) | A cumulative, thread-safe dollar ledger shared by every metered participant in a run. |

## Functions

| Name | Summary |
|---|---|
| [`register_pricing`](register_pricing.md) | Register (or override) the $/Mtok pricing for `model_id`, process-wide. |
| [`resolve_pricing`](resolve_pricing.md) | The effective pricing table: bundled defaults, overlaid with `register_pricing` entries, overlaid with the caller's `pricing` dict (each value `{"in": $/Mtok, "out": $/Mtok}`). |
| [`transcript_usage`](transcript_usage.md) | Aggregate the recorded usage of one transcript: total generated/input tokens, dollar cost, and a per-author breakdown — read from each committed message's metadata (`n_tokens` / `n_tokens_in` / `cost_usd`), the same source of truth `TokenBudget` and `CostBudget` use. |
