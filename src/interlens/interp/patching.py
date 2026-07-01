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
from typing import TYPE_CHECKING

import torch

from .layers import decoder_layers

if TYPE_CHECKING:
	from transformers import PreTrainedModel


@dataclass
class Patch:
	"""Activation patching: overwrite a decoder layer's residual at specific token ``positions`` with saved
	``activations`` (captured from another run/branch).

	This is the cross-branch causal-tracing primitive: capture activations at turn N in one branch (via
	``ActivationCache``), then inject them at the aligned positions of another branch's forward. The harness owns
	this because only it knows the turn/position correspondence between branches.

	P2 applies the patch on the (single) prompt forward — positions index into the prompt sequence. Aligning
	positions across branches is the caller's responsibility; ``Patch`` just performs the overwrite.
	"""

	activations: torch.Tensor  # [len(positions), d_model]
	layer: int
	positions: tuple[int, ...]

	def register(self, model: "PreTrainedModel") -> list:
		layers = decoder_layers(model)
		return [layers[self.layer].register_forward_hook(self._hook())]

	def _hook(self):
		acts = self.activations
		positions = self.positions

		def hook(module, inputs, output):
			is_tuple = isinstance(output, tuple)
			hs = output[0] if is_tuple else output
			# Only patch when the forward covers these positions (i.e. the prefill), not single-token decode steps.
			if hs.shape[1] > max(positions):
				hs = hs.clone()
				repl = acts.to(dtype=hs.dtype, device=hs.device)
				idx = torch.as_tensor(positions, device=hs.device, dtype=torch.long)
				hs[0, idx] = repl
			return (hs, *output[1:]) if is_tuple else hs

		return hook
