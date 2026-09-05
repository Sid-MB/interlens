# `ultimatum`

The **ultimatum game** [guth1982] as a scorable game: one proposer offers a split of a fixed `pie`, one responder accepts (both get the split) or rejects (both get 0), take-it-or-leave-it.

```python
ultimatum(
	*,
	pie: float = 10.0,
	n_options: int = 11,
	seed: int = 0,
) -> tuple[GameSpec, dict, dict]
```

Defined in [`interlens.arena.negotiation.games`](index.md) · [source](https://github.com/Sid-MB/interlens/blob/main/src/interlens/arena/negotiation/games.py#L77-L124)

Encoding: N=2, J=1 issue ("Split") whose `n_options` discrete options are the shares -- option `o` gives
the proposer `o * pie/(n_options-1)` and the responder the rest -- with thresholds `tau=0` (the BATNA is
the no-deal payoff 0), `rounds=1`, a fixed proposer (seat 0), and the responder-only single-shot vote
(`protocol_cfg = {"single_shot": True, "fixed_proposer": True}`).

Rational anchor -- the subgame-perfect equilibrium (the T=1 limit of Rubinstein 1982 alternating offers
[rubinstein1982] §5): the responder accepts **any positive share** (rejecting pays 0, so any surplus >= 0 is
weakly better), so the proposer keeps the whole pie. Under the harness's `>= 0` individual-rationality
convention (`solutions.ir_mask` default `strict=False`) the responder is *indifferent* at a 0 share and
(weakly) accepts, so the discrete SPE has the proposer keeping the entire pie (option `n_options-1`); the
classic "pie - epsilon" is the strict/continuous statement. The behavioral contrast [guth1982] -- humans
reject low positive offers -- is the LLM-vs-rational gap this preset exposes.

Note: this is a **pure division** (every split has the same total `pie`), so EVERY split is Pareto-optimal
and the acceptable set has `dominated_acceptable_fraction = 0` -- the score-sheet-repair knob
(`dominated_target`) does not apply here (there is no dominated slack to leave in play).

Parameters
----------
pie : total value to split (proposer share + responder share = `pie` for every option).
n_options : number of discrete splits (>= 2). `11` gives whole-unit shares `0..pie` for `pie=10`; a
    larger value = finer granularity (closer to the continuous game).
seed : accepted for a uniform preset interface; the ultimatum game is deterministic, so it is unused.

Returns `(GameSpec, analysis, protocol_cfg)`.

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `pie` | `float` | `10.0` |  |
| `n_options` | `int` | `11` |  |
| `seed` | `int` | `0` |  |
