# `interlens.arena.negotiation.beliefs`

Bayesian (and frequency-model fallback) belief oracle over an enumerated opponent-type grid.

Literature grounding:

- **Hypothesis space** = issue-weight rankings x per-issue evaluator shapes x reservation (tau) levels —
  Hindriks & Tykhonov, "Opponent modelling in automated multi-issue negotiation using Bayesian learning,"
  AAMAS 2008, pp. 331-338. https://research.vu.nl/en/publications/opponent-modelling-in-automated-multi-issue-negotiation-using-bay
  Their **separate-learning scalability trick** (learn weight-hypotheses and evaluator-hypotheses
  independently, each conditioned on the mean of the others) is implemented as `mode="separate"` so the
  full product grid never has to be materialized when it is large.
- **Concession likelihood** `P(b_t | h, b_{t-1}) proportional to exp(-delta+ / 2 sigma^2)` where
  `delta+` is the *positive part* of the opponent's own-utility increase `h(b_t) - h(b_{t-1})` — Chang &
  Fujita, "A Scalable Opponent Model Using Bayesian Learning ...," AAMAS 2023, pp. 2487-2489, Eqs. 2-5.
  https://www.southampton.ac.uk/~eg/AAMAS2023/pdfs/p2487.pdf  Hypotheses under which the opponent's *own*
  utility went UP are penalized (a rational opponent concedes, i.e. weakly lowers its own demanded utility).
- **Frequency model** cheap fallback (issue-stability weights + option-frequency values) — HardHeaded /
  Baarslag, Hendrikx, Hindriks & Jonker, "Learning about the opponent ...," JAAMAS 30(5):849-898, 2016,
  which repeatedly finds simple frequency heuristics often beat Bayesian models.
- **Soft / damped updates** (per-observation likelihood tempered by `lam < 1` + a uniform floor) so a
  deceptive / adversarial trace cannot catastrophically corrupt the posterior — Hua et al., "Game-Theoretic
  LLM ...," arXiv:2411.05990, Remark 1 (exact-rationality belief updates are corrupted by deception).

Multilateral handling: one independent model per opponent (the standard independence assumption).

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `REPLAY_CACHE_ENTRIES` |  |  |

## Classes

| Name | Summary |
|---|---|
| [`BeliefOracle`](BeliefOracle.md) | Maintains a per-opponent `BeliefState` for one agent and exposes the posteriors as the `beliefs` payload of an `OracleVerdict` (this oracle annotates beliefs; it does not itself value moves, so `action_values` is left empty and `best` None). |
| [`BeliefState`](BeliefState.md) | A single opponent's belief model: a damped Bayesian posterior over an enumerated `OpponentType` grid, with an optional Hindriks-Tykhonov *separate-learning* factorization for large grids and a frequency-model shadow kept in parallel as the cheap control readout. |
| [`FrequencyModel`](FrequencyModel.md) | Count-based opponent model: issue *stability* -> weights (an issue whose chosen option stays fixed across consecutive offers is important), option *frequency* -> values (a frequently-offered option is preferred). |
| [`OpponentType`](OpponentType.md) | One enumerated hypothesis about an opponent: normalized issue `weights` (sum 1), a per-issue evaluator `shapes` tuple, and a reservation `threshold` on the induced `[0, 1]` utility scale. |

## Functions

| Name | Summary |
|---|---|
| [`build_type_grid`](build_type_grid.md) | Enumerate the opponent-type hypothesis grid = weight-profiles x shape-assignments x tau-levels. |
| [`clear_replay_cache`](clear_replay_cache.md) | Drop every cached offer-prefix posterior. |
| [`replay_belief`](replay_belief.md) | A :class:`BeliefState` that has observed `offers` in order — reusing the longest cached prefix. |
