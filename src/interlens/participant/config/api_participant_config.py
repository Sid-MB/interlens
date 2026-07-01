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

from dataclasses import dataclass

from .participant_config import ParticipantConfig, register_config
from ..participants.api_participant import APIParticipant


@register_config
@dataclass
class APIParticipantConfig(ParticipantConfig):
	"""Serializable spec for an API-backed participant. Holds the provider + model id + generation params but no
	client (the client is constructed at build time / injectable)."""

	kind = "api"

	model_id: str = ""
	provider: str = "anthropic"
	max_tokens: int = 512
	temperature: float = 1.0

	def build(self, device, registry=None) -> APIParticipant:
		# device/registry are irrelevant to an API participant (no local model, no tools loop yet).
		if not self.model_id:
			raise ValueError("APIParticipantConfig.model_id is required (got empty); set the API model id explicitly.")
		return APIParticipant(
			name=self.name,
			system_prompt=self.system_prompt,
			private_context=self.private_context,
			model_id=self.model_id,
			provider=self.provider,
			max_tokens=self.max_tokens,
			temperature=self.temperature,
		)

	def _extra_dict(self) -> dict:
		return dict(model_id=self.model_id, provider=self.provider,
		            max_tokens=self.max_tokens, temperature=self.temperature)

	@classmethod
	def from_dict(cls, data: dict) -> "APIParticipantConfig":
		base = cls._base_kwargs(data)
		if "model_id" not in data:
			raise KeyError("APIParticipantConfig requires 'model_id'")
		return cls(**base, model_id=data["model_id"], provider=data.get("provider", "anthropic"),
		           max_tokens=data.get("max_tokens", 512), temperature=data.get("temperature", 1.0))
