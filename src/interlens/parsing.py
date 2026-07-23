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

"""One home for structured-action parsing and reasoning stripping.

Three call sites historically each carried their own copy of this logic — the arena's ``extract_json`` /
``strip_think`` (``arena/views.py``), the messaging policy's ``parse_json_actions``
(``communication/messaging.py``), and the model participant's ``parse_tool_calls`` / ``split_reasoning``
(``model_participant.py``) — with subtly divergent regexes and edge-case handling. They now all call the one
implementation here; the original names survive as thin shims so their signatures stay stable.

Two orthogonal jobs:

- **Fenced / tagged JSON extraction** — pulling structured actions out of a model's free text, whether they
  arrive as ```` ```json {...} ```` fences (the family-agnostic action surface) or ``<tag>{...}</tag>`` blocks
  (Hermes/Qwen tool calls). Malformed JSON is skipped, never fatal.
- **Reasoning stripping** — separating a ``<think>...</think>`` stream from the visible content, in two
  flavours: a strict *leading-block* split (the participant's own completion, where reasoning is a prefix) and
  a *strip-anywhere* pass (a defensive re-strip before content reaches another seat's view, robust to a
  generation truncated mid-``<think>``).
"""
from __future__ import annotations

import json
import re
from typing import Any

# A fenced JSON object: ```` ```json {...} ```` or a bare ```` ``` {...} ```` fence. The single source for
# every fenced-action parser in the library.
FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)

# A ``<think>...</think>`` reasoning block anywhere in the text (used for strip-anywhere and leak detection).
THINK_BLOCK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)

# A ``<think>...</think>`` block anchored at the START of the text — the participant-level convention where a
# thinking model emits its reasoning as a leading prefix (Qwen3, R1-style).
LEADING_THINK_RE = re.compile(r"^\s*<think>(.*?)</think>\s*", re.DOTALL)

_TAG_RE_CACHE: dict[str, re.Pattern] = {}


def _tag_re(tag: str) -> re.Pattern:
	"""A cached ``<tag>{json}</tag>`` extraction regex (e.g. ``tag='tool_call'`` for the Hermes/Qwen format)."""
	pattern = _TAG_RE_CACHE.get(tag)
	if pattern is None:
		pattern = re.compile(rf"<{re.escape(tag)}>\s*(\{{.*?\}})\s*</{re.escape(tag)}>", re.DOTALL)
		_TAG_RE_CACHE[tag] = pattern
	return pattern


# ------------------------------------------------------------------- JSON ---

def iter_fenced_json(text: str | None) -> list[dict]:
	"""Every parseable fenced JSON OBJECT in ``text``, in order (malformed fences skipped, not fatal). The fence
	regex captures ``{...}`` only — structured actions are always objects — so a stray fenced list/number is
	ignored, not mistaken for an action. Backs ``MessagingPolicy.parse_json_actions``."""
	out: list[dict] = []
	for candidate in FENCE_RE.findall(text or ""):
		try:
			out.append(json.loads(candidate))
		except json.JSONDecodeError:
			continue
	return out


def last_json(text: str | None) -> Any | None:
	"""The LAST fenced JSON object in ``text``, else the last balanced top-level ``{...}`` that parses, else
	``None``. "Last wins" because a model's final fenced block is its committed action when it revised mid-turn.
	Backs the arena's ``extract_json``."""
	for candidate in reversed(FENCE_RE.findall(text or "")):
		try:
			return json.loads(candidate)
		except json.JSONDecodeError:
			pass
	# fall back: scan for balanced top-level objects, keeping the last that parses
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


def iter_tagged_json(text: str | None, tag: str) -> list[tuple[dict, str]]:
	"""Every ``<tag>{json}</tag>`` block in ``text`` as ``(parsed_object, raw_match)`` pairs (malformed JSON
	skipped). ``raw_match`` is the whole matched ``<tag>...</tag>`` substring, for provenance. Backs the base
	``ModelParticipant.parse_tool_calls`` (Hermes/Qwen ``<tool_call>`` format)."""
	out: list[tuple[dict, str]] = []
	for match in _tag_re(tag).finditer(text or ""):
		try:
			data = json.loads(match.group(1))
		except json.JSONDecodeError:
			continue
		if isinstance(data, dict):
			out.append((data, match.group(0)))
	return out


# -------------------------------------------------------------- reasoning ---

def strip_think(text: str | None) -> tuple[str, str | None]:
	"""Remove ``<think>...</think>`` blocks ANYWHERE in ``text``; return ``(visible, think)``.

	The defensive strip used before content reaches another seat's view: a generation truncated mid-``<think>``
	leaves an *unterminated* block whose reasoning must not leak, so everything from an orphan ``<think>`` on is
	treated as reasoning. ``think`` is the joined reasoning, or ``None`` when there was none."""
	if not text:
		return "", None
	blocks = THINK_BLOCK_RE.findall(text)
	visible = THINK_BLOCK_RE.sub("", text).strip()
	if "<think>" in visible:  # unterminated block: the tail is all reasoning
		head, _, tail = visible.partition("<think>")
		blocks.append(tail)
		visible = head.strip()
	return visible, ("\n".join(blocks).strip() if blocks else None)


def split_leading_think(text: str) -> tuple[str, str | None]:
	"""Split a raw completion into ``(visible_content, parsed_think)`` on a LEADING ``<think>...</think>`` block
	only (the participant-level convention). No leading block → ``(text.strip(), None)``. Backs the base
	``ModelParticipant.split_reasoning``."""
	match = LEADING_THINK_RE.match(text)
	if not match:
		return text.strip(), None
	return text[match.end():].strip(), match.group(1).strip()


def first_think_block(text: str | None) -> str | None:
	"""The first complete ``<think>...</think>`` block's inner reasoning, or ``None``. A detection helper for
	leak gates that need the fragment itself (``arena.gates.check_reasoning_leak``)."""
	match = THINK_BLOCK_RE.search(text or "")
	return match.group(1) if match else None
