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
