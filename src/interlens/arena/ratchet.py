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

"""Adaptive difficulty ratchet: find the level where a model stops clearing the bar, then measure there.

A ceiling-saturated cell measures nothing — if every episode scores ~1.0 the comparison has no room to move.
The ratchet drives any ``Scenario`` with a difficulty ladder to the *found level*: the first level whose probe
mean fails the bar (default: mean primary < 0.75 of ceiling over ``probe_n`` probe episodes). Three phases,
run through an ``EpisodePool``:

1. **probe** — ``probe_n`` episodes per level, climbing while the mean clears ``step_up``. With
   ``speculative=True`` the first ``wave`` levels are probed CONCURRENTLY (then the rest, if every probed
   level cleared the bar) — the wall-clock optimization from the arena experiments' re-ratchet runs; the found
   decision is the same pure function either way (``found_level``).
2. **measure** — ``meas_n`` episodes at the found level and its neighbor below (or above when found == 0), on
   the deterministic shared instance pool, offset past the probe block so probe and measurement instances
   never overlap.
3. **solo baselines** — paired solo episodes on the SAME instances, each under a ``TokenBudget`` equal to the
   median team tokens-out at that level (the matched-compute recipe).

State is serialized after every batch, so a restarted ratchet resumes where it stopped and never duplicates a
completed episode (completed instances are skipped by id — paired-join safe). Instance pools are deterministic
per (scenario, level): instance ``i`` uses seed ``level*10000 + i``, shared by every arm and model.

Provenance: the collaboration-arena experiments' ratchet (sequential form) and their re-ratchet runs
(speculative form), re-based onto the ``EpisodePool`` driver.
"""
from __future__ import annotations

import asyncio
import json
import statistics
from pathlib import Path

from ..stop import TokenBudget
from .engine import EpisodePool, _participant_model_id
from .scenario import Scenario
from .schema import Episode, Instance, load_instances, save_instances

PROBE_N = 5
MEAS_N = 15
# Climb while the probe mean clears 75% of ceiling; the first level below the bar is the found level.
STEP_UP = 0.75


def found_level(probe_means: dict[int, float], step_up: float = STEP_UP) -> int:
	"""The found level implied by a set of probe means: the first (ascending) probed level whose mean fails
	the bar, else the highest level probed (the model never dropped below the bar). Pure — both probing modes
	and the ratchet's resume path decide through this one function."""
	if not probe_means:
		raise ValueError("no probe means")
	for level in sorted(probe_means):
		if probe_means[level] < step_up:
			return level
	return max(probe_means)


class DifficultyRatchet:
	"""Probe -> measure -> paired-solo driver over one scenario/participant pair (see the module docstring).

	``pool`` supplies the store (episode persistence + resume dedup) and optional ``UsageMeter`` (spend
	gating: each phase stops launching once the meter is exhausted; in-flight episodes finish)."""

	def __init__(self, scenario: Scenario, participant, pool: EpisodePool, *,
	             instances_dir: str | Path, state_path: str | Path, arm: str = "team",
	             probe_n: int = PROBE_N, meas_n: int = MEAS_N, step_up: float = STEP_UP,
	             speculative: bool = False, wave: int = 3, cfg: dict | None = None,
	             gen_config: dict | None = None, estimated_cost: float | None = None,
	             solo_budget_default: int = 4000, seed0: int = 1000):
		if pool.store is None:
			raise ValueError("DifficultyRatchet needs an EpisodePool with a store (resume/dedup reads it)")
		self.scenario = scenario
		self.participant = participant
		self.pool = pool
		self.model = _participant_model_id(participant)
		self.instances_dir = Path(instances_dir)
		self.state_path = Path(state_path)
		self.arm = arm
		self.probe_n, self.meas_n, self.step_up = probe_n, meas_n, step_up
		self.speculative, self.wave = speculative, wave
		self.cfg, self.gen_config = cfg, gen_config
		self.estimated_cost = estimated_cost
		self.solo_budget_default = solo_budget_default
		self.seed0 = seed0
		self.state = {"scenario": scenario.name, "phase": "probe", "level": 0,
		              "probe_means": {}, "found": None, "done": False,
		              "measured_levels": [], "solo_done": []}
		if self.state_path.exists():
			self.state.update(json.loads(self.state_path.read_text()))

	# ------------------------------------------------------------------------------------------ plumbing --

	def _save(self) -> None:
		self.state_path.parent.mkdir(parents=True, exist_ok=True)
		self.state_path.write_text(json.dumps(self.state))

	@property
	def _exhausted(self) -> bool:
		return self.pool.meter is not None and self.pool.meter.exhausted

	def _instances(self, level: int, n: int, offset: int = 0) -> list[Instance]:
		"""The deterministic shared instance pool per (scenario, level): instance ``i`` uses seed
		``level*10000 + i``. Every arm and model draws the same list; the pool file grows on demand."""
		path = self.instances_dir / f"{self.scenario.name}_L{level}.json"
		have = []
		if path.exists():
			have = load_instances(self.instances_dir, self.scenario.name, level)
		while len(have) < offset + n:
			i = len(have)
			have.append(self.scenario.generate_instance(level, level * 10_000 + i))
		save_instances(have, self.instances_dir)
		return have[offset:offset + n]

	def _done_instance_ids(self, level: int, arm: str) -> set[str]:
		return {e["instance_id"] for e in self.pool.store.load_all(self.scenario.name)
		        if e["arm"] == arm and e["model"] == self.model
		        and e["level"] == level and e["status"] == "done"}

	async def _run_batch(self, level: int, n: int, offset: int, arm: str,
	                     solo_budget: int | None = None) -> list[Episode]:
		"""One batch of episodes at ``level``; instances already completed for this (scenario, arm, model,
		level) are skipped, so a resume inside a batch never duplicates episodes (paired-join safe)."""
		instances = self._instances(level, n, offset)
		done = self._done_instance_ids(level, arm)
		jobs = [dict(scenario=self.scenario, instance=inst, arm=arm, participant=self.participant,
		             seed=self.seed0 + k, cfg=self.cfg, gen_config=self.gen_config,
		             estimated_cost=self.estimated_cost,
		             budget=(TokenBudget(per_conversation=solo_budget) if solo_budget else None))
		        for k, inst in enumerate(instances) if inst.instance_id not in done]
		return await self.pool.run_pool(jobs)

	async def _probe_mean(self, level: int) -> float:
		episodes = await self._run_batch(level, self.probe_n, 0, self.arm)
		scores = [e.outcome.get("primary", 0.0) for e in episodes if e.status == "done"]
		if not scores:  # resumed past this batch: read the stored probe episodes back
			probe_ids = {i.instance_id for i in self._instances(level, self.probe_n, 0)}
			scores = [e["outcome"].get("primary", 0.0)
			          for e in self.pool.store.load_all(self.scenario.name)
			          if e["arm"] == self.arm and e["model"] == self.model
			          and e["level"] == level and e["status"] == "done"
			          and e["instance_id"] in probe_ids]
		return statistics.mean(scores) if scores else 0.0

	# -------------------------------------------------------------------------------------------- phases --

	async def _probe_sequential(self) -> None:
		while self.state["phase"] == "probe" and not self._exhausted:
			level = self.state["level"]
			mean = await self._probe_mean(level)
			self.state["probe_means"][str(level)] = mean
			if mean >= self.step_up and level < self.scenario.N_LEVELS - 1:
				self.state["level"] = level + 1
			else:
				self.state["found"] = found_level(
					{int(k): v for k, v in self.state["probe_means"].items()}, self.step_up)
				self.state["phase"] = "measure"
			self._save()

	async def _probe_speculative(self) -> None:
		"""Probe the first ``wave`` levels concurrently; if every probed level clears the bar and levels
		remain, probe the rest — then decide through the same pure ``found_level``."""
		n_levels = self.scenario.N_LEVELS
		means = {int(k): v for k, v in self.state["probe_means"].items()}
		for wave in (list(range(min(self.wave, n_levels))),
		             list(range(self.wave, n_levels))):
			wave = [lv for lv in wave if lv not in means]
			if not wave or self._exhausted:
				break
			results = await asyncio.gather(*[self._probe_mean(lv) for lv in wave])
			for lv, mean in zip(wave, results):
				means[lv] = mean
			self.state["probe_means"] = {str(k): v for k, v in means.items()}
			self._save()
			if any(means[lv] < self.step_up for lv in means):
				break  # the found level is already determined; don't probe further waves
		self.state["found"] = found_level(means, self.step_up)
		self.state["phase"] = "measure"
		self._save()

	async def _measure(self) -> None:
		found = self.state["found"]
		neighbor = found - 1 if found > 0 else found + 1
		neighbor = min(max(neighbor, 0), self.scenario.N_LEVELS - 1)
		self.state["meas_levels"] = sorted({found, neighbor})
		for level in self.state["meas_levels"]:
			if level in self.state["measured_levels"] or self._exhausted:
				continue
			# probe episodes at this level used instances [0, probe_n); measurement uses
			# [probe_n, probe_n + meas_n) for clean pairing
			await self._run_batch(level, self.meas_n, self.probe_n, self.arm)
			self.state["measured_levels"].append(level)
			self._save()
		if set(self.state["meas_levels"]) <= set(self.state["measured_levels"]):
			self.state["phase"] = "solo"
			self._save()

	async def _solo(self) -> None:
		for level in self.state.get("meas_levels", []):
			if level in self.state["solo_done"] or self._exhausted:
				continue
			team = [e for e in self.pool.store.load_all(self.scenario.name)
			        if e["arm"] == "team" and e["level"] == level
			        and e["model"] == self.model and e["status"] == "done"]
			budget = (int(statistics.median([e["tokens_out"] for e in team]))
			          if team else self.solo_budget_default)
			await self._run_batch(level, self.meas_n, self.probe_n, "solo", solo_budget=budget)
			self.state["solo_done"].append(level)
			self._save()
		self.state["phase"] = "done"

	# ----------------------------------------------------------------------------------------------- run --

	async def run(self) -> dict:
		"""Run (or resume) the ratchet to completion; returns the final state dict."""
		if self.state["phase"] == "probe" and not self._exhausted:
			if self.speculative:
				await self._probe_speculative()
			else:
				await self._probe_sequential()
		if self.state["phase"] == "measure" and not self._exhausted:
			await self._measure()
		if self.state["phase"] == "solo":
			if self.scenario.has_solo and self.arm == "team":
				await self._solo()
			else:
				self.state["phase"] = "done"
		if self.state["phase"] == "done" or not self.scenario.has_solo:
			self.state["done"] = True
			self.state["phase"] = "done"
		self._save()
		return self.state
