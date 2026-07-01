from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TYPE_CHECKING

import torch

from .layers import decoder_layers

if TYPE_CHECKING:
	from transformers import PreTrainedModel

Mode = Literal["add", "ablate"]


@dataclass
class SteeringSpec:
	"""A residual-stream intervention applied during generation via forward hooks on decoder layers.

	``mode='add'`` adds ``coef * direction`` to the residual at ``layers``; ``mode='ablate'`` projects the
	``direction`` component *out* of the residual (directional ablation). The same mechanism covers both because
	ablation is just the projection-removal variant of an additive hook.

	A summary (mode, layers, coef, direction norm) is recorded into ``Message.metadata['steering']`` by the
	participant so a steered/ablated turn is reproducible.
	"""

	direction: torch.Tensor  # [d_model]
	layers: tuple[int, ...]
	coef: float = 1.0
	mode: Mode = "add"

	def register(self, model: "PreTrainedModel") -> list:
		"""Register the steering hooks on ``model`` and return the handles (caller removes them after generate)."""
		layers = decoder_layers(model)
		handles = []
		for li in self.layers:
			handles.append(layers[li].register_forward_hook(self._hook()))
		return handles

	def _hook(self):
		direction = self.direction
		coef = self.coef
		mode = self.mode

		def hook(module, inputs, output):
			is_tuple = isinstance(output, tuple)
			hs = output[0] if is_tuple else output
			d = direction.to(dtype=hs.dtype, device=hs.device)
			if mode == "add":
				hs = hs + coef * d
			else:  # ablate: remove the component along `direction` from every position
				u = d / (d.norm() + 1e-8)
				proj = (hs * u).sum(dim=-1, keepdim=True) * u
				hs = hs - proj
			return (hs, *output[1:]) if is_tuple else hs

		return hook

	def summary(self) -> dict:
		return {"mode": self.mode, "layers": list(self.layers), "coef": self.coef,
		        "direction_norm": float(self.direction.norm())}
