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

from dataclasses import dataclass

import torch

from .participant_config import ParticipantConfig, register_config
from ..participants.model_participant import ModelParticipant

_DTYPES = {"float32": torch.float32, "float16": torch.float16, "bfloat16": torch.bfloat16}


def dtype_to_str(dtype: torch.dtype) -> str:
	return str(dtype).replace("torch.", "")


def str_to_dtype(name: str) -> torch.dtype:
	return _DTYPES[name]


@register_config
@dataclass
class ModelParticipantConfig(ParticipantConfig):
	"""Serializable spec for a local-model participant.

	Stores *what to build* — the HF model id, optional pinned ``revision``, dtype, generation params, reasoning
	controls, and the private framing — but never weights. ``build`` loads the model onto a device and returns the
	family-appropriate live participant (resolved from ``config.model_type``).
	"""

	kind = "model"

	model: str = ""
	revision: str | None = None
	dtype: str = "bfloat16"
	attn: str = "flash_attention_2"
	quant: str | None = None
	max_new_tokens: int = 512
	temperature: float = 0.8
	top_p: float = 0.95
	seed: int | None = None
	thinking: bool | str = "auto"
	reasoning_effort: str | None = None
	tool_names: tuple[str, ...] = ()
	max_tool_iters: int = 4
	kv_reuse: bool | str = "auto"
	weights_path: str | None = None

	def build(self, device, registry=None) -> ModelParticipant:
		from ...factories import AutoModelParticipant

		source = self.weights_path or self.model
		tools = ()
		if self.tool_names:
			from ...tools.registry import DEFAULT_REGISTRY
			tools = tuple((registry or DEFAULT_REGISTRY).resolve(self.tool_names))
		return AutoModelParticipant.from_pretrained(
			source,
			name=self.name,
			device=device,
			load_kwargs={"dtype": str_to_dtype(self.dtype), "attn": self.attn, "quant": self.quant,
			             "revision": self.revision},
			max_new_tokens=self.max_new_tokens,
			temperature=self.temperature,
			top_p=self.top_p,
			seed=self.seed,
			thinking=self.thinking,
			system_prompt=self.system_prompt,
			private_context=self.private_context,
			tools=tools,
			max_tool_iters=self.max_tool_iters,
			kv_reuse=self.kv_reuse,
		)

	def _extra_dict(self) -> dict:
		return dict(
			model=self.model,
			revision=self.revision,
			dtype=self.dtype,
			attn=self.attn,
			quant=self.quant,
			max_new_tokens=self.max_new_tokens,
			temperature=self.temperature,
			top_p=self.top_p,
			seed=self.seed,
			thinking=self.thinking,
			reasoning_effort=self.reasoning_effort,
			tool_names=list(self.tool_names),
			max_tool_iters=self.max_tool_iters,
			kv_reuse=self.kv_reuse,
			weights_path=self.weights_path,
		)

	@classmethod
	def from_dict(cls, data: dict) -> "ModelParticipantConfig":
		base = cls._base_kwargs(data)
		return cls(
			**base,
			model=data["model"],
			revision=data.get("revision"),
			dtype=data.get("dtype", "bfloat16"),
			attn=data.get("attn", "flash_attention_2"),
			quant=data.get("quant"),
			max_new_tokens=data.get("max_new_tokens", 512),
			temperature=data.get("temperature", 0.8),
			top_p=data.get("top_p", 0.95),
			seed=data.get("seed"),
			thinking=data.get("thinking", "auto"),
			reasoning_effort=data.get("reasoning_effort"),
			tool_names=tuple(data.get("tool_names", ())),
			max_tool_iters=data.get("max_tool_iters", 4),
			kv_reuse=data.get("kv_reuse", "auto"),
			weights_path=data.get("weights_path"),
		)
