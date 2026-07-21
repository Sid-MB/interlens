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

"""The adaptive difficulty ratchet: the pure found-level decision, the phased probe->measure->solo run over
scripted episodes, resume safety (no duplicated episodes), and the speculative wave variant."""
from __future__ import annotations

import asyncio
import json

import pytest

from interlens.message import Message
from interlens.participant import Participant
from interlens.arena import DifficultyRatchet, EpisodePool, EpisodeStore, found_level
from interlens.arena.scenarios import InfoRelay


def run(coro):
	return asyncio.run(coro)


# ------------------------------------------------------------------------------------------- decision rule --

def test_found_level_first_failing_level():
	assert found_level({0: 0.9, 1: 0.8, 2: 0.5}) == 2       # first mean below the 0.75 bar
	assert found_level({0: 0.2}) == 0                       # fails immediately
	assert found_level({0: 0.9, 1: 0.8}) == 1               # never fails -> highest probed
	assert found_level({0: 0.75}) == 0                      # exactly at the bar clears it (climb rule: >=)
	assert found_level({0: 0.9, 1: 0.74999}) == 1
	with pytest.raises(ValueError):
		found_level({})


def test_found_level_ignores_gaps():
	# speculative waves can leave gaps; the decision scans ascending over what was probed
	assert found_level({0: 0.9, 2: 0.6}) == 2
	assert found_level({1: 0.9, 3: 0.9}) == 3


# --------------------------------------------------------------------------------------------- phased run --

class ScriptedAnswer(Participant):
	"""Scripted relay seat: shares notes on regular turns, submits ``final_text`` on finalization prompts."""

	def __init__(self, final_text: str):
		self.name = "scripted"
		self.final_text = final_text

	def generate(self, view, *, max_new_tokens=None, **kwargs):
		last = view[-1]["content"]
		finalizing = ("You MUST now submit" in last or "RIGHT NOW" in last
		              or "Token budget reached" in last)
		text = self.final_text if finalizing else "Sharing my shard."
		return Message(self.name, text, {"n_tokens": 10, "n_tokens_in": 20})


class BreakingPool(EpisodePool):
	"""Builds a per-episode scripted seat that answers correctly only BELOW the break level, so probe means
	are 1.0 under the break level and 0.0 at/above it (each episode gets its own participant — no shared
	mutable state across concurrent episodes)."""

	def __init__(self, store, break_level):
		super().__init__(store)
		self.break_level = break_level

	async def run_episode(self, scenario, instance, arm, participant, **kwargs):
		# the relay scorer accepts answers within 2% of gold, so "wrong" must be far off
		gold = (instance.payload["gold"] if instance.level < self.break_level
		        else instance.payload["gold"] * 3 + 12345)
		seat = ScriptedAnswer(f'```json\n{{"answer": {gold}}}\n```')
		return await super().run_episode(scenario, instance, arm, seat, **kwargs)


def _ratchet(tmp_path, break_level, *, speculative=False, probe_n=2, meas_n=2):
	scenario = InfoRelay()
	pool = BreakingPool(EpisodeStore(tmp_path / "eps"), break_level)
	return DifficultyRatchet(scenario, ScriptedAnswer("unused"), pool,
	                         instances_dir=tmp_path / "instances",
	                         state_path=tmp_path / "ratchet.json",
	                         probe_n=probe_n, meas_n=meas_n, speculative=speculative)


def test_sequential_ratchet_finds_break_level_and_measures(tmp_path):
	r = _ratchet(tmp_path, break_level=2)
	state = run(r.run())
	assert state["found"] == 2                      # probe means: L0=1.0, L1=1.0, L2=0.0
	assert state["probe_means"]["0"] == 1.0 and state["probe_means"]["2"] == 0.0
	assert state["done"] and state["phase"] == "done"
	assert state["meas_levels"] == [1, 2]           # found + neighbor below
	assert sorted(state["measured_levels"]) == [1, 2]
	assert sorted(state["solo_done"]) == [1, 2]     # paired solos ran (InfoRelay has a solo arm)
	# the persisted state file matches
	assert json.loads((tmp_path / "ratchet.json").read_text())["found"] == 2
	# solo episodes exist on the same instances as the team measurement
	eps = r.pool.store.load_all("e5_relay")
	team_meas = {e["instance_id"] for e in eps if e["arm"] == "team" and e["level"] == 2}
	solo_meas = {e["instance_id"] for e in eps if e["arm"] == "solo" and e["level"] == 2}
	assert solo_meas and solo_meas <= team_meas     # paired: identical instance ids


def test_ratchet_resume_never_duplicates_episodes(tmp_path):
	r1 = _ratchet(tmp_path, break_level=1)
	state1 = run(r1.run())
	assert state1["found"] == 1
	n_before = len(r1.pool.store.load_all("e5_relay"))
	# a fresh ratchet over the same store + state file re-runs to completion without new episodes
	r2 = _ratchet(tmp_path, break_level=1)
	state2 = run(r2.run())
	assert state2["found"] == 1
	assert len(r2.pool.store.load_all("e5_relay")) == n_before


def test_ratchet_resume_mid_run_completes(tmp_path):
	# simulate a crash after probing: state says measure phase, no measurements yet
	r1 = _ratchet(tmp_path, break_level=1)
	run(r1._probe_sequential())
	assert r1.state["phase"] == "measure" and r1.state["found"] == 1
	r2 = _ratchet(tmp_path, break_level=1)
	assert r2.state["phase"] == "measure"           # resumed from the state file
	state = run(r2.run())
	assert state["done"] and sorted(state["measured_levels"]) == [0, 1]


def test_speculative_ratchet_same_decision(tmp_path):
	seq = run(_ratchet(tmp_path / "seq", break_level=2).run())
	spec = run(_ratchet(tmp_path / "spec", break_level=2, speculative=True).run())
	assert spec["found"] == seq["found"] == 2
	# the speculative first wave probed levels 0-2 (concurrently); the decision is the same pure function
	assert set(spec["probe_means"]) >= {"0", "1", "2"}


def test_speculative_ratchet_probes_second_wave_when_all_clear(tmp_path):
	spec = run(_ratchet(tmp_path, break_level=99, speculative=True).run())
	# never breaks -> both waves probed, found = hardest level
	assert set(spec["probe_means"]) == {"0", "1", "2", "3", "4"}
	assert spec["found"] == 4
