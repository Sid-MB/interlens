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

"""The bundled scenarios as Inspect tasks.

Each task generates a solver-verified instance bank (deterministic in ``seed0``), exposes it as samples (the
full instance JSON + situational config in sample metadata, per-seat framings included), plays each sample
with the evaluated model in every seat via ``arena_solver``, and scores with the scenario's exact scorer.
Episode-level budgets map to Inspect's native per-sample limits where an equivalent exists (``token_limit``
carries the episode token budget so Inspect enforces and displays it); arena-specific accounting (dollar cost,
per-seat usage) is enforced in the solver and reported in sample metadata/score metadata — one budget
definition, two enforcement surfaces.

Run e.g.::

    inspect eval interlens.arena.inspect/info_relay --model anthropic/claude-sonnet-5 -T level=2 -T cell=wrong_confident
    inspect eval interlens.arena.inspect/negotiation --model openai/gpt-5 -T arm=solo
"""
from __future__ import annotations

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample

from ..scenario import Scenario
from ..scenarios import InfoRelay, Negotiation
from .adapter import arena_solver, scenario_scorer


def _samples(scenario: Scenario, *, level: int, n_instances: int, seed0: int, cfg: dict,
             generate_kwargs: dict | None = None) -> list[Sample]:
	samples = []
	for i in range(n_instances):
		instance = scenario.generate_instance(level, seed0 + i, **(generate_kwargs or {}))
		state = scenario.make_state(instance, "team", instance.seed, cfg=cfg or None)
		samples.append(Sample(
			id=instance.instance_id,
			input=(f"{scenario.name} instance {instance.instance_id} (level {level}, seed {instance.seed}); "
			       f"the arena solver plays every seat."),
			target=str(instance.solution.get("gold", instance.solution.get("best_joint", ""))),
			metadata={"instance": instance.to_json(), "cfg": cfg,
			          "seat_framings": scenario.seat_framings(state)},
		))
	return samples


@task
def info_relay(level: int = 0, n_instances: int = 10, seed0: int = 1, arm: str = "team",
               communication: str = "round_robin", n_rounds: int | None = None,
               framing: str | None = None, honest_persona: str | None = None,
               wrong_persona: str | None = None, turn_max_tokens: int = 2048,
               token_limit: int | None = None, messaging_turns: int = 24) -> Task:
	"""The info-relay scenario (wrong-shard epistemics) as an Inspect task. ``communication`` selects the
	published round-robin protocol or the autonomous messaging variant; the situational knobs mirror the
	scenario's ``cfg``. ``token_limit`` (per sample) is Inspect's native enforcement of an episode budget."""
	cfg = {k: v for k, v in (("cell", "inspect"), ("n_rounds", n_rounds), ("framing", framing),
	                         ("honest_persona", honest_persona), ("wrong_persona", wrong_persona))
	       if v is not None}
	return Task(
		dataset=MemoryDataset(_samples(InfoRelay(), level=level, n_instances=n_instances,
		                               seed0=seed0, cfg=cfg)),
		solver=arena_solver(arm=arm, communication=communication, turn_max_tokens=turn_max_tokens,
		                    messaging_turns=messaging_turns),
		scorer=scenario_scorer(),
		token_limit=token_limit,
	)


@task
def negotiation(level: int = 0, n_parties: int | None = None, n_instances: int = 10, seed0: int = 1,
                arm: str = "team", coherent: bool = True, communication: str = "round_robin",
                n_rounds: int | None = None, stakes: str | None = None, personas: str | None = None,
                turn_max_tokens: int = 2048, token_limit: int | None = None,
                messaging_turns: int = 24) -> Task:
	"""The negotiation scenario as an Inspect task. ``n_parties`` switches to the sweep generator (3-8 seats,
	fixed deal space); otherwise the 6-party difficulty ladder at ``level`` (``coherent`` per the role-prior
	table). ``stakes``/``personas``/``n_rounds`` mirror the scenario's situational config."""
	scenario = Negotiation()
	cfg = {k: v for k, v in (("cell", "inspect"), ("n_rounds", n_rounds), ("stakes", stakes),
	                         ("personas", personas)) if v is not None}
	if n_parties is not None:
		samples = []
		for i in range(n_instances):
			instance = scenario.generate_instance_n(n_parties, seed0 + i)
			state = scenario.make_state(instance, "team", instance.seed, cfg=cfg or None)
			samples.append(Sample(
				id=instance.instance_id,
				input=(f"{scenario.name} instance {instance.instance_id} ({n_parties} parties, "
				       f"seed {instance.seed}); the arena solver plays every seat."),
				target=str(instance.solution["best_joint"]),
				metadata={"instance": instance.to_json(), "cfg": cfg,
				          "seat_framings": scenario.seat_framings(state)}))
		dataset = MemoryDataset(samples)
	else:
		dataset = MemoryDataset(_samples(scenario, level=level, n_instances=n_instances, seed0=seed0,
		                                 cfg=cfg, generate_kwargs={"coherent": coherent}))
	return Task(
		dataset=dataset,
		solver=arena_solver(arm=arm, communication=communication, turn_max_tokens=turn_max_tokens,
		                    messaging_turns=messaging_turns),
		scorer=scenario_scorer(),
		token_limit=token_limit,
	)
