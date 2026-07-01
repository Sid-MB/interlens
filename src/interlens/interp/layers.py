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
