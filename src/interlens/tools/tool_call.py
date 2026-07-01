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

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolCall:
	"""A parsed request from the model to invoke a tool: the tool ``name`` and its ``arguments``.

	``raw`` keeps the exact text the model emitted (useful for debugging a family parser). Tool calls are parsed
	out of the generation by a per-family ``parse_tool_calls`` — the format differs across model families, so the
	parsed structure is uniform even though the surface syntax isn't.
	"""

	name: str
	arguments: dict = field(default_factory=dict)
	raw: str = ""


@dataclass
class ToolResult:
	"""The outcome of executing a ``ToolCall``: the tool ``name`` and its string ``output`` (or error text)."""

	name: str
	output: str
	error: bool = False
