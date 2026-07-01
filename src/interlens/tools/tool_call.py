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
