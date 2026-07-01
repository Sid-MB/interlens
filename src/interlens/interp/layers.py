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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from transformers import PreTrainedModel


def decoder_layers(model: "PreTrainedModel"):
	"""Return the list of transformer decoder layer modules, across common HF architectures.

	Steering/patching hooks and per-layer capture all need the ordered layer stack. Qwen and Gemma both expose
	it at ``model.model.layers``; a few fallbacks cover other families so the interp layer isn't Qwen/Gemma-only.
	"""
	for path in ("model.layers", "transformer.h", "gpt_neox.layers", "model.decoder.layers"):
		obj = model
		try:
			for attr in path.split("."):
				obj = getattr(obj, attr)
			return obj
		except AttributeError:
			continue
	raise AttributeError(f"could not locate decoder layers on {type(model).__name__}")
