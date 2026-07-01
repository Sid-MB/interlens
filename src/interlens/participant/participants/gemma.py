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

from __future__ import annotations

import logging

from .model_participant import ModelParticipant

logger = logging.getLogger(__name__)


class GemmaModelParticipant(ModelParticipant):
	"""A Gemma-family participant.

	Gemma's chat template has two constraints the base flatten must respect, both expressed purely by overriding
	capability flags (the base ``finalize_view`` does the work — no method override needed):

	- It **rejects a standalone ``system`` role** — system content must be folded into the first user turn
	  (``supports_system_role=False``).
	- It **requires strictly alternating** user/model turns — so the moderator seed + another speaker + private
	  context (all mapping to ``user``) must be merged, or ``apply_chat_template`` raises
	  (``requires_alternating_roles=True``).

	Gemma also renders the assistant as role ``model``, but that mapping is handled by the tokenizer's own
	template when we pass standard ``assistant`` roles, so no override is needed here. Tool-call format
	(```` ```tool_code ````) parsing arrives with the tools phase.

	The flags are plain class attributes (not dataclass fields), so ``GemmaModelParticipant`` is just a
	``ModelParticipant`` with two behaviors flipped — it inherits the dataclass ``__init__`` unchanged.
	"""

	supports_system_role = False
	requires_alternating_roles = True

	def parse_tool_calls(self, text: str) -> list:
		"""Parse Gemma's ```` ```tool_code ```` function-call blocks (best-effort).

		Gemma emits calls like ```` ```tool_code\nname(arg="x", n=2)\n``` ```` rather than Hermes JSON. We extract
		the block, then the function name and simple keyword arguments. Falls back to ``[]`` (treat as final
		message) on anything it can't parse, matching the base contract of never misfiring silently.
		"""
		import ast
		import re
		from ...tools.tool_call import ToolCall

		calls = []
		for block in re.findall(r"```tool_code\s*(.*?)```", text, re.DOTALL):
			call_match = re.match(r"\s*([A-Za-z_][\w.]*)\s*\((.*)\)\s*$", block.strip(), re.DOTALL)
			if not call_match:
				continue
			name, arg_src = call_match.group(1), call_match.group(2)
			arguments = {}
			try:
				# Parse ``k=v`` pairs via a synthetic call node, so values are real Python literals.
				parsed = ast.parse(f"f({arg_src})", mode="eval")
				for kw in parsed.body.keywords:
					arguments[kw.arg] = ast.literal_eval(kw.value)
			except (SyntaxError, ValueError) as exc:
				logger.debug("dropping unparseable tool_code block %r: %s", block, exc)
				continue
			calls.append(ToolCall(name=name.split(".")[-1], arguments=arguments, raw=block))
		return calls


class Gemma3ModelParticipant(GemmaModelParticipant):
	"""Gemma 3. Shares Gemma 2's ``tool_code`` parsing and strict user/model alternation, but — unlike Gemma 2 —
	its chat template **accepts a standalone ``system`` role**, so it must NOT fold system into the first user
	turn. (Verified against the real template by ``tests/test_family_flags.py``.)"""

	supports_system_role = True
