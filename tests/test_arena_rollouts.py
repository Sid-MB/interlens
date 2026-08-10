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

# [fix: rational_agents orig (results review)] 2026-08-10 — rollout-set management.
"""Rollout-set semantics: open-or-create, the config-fingerprint append refusal, dedupe/resume, and summary.

Everything here is pure CPU: the seats are computable policies (``rational_table``), so a real episode plays
end to end through ``ScorableNegotiation`` and the async ``EpisodePool`` with no GPU and no API key.
"""
from __future__ import annotations

import json

import pytest

from interlens.arena.engine import EMPTY_TURN_PLACEHOLDER
from interlens.arena.negotiation.sheets import GameSpec, ScoreSheet
from interlens.arena.negotiation.space import DealSpace, Issue
from interlens.arena.rollouts import (MANIFEST_NAME, RolloutConfigMismatch, RolloutSet,
                                      config_fingerprint, rollout)
from interlens.arena.scenarios.scorable import ScorableNegotiation
from interlens.arena.schema import Instance, new_id
from interlens.arena.table import rational_table

CONFIG = {"model": "policy:boulware+conceder+tough", "scaffold": "canonical", "info": "full",
          "arms": ["moves_chat"]}


def make_instance(seed: int) -> Instance:
	"""A tiny fixed 3-party game (the shape ``test_arena_scorable`` uses), one instance per ``seed``."""
	space = DealSpace((Issue("Site", ("North", "South")), Issue("Fund", ("Low", "Mid", "High"))))
	sheets = (ScoreSheet("Alpha", ((10.0, 0.0), (0.0, 3.0, 6.0)), threshold=5.0),
	          ScoreSheet("Beta", ((0.0, 10.0), (0.0, 3.0, 6.0)), threshold=5.0),
	          ScoreSheet("Gamma", ((5.0, 5.0), (6.0, 3.0, 0.0)), threshold=3.0))
	spec = GameSpec(space, sheets, rounds=2, info="full", chat=True, proposer=0, veto=None, min_accept=None)
	return Instance(f"{new_id('rollout-test')}-{seed}", ScorableNegotiation.name, 0, seed,
	                payload=spec.to_json(), ceiling=1.0, floor=0.0, solution={})


def seat_lineup(instance, arm, seed):
	"""Fresh policy seats per episode (their belief/offer state is per-episode mutable)."""
	game = GameSpec.from_json(instance.payload)
	return rational_table(game, ["boulware", "conceder", "tough"], deadline=game.rounds)


def run(out, instances, seeds, **kw) -> RolloutSet:
	return rollout(scenario=ScorableNegotiation(), instances=instances, participant=seat_lineup,
	               out=out, seeds=seeds, arms=["moves_chat"], config=kw.pop("config", CONFIG),
	               concurrency=4, **kw)


@pytest.fixture(scope="module")
def instances():
	return [make_instance(s) for s in range(2)]


# ------------------------------------------------------------------------------- open-or-create --
def test_open_or_create_writes_a_manifest_and_reopens_it(tmp_path):
	root = tmp_path / "set"
	rs = RolloutSet(root, config=CONFIG, model="policy:zoo", scenario="scorable_negotiation")
	assert (root / MANIFEST_NAME).exists()
	assert rs.fingerprint == config_fingerprint(CONFIG)

	again = RolloutSet(root)                      # reopen: the manifest on disk is the authority
	assert again.fingerprint == rs.fingerprint
	assert again.manifest["model"] == "policy:zoo"
	assert again.keys() == set()

	with pytest.raises(FileNotFoundError):
		RolloutSet(tmp_path / "absent", create=False)


def test_reopening_ignores_a_passed_config_but_records_artifacts(tmp_path):
	root = tmp_path / "set"
	RolloutSet(root, config=CONFIG)
	reopened = RolloutSet(root, config={"totally": "different"})
	assert reopened.fingerprint == config_fingerprint(CONFIG)   # manifest wins; the mismatch is caught on append
	reopened.record_artifacts(hf_dataset="https://huggingface.co/datasets/x/y")
	assert json.loads((root / MANIFEST_NAME).read_text())["artifacts"]["hf_dataset"].endswith("x/y")


# --------------------------------------------------------------------------------- run + resume --
def test_rollout_runs_episodes_and_resume_skips_completed_keys(tmp_path, instances):
	out = tmp_path / "pilot"
	rs = run(out, instances, seeds=[0])
	assert rs.summary()["n_episodes"] == 2                      # 2 instances x 1 seed x 1 arm
	assert rs.keys() == {(i.instance_id, 0, "moves_chat") for i in instances}
	assert [inv["added"] for inv in rs.manifest["invocations"]] == [2]

	# the same call again is a no-op: nothing planned is missing, so no episode is replayed
	same = run(out, instances, seeds=[0])
	assert same.summary()["n_episodes"] == 2
	assert len(same.manifest["invocations"]) == 1               # no second append recorded

	# widening the seed list runs ONLY the new (instance, seed) pairs
	wider = run(out, instances, seeds=[0, 1])
	assert wider.summary()["n_episodes"] == 4
	assert wider.manifest["invocations"][-1]["added"] == 2
	assert (out / "instances").is_dir() and len(list((out / "instances").glob("*.json"))) == 2


def test_load_instances_round_trips_the_saved_bank(tmp_path, instances):
	"""The set's own bank is reusable, which is what keeps a resume from replaying everything: instance ids are
	uuid-based, so regenerating the same games would mint new ids and match nothing."""
	rs = run(tmp_path / "pilot", instances, seeds=[0])
	loaded = rs.load_instances()
	assert sorted(i.instance_id for i in loaded) == sorted(i.instance_id for i in instances)
	assert rs.missing(loaded, [0], ["moves_chat"]) == []
	assert RolloutSet(tmp_path / "fresh", config=CONFIG).load_instances() == []


def test_missing_lists_exactly_the_unplayed_keys(tmp_path, instances):
	out = tmp_path / "pilot"
	rs = run(out, instances, seeds=[0])
	assert rs.missing(instances, [0], ["moves_chat"]) == []
	assert sorted(rs.missing(instances, [0, 1], ["moves_chat"])) == sorted(
		(i.instance_id, 1, "moves_chat") for i in instances)


# ----------------------------------------------------------------------- fingerprint enforcement --
def test_rollout_refuses_a_set_built_under_a_different_config(tmp_path, instances):
	out = tmp_path / "pilot"
	run(out, instances, seeds=[0])
	before = len(list((out / "episodes").glob("**/*.json")))
	with pytest.raises(RolloutConfigMismatch) as exc:
		run(out, instances, seeds=[1], config={**CONFIG, "scaffold": "terse"})
	assert "scaffold" in str(exc.value)
	# refused BEFORE anything ran: not one extra episode on disk
	assert len(list((out / "episodes").glob("**/*.json"))) == before


def test_append_refuses_a_mismatched_config_and_writes_nothing(tmp_path, instances):
	out = tmp_path / "pilot"
	rs = run(out, instances, seeds=[0])
	foreign = run(tmp_path / "other", instances, seeds=[1], config={**CONFIG, "info": "private"})
	episodes = foreign.episodes()
	with pytest.raises(RolloutConfigMismatch):
		rs.append(episodes, config={**CONFIG, "info": "private"})
	assert rs.summary()["n_episodes"] == 2
	assert rs.manifest["mismatched_appends"] == []


def test_allow_mismatch_accepts_but_stamps_every_row_and_the_manifest(tmp_path, instances):
	out = tmp_path / "pilot"
	rs = run(out, instances, seeds=[0])
	foreign = run(tmp_path / "other", instances, seeds=[1], config={**CONFIG, "info": "private"})
	result = rs.append(foreign.episodes(), config={**CONFIG, "info": "private"}, allow_mismatch=True)

	assert result["added"] == 2 and result["mismatch"] is True
	assert rs.summary()["n_episodes"] == 4
	assert rs.summary()["n_mismatched_appends"] == 1
	assert rs.manifest["mismatched_appends"][0]["differing_keys"] == ["info"]
	stamped = [ep for ep in rs.episodes() if (ep.get("cell_cfg") or {}).get("rollout_config_mismatch")]
	assert len(stamped) == 2
	assert "MIXED" in rs.summary_text()


# ------------------------------------------------------------------------------------- de-duping --
def test_append_dedupes_on_instance_seed_arm(tmp_path, instances):
	out = tmp_path / "pilot"
	rs = run(out, instances, seeds=[0])
	episodes = rs.episodes()
	# the same episodes offered again, and a fresh record that only differs by episode_id: both are the same
	# planned rollout, so neither is added
	duplicate = {**episodes[0], "episode_id": new_id("dupe")}
	result = rs.append(episodes + [duplicate], config=CONFIG)
	assert result == {"added": 0, "skipped": 3, "keys": [], "mismatch": False}
	assert rs.summary()["n_episodes"] == 2


# --------------------------------------------------------------------------------------- summary --
def test_summary_reports_counts_scores_and_a_clean_fabrication_audit(tmp_path, instances):
	rs = run(tmp_path / "pilot", instances, seeds=[0, 1])
	s = rs.summary()
	assert s["n_episodes"] == 4 == s["n_keys"]
	assert s["status_counts"] == {"done": 4}
	assert s["by_arm"] == {"moves_chat": 4}
	assert 0.0 <= s["success_rate"] <= 1.0
	assert s["n_scored"] == 4 and s["mean_primary"] is not None
	assert s["fabricated_turns"] == 0 and s["episodes_with_fabricated_turns"] == 0
	assert s["cost_usd"] == 0.0                                   # policy seats cost nothing
	assert "fabricated turns: 0" in rs.summary_text()


# --------------------------------------------------------------------- the placeholder budget (note 0041) --
def burned_turn(idx: int, rnd: int) -> dict:
	"""A turn where the model spent its whole 2,048-token cap inside an unterminated `<think>` and emitted no
	visible action. Note the two naive screens it passes: parse_ok True, content non-empty."""
	return {"idx": idx, "round": rnd, "phase": "turn", "seat": "Avery", "content": EMPTY_TURN_PLACEHOLDER,
	        "parsed_action": {"atype": "none"}, "parse_ok": True, "n_tokens_out": 2048, "cap": 2048,
	        "raw": "<think>\nOkay, let me work through this as Avery. The offers on the table are",
	        "stop_reason": None, "gen_failed": False}


def healthy_turn(idx: int, rnd: int) -> dict:
	return {"idx": idx, "round": rnd, "phase": "turn", "seat": "Blake", "content": '```json\n{"action": "pass"}\n```',
	        "parsed_action": {"atype": "pass"}, "parse_ok": True, "n_tokens_out": 96, "cap": 2048,
	        "raw": None, "stop_reason": None, "gen_failed": False}


def episode_with(turns: list[dict], instance_id: str = "inst-a", seed: int = 0) -> dict:
	return {"episode_id": new_id("ep"), "scenario": "s", "arm": "moves_chat", "model": "m", "level": 0,
	        "instance_id": instance_id, "seed": seed, "seats": [], "cell": "base", "cell_cfg": {},
	        "turns": turns, "round_checkpoints": [], "outcome": {"success": True, "primary": 1.0},
	        "status": "done", "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "schema_version": "v1.2"}


def test_burned_cap_turns_are_caught_though_every_standard_gate_reads_clean(tmp_path):
	"""The note-0041 failure: a quarter of turns say nothing while fabrication, parse_ok and empty-content all
	report perfect health. The placeholder budget is the only gate that sees it."""
	rs = RolloutSet(tmp_path / "silent", config=CONFIG)
	turns = [healthy_turn(0, 1), healthy_turn(1, 1), burned_turn(2, 2), burned_turn(3, 3)]
	rs.append([episode_with(turns)], config=CONFIG)
	s = rs.summary()

	assert s["fabricated_turns"] == 0                       # the engine did its job — correctly clean
	assert all(t["parse_ok"] for t in turns)                # and parse_ok is no help either
	assert s["placeholder_rate"] == 0.5
	assert s["turn_signature_rates"]["empty_gen"] == 0.5    # burned cap, not engine failure
	assert s["turn_signature_rates"]["gen_failed"] == 0.0
	assert s["turn_signature_rates"]["truncated"] == 0.5    # local seats have no stop_reason; cap hit carries it
	assert s["placeholder_budget_exceeded"] is True
	assert s["episodes_with_placeholder_turns"] == 1

	text = rs.summary_text()
	assert "PLACEHOLDER BUDGET EXCEEDED" in text and "burned cap" in text


def test_the_two_placeholder_causes_are_separated(tmp_path):
	"""Same placeholder string, different remedies: raising the cap cannot fix an engine fabrication."""
	rs = RolloutSet(tmp_path / "mixed", config=CONFIG)
	fabricated = {**burned_turn(0, 1), "n_tokens_out": 0, "raw": None, "gen_failed": True,
	              "gen_failure": "CUDA OOM"}
	rs.append([episode_with([fabricated, burned_turn(1, 2)])], config=CONFIG)
	s = rs.summary()
	assert s["placeholder_rate"] == 1.0
	assert s["turn_signature_rates"]["gen_failed"] == 0.5
	assert s["turn_signature_rates"]["empty_gen"] == 0.5
	assert s["fabricated_turns"] == 1


def test_placeholder_rate_is_broken_down_by_round(tmp_path):
	"""Budget exhaustion grows with transcript length, so a pooled figure hides it and a short read misses it
	entirely — round 1 is clean here while round 3 is fully silent."""
	rs = RolloutSet(tmp_path / "byround", config=CONFIG)
	rs.append([episode_with([healthy_turn(0, 1), healthy_turn(1, 1),
	                         healthy_turn(2, 2), burned_turn(3, 2),
	                         burned_turn(4, 3), burned_turn(5, 3)])], config=CONFIG)
	s = rs.summary()
	assert s["placeholder_rate_by_round"] == {1: 0.0, 2: 0.5, 3: 1.0}
	assert s["worst_round_placeholder_rate"] == 1.0


def test_a_late_round_over_budget_is_flagged_even_when_pooled_is_clean(tmp_path):
	"""The under-detection shape: 1 silent turn in 60 pools to 1.7% (under a 2% budget) but round 3 is at 25%."""
	rs = RolloutSet(tmp_path / "late", config=CONFIG)
	turns = [healthy_turn(i, 1 + i // 20) for i in range(59)] + [burned_turn(59, 3)]
	rs.append([episode_with(turns)], config=CONFIG)
	s = rs.summary()
	assert s["placeholder_budget_exceeded"] is False
	assert s["worst_round_placeholder_rate"] > s["placeholder_budget"]
	assert "this failure grows with transcript length" in rs.summary_text()


def test_the_budget_is_configurable_and_never_raises(tmp_path):
	rs = RolloutSet(tmp_path / "silent", config=CONFIG)
	rs.append([episode_with([healthy_turn(0, 1), burned_turn(1, 2)])], config=CONFIG)
	assert rs.summary(placeholder_budget=0.9)["placeholder_budget_exceeded"] is False
	assert rs.summary(placeholder_budget=0.0)["placeholder_budget_exceeded"] is True


def test_the_health_verdict_is_stamped_into_the_manifest(tmp_path):
	"""A gate that only prints is a gate nobody finds later, so the verdict is durable on the manifest."""
	rs = RolloutSet(tmp_path / "silent", config=CONFIG)
	rs.append([episode_with([healthy_turn(0, 1), burned_turn(1, 2)])], config=CONFIG)
	health = json.loads((tmp_path / "silent" / MANIFEST_NAME).read_text())["turn_health"]
	assert health["placeholder_budget_exceeded"] is True
	assert health["placeholder_rate"] == 0.5
	assert health["turn_signature_counts"]["empty_gen"] == 1


def test_a_clean_real_run_reports_both_gates_clean(tmp_path, instances):
	rs = run(tmp_path / "pilot", instances, seeds=[0])
	s = rs.summary()
	assert s["n_turns"] > 0
	assert s["placeholder_rate"] == 0.0 and s["placeholder_budget_exceeded"] is False
	assert s["turn_signature_rates"]["empty_gen"] == 0.0
	assert "placeholder turns: 0/" in rs.summary_text()


def test_summary_on_an_empty_set_is_well_defined(tmp_path):
	s = RolloutSet(tmp_path / "empty", config=CONFIG).summary()
	assert s["n_episodes"] == 0 and s["success_rate"] is None and s["mean_primary"] is None
	assert s["n_turns"] == 0 and s["placeholder_rate"] == 0.0
	assert s["placeholder_budget_exceeded"] is False and s["placeholder_rate_by_round"] == {}


def test_engine_batched_refuses_a_per_episode_factory(tmp_path, instances):
	with pytest.raises(ValueError, match="factory"):
		run(tmp_path / "pilot", instances, seeds=[0], engine="batched")
