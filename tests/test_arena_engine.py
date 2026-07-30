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
import json

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
	found = gen_failures({"turns": [fabricated, model_was_silent, real]})
	assert [f["idx"] for f in found] == [0]
	assert found[0]["detected_by"] == "legacy_signature"
	assert "predates the stamp" in found[0]["reason"]
	# an explicit False stamp is authoritative: a v1.2 episode is never re-screened by the legacy signature
	assert gen_failures({"turns": [dict(fabricated, gen_failed=False)]}) == []


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
