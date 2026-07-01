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

import torch
from transformers import PreTrainedModel, PreTrainedTokenizerBase

from .conversation import Conversation, PromptLike
from .loading import load_model, load_tokenizer, participant_class, generation_for_hf_id
from .participant.participants.model_participant import ModelParticipant

# A model to build a participant from: a registry short name / HF id (str), or an already-loaded model.
ModelLike = str | PreTrainedModel


class AutoModelParticipant:
	"""HF-style factory for family-correct local-model participants — the participant analog of
	``AutoModelForCausalLM``.

	- ``from_`` dispatches on the argument type (str id → load; ``PreTrainedModel`` → wrap).
	- ``from_pretrained`` loads a model by short name / HF id and returns the right ``ModelParticipant`` subclass.
	- ``from_model`` wraps weights you already hold (e.g. to share weights between speakers); the tokenizer is
	  optional (inferred from the model when omitted).
	- ``class_for`` just resolves the class without loading anything.
	"""

	@staticmethod
	def from_(model: ModelLike, *, name: str, tokenizer: PreTrainedTokenizerBase | None = None,
	          device: str | torch.device = "cuda", generation: str | None = None,
	          load_kwargs: dict | None = None, **participant_kwargs) -> ModelParticipant:
		"""Build a participant from either a model id (str) or an already-loaded ``PreTrainedModel``, dispatching to
		``from_pretrained`` / ``from_model``. ``tokenizer`` applies only to the loaded-model case (a str id loads
		its own matching tokenizer, so it is ignored there)."""
		if isinstance(model, str):
			return AutoModelParticipant.from_pretrained(model, name=name, device=device, generation=generation,
			                                            load_kwargs=load_kwargs, **participant_kwargs)
		return AutoModelParticipant.from_model(model, tokenizer, name=name, generation=generation,
		                                       device=device, **participant_kwargs)

	@staticmethod
	def from_pretrained(id_or_name: str, *, name: str, device: str | torch.device = "cuda",
	                    generation: str | None = None, load_kwargs: dict | None = None,
	                    **participant_kwargs) -> ModelParticipant:
		"""Load ``id_or_name`` (short registry name or raw HF id) and return the family-correct participant.

		``load_kwargs`` are forwarded to ``load_model`` (``dtype`` / ``attn`` / ``quant`` / ``revision`` — their
		defaults live there, not here); ``participant_kwargs`` (``temperature``, ``max_new_tokens``,
		``system_prompt``, ``tools``, ``kv_reuse``, …) go to the participant. ``generation`` forces the
		chat-behavior class for a raw HF id the registry can't resolve. Weight loads are process-cached, so calling
		this twice with the same id/device/dtype shares ONE model object (weight sharing is automatic).
		"""
		model, tokenizer = load_model(id_or_name, device=device, **(load_kwargs or {}))
		cls = participant_class(id_or_name, generation=generation)
		return cls(model=model, tokenizer=tokenizer, name=name, device=device, **participant_kwargs)

	@staticmethod
	def from_model(model: PreTrainedModel, tokenizer: PreTrainedTokenizerBase | None = None, *, name: str,
	               id_or_name: str | None = None, generation: str | None = None,
	               device: str | torch.device | None = None, **participant_kwargs) -> ModelParticipant:
		"""Build a family-correct participant from an already-loaded ``model``. ``tokenizer`` is optional — when
		omitted it is inferred from ``model.config._name_or_path`` via ``load_tokenizer``. The class is resolved
		from ``generation``, else ``id_or_name``, else the model's own HF id (so a registry model wraps to the
		right family with no extra args); an unknown model falls back to the base ``ModelParticipant``."""
		hf_id = getattr(model.config, "_name_or_path", None)
		if generation is None and id_or_name is None and hf_id:
			generation = generation_for_hf_id(hf_id)  # detect family from the loaded model's HF id
		if tokenizer is None:
			if not hf_id:
				raise ValueError("cannot infer a tokenizer: model.config._name_or_path is empty; pass tokenizer=")
			tokenizer = load_tokenizer(hf_id)
		cls = participant_class(id_or_name, generation=generation)
		return cls(model=model, tokenizer=tokenizer, name=name, device=device, **participant_kwargs)

	@staticmethod
	def class_for(id_or_name: str | None = None, *, generation: str | None = None) -> type[ModelParticipant]:
		"""Resolve the participant class for a model id / generation without loading anything (the low-level
		primitive behind ``from_pretrained`` / ``from_model``)."""
		return participant_class(id_or_name, generation=generation)


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
	"""Scaffold a conversation from a tuple of ``models`` — each a registry short name / HF id (str) or an
	already-loaded ``PreTrainedModel`` (see ``ModelLike``). Each becomes a family-correct participant via
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
