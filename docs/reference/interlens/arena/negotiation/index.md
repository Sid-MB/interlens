# `interlens.arena.negotiation`

Multi-issue, multi-party scorable negotiation: deal spaces, private score sheets, exact solution
concepts, computable rational-agent oracles, and an executable strategy zoo.

Each module's docstring carries the primary citations for the algorithm it implements; `references.py` maps
every citation key to its full reference.

## Modules

- [`acceptance`](acceptance/index.md) — Optimal-stopping acceptance oracle: when is accepting the standing offer better than holding out?
- [`analysis`](analysis/index.md) — Measurement over stored negotiation episodes: how far from rational was this play, and where?
- [`belief_accuracy`](belief_accuracy/index.md) — How well does a :class:`~interlens.arena.negotiation.beliefs.BeliefState` actually know its opponent?
- [`beliefs`](beliefs/index.md) — Bayesian (and frequency-model fallback) belief oracle over an enumerated opponent-type grid.
- [`bestresponse`](bestresponse/index.md) — Exact expectimax best-response oracle over (remaining rounds x deal space x type posterior).
- [`calibrated`](calibrated/index.md) — Behaviourally-calibrated rational negotiation: :class:`CalibratedRationalPolicy`.
- [`equilibrium`](equilibrium/index.md) — Banks-Duggan stationary-equilibrium oracle for the multilateral unanimity bargaining game.
- [`fairness`](fairness/index.md) — The **table objective**: one number per deal saying how good that deal is *for the whole table*.
- [`games`](games/index.md) — Swappable game presets: name a classic bargaining situation, get a ready-to-play game in one call.
- [`generate`](generate/index.md) — Scorable-negotiation scenario generator with the score-sheet repairs the reproducibility studies demand.
- [`llm_calibrated`](llm_calibrated/index.md) — Private-information rational negotiation against an **empirically fitted LLM opponent model**: :class:`LLMCalibratedRationalPolicy`.
- [`oracle_context`](oracle_context/index.md) — The per-decision-point context the negotiation oracles share, written once.
- [`policy_participant`](policy_participant/index.md) — `PolicyParticipant`: a state-dependent pure-Python seat that computes its move from a bound policy.
- [`references`](references/index.md) — Citation-key registry for the negotiation solution-concept and generator modules.
- [`rewards`](rewards/index.md) — Outcome rewards for RL on scorable negotiation: the smoothed log-Nash objective.
- [`sheets`](sheets/index.md) — Private score sheets, the additive utility model, the game specification, and the NumPy utility matrix.
- [`solutions`](solutions/index.md) — Exact axiomatic solution concepts over the fully-enumerated deal space.
- [`space`](space/index.md) — The deal space: issues, their discrete options, and the fully-enumerable Cartesian product of options.
- [`strategies`](strategies/index.md) — The executable rational / scripted negotiator zoo as **policies** (`state -> action`), the computable opponent pool the LLMs are measured against.
- [`talking`](talking/index.md) — The **talking rational agent**: the composed Bayesian negotiator with a truthful templated voice.
