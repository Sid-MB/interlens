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
from typing import ClassVar

from .model_participant import ModelParticipant

logger = logging.getLogger(__name__)


class GemmaModelParticipant(ModelParticipant):
	"""A Gemma-family participant. The only thing that differs from base is the tool-call format
	(```` ```tool_code ````); the chat-template flags (Gemma 2 rejects a standalone ``system`` role and requires
	strict user/model alternation, Gemma 3 accepts a system role) are auto-derived from the tokenizer's own
	template, so both generations use this one class."""

	MODEL_TYPES: ClassVar[frozenset[str]] = frozenset({"gemma2", "gemma3"})

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
