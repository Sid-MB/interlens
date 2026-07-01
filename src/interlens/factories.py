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
from .loading import load_model, load_tokenizer, participant_class_for, derive_chat_flags
from .participant.participants.model_participant import ModelParticipant

# A model to build a participant from: an HF id / local path (str), or an already-loaded model.
ModelLike = str | PreTrainedModel


def _build(model, tokenizer, *, name, device, **participant_kwargs) -> ModelParticipant:
	"""Construct the family-correct participant for a loaded ``model`` + ``tokenizer``: the class comes from the
	model's ``config.model_type`` (AutoModel-style), the chat-template flags are derived from the tokenizer."""
	cls = participant_class_for(getattr(model.config, "model_type", None))
	supports_system, requires_alt = derive_chat_flags(tokenizer)
	p = cls(model=model, tokenizer=tokenizer, name=name, device=device, **participant_kwargs)
	p.supports_system_role = supports_system
	p.requires_alternating_roles = requires_alt
	return p


class AutoModelParticipant:
	"""HF-style factory for family-correct local-model participants — the participant analog of
	``AutoModelForCausalLM``.

	- ``from_`` dispatches on the argument type (str id → load; ``PreTrainedModel`` → wrap).
	- ``from_pretrained`` loads a model by HF id / local path and returns the right ``ModelParticipant`` subclass,
	  resolved from the model's ``config.model_type``.
	- ``from_model`` wraps weights you already hold (e.g. to share weights between speakers); the tokenizer is
	  optional (inferred from the model when omitted).
	"""

	@staticmethod
	def from_(model: ModelLike, *, name: str, tokenizer: PreTrainedTokenizerBase | None = None,
	          device: str | torch.device = "cuda", load_kwargs: dict | None = None,
	          **participant_kwargs) -> ModelParticipant:
		"""Build a participant from either an HF id (str) or an already-loaded ``PreTrainedModel``, dispatching to
		``from_pretrained`` / ``from_model``. ``tokenizer`` applies only to the loaded-model case (a str id loads
		its own matching tokenizer, so it is ignored there)."""
		if isinstance(model, str):
			return AutoModelParticipant.from_pretrained(model, name=name, device=device,
			                                            load_kwargs=load_kwargs, **participant_kwargs)
		return AutoModelParticipant.from_model(model, tokenizer, name=name, device=device, **participant_kwargs)

	@staticmethod
	def from_pretrained(id_or_name: str, *, name: str, device: str | torch.device = "cuda",
	                    load_kwargs: dict | None = None, **participant_kwargs) -> ModelParticipant:
		"""Load ``id_or_name`` (an HF id or local path) and return the family-correct participant, with its class
		resolved from ``config.model_type`` and its chat-template flags derived from the tokenizer.

		``load_kwargs`` are forwarded to ``load_model`` (``dtype`` / ``attn`` / ``quant`` / ``revision`` — their
		defaults live there, not here); ``participant_kwargs`` (``temperature``, ``max_new_tokens``,
		``system_prompt``, ``tools``, ``kv_reuse``, …) go to the participant. Weight loads are process-cached, so
		calling this twice with the same id/device/dtype shares ONE model object (weight sharing is automatic).
		"""
		model, tokenizer = load_model(id_or_name, device=device, **(load_kwargs or {}))
		return _build(model, tokenizer, name=name, device=device, **participant_kwargs)

	@staticmethod
	def from_model(model: PreTrainedModel, tokenizer: PreTrainedTokenizerBase | None = None, *, name: str,
	               device: str | torch.device | None = None, **participant_kwargs) -> ModelParticipant:
		"""Build a family-correct participant from an already-loaded ``model``. ``tokenizer`` is optional — when
		omitted it is inferred from ``model.config._name_or_path`` via ``load_tokenizer``. The class is resolved
		from the model's ``config.model_type`` and the chat-template flags from the tokenizer, so an unknown model
		falls back to the base ``ModelParticipant`` with correctly-derived flags."""
		if tokenizer is None:
			hf_id = getattr(model.config, "_name_or_path", None)
			if not hf_id:
				raise ValueError("cannot infer a tokenizer: model.config._name_or_path is empty; pass tokenizer=")
			tokenizer = load_tokenizer(hf_id)
		return _build(model, tokenizer, name=name, device=device, **participant_kwargs)


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
