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

"""The Inspect adapter, run against inspect-ai's mockllm provider (skipped when the ``inspect`` extra is not
installed; no network). Covers both communication modes, scoring, per-sample concurrency, and cross-episode
state isolation."""
from __future__ import annotations

import pytest

inspect_ai = pytest.importorskip("inspect_ai")

from inspect_ai import eval as inspect_eval  # noqa: E402
from inspect_ai.model import ModelOutput, get_model  # noqa: E402

from interlens.arena.scenarios import InfoRelay  # noqa: E402
from interlens.arena.inspect import info_relay, negotiation  # noqa: E402


@pytest.fixture(autouse=True)
def _writable_inspect_dirs(tmp_path, monkeypatch):
	# inspect-ai writes traces/logs under XDG data dirs, which may be read-only on CI
	monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
	monkeypatch.setenv("INSPECT_LOG_DIR", str(tmp_path / "logs"))


def _outputs(text: str, n: int):
	return [ModelOutput.from_content(model="mockllm/model", content=text) for _ in range(n)]


def _gold(seed: int = 1) -> int:
	return InfoRelay().generate_instance(0, seed).payload["gold"]


def test_round_robin_task_scores_correct_answer():
	answer = f'My notes say things. ```json\n{{"answer": {_gold()}}}\n```'
	model = get_model("mockllm/model", custom_outputs=_outputs(answer, 40))
	log = inspect_eval(info_relay(n_instances=1, communication="round_robin"), model=model,
	                   display="none")[0]
	assert log.status == "success"
	sample = log.samples[0]
	assert sample.scores["scenario_scorer"].value["success"] == 1.0
	assert sample.scores["scenario_scorer"].value["primary"] == 1.0
	# the multi-agent flow is mirrored into the sample messages, seat-attributed, for inspect view
	seat_turns = [m for m in sample.messages if m.role == "assistant"]
	assert seat_turns and seat_turns[0].text.startswith("[")
	# outcome + usage + ids in the store for downstream analysis
	assert sample.store.get("arena:outcome")["success"] is True
	assert sample.store.get("arena:instance_id") == sample.id


def test_messaging_is_the_default_and_delivers_and_scores():
	# messaging is the package default: no communication= argument here, and the scenario declares it
	from interlens.arena.scenario import Scenario
	assert Scenario.default_communication == "messaging"
	text = ('Update. ```json\n{"send_message": {"recipient": "Blake", "content": "x-check", '
	        '"priority": "high"}}\n```\n'
	        f'Answer: ```json\n{{"answer": {_gold()}}}\n```')
	model = get_model("mockllm/model", custom_outputs=_outputs(text, 60))
	log = inspect_eval(info_relay(n_instances=1, messaging_turns=8),
	                   model=model, display="none")[0]
	assert log.status == "success"
	sample = log.samples[0]
	assert sample.scores["scenario_scorer"].value["success"] == 1.0
	usage = sample.store.get("arena:usage")
	assert usage and usage["by_author"]  # per-seat usage recorded


def test_ten_concurrent_episodes_no_state_leakage():
	"""The concurrency requirement: >=10 samples in flight through inspect eval, each episode isolated —
	verified via instance/episode id integrity across the logs."""
	log = inspect_eval(info_relay(n_instances=10, communication="round_robin"), model="mockllm/model",
	                   max_samples=10, display="none")[0]
	assert log.status == "success"
	assert len(log.samples) == 10
	episode_ids = {s.store.get("arena:episode_id") for s in log.samples}
	assert len(episode_ids) == 10                      # no shared episode state across samples
	for s in log.samples:
		assert s.store.get("arena:instance_id") == s.id  # each sample scored its own instance


def test_negotiation_task_builds_both_generators():
	assert len(negotiation(n_instances=2).dataset) == 2
	task = negotiation(n_instances=2, n_parties=3)
	assert len(task.dataset) == 2
	assert task.dataset[0].metadata["instance"]["payload"]["n_parties"] == 3


def test_turn_reasoning_renders_as_content_block():
	"""A turn carrying a reasoning record surfaces it as a first-class ContentReasoning block on the
	assistant message (the model event inspect view renders), redacted=True when the provider withheld
	or summarized the stream."""
	from inspect_ai.model import ContentReasoning, ContentText

	from interlens.arena.inspect.adapter import _turn_message

	turn = {"seat": "Avery", "round": 1, "phase": "discuss", "content": "I propose 4.",
	        "reasoning": "summarized thoughts", "reasoning_provenance": "withheld_or_summarized"}
	msg = _turn_message(turn)
	assert isinstance(msg.content, list)
	reasoning = [c for c in msg.content if isinstance(c, ContentReasoning)]
	text = [c for c in msg.content if isinstance(c, ContentText)]
	assert reasoning and reasoning[0].reasoning == "summarized thoughts" and reasoning[0].redacted
	assert text and "I propose 4." in text[0].text

	full = _turn_message({**turn, "reasoning_provenance": "full"})
	assert not [c for c in full.content if isinstance(c, ContentReasoning)][0].redacted

	plain = _turn_message({"seat": "Avery", "round": 1, "phase": "discuss", "content": "hi",
	                       "reasoning": None, "reasoning_provenance": "none"})
	assert isinstance(plain.content, str)
