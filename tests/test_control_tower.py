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

"""The optional Control Tower policy-boundary adapter, tested without model weights or Control Tower itself."""
from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("inspect_ai")

from inspect_ai.model import (ChatMessageAssistant, ChatMessageSystem, ChatMessageTool, ChatMessageUser,
                              GenerateConfig)
from inspect_ai.tool import Tool, ToolCall, tool

from interlens.integrations.control_tower import participant_generate
from interlens.message import Message


@tool
def shell_tool() -> Tool:
	"""A harmless schema-only tool used to verify that Interlens does not execute Control Tower actions."""

	async def execute(cmd: str) -> str:
		"""Return a marker.

		Args:
			cmd: Shell command to echo. Use any string when checking schema translation.
		"""
		raise AssertionError(f"adapter executed Control Tower tool privately: {cmd}")

	return execute


class FakeStepParticipant:
	"""Records one-step calls and emits a scripted Interlens tool request."""

	name = "policy"
	hf_id = "local/test-model"

	def __init__(self):
		"""Initialize the captured-call list."""
		self.calls = []

	def generate_step(self, view, **kwargs) -> Message:
		"""Record translated input and return a tool call.

		Args:
			view: Inspect history translated to Interlens dictionaries.
			**kwargs: Generation options, including outer-runtime tool schemas.

		Returns:
			A scripted tool-calling message.
		"""
		self.calls.append((view, kwargs))
		return Message(
			author=self.name,
			content="",
			metadata={
				"n_tokens_in": 12,
				"n_tokens": 4,
				"tool_calls": [{"name": "shell_tool", "arguments": {"cmd": "ls"}}],
			},
		)


def test_participant_generate_preserves_control_tower_tool_boundary():
	participant = FakeStepParticipant()
	generate = participant_generate(participant)
	prior_call = ToolCall(id="prior", function="shell_tool", arguments={"cmd": "pwd"})
	output = asyncio.run(
		generate(
			[
				ChatMessageSystem(content="Work safely."),
				ChatMessageUser(content="List files."),
				ChatMessageAssistant(content="", tool_calls=[prior_call]),
				ChatMessageTool(content="/tmp", tool_call_id="prior", function="shell_tool"),
			],
			[shell_tool()],
			"auto",
			GenerateConfig(max_tokens=64),
		)
	)

	view, kwargs = participant.calls[0]
	assert view[2]["tool_calls"][0]["function"]["name"] == "shell_tool"
	assert view[3] == {"role": "tool", "content": "/tmp", "tool_call_id": "prior", "name": "shell_tool"}
	assert kwargs["tool_schemas"][0]["function"]["name"] == "shell_tool"
	assert kwargs["max_new_tokens"] == 64

	choice = output.choices[0]
	assert choice.stop_reason == "tool_calls"
	assert choice.message.tool_calls[0].function == "shell_tool"
	assert choice.message.tool_calls[0].arguments == {"cmd": "ls"}
	assert output.usage.input_tokens == 12
	assert output.usage.output_tokens == 4


def test_participant_generate_hides_tools_for_none_choice():
	participant = FakeStepParticipant()
	generate = participant_generate(participant)
	asyncio.run(
		generate(
			[ChatMessageUser(content="Answer without tools.")],
			[shell_tool()],
			"none",
			GenerateConfig(),
		)
	)
	assert participant.calls[0][1]["tool_schemas"] == []


def test_participant_generate_rejects_required_tool_choice():
	generate = participant_generate(FakeStepParticipant())
	with pytest.raises(NotImplementedError, match="required/forced"):
		asyncio.run(
			generate(
				[ChatMessageUser(content="You must use a tool.")],
				[shell_tool()],
				"any",
				GenerateConfig(),
			)
		)
