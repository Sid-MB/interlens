# `interlens.arena.negotiation.analysis`

Measurement over stored negotiation episodes: how far from rational was this play, and where?

Reading an episode back is the other half of running one, and none of it is specific to a single study — any
experiment over this game family asks the same questions. So the measurement stack lives here, next to the game
and the oracles, rather than inside one experiment:

- :mod:`surplus` — surplus-vector primitives: Pareto/dominance geometry and distances. (The welfare and
  inequality SCALARS live in `negotiation.solutions`, with the solution concepts they are compared against.)
- :mod:`game_analysis` — :class:`~.game_analysis.GameAnalysis`, the solved-game bundle the metrics read: the
  frontier, the axiomatic solution points, and the per-party scales, built from a stored `Instance` or a
  `GameSpec`.
- :mod:`episode_view` — :class:`~.episode_view.EpisodeView` / `TurnView`: a stored episode parsed into the
  per-turn move ledger (offers, votes, walks) the metrics iterate.
- :mod:`curves` — concession-curve fitting (the tanh τ / CRI summary) and the Park et al. no-regret trend tests.
- :mod:`annotations` — the per-turn annotation records (`TurnAnnotation` / `EpisodeAnnotation` /
  `DivergenceSummary`) and the readers that group an episode's inline `OracleRecord` rows.
- :mod:`metrics` — the outcome and per-turn metric functions (welfare/distance-to-frontier, regret series, IR
  and dominated-proposal detection, concession summaries).
- :mod:`taxonomy` — the failure taxonomy: named divergence rows tiered from fully mechanical to judge-scored.
- :mod:`rollout` — counterfactual-rollout regret (replay a turn under a reference policy and re-score).
- :mod:`cot_localize` — within-chain-of-thought localization of the first divergent reasoning step.

Framing a run's numbers into a report (the "atlas") stays with the experiment that defines the run — this
package supplies the measurements, not the presentation.

Submodules are imported explicitly (`from interlens.arena.negotiation.analysis import metrics`) rather than
re-exported here, so importing one measurement does not pull numpy-heavy siblings you did not ask for.

## Modules

- [`annotations`](annotations/index.md) — Per-turn annotation records: the divergence data model `annotate.py` writes and `taxonomy.py` / `report.py` read (disk I/O lives in `runio.AnnotationStore`).
- [`cot_localize`](cot_localize/index.md) — OmegaPRM-style within-CoT divergence localization: binary-search the first reasoning step that flips the induced action to a divergent one, in O(log n) oracle calls (arXiv:2406.06592 — exploit prefix monotonicity: correct until the first error, wrong after).
- [`curves`](curves/index.md) — Trajectory-shape metrics over a *series* (not a single turn).
- [`episode_view`](episode_view/index.md) — `EpisodeView`: a stored arena `Episode` JSON parsed into a normalized negotiation action series that the metrics read instead of raw `parsed_action` — an ordered `TurnView` list (typed action, deal canonicalized to an index tuple, offer id, any acceptable-offer/belief note, private thinking), the offer registry, the per-round standing offer, and the final deal / reached flag.
- [`game_analysis`](game_analysis/index.md) — `GameAnalysis`: the solved-game bundle the metrics read — the adapter seam between interlens' `GameSpec`/`solutions.py` and the pure metric math.
- [`metrics`](metrics/index.md) — The divergence metric suite: outcome-, turn-, and faithfulness-level measures over one episode.
- [`rollout`](rollout/index.md) — Counterfactual-rollout regret: label a divergence by Δ expected surplus, not by action mismatch.
- [`surplus`](surplus/index.md) — Pure surplus-vector math: Pareto geometry, dominance, and distances.
- [`taxonomy`](taxonomy/index.md) — The 12-row LLM-negotiation failure taxonomy as executable checks.
