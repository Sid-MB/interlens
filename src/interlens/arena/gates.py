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

"""Template-fidelity gates: preflight checks before spending GPU-hours on local-model rollouts.

Two silent failure modes cost real runs in the arena experiments, and both are cheap to gate on:

1. **Template drift** — the token ids a model is *actually* conditioned on
   (``apply_chat_template(tokenize=True)``) can differ from tokenizing the rendered string, e.g. when a
   template inserts special tokens the string round-trip re-splits. ``check_template_fidelity`` asserts exact
   token-id equality over real rendered multi-party views, for the exact id path batched generation feeds to
   ``generate``.
2. **Reasoning leaks** — a ``<think>`` block from one seat's raw completion ending up inside another seat's
   later view (observed live when a turn truncates mid-``<think>``). ``check_reasoning_leak`` scans a played
   episode for any raw think fragment appearing in a later turn's visible content.

Run both on smoke instances before a full rollout; each returns a report dict with ``ok: bool``.
"""
from __future__ import annotations

from ..parsing import first_think_block
from .scenario import Scenario
from .schema import Episode


def scenario_smoke_views(scenario: Scenario, *, level: int = 0, seed: int = 999_101,
                         scripted_turn: str = "I suggest we start by sharing our goals.") -> list[list[dict]]:
	"""Real rendered views for gating: a fresh team state's first requests, plus the views after one scripted
	turn (so later views carry assistant/user mixes, which is where templates diverge)."""
	instance = scenario.generate_instance(level, seed)
	state = scenario.make_state(instance, "team", 0)
	requests = scenario.next_requests(state)
	views = [r.view for r in requests]
	scenario.apply(state, requests[0], scripted_turn)
	views.extend(r.view for r in scenario.next_requests(state)[:1])
	return views


def check_template_fidelity(tokenizer, views: list[list[dict]], **template_kwargs) -> dict:
	"""Assert token-id equality between ``tokenizer(apply_chat_template(tokenize=False))`` and
	``apply_chat_template(tokenize=True)`` for every view. ``template_kwargs`` are forwarded to both template
	calls (e.g. ``enable_thinking=True`` for Qwen3, matching the generation-time configuration)."""
	mismatches = []
	for i, view in enumerate(views):
		rendered = tokenizer.apply_chat_template(view, tokenize=False, add_generation_prompt=True,
		                                         **template_kwargs)
		ids_from_string = tokenizer(rendered, add_special_tokens=False)["input_ids"]
		ids_direct = tokenizer.apply_chat_template(view, tokenize=True, add_generation_prompt=True,
		                                           **template_kwargs)
		if ids_from_string != ids_direct:
			mismatches.append(i)
	return {"ok": not mismatches, "views": len(views), "mismatch_indices": mismatches}


def check_reasoning_leak(episode: Episode | dict, *, fragment_length: int = 80) -> dict:
	"""Scan a played episode for reasoning leakage: any turn whose raw completion contains a ``<think>`` block
	whose content then appears verbatim in a LATER turn's visible content (meaning another seat saw it).
	Accepts a live ``Episode`` or its stored JSON dict."""
	turns = episode.turns if isinstance(episode, Episode) else episode["turns"]

	def _field(turn, name):
		return getattr(turn, name) if not isinstance(turn, dict) else turn.get(name)

	think_turns = 0
	leaks = []
	for turn in turns:
		raw = _field(turn, "raw")
		if not raw or "<think>" not in raw:
			continue
		think_turns += 1
		block = first_think_block(raw)
		if block is None:
			continue
		fragment = block.strip()[:fragment_length]
		if not fragment:
			continue
		idx = _field(turn, "idx")
		if any(fragment in _field(later, "content") for later in turns if _field(later, "idx") > idx):
			leaks.append(idx)
	return {"ok": not leaks, "turns": len(turns), "think_turns": think_turns, "leak_indices": leaks}
