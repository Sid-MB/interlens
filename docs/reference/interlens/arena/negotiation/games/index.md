# `games`

Module `interlens.arena.negotiation.games`

Swappable game presets: name a classic bargaining situation, get a ready-to-play game in one call.

A **preset** is a factory returning `(GameSpec, analysis, protocol_cfg)` — the game spec, its
enumeration-verified :func:`~interlens.arena.negotiation.solutions.analyze` dict, and the scenario protocol knobs
that turn the shared `ScorableNegotiation` state machine into that specific game (single-shot / fixed-proposer /
majority). Presets are parameterizations, not new engines: the deal space, the oracle stack, and the annotation
layer all run unchanged on any of them.

Presets shipped:

======================  ============================================================  =========================
Preset                  Encoding                                                      Rational anchor
======================  ============================================================  =========================
`scorable` (default)  the full §2 generator (a thin alias -- defaults in one place) the §4 oracle stack
`ultimatum`           N=2, J=1 pie split, tau=0, rounds=1, fixed proposer,          SPE (Rubinstein 1982 §5
                        responder-only single-shot vote                               one-round limit); human
                                                                                      rejection [guth1982]
`divide_dollar`       N parties, J=1 discrete-shares split, rotating proposer,       Baron-Ferejohn 1989 /
                        multi-round, unanimity or majority                            Okada 1996 (v = 1/n)
`bilateral_multiissue`  DoND-style N=2, J issues, private values (the generator)     Lewis et al. 2017 lineage
======================  ============================================================  =========================

Usage:

```python
from interlens.arena.negotiation import games

game, analysis, protocol_cfg = games.make_preset("ultimatum", pie=10, n_options=11)
game.n_parties                              # 2
analysis["deal_space_size"]                 # 11 (one split per option)

# the arena bridge: a solver-verified Instance + the scenario cfg to play it under
instance, protocol_cfg = games.build_preset_instance("ultimatum")
from interlens.arena.scenarios import ScorableNegotiation
ScorableNegotiation().make_state(instance, "moves_only", seed=0, cfg=protocol_cfg)   # single-shot ultimatum
```

Each preset's own docstring carries its citation keys; `references.py` maps every key to the full reference.
The `scorable` alias re-uses the generator's defaults verbatim (never re-defaulted here).

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `PRESETS` | `dict[str, Preset]` |  |
| `Preset` |  |  |

## Functions

| Name | Summary |
|---|---|
| [`bilateral_multiissue`](bilateral_multiissue.md) | A **DoND-style bilateral, multi-issue, private-value** negotiation [lewis2017]: two parties bargain over `n_issues` item types, each with private per-item values -- the classic "Deal or No Deal" item-division game, reproduced here as the scorable generator restricted to `n_parties=2`. |
| [`build_preset_instance`](build_preset_instance.md) | Build a solver-verified arena :class:`~interlens.arena.schema.Instance` from a preset, plus the scenario `protocol_cfg` to play it under -- the one-call bridge from a preset name to a runnable game. |
| [`divide_dollar`](divide_dollar.md) | The **divide-the-dollar / legislative-bargaining** testbed [baron_ferejohn1989]: `n_parties` split a unit pie over multiple rounds with a rotating proposer, under a unanimity or majority agreement rule. |
| [`make_preset`](make_preset.md) | Look up a preset by `name` and build it, returning `(GameSpec, analysis, protocol_cfg)`. |
| [`scorable`](scorable.md) | The default multi-party, multi-issue **scorable** game -- a thin alias to the existing generator so the whole preset machinery has one uniform entry point. |
| [`ultimatum`](ultimatum.md) | The **ultimatum game** [guth1982] as a scorable game: one proposer offers a split of a fixed `pie`, one responder accepts (both get the split) or rejects (both get 0), take-it-or-leave-it. |
