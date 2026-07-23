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

import json
import re
from typing import Any


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

_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def extract_json(text: str) -> Any | None:
	"""The last fenced JSON object in ``text``, else the last balanced top-level ``{...}`` that parses."""
	fenced = _FENCE.findall(text or "")
	for candidate in reversed(fenced):
		try:
			return json.loads(candidate)
		except json.JSONDecodeError:
			pass
	# fall back: scan for balanced objects
	s = text or ""
	best = None
	depth = 0
	start = None
	for i, ch in enumerate(s):
		if ch == "{":
			if depth == 0:
				start = i
			depth += 1
		elif ch == "}":
			if depth > 0:
				depth -= 1
				if depth == 0 and start is not None:
					try:
						best = json.loads(s[start:i + 1])
					except json.JSONDecodeError:
						pass
	return best


def strip_think(text: str) -> tuple[str, str | None]:
	"""Remove ``<think>...</think>`` blocks anywhere in ``text``. Returns ``(visible, think)``.

	Stricter than the participant-level leading-block parse: a generation truncated mid-``<think>`` leaves an
	*unterminated* block, whose reasoning must not leak into other seats' views — everything from the orphan
	``<think>`` on is treated as reasoning."""
	if not text:
		return "", None
	blocks = re.findall(r"<think>(.*?)</think>", text, re.DOTALL)
	visible = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
	if "<think>" in visible:  # unterminated block: the tail is all reasoning
		head, _, tail = visible.partition("<think>")
		blocks.append(tail)
		visible = head.strip()
	return visible, ("\n".join(blocks).strip() if blocks else None)
