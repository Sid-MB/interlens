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
from ..scenarios import CodingCollab, InfoRelay, Negotiation, SecurityDilemma, dlc_scenario
from ..schema import Instance
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
def security_dilemma(level: int = 0, n_instances: int = 10, seed0: int = 1,
                     turn_max_tokens: int = 2048, token_limit: int | None = None) -> Task:
	"""The repeated security dilemma as an Inspect task: 12 rounds of message + simultaneous
	build/deescalate/attack waves with noisy intelligence; ``level`` sets the first-strike bonus and the
	observation-noise probability. Team arm only (the game is irreducibly 2-party), round-robin protocol only
	(a simultaneous-move payoff game has no sound free-messaging reduction)."""
	return Task(
		dataset=MemoryDataset(_samples(SecurityDilemma(), level=level, n_instances=n_instances,
		                               seed0=seed0, cfg={"cell": "inspect"})),
		solver=arena_solver(arm="team", turn_max_tokens=turn_max_tokens),
		scorer=scenario_scorer(),
		token_limit=token_limit,
	)


@task
def coding_collab(level: int = 0, n_instances: int = 10, seed0: int = 1, arm: str = "team",
                  communication: str = "round_robin", turn_max_tokens: int = 2048,
                  token_limit: int | None = None, messaging_turns: int = 24) -> Task:
	"""The coding-collaboration scenario as an Inspect task: 3 seats jointly write one Python module against a
	public pytest suite while each holds private style constraints; ``level`` sets how many constraints are
	dealt. Scoring runs the sandboxed test suite + AST constraint checks. ``communication="messaging"`` runs
	the autonomous mailbox variant; the latest complete ```python fence in the sends is the submission."""
	return Task(
		dataset=MemoryDataset(_samples(CodingCollab(), level=level, n_instances=n_instances,
		                               seed0=seed0, cfg={"cell": "inspect"})),
		solver=arena_solver(arm=arm, communication=communication, turn_max_tokens=turn_max_tokens,
		                    messaging_turns=messaging_turns),
		scorer=scenario_scorer(),
		token_limit=token_limit,
	)


@task
def distributed_longcontext(instances: str, task_name: str | None = None, n_instances: int | None = None,
                            arm: str = "team", communication: str = "round_robin",
                            token_limit: int | None = None) -> Task:
	"""A distributed long-context task as an Inspect task. Instances embed megabytes of context and are built
	offline (``interlens.arena.scenarios.dlc.build``); pass the saved bank as ``-T instances=/path/to/
	dlc_sniah_L0.json``. ``task_name`` overrides the task inferred from the bank's first instance.
	``communication="messaging"`` runs the scenario's NATIVE directed-messaging arm (``team-msg`` — each
	non-finalizer turn routes private fenced-JSON messages), not the generic mailbox variant, so episodes stay
	replayable. Per-turn caps come from the task adapter (they are part of the task definition)."""
	import json as _json
	from pathlib import Path as _Path

	raw = _json.loads(_Path(instances).read_text())
	if n_instances is not None:
		raw = raw[:n_instances]
	bank = [Instance.from_json(d) for d in raw]
	scenario = dlc_scenario(task_name or bank[0].payload["task"], name=bank[0].scenario)
	if communication == "messaging":
		arm, communication = "team-msg", "round_robin"
	samples = []
	for instance in bank:
		state = scenario.make_state(instance, "team", instance.seed)
		samples.append(Sample(
			id=instance.instance_id,
			input=(f"{scenario.name} instance {instance.instance_id} (seed {instance.seed}); "
			       f"the arena solver plays every seat."),
			target=str(instance.solution),
			metadata={"instance": instance.to_json(), "cfg": {"cell": "inspect"},
			          "seat_framings": scenario.seat_framings(state)},
		))
	return Task(
		dataset=MemoryDataset(samples),
		solver=arena_solver(arm=arm, communication=communication),
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
