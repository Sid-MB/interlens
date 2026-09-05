# `interlens.arena.oracles`

The oracle layer: per-turn "what would a rational agent have done here?" annotations.

An `Oracle` scores every action available to a seat at a decision point and names the best one; the arena
then measures the seat's *regret* — `value(best) - value(chosen)` in the game's value units — the
centipawn-loss analog for negotiation (Regan & Haworth 2011). Oracles compose: a solution oracle, a belief
oracle, an acceptance oracle, an equilibrium oracle, each citing its own literature — those concrete
negotiation oracles live in `interlens.arena.negotiation` and subclass this generic `Oracle` ABC.

Two annotation paths write into an episode's oracle log, both typed as :class:`OracleRecord`:

- **inline pure-Python oracles** — run post-`apply` with no extra generation (`Scenario.annotate_turn`),
  scoring the seat's ACTUAL move against the oracle's best on the same state. Cheap, so every turn can carry
  one.
- **forked provisional elicitations** — re-ask the *model* to finalize now on a private forked view
  (`Scenario.provisional_due`), an LLM-side probe of where the model thinks it stands.

Both land in `Episode.round_checkpoints` (kept as the field name for record compatibility) as
`OracleRecord.to_json()` dicts.

## Classes

| Name | Summary |
|---|---|
| [`Oracle`](Oracle.md) | A rational reference policy that scores a seat's options at a decision point. |
| [`OracleRecord`](OracleRecord.md) | One per-turn oracle annotation on an episode (the typed replacement for the loose checkpoint dict). |
| [`OracleVerdict`](OracleVerdict.md) | One oracle's read of a decision point. |

## Functions

| Name | Summary |
|---|---|
| [`annotate`](annotate.md) | Run every oracle over one decision point and return one inline :class:`OracleRecord` each — the ready helper a scenario calls from `annotate_turn` so its oracle wiring is a single line. |
