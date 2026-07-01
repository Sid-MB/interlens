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

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..participant import Participant
from ..role import Role
from ...context_item import ContextItem

# kind tag -> config class, for polymorphic deserialization. Subclasses register themselves at import.
_CONFIG_KINDS: dict[str, type["ParticipantConfig"]] = {}


def register_config(cls: type["ParticipantConfig"]) -> type["ParticipantConfig"]:
	_CONFIG_KINDS[cls.kind] = cls
	return cls


def participant_config_from_dict(data: dict) -> "ParticipantConfig":
	"""Reconstruct the right config subclass from its ``kind`` tag."""
	return _CONFIG_KINDS[data["kind"]].from_dict(data)


@dataclass
class ParticipantConfig(ABC):
	"""A serializable *spec* for a participant — what to build, holding no weights.

	This is half of the config/live split that makes serialization clean: every runtime ``Participant`` has a
	paired ``ParticipantConfig`` (via ``to_config``), and a config rebuilds a live participant on any device via
	``build``. Templates are just lists of these specs.

	Shared fields cover identity + private framing. ``self_role``/``others_role`` default to assistant/user and
	are rarely overridden.
	"""

	kind = "participant"

	name: str
	system_prompt: str | None = None
	private_context: tuple[ContextItem, ...] = ()
	self_role: Role = "assistant"
	others_role: Role = "user"

	@abstractmethod
	def build(self, device, registry=None) -> Participant:
		"""Instantiate the live participant on ``device``. ``registry`` (a ``ToolRegistry``) resolves any tool
		names to callables; ``None`` uses the process-global default registry."""
		...

	def to_dict(self) -> dict:
		return {
			"kind": self.kind,
			"name": self.name,
			"system_prompt": self.system_prompt,
			"private_context": [
				{"content": c.content, "role_hint": c.role_hint, "author": c.author} for c in self.private_context
			],
			"self_role": self.self_role,
			"others_role": self.others_role,
			**self._extra_dict(),
		}

	def _extra_dict(self) -> dict:
		"""Subclass-specific fields beyond the shared ones."""
		return {}

	@staticmethod
	def _base_kwargs(data: dict) -> dict:
		"""Parse the shared fields common to every config subclass."""
		return dict(
			name=data["name"],
			system_prompt=data.get("system_prompt"),
			private_context=tuple(
				ContextItem(c["content"], c.get("role_hint", "user"), c.get("author", "moderator"))
				for c in data.get("private_context", [])
			),
			self_role=data.get("self_role", "assistant"),
			others_role=data.get("others_role", "user"),
		)
