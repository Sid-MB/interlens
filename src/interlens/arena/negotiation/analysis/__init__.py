# interlens: a framework for scaffolding and interpreting multi-agent conversations
# Copyright (C) 2026 Siddharth M. Bhatia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of version 3 of the GNU Affero General Public License
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# [rational_agents restructure: phase-C] 2026-07-24 — measurement moved up from the experiment layer.
"""Measurement over stored negotiation episodes: how far from rational was this play, and where?

Reading an episode back is the other half of running one, and none of it is specific to a single study — any
experiment over this game family asks the same questions. So the measurement stack lives here, next to the game
and the oracles, rather than inside one experiment:

- :mod:`surplus` — surplus-vector primitives: Pareto/dominance geometry and distances. (The welfare and
  inequality SCALARS live in ``negotiation.solutions``, with the solution concepts they are compared against.)
- :mod:`game_analysis` — :class:`~.game_analysis.GameAnalysis`, the solved-game bundle the metrics read: the
  frontier, the axiomatic solution points, and the per-party scales, built from a stored ``Instance`` or a
  ``GameSpec``.
- :mod:`episode_view` — :class:`~.episode_view.EpisodeView` / ``TurnView``: a stored episode parsed into the
  per-turn move ledger (offers, votes, walks) the metrics iterate.
- :mod:`curves` — concession-curve fitting (the tanh τ / CRI summary) and the Park et al. no-regret trend tests.
- :mod:`annotations` — the per-turn annotation records (``TurnAnnotation`` / ``EpisodeAnnotation`` /
  ``DivergenceSummary``) and the readers that group an episode's inline ``OracleRecord`` rows.
- :mod:`metrics` — the outcome and per-turn metric functions (welfare/distance-to-frontier, regret series, IR
  and dominated-proposal detection, concession summaries).
- :mod:`taxonomy` — the failure taxonomy: named divergence rows tiered from fully mechanical to judge-scored.
- :mod:`rollout` — counterfactual-rollout regret (replay a turn under a reference policy and re-score).
- :mod:`cot_localize` — within-chain-of-thought localization of the first divergent reasoning step.

Framing a run's numbers into a report (the "atlas") stays with the experiment that defines the run — this
package supplies the measurements, not the presentation.

Submodules are imported explicitly (``from interlens.arena.negotiation.analysis import metrics``) rather than
re-exported here, so importing one measurement does not pull numpy-heavy siblings you did not ask for.
"""
