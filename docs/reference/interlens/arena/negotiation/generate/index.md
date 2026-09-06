# `generate`

Module `interlens.arena.negotiation.generate`

Scorable-negotiation scenario generator with the score-sheet repairs the reproducibility studies demand.

The generator draws private additive score sheets from an explicit issue-type mix, calibrates thresholds to a
target acceptable-set size, and -- the central repair -- rejection-samples over seeds to hit a target fraction of
acceptable deals that are Pareto-*dominated*, so the game is not near-zero-sum the moment it is feasible
[reproA2025]. Every generated game ships with a precomputed analysis dict
(:func:`interlens.arena.negotiation.solutions.analyze`) whose descriptors are *verified by enumeration*.

Issue types (the `mix` / `issue_types` knobs), which shape the cross-party correlation of the value columns:

- `distributive` -- opposed preferences (a fixed pie): parties split into camps with reversed option
  rankings and high weight, so acceptable deals get pushed onto the frontier (near-zero-sum).
- `compatible`   -- a shared option ranking: everyone prefers the same option, so the worse options are
  Pareto-dominated-for-all yet may stay acceptable under loose thresholds (a prime source of dominated slack).
- `integrative`  -- parties weight *different* issues (non-carers score the issue 0, creating sparsity), so
  conceding an issue you don't care about to someone who does is a free logroll; failing to do so lands you at a
  dominated interior deal.

So the mix is the geometric lever on the dominated fraction, while threshold calibration fixes the acceptable-set
*size* independently.

Example:

```python
game, analysis = generate_game(n_parties=5, n_issues=5, n_options=4,
                               feasible_fraction=0.12, dominated_target=0.6, seed=1)
analysis["dominated_acceptable_fraction"]   # ~0.6, verified by enumeration
analysis["ir_count"], game.n_parties
```

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `INSTANCE_LADDER` | `list[dict]` |  |
| `LADDER_DISCOUNT` |  |  |
| `SCALE` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`IssueType`](IssueType.md) | The three issue archetypes that set how parties' value columns correlate (see module docstring). |

## Functions

| Name | Summary |
|---|---|
| [`build_instance`](build_instance.md) | Wrap a generated `(GameSpec, analysis)` into a solver-verified arena :class:`~interlens.arena.schema.Instance`. |
| [`game_at_level`](game_at_level.md) | The `(GameSpec, analysis)` at difficulty `level` from `seed` -- the level -> generator-knob mapping shared by :func:`generate_instance` and the `games.scorable` preset, so the difficulty ladder and the per-round discount default live in exactly one place (never re-defaulted at a call site). |
| [`generate_game`](generate_game.md) | Generate one scorable-negotiation game plus its enumeration-verified analysis dict. |
| [`generate_games`](generate_games.md) | Generate `count` independent games with consecutive base seeds `seed, seed+1, ...` (all other knobs forwarded to :func:`generate_game`). |
| [`generate_instance`](generate_instance.md) | Generate one solver-verified arena :class:`~interlens.arena.schema.Instance` at difficulty `level` from `seed` -- the bridge a `ScorableNegotiation` scenario's `generate_instance` delegates to. |
