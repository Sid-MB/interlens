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


class LlamaModelParticipant(ModelParticipant):
	"""A Llama-family participant. Chat-template flags are auto-derived from the tokenizer; only the tool-call
	format differs from base: Llama 3 emits calls as ``<|python_tag|>{json}`` rather than Hermes/Qwen
	``<tool_call>`` blocks."""

	MODEL_TYPES: ClassVar[frozenset[str]] = frozenset({"llama"})

	def parse_tool_calls(self, text: str) -> list:
		"""Parse Llama-3's ``<|python_tag|>{json}`` function-call format (best-effort).

		Everything after ``<|python_tag|>`` is one or more JSON objects (separated by newlines or semicolons),
		each ``{"name": ..., "arguments"/"parameters": {...}}``. Anything unparseable is skipped, so a malformed
		call yields ``[]`` (treated as a final message), matching the base contract of never misfiring."""
		import json
		from ...tools.tool_call import ToolCall

		tag = "<|python_tag|>"
		idx = text.find(tag)
		if idx < 0:
			return []
		body = text[idx + len(tag):]
		calls = []
		for chunk in body.replace(";", "\n").splitlines():
			chunk = chunk.strip()
			if not chunk:
				continue
			try:
				data = json.loads(chunk)
				name = data["name"]
				arguments = data.get("arguments") or data.get("parameters") or {}
			except (json.JSONDecodeError, KeyError) as exc:
				logger.debug("dropping unparseable python_tag call %r: %s", chunk, exc)
				continue
			calls.append(ToolCall(name=name, arguments=arguments, raw=chunk))
		return calls
