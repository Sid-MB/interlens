from __future__ import annotations

from abc import ABC, abstractmethod


class Tool(ABC):
	"""A capability a participant can invoke during its turn.

	A tool has a ``name``, a JSON ``schema`` (in the function-calling format chat templates render via their
	``tools=`` argument), and is callable with keyword arguments to produce a string result. Tools contain live
	callables and so are NOT serializable — templates store tool *names* and resolve them against a
	``ToolRegistry`` at build time, mirroring how models are resolved from ids.
	"""

	name: str

	@property
	@abstractmethod
	def schema(self) -> dict:
		"""The tool's JSON function schema, e.g.
		``{"type": "function", "function": {"name", "description", "parameters": {...}}}``, passed straight to
		``apply_chat_template(tools=...)`` so each family renders it in its native format."""
		...

	@abstractmethod
	def __call__(self, **arguments) -> str:
		"""Execute the tool and return a string result."""
		...
