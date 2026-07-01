from __future__ import annotations

from .tool import Tool


class ToolRegistry:
	"""Resolves tool *names* (which serialize) to live ``Tool`` instances (which don't).

	This is the tools analogue of the model registry: a template stores ``tool_names`` and, at ``build`` time on
	each worker, the registry turns them into callables. Because spawned worker processes inherit no parent
	state, tools must be registered at import time (or via a worker-init hook), not imperatively in the parent.
	"""

	def __init__(self):
		self._tools: dict[str, Tool] = {}

	def register(self, tool: Tool) -> Tool:
		self._tools[tool.name] = tool
		return tool

	def resolve(self, names) -> list[Tool]:
		missing = [n for n in names if n not in self._tools]
		if missing:
			raise KeyError(f"tools not registered: {missing} (registered: {sorted(self._tools)})")
		return [self._tools[n] for n in names]

	def __contains__(self, name) -> bool:
		return name in self._tools


# Process-global default registry. Experiments register their tools here (at import time); configs that don't
# pass an explicit registry resolve against this one.
DEFAULT_REGISTRY = ToolRegistry()
