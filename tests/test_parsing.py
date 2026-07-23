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

# [rational_agents scaffold: interlens-core] 2026-07-23

"""The consolidated parsing module: fenced/tagged JSON extraction and reasoning stripping, plus the thin shims
(``arena.views.extract_json`` / ``strip_think``, ``communication.messaging.parse_json_actions``,
``ModelParticipant.split_reasoning`` / ``parse_tool_calls``) that must keep call-through behavior identical."""
from __future__ import annotations

from interlens import parsing
from interlens.arena.views import extract_json, strip_think
from interlens.communication.messaging import parse_json_actions


def test_iter_fenced_json_all_objects_in_order():
	text = 'first ```json\n{"a": 1}\n``` mid ```\n{"b": 2}\n``` end'
	assert parsing.iter_fenced_json(text) == [{"a": 1}, {"b": 2}]
	# malformed fence skipped, not fatal; a fenced list is not an object -> ignored (never mistaken for an action)
	assert parsing.iter_fenced_json('```json\n{bad}\n``` ```json\n[1,2]\n```') == []
	assert parse_json_actions(text) == [{"a": 1}, {"b": 2}]   # the messaging shim is identical


def test_last_json_prefers_last_fence_then_balanced():
	assert parsing.last_json('```json\n{"a": 1}\n```\n```json\n{"a": 2}\n```') == {"a": 2}
	# no fence -> last balanced top-level object
	assert parsing.last_json('noise {"x": 1} then {"y": 2} tail') == {"y": 2}
	assert parsing.last_json("nothing here") is None
	assert extract_json('```json\n{"deal": 1}\n```') == {"deal": 1}   # the arena shim is identical


def test_iter_tagged_json_tool_call_format():
	text = 'x<tool_call>{"name": "calc", "arguments": {"e": "6*7"}}</tool_call>'
	pairs = parsing.iter_tagged_json(text, "tool_call")
	assert len(pairs) == 1
	data, raw = pairs[0]
	assert data["name"] == "calc" and raw.startswith("<tool_call>")
	assert parsing.iter_tagged_json("<tool_call>{bad json}</tool_call>", "tool_call") == []


def test_strip_think_anywhere_and_unterminated():
	assert strip_think("<think>secret</think>hello") == ("hello", "secret")
	assert strip_think("a<think>x</think>b<think>y</think>c") == ("abc", "x\ny")
	# an unterminated (truncated) block: everything from the orphan <think> on is reasoning, never leaked
	visible, think = strip_think("visible tail <think>leaked plan continues")
	assert visible == "visible tail" and think == "leaked plan continues"
	assert strip_think("") == ("", None)
	assert strip_think("no reasoning") == ("no reasoning", None)


def test_split_leading_think_prefix_only():
	assert parsing.split_leading_think("<think>reason</think>answer") == ("answer", "reason")
	# a <think> NOT at the start is left in place (not a leading block)
	assert parsing.split_leading_think("answer <think>mid</think>") == ("answer <think>mid</think>", None)
	assert parsing.split_leading_think("plain") == ("plain", None)


def test_first_think_block_detection():
	assert parsing.first_think_block("a<think>b</think>c") == "b"
	assert parsing.first_think_block("no block") is None
