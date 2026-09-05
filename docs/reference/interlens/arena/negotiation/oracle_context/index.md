# `interlens.arena.negotiation.oracle_context`

The per-decision-point context the negotiation oracles share, written once.

The four numeric oracles (beliefs / acceptance / bestresponse / equilibrium) each need the same three things at
a decision point, so they live here rather than in any one of them: the `|D|×n` utility/surplus tables
(:class:`GameTables`, built once per game and cached on it by :func:`game_tables`), READERS that recover the
turn context — standing offers, round, rounds left, continuation discount, proposer rotation — from the loose
history/offer-registry shapes a scenario emits, and the :func:`make_verdict` constructor. The typed actions and
the `Oracle` ABC / `OracleVerdict` are imported from interlens-core (`arena/actions.py`,
`arena/oracles.py`); the structured state a *policy* reads is `strategies.NegotiationState`.

A *game* is duck-typed: any object exposing `.space` and seat-indexed `.sheets` works, plus optionally
`.rounds` / `.info` / `.discount` / `.proposer` / `.veto` (the real one is
:class:`~interlens.arena.negotiation.sheets.GameSpec`). `Deal = tuple[int, ...]` is one option index per issue.

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `Deal` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`GameTables`](GameTables.md) | Precomputed dense tables for a game — built once, shared by every oracle so the `O(n*J*\|D\|)` utility pass is never duplicated. |

## Functions

| Name | Summary |
|---|---|
| [`current_round`](current_round.md) | 1-indexed current round. |
| [`deal_list`](deal_list.md) | Materialize the deal space in a *stable* order (matrix rows below use this exact order). |
| [`effective_discount`](effective_discount.md) | The per-round continuation factor the acceptance/best-response/equilibrium oracles should use, read from the game as the single source of truth: `discount * (1 - breakdown_risk)` (time preference times the per-round no-breakdown survival probability — the BRW 1986 breakdown model). |
| [`game_tables`](game_tables.md) | `GameTables` for `game`, cached on the game object when possible. |
| [`issue_sizes`](issue_sizes.md) | Per-issue option counts `(O_1, ..., O_J)`, discovered from (in order): an `.issue_sizes` / `.n_options` attribute on the space; a sheet's `.values` rows; or the max option index seen in `deals`. |
| [`make_verdict`](make_verdict.md) | Build an `OracleVerdict` with its free-form `extra` diagnostics coerced JSON-safe up front (the `\|D\|×n` numpy tables / typed actions the oracles stash) via the shared `_jsonify`, so `to_json` and the episode save never crash. |
| [`n_agents`](n_agents.md) |  |
| [`normalize`](normalize.md) | Return a probability vector from nonnegative weights, optionally mixed with `floor` uniform mass. |
| [`offer_registry`](offer_registry.md) | Recover `{offer_id: Deal}` from the game/history. |
| [`proposer_sequence`](proposer_sequence.md) | Per-round proposer seat indices. |
| [`rounds_left`](rounds_left.md) | Rounds remaining (this turn inclusive). |
| [`seat_index`](seat_index.md) | Resolve `agent` to a seat index. |
| [`softmax`](softmax.md) | Tempered softmax; `temperature -> 0` approaches a hard argmax (used to break equilibrium cycles). |
