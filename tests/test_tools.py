# interlens: a framework for scaffolding and interpreting multi-agent conversations
# Copyright (C) 2026 Siddharth M. Bhatia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Tools: registry, per-family parse, execute, and the tool-calling loop (scripted, no model)."""
from __future__ import annotations

import torch

from interlens import Tool, ToolRegistry, ModelParticipantConfig
from interlens.participant.participants.model_participant import ModelParticipant, _GenResult
from interlens.participant.participants.gemma import GemmaModelParticipant
from interlens.tools.tool_call import ToolCall


class Calculator(Tool):
	name = "calculator"

	@property
	def schema(self):
		return {"type": "function", "function": {"name": "calculator", "description": "eval",
			"parameters": {"type": "object", "properties": {"expression": {"type": "string"}}}}}

	def __call__(self, expression):
		return str(eval(expression, {"__builtins__": {}}))


CALC = Calculator()


def test_registry_resolve_and_missing():
	import pytest
	reg = ToolRegistry()
	reg.register(CALC)
	assert reg.resolve(["calculator"])[0] is CALC
	with pytest.raises(KeyError):
		reg.resolve(["nope"])


def test_hermes_parse_execute_render():
	mp = ModelParticipant.__new__(ModelParticipant)
	mp.tools = (CALC,)
	calls = mp.parse_tool_calls('x<tool_call>{"name": "calculator", "arguments": {"expression": "6*7"}}</tool_call>')
	assert len(calls) == 1 and calls[0].arguments == {"expression": "6*7"}
	res = mp._execute(calls[0])
	assert res.output == "42" and not res.error
	assert mp._execute(ToolCall("missing")).error   # unknown tool -> error result, not a crash
	assert mp.render_tool_result(calls[0], res) == {"role": "tool", "name": "calculator", "content": "42"}


def test_gemma_tool_code_parse():
	gm = GemmaModelParticipant.__new__(GemmaModelParticipant)
	calls = gm.parse_tool_calls('go\n```tool_code\ncalculator(expression="6*7")\n```')
	assert len(calls) == 1 and calls[0].name == "calculator" and calls[0].arguments == {"expression": "6*7"}


class _Scripted(ModelParticipant):
	"""Overrides _run_model to return scripted raw outputs, so the loop is deterministic without a model."""

	def __init__(self, name, tools, scripted, max_tool_iters=4):
		self.name = name
		self.tools = tuple(tools)
		self.max_tool_iters = max_tool_iters
		self.seed = None
		self.kv_reuse = False
		self._scripted = list(scripted)
		self._i = 0
		self.views = []

	def _run_model(self, messages, schemas, steering, patch, return_logprobs):
		self.views.append(messages)
		raw = self._scripted[min(self._i, len(self._scripted) - 1)]
		self._i += 1
		return _GenResult(raw=raw, full_ids=torch.tensor([0]), prompt_len=0,
		                  new_tokens=torch.tensor([0]), n_tokens=1, scores=None)


def test_tool_loop_final_message_and_private_trail():
	sp = _Scripted("alice", (CALC,), [
		'<tool_call>{"name": "calculator", "arguments": {"expression": "21+21"}}</tool_call>',
		"The answer is 42.",
	])
	msg = sp.generate([{"role": "user", "content": "21+21?"}])
	assert msg.content == "The answer is 42."                       # final = natural language, not the call
	assert msg.metadata["tool_trail"][0]["output"] == "42"          # trail kept privately in metadata
	# The tool result was fed into the 2nd generation's working view.
	assert any(m.get("role") == "tool" and m["content"] == "42" for m in sp.views[1])


def test_tool_loop_respects_max_iters():
	loopy = _Scripted("bob", (CALC,),
	                  ['<tool_call>{"name":"calculator","arguments":{"expression":"1+1"}}</tool_call>'],
	                  max_tool_iters=2)
	msg = loopy.generate([{"role": "user", "content": "loop"}])
	assert loopy._i == 3   # max_tool_iters + 1 generations, then stop
	assert any("max_tool_iters" in str(e) for e in msg.metadata["tool_trail"])


def test_config_tool_round_trip():
	cfg = ModelParticipantConfig(name="a", model="qwen2.5-0.5b", tool_names=("calculator",), max_tool_iters=3)
	cfg2 = ModelParticipantConfig.from_dict(cfg.to_dict())
	assert cfg2.tool_names == ("calculator",) and cfg2.max_tool_iters == 3
