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

"""Inspect tasks for the second scenario wave (security dilemma, coding collaboration, distributed
long-context), run against inspect-ai's mockllm provider (skipped without the ``inspect`` extra)."""
import json
import random

import pytest

inspect_ai = pytest.importorskip("inspect_ai")

from inspect_ai import eval as inspect_eval  # noqa: E402
from inspect_ai.model import ModelOutput, get_model  # noqa: E402

from interlens.arena.schema import Instance, new_id  # noqa: E402
from interlens.arena.scenarios import CodingCollab  # noqa: E402
from interlens.arena.scenarios.dlc.build import char_split4, insert_needle  # noqa: E402
from interlens.arena.inspect import coding_collab, distributed_longcontext, security_dilemma  # noqa: E402


@pytest.fixture(autouse=True)
def _writable_inspect_dirs(tmp_path, monkeypatch):
	monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
	monkeypatch.setenv("INSPECT_LOG_DIR", str(tmp_path / "logs"))


def _outputs(text: str, n: int):
	return [ModelOutput.from_content(model="mockllm/model", content=text) for _ in range(n)]


def test_security_dilemma_task_full_cooperation():
	# one canned output serves both phases: message text plus a deescalate action fence
	text = 'We seek peace.\n```json\n{"action": "deescalate"}\n```'
	model = get_model("mockllm/model", custom_outputs=_outputs(text, 80))
	log = inspect_eval(security_dilemma(n_instances=1), model=model, display="none")[0]
	assert log.status == "success"
	value = log.samples[0].scores["scenario_scorer"].value
	assert value["success"] == 1.0 and value["primary"] == 1.0     # 12 rounds of mutual deescalation
	outcome = log.samples[0].store.get("arena:outcome")
	assert outcome["joint_payoff"] == 96 and not outcome["spiral"]


def test_security_dilemma_rejects_messaging_mode():
	from interlens.arena.inspect.adapter import _run_messaging_episode
	from interlens.arena.scenarios import SecurityDilemma
	scenario = SecurityDilemma()
	instance = scenario.generate_instance(0, 1)
	with pytest.raises(ValueError, match="messaging"):
		_run_messaging_episode(scenario, instance, None, None, None, 100, 4)


def test_coding_collab_task_reference_solution_scores_1():
	scenario = CodingCollab()
	instance = scenario.generate_instance(0, 3)
	good = instance.solution["code"]
	text = f'Draft:\n```python\n{good}\n```\n```json\n{{"constraints_ok": true}}\n```'
	model = get_model("mockllm/model", custom_outputs=_outputs(text, 40))
	log = inspect_eval(coding_collab(n_instances=1, seed0=3, communication="round_robin"),
	                   model=model, display="none")[0]
	assert log.status == "success"
	value = log.samples[0].scores["scenario_scorer"].value
	assert value["success"] == 1.0 and value["primary"] == 1.0
	assert log.samples[0].store.get("arena:outcome")["finalized_by"] == "early_consensus"


def test_coding_collab_messaging_mode_scores_latest_fence():
	scenario = CodingCollab()
	instance = scenario.generate_instance(0, 3)
	good = instance.solution["code"]
	text = (f'```json\n{{"messages": [{{"to": "all", "content": "posting the module"}}]}}\n```\n'
	        f'```python\n{good}\n```')
	model = get_model("mockllm/model", custom_outputs=_outputs(text, 80))
	log = inspect_eval(coding_collab(n_instances=1, seed0=3, communication="messaging",
	                                 messaging_turns=6),
	                   model=model, display="none")[0]
	assert log.status == "success"
	value = log.samples[0].scores["scenario_scorer"].value
	assert value["primary"] == 1.0
	assert log.samples[0].store.get("arena:outcome")["finalized_by"] == "messaging"


def _fixture_bank(tmp_path) -> str:
	rng = random.Random(7)
	paras = [f"Paragraph {i}: " + " ".join(f"w{rng.randint(0, 99)}" for _ in range(30)) for i in range(40)]
	needle = "One of the special magic numbers for juniper is: 4415926."
	full, _ = insert_needle(rng, "\n\n".join(paras), needle)
	inst = Instance(new_id("sniah-fix"), "dlc_sniah", 0, 7,
	                {"task": "sniah", "question": "What is the special magic number for juniper?",
	                 "shards": char_split4(full), "gold_number": "4415926"},
	                1.0, 0.0, {"number": "4415926"})
	p = tmp_path / "dlc_sniah_fixture.json"
	p.write_text(json.dumps([inst.to_json()]))
	return str(p)


def test_distributed_longcontext_task_round_robin(tmp_path):
	bank = _fixture_bank(tmp_path)
	text = 'I found it. ```json\n{"answer": "4415926"}\n```'
	model = get_model("mockllm/model", custom_outputs=_outputs(text, 40))
	log = inspect_eval(distributed_longcontext(instances=bank, communication="round_robin"),
	                   model=model, display="none")[0]
	assert log.status == "success"
	value = log.samples[0].scores["scenario_scorer"].value
	assert value["success"] == 1.0
	outcome = log.samples[0].store.get("arena:outcome")
	assert outcome["outcome_class"] == "answered"


def test_distributed_longcontext_task_messaging_maps_to_team_msg(tmp_path):
	bank = _fixture_bank(tmp_path)
	# one canned output serves both: a routed message fence AND the final answer fence
	text = ('```json\n{"messages": [{"to": "all", "content": "the number is 4415926"}]}\n```\n'
	        '```json\n{"answer": "4415926"}\n```')
	model = get_model("mockllm/model", custom_outputs=_outputs(text, 60))
	log = inspect_eval(distributed_longcontext(instances=bank, communication="messaging"),
	                   model=model, display="none")[0]
	assert log.status == "success"
	assert log.samples[0].scores["scenario_scorer"].value["success"] == 1.0
