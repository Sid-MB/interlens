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

"""Per-seat view construction + structured-action parsing for arena scenarios.

Views are family-agnostic role/content message lists; the participant applies the family-correct chat template
(``ModelParticipant``) or provider format (``APIParticipant``). Views alternate user/assistant with the seat's
own past turns as assistant turns and everyone else's (author-labelled) as merged user turns — the same
semantics as the core per-speaker view pipeline, specialized to a scenario's event list with per-seat private
events.
"""
from __future__ import annotations

from typing import Any

from ..parsing import last_json, strip_think

__all__ = ["build_view", "extract_json", "strip_think"]


def build_view(seat: str, system: str, events: list[dict], phase_prompt: str) -> list[dict]:
	"""Render ``events`` (``[{seat|'MODERATOR', content, only?}]``, public unless ``only`` names seats) into an
	alternating per-speaker view for ``seat``, ending with ``phase_prompt`` as the final user turn."""
	messages: list[dict] = [{"role": "system", "content": system}]
	buffer: list[str] = []

	def flush():
		if buffer:
			messages.append({"role": "user", "content": "\n\n".join(buffer)})
			buffer.clear()

	for event in events:
		visible_to = event.get("only")
		if visible_to is not None and seat not in visible_to:
			continue  # private event (e.g. per-seat noisy observations)
		if event["seat"] == seat:
			flush()
			messages.append({"role": "assistant", "content": event["content"]})
		else:
			label = "[Moderator]" if event["seat"] == "MODERATOR" else f"[{event['seat']}]"
			buffer.append(f"{label}\n{event['content']}")
	buffer.append(phase_prompt)
	flush()
	return messages


# ---------------------------------------------------------------- parsing ---
# The fenced-JSON and think-stripping implementations live in ``interlens.parsing`` (one home for every parser
# in the library). These names are the arena's stable call-through surface.


def extract_json(text: str) -> Any | None:
	"""The last fenced JSON object in ``text``, else the last balanced top-level ``{...}`` that parses.
	Thin alias for :func:`interlens.parsing.last_json`."""
	return last_json(text)
