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

# [rational_agents restructure: phase-C] 2026-07-24 — moved up from experiments/rational_agents/analysis/:
# negotiation-generic measurement, reusable by any experiment over this game family.
"""Counterfactual-rollout regret: label a divergence by Δ expected surplus, not by action mismatch. At turn t,
roll k continuations from the model's action and from the oracle's action against the *same frozen counterpart
policies* and score the gap in the acting party's expected surplus (mismatch alone over-labels — many actions
are near-optimal). Engine-agnostic: works against a small ``RolloutEnv`` protocol + a per-seat ``Policy`` map;
``policy_rollout_env`` is the (unimplemented) hook to bind ``ScorableNegotiation`` + the rational policies.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

Action = Any
State = Any
Policy = Callable[[State, str], Action]   # (state, seat) -> action, for a frozen counterpart


class RolloutEnv(Protocol):
	"""The negotiation transition a rollout needs. Implementations must not mutate the input state in ``step``
	(return a fresh/cloned state) so a single state can seed many counterfactual branches."""

	def next_seat(self, state: State) -> str | None:
		"""The seat to move now, or ``None`` if the state is terminal."""

	def legal_actions(self, state: State, seat: str) -> list:
		"""Legal actions for ``seat`` at ``state`` (used to validate / enumerate; may be empty if unbounded)."""

	def step(self, state: State, seat: str, action: Action) -> State:
		"""Apply ``action`` by ``seat``; return the successor state (no in-place mutation)."""

	def surplus(self, state: State, agent: str) -> float:
		"""Terminal surplus for ``agent`` (call only at a terminal state)."""


def rollout(env: RolloutEnv, state: State, policies: dict[str, Policy], *, max_steps: int = 500) -> State:
	"""Drive ``state`` to a terminal state, each seat acting by its policy in ``policies``. ``max_steps`` guards
	against a non-terminating env (a policy that never closes)."""
	for _ in range(max_steps):
		seat = env.next_seat(state)
		if seat is None:
			return state
		if seat not in policies:
			raise KeyError(f"no policy for seat {seat!r}")
		state = env.step(state, seat, policies[seat](state, seat))
	return state


@dataclass
class CounterfactualRegret:
	"""Δ expected surplus between the oracle action and the model action for the acting ``agent``: positive =
	the oracle's action leads to more surplus (a real divergence), 0 = the model's action was as good."""

	agent: str
	surplus_model: float
	surplus_oracle: float
	delta: float           # surplus_oracle - surplus_model
	k: int

	def to_json(self) -> dict:
		return {"agent": self.agent, "surplus_model": self.surplus_model,
		        "surplus_oracle": self.surplus_oracle, "delta": self.delta, "k": self.k}


def counterfactual_regret(env: RolloutEnv, state: State, agent: str,
                          model_action: Action, oracle_action: Action,
                          policies: dict[str, Policy], *, k: int = 8) -> CounterfactualRegret:
	"""Roll ``k`` continuations from the model's action and from the oracle's action (both taken by ``agent`` at
	``state``, then everyone — including ``agent`` — follows ``policies``) and report the mean-surplus gap.

	With deterministic policies the k rollouts coincide and ``k`` is effectively 1; ``k`` matters once a policy
	is stochastic (a mixed strategy or, later, an LLM counterpart at temperature). ``policies`` must include a
	continuation policy for ``agent`` itself (its post-branch behavior)."""
	def mean_surplus(first_action: Action) -> float:
		total = 0.0
		for _ in range(k):
			nxt = env.step(state, agent, first_action)
			term = rollout(env, nxt, policies)
			total += env.surplus(term, agent)
		return total / k
	s_model = mean_surplus(model_action)
	s_oracle = mean_surplus(oracle_action)
	return CounterfactualRegret(agent=agent, surplus_model=s_model, surplus_oracle=s_oracle,
	                            delta=s_oracle - s_model, k=k)


def policy_rollout_env(scenario: Any, instance: Any):
	"""HOOK (unimplemented): bind the rational policies as rollout counterparts — ``NegotiationState`` as the env
	``State``, ``ScorableNegotiation.apply`` as the transition, each frozen counterpart a ``policy(state)->action``.
	The env-agnostic ``counterfactual_regret``/``rollout`` core is already tested via a synthetic env."""
	raise NotImplementedError(
		"policy_rollout_env binds ScorableNegotiation.apply as the transition and NegotiationState-driven "
		"policy(state)->Action counterparts; the env-agnostic rollout core is already tested via test_annotate")
