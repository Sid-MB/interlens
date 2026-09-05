# `interlens.arena.viz.episode`

One stored episode, turned into the single JSON payload the interactive page renders.

This is the data layer of the episode visualizer: it reads a run's three record stores — the `Episode` JSON, the
`Instance` it was played on, and (optionally) the post-hoc annotation record — and merges them into one
self-describing dict. Everything the page shows is computed here; the browser only draws it.

What the merge adds beyond the raw records:

- **numbers on every turn** — the action's deal placed in the instance's geometry (per-party surplus vs each
  threshold, welfare scalars, distance below the frontier), plus per-oracle chosen/best/regret values.
- **the post-hoc oracle counterfactual** — for every oracle that scored the turn, the action it ranks highest
  instead, resolved to a deal and its numbers, so the page can show "the model did X (value v) where the oracle
  would have done Y (value v*), regret v* - v" side by side. Runs without a `bestresponse` oracle are reported
  as such rather than silently rendering an empty column.
- **seat identity** — which seats were played by an LLM and which by a computable policy, so a mixed table reads
  correctly and a seat-swap comparison knows its focal seat. Read from the run manifest's recorded invocation
  when available, else inferred from generation accounting (a policy seat emits zero output tokens).
- **prompt provenance** — the exact rendered view per turn, marked `stored` when the episode recorded it,
  `reconstructed` when it was re-derived by deterministic replay through the scenario state machine (current
  prompt code, so it can differ from what the model actually saw), or `absent`.
- **the public ledger** — which turns were actually PUBLISHED to the other seats, the offer id each proposal was
  registered under, and the deal standing on the table as of each turn (see :func:`public_ledger`). This is what
  the page's conversation view and per-agent issue view read, and it is deliberately reconstructed here rather
  than in the browser so the page can render it server-side.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `CLOSING_ACTIONS` |  |  |
| `COUNTERFACTUAL_ALIASES` |  |  |
| `COUNTERFACTUAL_ORACLES` |  |  |
| `OFFER_PREFIX` |  |  |
| `RAW_EXCERPT_CHARS` |  |  |
| `RETRY_SOURCE` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`RunDir`](RunDir.md) | A run directory's three record stores, indexed for lookup: `episodes/`, `instances/`, and the annotation subdirectory named by `annotations_dirname` (`annotations/` by default), plus `manifest.json`. |

## Functions

| Name | Summary |
|---|---|
| [`closing_turn_index`](closing_turn_index.md) | The index of the turn that CLOSED the deal, or `None` when nothing closed. |
| [`episode_payload`](episode_payload.md) | The complete render payload for one episode. |
| [`public_ledger`](public_ledger.md) | Reconstruct what the seats publicly saw, from the per-turn records alone. |
| [`reconstruct_views`](reconstruct_views.md) | Re-derive each turn's rendered view by deterministic replay, for episodes recorded before the per-turn `view` field existed. |
| [`seat_kinds`](seat_kinds.md) | Which seats an LLM played and which a computable policy played. |
