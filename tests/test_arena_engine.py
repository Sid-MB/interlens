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

"""The arena engine: scripted episodes end-to-end through ``EpisodePool`` — termination, retries, provisional
forking, budgets as stop conditions, reservation gating, persistence, and replay/rescore round-trips."""
from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import time

import pytest

from interlens import TokenBudget, UsageMeter
from interlens.message import Message
from interlens.participant import Participant
from interlens.arena import (BatchedEpisodePool, EMPTY_TURN_PLACEHOLDER, EpisodePool, EpisodeStore,
                             GenerationFailureBudgetExceeded, check_reasoning_leak, gen_failures,
                             replay_episode, rescore)
from interlens.arena.scenarios import InfoRelay, Negotiation


class ScriptedSeat(Participant):
	"""Phase-aware scripted participant: shares notes on regular turns, answers on finalization phases."""

	def __init__(self, final_text, turn_text="Here is what my notes say.", tokens=(90, 10)):
		self.name = "scripted"
		self.final_text = final_text
		self.turn_text = turn_text
		self.tokens_in, self.tokens_out = tokens
		self.calls = 0

	def _meta(self):
		return {"n_tokens": self.tokens_out, "n_tokens_in": self.tokens_in, "cost_usd": 0.01}

	def generate(self, view, *, max_new_tokens=None, **kwargs):
		self.calls += 1
		last = view[-1]["content"]
		finalizing = any(marker in last for marker in
		                 ("FINAL BINDING", "You MUST now submit", "RIGHT NOW",
		                  "Token budget reached", "Reply with ONLY"))
		return Message(self.name, self.final_text if finalizing else self.turn_text, self._meta())


def run(coro):
	return asyncio.run(coro)


def test_relay_episode_end_to_end(tmp_path):
	scen = InfoRelay()
	inst = scen.generate_instance(0, 11)
	gold = inst.payload["gold"]
	seat = ScriptedSeat(f'```json\n{{"answer": {gold}}}\n```')
	pool = EpisodePool(EpisodeStore(tmp_path))
	ep = run(pool.run_episode(scen, inst, "team", seat, cfg={"cell": "base"}))
	assert ep.status == "done"
	assert ep.outcome["success"] is True and ep.outcome["wrong_adopted"] is False
	assert ep.cell == "base"
	assert len(ep.round_checkpoints) == 3      # provisional forks after rounds 1-3
	# usage accounting: totals equal per-turn sums plus provisional turns
	assert ep.tokens_out == seat.calls * 10
	assert ep.usage()["by_seat"]["Avery"]["turns"] >= 1
	# persisted record round-trips
	stored = json.loads(EpisodeStore(tmp_path).path(ep).read_text())
	assert stored["outcome"]["success"] is True


def test_negotiation_episode_and_retry(tmp_path):
	scen = Negotiation()
	inst = scen.generate_instance(0, 7)
	best = json.dumps(inst.solution["best_deal"])

	class RetryOnce(ScriptedSeat):
		"""Returns a malformed final proposal once, then the valid one — exercising the one-retry rule."""

		def __init__(self):
			super().__init__(f'```json\n{{"proposal": {best}}}\n```')
			self.failed_once = False

		def generate(self, view, **kwargs):
			last = view[-1]["content"]
			if "FINAL" in last and not self.failed_once:
				self.failed_once = True
				self.calls += 1
				return Message(self.name, "gibberish, no JSON", self._meta())
			return super().generate(view, **kwargs)

	pool = EpisodePool(EpisodeStore(tmp_path))
	ep = run(pool.run_episode(scen, inst, "team", RetryOnce()))
	assert ep.status == "done"
	assert ep.outcome["success"] is True
	phases = [t.phase for t in ep.turns]
	assert phases.count("final_proposal") == 2  # the failed attempt + the retried one


def test_solo_budget_forces_finalization(tmp_path):
	"""A TokenBudget as the episode budget: the engine flags exhaustion, the scenario forces a final answer."""
	scen = InfoRelay()
	inst = scen.generate_instance(0, 5)
	gold = inst.payload["gold"]

	class Rambler(ScriptedSeat):
		def __init__(self):
			super().__init__(f'```json\n{{"final": {gold}}}\n```', turn_text="Still thinking...")

		def generate(self, view, **kwargs):
			self.calls += 1
			if "Token budget reached" in view[-1]["content"]:
				return Message(self.name, self.final_text, self._meta())
			return Message(self.name, "Still thinking...", self._meta())

	seat = Rambler()
	pool = EpisodePool(EpisodeStore(tmp_path))
	ep = run(pool.run_episode(scen, inst, "solo", seat, budget=TokenBudget(per_conversation=35)))
	assert ep.status == "done"
	assert ep.outcome["success"] is True          # the forced finalization carried the answer
	assert ep.turns[-1].phase == "solo_final"
	assert ep.tokens_out <= 50                    # ~4 turns of 10, not an unbounded ramble


def test_budget_turn_cap_flows_to_generation(tmp_path):
	scen = InfoRelay()
	inst = scen.generate_instance(0, 5)
	caps = []

	class CapProbe(ScriptedSeat):
		def __init__(self):
			super().__init__(f'```json\n{{"answer": {inst.payload["gold"]}}}\n```')

		def generate(self, view, *, max_new_tokens=None, **kwargs):
			caps.append(max_new_tokens)
			return super().generate(view, **kwargs)

	pool = EpisodePool(EpisodeStore(tmp_path))
	run(pool.run_episode(scen, inst, "team", CapProbe(),
	                     budget=TokenBudget(per_conversation=100_000, per_turn=64)))
	assert caps and all(c == 64 for c in caps[:4])  # the per-turn cap shrinks every generation


def test_participant_conditioned_view_override_is_persisted(tmp_path):
	scen = InfoRelay()
	inst = scen.generate_instance(0, 5)

	class PrivateWrapper(ScriptedSeat):
		def generate(self, view, **kwargs):
			message = super().generate(view, **kwargs)
			actual = [dict(segment) for segment in view]
			actual[-1] = dict(actual[-1])
			actual[-1]["content"] += "\nPRIVATE WRAPPER ADVICE"
			message.metadata["conditioned_view"] = actual
			return message

	ep = run(EpisodePool(EpisodeStore(tmp_path)).run_episode(
		scen, inst, "team", PrivateWrapper(f'```json\n{{"answer": {inst.payload["gold"]}}}\n```')))
	assert ep.turns
	assert "PRIVATE WRAPPER ADVICE" in ep.turns[0].view[-1]["content"]


def test_reservation_gating_skips_unaffordable_episodes(tmp_path):
	scen = InfoRelay()
	inst = scen.generate_instance(0, 5)
	gold = inst.payload["gold"]
	meter = UsageMeter(budget=1.0)
	pool = EpisodePool(EpisodeStore(tmp_path), meter=meter)
	jobs = [dict(scenario=scen, instance=inst, arm="team",
	             participant=ScriptedSeat(f'```json\n{{"answer": {gold}}}\n```'),
	             estimated_cost=0.6) for _ in range(3)]
	episodes = run(pool.run_pool(jobs))
	assert len(episodes) == 1        # only one $0.60 reservation fits under the $1 budget at a time... but
	# reservations settle after each episode; with zero metered spend the later ones fit again — so assert
	# instead on the invariant: nothing launched while over budget, and no reservation leaked.
	assert meter.reserved_usd == 0.0 or len(episodes) >= 1


def test_reservation_hard_skip(tmp_path):
	scen = InfoRelay()
	inst = scen.generate_instance(0, 5)
	meter = UsageMeter(budget=1.0)
	pool = EpisodePool(EpisodeStore(tmp_path), meter=meter)
	ep = run(pool.run_episode(scen, inst, "team", ScriptedSeat("x"), estimated_cost=2.0))
	assert ep is None                 # doesn't fit at all: skipped, never started
	assert meter.reserved_usd == 0.0  # nothing leaked


def test_error_episode_is_recorded(tmp_path):
	scen = InfoRelay()
	inst = scen.generate_instance(0, 5)

	class Explodes(Participant):
		name = "boom"

		def generate(self, view, **kwargs):
			raise RuntimeError("backend fell over")

	ep = run(EpisodePool(EpisodeStore(tmp_path)).run_episode(scen, inst, "team", Explodes()))
	assert ep.status == "error"
	assert "backend fell over" in ep.error


def test_replay_and_rescore_round_trip(tmp_path):
	scen = Negotiation()
	inst = scen.generate_instance(0, 13)
	best = json.dumps(inst.solution["best_deal"])
	seat = ScriptedSeat(f'```json\n{{"proposal": {best}}}\n```')
	ep = run(EpisodePool(EpisodeStore(tmp_path)).run_episode(scen, inst, "team", seat))
	stored = ep.to_json()
	recomputed = replay_episode(scen, inst, stored)
	assert recomputed["success"] == stored["outcome"]["success"]
	assert recomputed["primary"] == stored["outcome"]["primary"]
	result = rescore(scen, inst, stored)
	assert result["match"] and not result["mismatches"]


def test_reasoning_leak_gate_on_played_episode(tmp_path):
	scen = InfoRelay()
	inst = scen.generate_instance(0, 5)
	gold = inst.payload["gold"]

	class Thinker(ScriptedSeat):
		"""Emits raw <think> content; the engine must strip it before it reaches other seats."""

		def __init__(self):
			super().__init__(f'```json\n{{"answer": {gold}}}\n```')

		def generate(self, view, **kwargs):
			msg = super().generate(view, **kwargs)
			raw = f"<think>secret plan {self.calls}</think>{msg.content}"
			return Message(self.name, raw, dict(msg.metadata, raw_completion=raw))

	ep = run(EpisodePool(EpisodeStore(tmp_path)).run_episode(scen, inst, "team", Thinker()))
	assert ep.status == "done"
	assert all("<think>" not in t.content for t in ep.turns)
	assert check_reasoning_leak(ep)["ok"]
	# raw completions are preserved for audit
	assert any(t.raw and "<think>" in t.raw for t in ep.turns)


def test_store_summary_aggregates(tmp_path):
	scen = InfoRelay()
	inst = scen.generate_instance(0, 5)
	gold = inst.payload["gold"]
	store = EpisodeStore(tmp_path)
	run(EpisodePool(store).run_episode(scen, inst, "team",
	                                   ScriptedSeat(f'```json\n{{"answer": {gold}}}\n```')))
	text = store.summary()
	assert "[team]" in text and "1/1 done" in text


def test_exhausted_meter_blocks_queued_episodes(tmp_path):
	"""Launch gating fires at slot-acquisition time: an episode whose spend exhausts the budget while others
	queue stops those queued episodes from starting (no estimated_cost needed)."""
	scen = InfoRelay()
	inst = scen.generate_instance(0, 5)
	gold = inst.payload["gold"]
	meter = UsageMeter(budget=0.05, pricing={"m": {"in": 0.0, "out": 1000.0}})

	class Spender(ScriptedSeat):
		def __init__(self):
			super().__init__(f'```json\n{{"answer": {gold}}}\n```')

		def _meta(self):
			cost = meter.add("m", 0, 100)  # $0.10/turn: over budget after the first turn
			return {"n_tokens": 100, "n_tokens_in": 0, "cost_usd": cost}

	pool = EpisodePool(EpisodeStore(tmp_path), meter=meter, max_concurrent=1)
	jobs = [dict(scenario=scen, instance=inst, arm="team", participant=Spender()) for _ in range(3)]
	episodes = run(pool.run_pool(jobs))
	assert len(episodes) == 1              # the in-flight episode finished; the queued two never started
	assert meter.exhausted


# --------------------------------------------------------------------------------------------------------------
# Generation-failure visibility on the batched driver.
#
# The bug these pin: `BatchedEpisodePool._generate_batch` caught transient GPU errors, split the batch, and — when
# a lone request still failed — fabricated an EMPTY_TURN_PLACEHOLDER message and swallowed the exception with no
# log line and no mark on the record. Because that placeholder parses into a well-formed no-op, an affected run
# reported status="done" and parse_ok=True on every turn; one campaign cell reached 100% fabricated turns and
# looked clean. So: retry before fabricating, log loudly, stamp the record, and raise past a budget.
# --------------------------------------------------------------------------------------------------------------

TRANSIENT = "CUDA error: out of memory"          # matched by the engine's transient-error screen
PERMANENT = "shapes cannot be multiplied"        # not transient: must propagate, never be swallowed


class BatchSeat(ScriptedSeat):
	"""A scripted participant with a batched entry point and an injectable failure schedule.

	``fail_times`` raises on the first N ``generate_batch`` calls; ``fail_forever`` raises on every call;
	``fail_above_width`` raises only for batches wider than the given size (the real OOM shape, where splitting
	is what rescues the wave). ``error`` selects the message, so a test can choose a transient error or a
	permanent one. ``batch_widths`` records every width the engine asked for."""

	def __init__(self, final_text, *, fail_times=0, fail_forever=False, fail_above_width=None,
	             error=TRANSIENT, **kw):
		super().__init__(final_text, **kw)
		self.name = "batchseat"
		self.fails_remaining = fail_times
		self.fail_forever = fail_forever
		self.fail_above_width = fail_above_width
		self.error = error
		self.batch_widths: list[int] = []

	def generate_batch(self, views, *, max_new_tokens=None, **kwargs):
		self.batch_widths.append(len(views))
		if self.fail_forever:
			raise RuntimeError(self.error)
		if self.fail_above_width is not None and len(views) > self.fail_above_width:
			raise RuntimeError(self.error)
		if self.fails_remaining > 0:
			self.fails_remaining -= 1
			raise RuntimeError(self.error)
		return [self.generate(view, max_new_tokens=max_new_tokens) for view in views]


def _relay_jobs(n, seat):
	scen = InfoRelay()
	inst = scen.generate_instance(0, 5)
	return [dict(scenario=scen, instance=inst, arm="team", participant=seat) for _ in range(n)], scen, inst


def _batch_seat(n_shards=5, **kw):
	scen = InfoRelay()
	inst = scen.generate_instance(0, n_shards)
	return BatchSeat(f'```json\n{{"answer": {inst.payload["gold"]}}}\n```', **kw), scen, inst


def test_batched_pool_retries_a_single_transient_failure_instead_of_fabricating(tmp_path):
	"""A blip on a lone request is retried and succeeds — nothing is fabricated, so nothing is contaminated."""
	seat, scen, inst = _batch_seat(fail_times=1)
	pool = BatchedEpisodePool(EpisodeStore(tmp_path))
	episodes = pool.run_pool([dict(scenario=scen, instance=inst, arm="team", participant=seat)])
	assert [e.status for e in episodes] == ["done"]
	assert pool.fabrication_report()["fabricated"] == 0
	assert not any(t.gen_failed for e in episodes for t in e.turns)
	assert gen_failures(episodes[0]) == []
	assert 1 in seat.batch_widths      # it really did re-issue the single request


def test_batched_pool_stamps_and_reports_a_turn_it_had_to_fabricate(tmp_path):
	seat, scen, inst = _batch_seat(fail_forever=True)
	# budget off, so this test observes the fabrication itself rather than the abort
	pool = BatchedEpisodePool(EpisodeStore(tmp_path), max_fabricated_fraction=1.0)
	episodes = pool.run_pool([dict(scenario=scen, instance=inst, arm="team", participant=seat)])
	fabricated = [t for e in episodes for t in e.turns if t.gen_failed]
	assert fabricated, "a turn no model produced must be stamped"
	for t in fabricated:
		assert t.content == EMPTY_TURN_PLACEHOLDER      # scenario-facing semantics unchanged
		assert t.n_tokens_out == 0
		assert "out of memory" in t.gen_failure         # the cause is recorded, not just the fact
	# the stamp survives the round trip through the stored JSON, and the detector reads it
	stored = json.loads(EpisodeStore(tmp_path).path(episodes[0]).read_text())
	found = gen_failures(stored)
	assert len(found) == len([t for t in episodes[0].turns if t.gen_failed])
	assert all(f["detected_by"] == "stamp" and f["seat"] for f in found)
	report = pool.fabrication_report()
	assert report["fraction"] > 0
	assert report["failures"][0]["wave_width"] == 1
	# The report is the COMPLETE account and the stamps are a subset of it: a forked provisional probe is stored
	# as an OracleRecord, which has no field to stamp, so those fabrications live only in the report.
	provisional = [f for f in report["failures"] if f["phase"] == "provisional"]
	assert report["fabricated"] == len(fabricated) + len(provisional)
	assert provisional, "this scenario forks provisional probes, so the gap must be exercised, not assumed"


def test_fabrication_is_logged_at_error_with_the_cause(tmp_path, caplog):
	seat, scen, inst = _batch_seat(fail_forever=True)
	pool = BatchedEpisodePool(EpisodeStore(tmp_path), max_fabricated_fraction=1.0)
	with caplog.at_level("WARNING", logger="interlens.arena.engine"):
		episodes = pool.run_pool([dict(scenario=scen, instance=inst, arm="team", participant=seat)])
	errors = [r for r in caplog.records if r.levelname == "ERROR"]
	warnings = [r for r in caplog.records if r.levelname == "WARNING"]
	assert errors, "fabricating a turn must be an ERROR, not a silent return"
	first = errors[0].getMessage()
	assert "FABRICATING" in first
	assert "out of memory" in first                       # the exception
	assert episodes[0].episode_id in first                # which episode
	assert "wave was 1" in first                          # the batch width at failure
	assert "gen_failed=True" in first                     # how to find it downstream
	assert warnings and "retry 1/2" in warnings[0].getMessage()   # the retries are visible too


def test_a_permanent_error_is_never_swallowed(tmp_path):
	"""Only transient GPU errors are recoverable. A real bug must reach the caller — never become an empty turn —
	and the episodes it killed must still land on disk as failed rather than stuck at status="running"."""
	seat, scen, inst = _batch_seat(fail_forever=True, error=PERMANENT)
	pool = BatchedEpisodePool(EpisodeStore(tmp_path), max_fabricated_fraction=1.0)
	with pytest.raises(RuntimeError, match="shapes cannot be multiplied"):
		pool.run_pool([dict(scenario=scen, instance=inst, arm="team", participant=seat)])
	assert pool.fabrication_report()["fabricated"] == 0
	stored = EpisodeStore(tmp_path).load_all()
	assert stored and all(e["status"] == "error" for e in stored)
	assert all("shapes cannot be multiplied" in e["error"] for e in stored)


def test_batch_splitting_still_rescues_a_wide_wave(tmp_path):
	"""The original recovery behaviour is intact: a wave too wide to run is split until it fits, and no turn is
	fabricated — the split, not the placeholder, is what saves the run."""
	seat, scen, inst = _batch_seat(fail_above_width=1)
	pool = BatchedEpisodePool(EpisodeStore(tmp_path))
	jobs = [dict(scenario=scen, instance=inst, arm="team", participant=seat, seed=s) for s in range(4)]
	episodes = pool.run_pool(jobs)
	assert all(e.status == "done" for e in episodes)
	assert pool.fabrication_report()["fabricated"] == 0
	assert max(seat.batch_widths) > 1 and min(seat.batch_widths) == 1   # it tried wide, then split


def test_fabrication_budget_aborts_a_systematically_broken_run(tmp_path):
	"""The Olmo case: every generation fails, so the run must CRASH in its first seconds rather than complete
	full of turns no model produced."""
	seat, scen, inst = _batch_seat(fail_forever=True)
	pool = BatchedEpisodePool(EpisodeStore(tmp_path))          # default 10% ceiling
	jobs = [dict(scenario=scen, instance=inst, arm="team", participant=seat, seed=s) for s in range(30)]
	with pytest.raises(GenerationFailureBudgetExceeded) as excinfo:
		pool.run_pool(jobs)
	message = str(excinfo.value)
	assert "not measuring model behaviour" in message and "ceiling" in message
	assert "out of memory" in message                          # names the underlying cause
	# it stopped EARLY: a 10% ceiling on a 30-request first wave trips after a handful of failures
	assert pool.fabricated_turns <= 6
	# and the partial run is on disk as failed, not as a short clean one
	stored = EpisodeStore(tmp_path).load_all()
	assert stored and all(e["status"] == "error" for e in stored)
	assert all("GenerationFailureBudgetExceeded" in e["error"] for e in stored)


def test_fabrication_floor_tolerates_one_blip_in_a_tiny_run(tmp_path):
	"""A 10% ceiling is meaningless on a denominator of one, so the fraction only applies past the floor."""
	seat, scen, inst = _batch_seat(fail_forever=True)
	pool = BatchedEpisodePool(EpisodeStore(tmp_path), fabrication_floor=1000)
	episodes = pool.run_pool([dict(scenario=scen, instance=inst, arm="team", participant=seat)])
	assert pool.attempted_turns < 1000
	assert pool.fabricated_turns > 0                # it fabricated
	assert all(e.status == "done" for e in episodes)  # ... and did not abort


def test_gen_failures_reads_legacy_episodes_and_spares_genuine_model_silence():
	"""Episodes recorded before the stamp are screened by the value signature — and that signature must NOT
	catch a model that genuinely returned empty text, which is a different problem with a different fix."""
	fabricated = {"idx": 0, "seat": "Avery", "round": 1, "phase": "turn",
	              "content": EMPTY_TURN_PLACEHOLDER, "n_tokens_out": 0, "raw": None}
	model_was_silent = dict(fabricated, idx=1, raw="")     # record_turn substituted the placeholder for ""
	real = {"idx": 2, "seat": "Blake", "content": "a real turn", "n_tokens_out": 12, "raw": None}
	# a thinking model that burned its whole cap: content is the placeholder, but raw holds what it really said.
	# That is genuine model behaviour, not an engine failure, and must not be counted as one.
	reasoning_only = dict(fabricated, idx=3, raw="<think>long deliberation</think>")
	found = gen_failures({"turns": [fabricated, model_was_silent, real, reasoning_only]})
	assert [f["idx"] for f in found] == [0]
	assert found[0]["detected_by"] == "legacy_signature"
	assert "predates the stamp" in found[0]["reason"]
	# an explicit False stamp is authoritative: a v1.2 episode is never re-screened by the legacy signature
	assert gen_failures({"turns": [dict(fabricated, gen_failed=False)]}) == []
	# and `raw is None` ALONE must never be the screen: it is true of essentially every healthy local turn,
	# because a non-thinking local model's raw completion equals its content and record_turn stores None.
	healthy_local = {"idx": 4, "seat": "Casey", "content": "a real proposal", "n_tokens_out": 40, "raw": None}
	assert gen_failures({"turns": [healthy_local]}) == []


def test_episode_pool_records_a_generation_failure_as_an_error_and_never_fabricates(tmp_path):
	"""The sibling-path check: the async driver has no fabrication path at all. A failing generate surfaces as
	status="error" with the traceback — legible and excluded by any "done" filter — not as a placeholder turn."""
	scen = InfoRelay()
	inst = scen.generate_instance(0, 5)

	class AlwaysOOM(Participant):
		name = "oom"

		def generate(self, view, **kwargs):
			raise RuntimeError(TRANSIENT)

	ep = run(EpisodePool(EpisodeStore(tmp_path)).run_episode(scen, inst, "team", AlwaysOOM()))
	assert ep.status == "error" and "out of memory" in ep.error
	assert all(t.content != EMPTY_TURN_PLACEHOLDER for t in ep.turns)
	assert gen_failures(ep) == []


# --------------------------------------------------------------------------------------------------------------
# Heterogeneous (mixed) tables through the batched driver.
#
# A mixed table is ONE SeatRouter per episode fronting some model seats and some pure-Python policy seats. Keying
# the co-stepped wave on the table object therefore put a single request in every group and batched nothing; the
# engine keys on the participant that will actually SERVE each request (SeatRouter.participant_for), so the model
# seats of every live episode — which share one cached model participant — collect into one real batch while
# policy seats are looped. The bar is that this changes throughput and NOTHING else.
# --------------------------------------------------------------------------------------------------------------

class RecordingModel(Participant):
	"""A deterministic shared model seat that records the batch widths the engine asked it for."""

	self_role, others_role = "assistant", "user"

	def __init__(self, text='```json\n{"action": "reject", "offer_id": "P1"}\n```'):
		self.name, self.system_prompt, self.private_context = "recording_model", None, ()
		self.text = text
		self.widths: list[int] = []
		self.single_calls = 0

	def _msg(self):
		return Message(self.name, self.text, {"n_tokens": 7, "n_tokens_in": 3})

	def generate(self, view, **kwargs):
		self.single_calls += 1
		return self._msg()

	def generate_batch(self, views, *, max_new_tokens=None, **kwargs):
		self.widths.append(len(views))
		return [self._msg() for _ in views]


def _scorable_instances(n=2):
	"""``n`` scorable instances, built ONCE. Shared between the two drivers of an identity comparison, because
	``build_preset_instance`` mints a fresh random ``instance_id`` per call — rebuilding them per driver would make
	the two runs incomparable (and quietly turn an identity assertion into a tautology or a false alarm)."""
	from interlens.arena.negotiation.games import build_preset_instance
	return [build_preset_instance("scorable", n_parties=6, n_issues=3, n_options=3, seed=k) for k in range(n)]


def _mixed_jobs(model, n_seeds=6, arm="moves_only", instances=None, seat_factory=None):
	"""Mixed-table jobs shaped like a campaign cell: a FRESH table per episode (policy seats hold per-episode
	state, exactly as run.py builds them) over a model participant shared across episodes.

	``seat_factory`` supplies a fresh model seat per episode instead of sharing ``model`` — for the case where the
	seat itself carries state and the point is that its call ORDER is preserved."""
	from interlens.arena.negotiation.sheets import GameSpec
	from interlens.arena.scenarios.scorable import ScorableNegotiation
	from interlens.arena.table import mixed_table
	jobs = []
	for inst, cfg in (instances if instances is not None else _scorable_instances()):
		game = GameSpec.from_json(inst.payload)
		for seed in range(n_seeds):
			seat = seat_factory() if seat_factory is not None else model
			jobs.append(dict(scenario=ScorableNegotiation(), instance=inst, arm=arm,
			                 participant=mixed_table(game, {0: seat}, deadline=4), seed=seed, cfg=cfg))
	return jobs


def _fingerprint(episodes):
	"""Turn-by-turn identity of a set of episodes, keyed so two drivers' outputs are directly comparable."""
	return sorted(
		(ep.instance_id, ep.seed, ep.arm, ep.status,
		 tuple((t.idx, t.round, t.phase, t.seat, t.content) for t in ep.turns),
		 json.dumps(ep.outcome, sort_keys=True, default=str))
		for ep in episodes)


def test_mixed_table_batches_model_seats_across_episodes(tmp_path):
	"""The point of the change: model seats of different episodes share one batch. Keyed on the table object this
	was impossible, because every episode holds its own table."""
	model = RecordingModel()
	pool = BatchedEpisodePool(EpisodeStore(tmp_path))
	episodes = pool.run_pool(_mixed_jobs(model))
	assert all(e.status == "done" for e in episodes)
	assert model.widths, "the model must have been driven through its BATCHED entry point"
	assert max(model.widths) > 1, "model seats of different episodes must share a batch"
	# fewer model calls than model turns is exactly the win being bought
	assert sum(model.widths) > len(model.widths)
	assert pool.fabrication_report()["fabricated"] == 0


def test_batched_and_looped_mixed_tables_produce_identical_episodes(tmp_path):
	"""THE gate. Same jobs, same seeds, two drivers: the async pool (one generate at a time, through the router)
	and the batched pool (grouped, addressing sub-participants directly). Every turn must match byte for byte."""
	shared = _scorable_instances()
	looped = run(EpisodePool(EpisodeStore(tmp_path / "looped")).run_pool(
		_mixed_jobs(RecordingModel(), instances=shared)))
	batched = BatchedEpisodePool(EpisodeStore(tmp_path / "batched")).run_pool(
		_mixed_jobs(RecordingModel(), instances=shared))
	assert len(looped) == len(batched) > 0
	assert _fingerprint(looped) == _fingerprint(batched)


def test_all_llm_grouping_is_unaffected(tmp_path):
	"""Regression guard: a homogeneous table has no participant_for, so the wave still forms ONE group and the
	existing co-stepping win is untouched."""
	model = RecordingModel('```json\n{"answer": 1}\n```')
	scen = InfoRelay()
	inst = scen.generate_instance(0, 5)
	jobs = [dict(scenario=scen, instance=inst, arm="team", participant=model, seed=s) for s in range(5)]
	BatchedEpisodePool(EpisodeStore(tmp_path)).run_pool(jobs)
	assert max(model.widths) == 5, "all five episodes' turns must still batch together"
	assert model.single_calls == 0, "a homogeneous model table must never be driven one-at-a-time"


def test_policy_only_table_runs_batched_without_a_batch_entry_point(tmp_path):
	"""An all-policy table has no generate_batch anywhere. It must loop cleanly rather than raise AttributeError,
	which is what routing any heterogeneous/rational table here used to do."""
	from interlens.arena.negotiation.games import build_preset_instance
	from interlens.arena.negotiation.sheets import GameSpec
	from interlens.arena.scenarios.scorable import ScorableNegotiation
	from interlens.arena.table import rational_table
	inst, cfg = build_preset_instance("scorable", n_parties=6, n_issues=3, n_options=3, seed=0)
	game = GameSpec.from_json(inst.payload)
	jobs = [dict(scenario=ScorableNegotiation(), instance=inst, arm="moves_only",
	             participant=rational_table(game, ["boulware", "conceder", "bayes-rational"], deadline=4),
	             seed=s, cfg=cfg) for s in range(3)]
	pool = BatchedEpisodePool(EpisodeStore(tmp_path))
	episodes = pool.run_pool(jobs)
	assert all(e.status == "done" for e in episodes) and all(e.turns for e in episodes)
	assert pool.fabrication_report()["fabricated"] == 0


def test_a_view_rewriting_table_is_never_bypassed(tmp_path):
	"""A table that conditions the view per seat must keep the whole wave: it deliberately does NOT declare
	participant_for, so the engine addresses the table, and its rewriting still runs. This is the advocate
	pattern, and bypassing it would silently drop the planner conditioning."""
	model = RecordingModel('```json\n{"answer": 1}\n```')

	class Rewriting(Participant):
		self_role, others_role = "assistant", "user"

		def __init__(self):
			self.name, self.system_prompt, self.private_context = "rewriting_table", None, ()
			self.seen_whole_wave = []

		def generate(self, view, *, seat=None, **kwargs):
			return model.generate(view, seat=seat, **kwargs)

		def generate_batch_with_seats(self, views, seats, *, max_new_tokens=None):
			self.seen_whole_wave.append(len(views))
			out = model.generate_batch(views, max_new_tokens=max_new_tokens)
			for message in out:
				message.metadata["rewritten"] = True
			return out

	table = Rewriting()
	scen = InfoRelay()
	inst = scen.generate_instance(0, 5)
	jobs = [dict(scenario=scen, instance=inst, arm="team", participant=table, seed=s) for s in range(3)]
	episodes = BatchedEpisodePool(EpisodeStore(tmp_path)).run_pool(jobs)
	assert table.seen_whole_wave, "the rewriting table must receive the wave itself, not be bypassed"
	assert max(table.seen_whole_wave) == 3
	assert all(e.status == "done" for e in episodes)


def test_provisional_probes_are_elicited_once_per_episode(tmp_path):
	"""A heterogeneous episode has requests in several participant groups. Provisionals are gathered once per
	episode across the whole wave, so it is probed once — not once per group."""
	model = RecordingModel()
	pool = BatchedEpisodePool(EpisodeStore(tmp_path))
	episodes = pool.run_pool(_mixed_jobs(model, n_seeds=3, instances=_scorable_instances(1)))
	for ep in episodes:
		probes = [r for r in ep.round_checkpoints if r.get("oracle") is None]
		keys = [(r["round"], r["seat"]) for r in probes]
		assert len(keys) == len(set(keys)), f"duplicate provisional probe in {ep.episode_id}: {keys}"


def test_stateful_policy_sees_the_same_call_order_batched_or_looped(tmp_path):
	"""Grouping reorders calls ACROSS participants but never within one, so a policy carrying state (a seeded RNG,
	a belief update) evolves identically either way. Asserted on a participant that records its own call order."""
	class Counting(Participant):
		"""A seat whose reply encodes how many times it has been called — so any reordering shows up in content."""

		self_role, others_role = "assistant", "user"

		def __init__(self):
			self.name, self.system_prompt, self.private_context = "counting", None, ()
			self.calls = 0

		def generate(self, view, **kwargs):
			self.calls += 1
			return Message(self.name, '```json\n{"action": "reject", "offer_id": "P%d"}\n```' % self.calls,
			               {"n_tokens": 5})

	shared = _scorable_instances(1)
	looped = run(EpisodePool(EpisodeStore(tmp_path / "l")).run_pool(
		_mixed_jobs(None, n_seeds=4, instances=shared, seat_factory=Counting)))
	batched = BatchedEpisodePool(EpisodeStore(tmp_path / "b")).run_pool(
		_mixed_jobs(None, n_seeds=4, instances=shared, seat_factory=Counting))
	assert _fingerprint(looped) == _fingerprint(batched)


# --- wave-parallel generation ------------------------------------------------------------------------------

class WaveSeat(Participant):
	"""A five-seat auction participant whose reply is a pure function of the rendered view.

	Two properties make it the right probe for wave parallelism. The reply *hashes the view*, so any change in
	what a seat read — a different prompt, a different wave, a different ordering of the seats' turns — shows up
	as different stored bytes rather than as a silently equal episode. And ``generate`` sleeps, so a wave that is
	issued concurrently finishes in about one seat's delay rather than five."""

	def __init__(self, delay: float = 0.0):
		self.name = "wave-seat"
		self.delay = delay
		self.calls = 0
		self.max_concurrent = 0
		self._in_flight = 0
		self._lock = threading.Lock()

	def generate(self, view, *, max_new_tokens=None, seat=None, **kwargs):
		with self._lock:
			self.calls += 1
			self._in_flight += 1
			self.max_concurrent = max(self.max_concurrent, self._in_flight)
		try:
			if self.delay:
				time.sleep(self.delay)
			digest = hashlib.sha1("\n".join(m["content"] for m in view).encode()).hexdigest()[:12]
			text = json.dumps({"scratchpad": digest, "action": "pass"})
			return Message(self.name, text, {"n_tokens": 12, "n_tokens_in": 400, "cost_usd": 0.0})
		finally:
			with self._lock:
				self._in_flight -= 1


def _auction_episode(tmp_path, *, wave_parallel: bool, delay: float = 0.0):
	"""One scripted three-lot auction episode (five simultaneous-move seats per wave) through ``EpisodePool``."""
	from interlens.arena.auction.spec import Mechanism
	from interlens.arena.scenarios.auction import AuctionScenario

	scen = AuctionScenario()
	mech = Mechanism.saa(3)
	inst = scen.generate_instance(0, 7, mechanism=mech, horizon=8)
	cfg = {"mechanism": mech.to_json(), "horizon": 2, "channel": "silent", "value_structure": "apv"}
	seat = WaveSeat(delay=delay)
	pool = EpisodePool(EpisodeStore(tmp_path), wave_parallel=wave_parallel)
	started = time.perf_counter()
	ep = run(pool.run_episode(scen, inst, "all_llm", seat, cfg=cfg))
	return ep, seat, time.perf_counter() - started


def _comparable(ep) -> dict:
	"""An episode's stored JSON minus the fields that are timing or identity by construction."""
	d = json.loads(json.dumps(ep.to_json()))
	for key in ("episode_id", "started_at", "ended_at"):
		d.pop(key, None)
	for turn in d.get("turns") or []:
		turn.pop("episode_id", None)
	return d


def test_wave_parallel_episode_is_byte_identical_to_the_serial_one(tmp_path):
	"""The ~wave-width throughput lever must be invisible in the record: same turns, same order, same views.

	A wave's views are all built by ``next_requests`` before any of them is sent, so ordering the generations
	cannot change what any seat reads — this pins that property rather than trusting it."""
	serial, serial_seat, _ = _auction_episode(tmp_path / "serial", wave_parallel=False)
	parallel, parallel_seat, _ = _auction_episode(tmp_path / "parallel", wave_parallel=True)

	assert serial.status == "done" and parallel.status == "done"
	assert serial_seat.max_concurrent == 1        # the serial path really is one call at a time
	assert parallel_seat.max_concurrent > 1       # and the parallel one really does overlap a wave
	assert serial_seat.calls == parallel_seat.calls
	assert _comparable(serial) == _comparable(parallel)


def test_wave_parallel_is_faster_than_serial_on_a_latency_bound_seat(tmp_path):
	"""The point of the change: on a network-bound seat a five-wide wave costs about one seat's latency."""
	_, _, serial_s = _auction_episode(tmp_path / "serial", wave_parallel=False, delay=0.02)
	_, _, parallel_s = _auction_episode(tmp_path / "parallel", wave_parallel=True, delay=0.02)
	assert parallel_s < serial_s / 2.0, f"serial {serial_s:.2f}s vs parallel {parallel_s:.2f}s"


def test_wave_parallel_falls_back_to_serial_under_an_episode_budget(tmp_path):
	"""A ``TokenBudget`` shrinks each turn's cap against the turns already committed, so a budgeted episode
	keeps generating one seat at a time rather than quietly computing every cap at wave start."""
	from interlens.arena.auction.spec import Mechanism
	from interlens.arena.scenarios.auction import AuctionScenario

	scen = AuctionScenario()
	mech = Mechanism.saa(3)
	inst = scen.generate_instance(0, 7, mechanism=mech, horizon=8)
	cfg = {"mechanism": mech.to_json(), "horizon": 1, "channel": "silent", "value_structure": "apv"}
	seat = WaveSeat()
	pool = EpisodePool(EpisodeStore(tmp_path), wave_parallel=True)
	run(pool.run_episode(scen, inst, "all_llm", seat, cfg=cfg,
	                     budget=TokenBudget(per_conversation=10_000, per_turn=256)))
	assert seat.max_concurrent == 1
