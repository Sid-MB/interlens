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

from pathlib import Path

import torch
from transformers import PreTrainedModel, PreTrainedTokenizerBase

from .conversation import Conversation, PromptLike
from .participant.participants.model_participant import ModelParticipant
from .participant.participants.gemma import GemmaModelParticipant
from .participant.participants.llama import LlamaModelParticipant
from .participant.participants.qwen import QwenModelParticipant

# A model to build a participant from: an HF id (str), a local path (str / Path), or an already-loaded model.
ModelLike = str | Path | PreTrainedModel


class AutoModelParticipant:
	"""HF-style factory for family-correct local-model participants — the participant analog of
	``AutoModelForCausalLM``. It resolves the concrete ``ModelParticipant`` subclass from the model's
	transformers ``config.model_type`` (``_BY_MODEL_TYPE``), then delegates the actual build to that class's
	``from_model`` / ``from_pretrained`` — so all the loading / tokenizer-inference / chat-flag logic lives in one
	place (on ``ModelParticipant``) and this class is *only* the family dispatcher.

	- ``from_`` dispatches on the argument type (str id → ``from_pretrained``; ``PreTrainedModel`` → ``from_model``).
	- To get a statically-known subclass, name it directly: ``QwenModelParticipant.from_pretrained(...)``. This
	  factory returns the (dynamically resolved) base ``ModelParticipant`` type.
	"""

	# model_type (from transformers ``config.model_type``) → participant class. Only families that need a
	# non-base subclass appear here; everything else falls through to ``ModelParticipant``. This is the single
	# source of the family mapping — no separate registry module.
	_BY_MODEL_TYPE: dict[str, type[ModelParticipant]] = {
		"gemma2": GemmaModelParticipant,
		"gemma3": GemmaModelParticipant,
		"llama": LlamaModelParticipant,
		"qwen2": QwenModelParticipant,
		"qwen3": QwenModelParticipant,
	}

	@classmethod
	def _class_for(cls, model: PreTrainedModel) -> type[ModelParticipant]:
		return cls._BY_MODEL_TYPE.get(getattr(model.config, "model_type", "") or "", ModelParticipant)

	@staticmethod
	def from_(model: ModelLike, *, name: str, tokenizer: PreTrainedTokenizerBase | None = None,
	          device: str | torch.device = "cuda", load_kwargs: dict | None = None,
	          **participant_kwargs) -> ModelParticipant:
		"""Build a participant from either an HF id (str) or an already-loaded ``PreTrainedModel``, dispatching to
		``from_pretrained`` / ``from_model``. ``tokenizer`` applies only to the loaded-model case (an id / path loads
		its own matching tokenizer, so it is ignored there)."""
		if isinstance(model, (str, Path)):
			return AutoModelParticipant.from_pretrained(model, name=name, device=device,
			                                            load_kwargs=load_kwargs, **participant_kwargs)
		return AutoModelParticipant.from_model(model, tokenizer, name=name, device=device, **participant_kwargs)

	@staticmethod
	def from_pretrained(id_or_path: str | Path, *, name: str, device: str | torch.device = "cuda",
	                    load_kwargs: dict | None = None, **participant_kwargs) -> ModelParticipant:
		"""Load ``id_or_path`` (an HF id or local path) and return the family-correct participant, with its class
		resolved from ``config.model_type``. ``load_kwargs`` / ``participant_kwargs`` are forwarded through the
		resolved class's ``from_pretrained`` (see :meth:`ModelParticipant.from_pretrained`)."""
		from .loading import load_model  # lazy: avoids importing torch/transformers loaders at module import
		model, tokenizer = load_model(id_or_path, device=device, **(load_kwargs or {}))
		return AutoModelParticipant.from_model(model, tokenizer, name=name, device=device, **participant_kwargs)

	@staticmethod
	def from_model(model: PreTrainedModel, tokenizer: PreTrainedTokenizerBase | None = None, *, name: str,
	               device: str | torch.device | None = None, **participant_kwargs) -> ModelParticipant:
		"""Build a family-correct participant from an already-loaded ``model`` — the class is resolved from
		``config.model_type`` (unknown types fall back to base ``ModelParticipant``), then that class's
		:meth:`ModelParticipant.from_model` does the tokenizer inference and chat-flag derivation."""
		cls = AutoModelParticipant._class_for(model)
		return cls.from_model(model, tokenizer, name=name, device=device, **participant_kwargs)


def conversation_from_models(
	models: tuple[ModelLike, ...],
	names: tuple[str, ...] = ("a", "b"),
	device: str | torch.device = "cuda",
	dtype: torch.dtype = torch.bfloat16,
	shared_context: str | None = None,
	shared_system_prompt: str | None = None,
	prompt: PromptLike = None,
	**gen_kwargs,
) -> Conversation:
	"""Scaffold a conversation from a tuple of ``models`` — each an HF id (str) or an already-loaded
	``PreTrainedModel`` (see ``ModelLike``). Each becomes a family-correct participant via
	``AutoModelParticipant.from_``; ``names`` gives them their identities. **The order of ``models`` / ``names``
	is the speaking order** — the first speaks first unless you pass ``first=`` to ``run`` — and ``**gen_kwargs``
	are forwarded to every participant.

	This is the implementation behind :meth:`Conversation.from_models` (which just wraps it). If two ids resolve
	to the same HF model the weights are loaded **once** and shared (via ``load_model``'s process cache).

	Two ways to seed the opening, without touching the transcript by hand:

	- ``shared_context`` — a neutral, ``moderator``-voiced turn everyone sees (scenario/topic framing); pair with
	  ``shared_system_prompt`` for system-role instructions. These are the principled framing knobs (serialized
	  into a template).
	- ``prompt`` — a *participant*-voiced opener: a ``str`` is attributed to the LAST participant so the first
	  speaker replies to it, a ``Message`` sets the author explicitly. Use this when the opener should read as
	  something a speaker said rather than moderator framing.
	"""
	participants = tuple(
		AutoModelParticipant.from_(m, name=n, device=device, load_kwargs={"dtype": dtype}, **gen_kwargs)
		for m, n in zip(models, names)
	)
	conv = Conversation(participants=participants, shared_context=shared_context,
	                    shared_system_prompt=shared_system_prompt)
	conv._append_prompt(prompt)
	return conv


def conversation_from_ids(ids: tuple[ModelLike, ...], **kwargs) -> Conversation:
	"""Deprecated thin alias for :func:`conversation_from_models` / :meth:`Conversation.from_models`, kept for
	back-compat. Prefer ``Conversation.from_models(models=..., ...)``."""
	return conversation_from_models(ids, **kwargs)
