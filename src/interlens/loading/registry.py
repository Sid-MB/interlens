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

import logging
from typing import NamedTuple

from ..participant.participants.model_participant import ModelParticipant
from ..participant.participants.qwen import QwenModelParticipant
from ..participant.participants.gemma import GemmaModelParticipant, Gemma3ModelParticipant

logger = logging.getLogger(__name__)

# THE single source of truth for everything keyed by model. Two tables:
#   MODELS       short-name  -> (hf_id, generation)          [one row per size]
#   GENERATIONS  generation  -> participant class + behavior [one row per generation]
# Adding a new size = one line in MODELS; adding a new generation = one line in GENERATIONS.


class ModelSpec(NamedTuple):
	"""Registry row for a short model name: the HF id to load and the ``generation`` it belongs to.

	``generation`` (e.g. ``qwen2.5`` vs ``qwen3``, ``gemma2`` vs ``gemma3``) is the behavior + tokenizer group.
	It is deliberately finer than a vendor ``family``: nothing guarantees ``gemma2`` and ``gemma3`` share a chat
	template or tokenizer, so the generation — not the vendor — is what selects chat behavior and tokenizer
	sharing. Every size of one generation shares its ``GENERATIONS`` entry."""

	hf_id: str
	generation: str


class GenerationSpec(NamedTuple):
	"""Behavior for one model generation: the participant ``cls`` (its chat-template flags + tool-call parser).

	Pointing two generations at the same class asserts they have *identical* chat behavior — an explicit,
	testable claim (see ``tests/test_family_flags.py``), not a hidden assumption. When a generation diverges,
	give it its own class here rather than silently reusing another's."""

	cls: type[ModelParticipant]


GENERATIONS: dict[str, GenerationSpec] = {
	"qwen2.5": GenerationSpec(QwenModelParticipant),
	"qwen3": GenerationSpec(QwenModelParticipant),
	"gemma2": GenerationSpec(GemmaModelParticipant),
	"gemma3": GenerationSpec(Gemma3ModelParticipant),
}

MODELS: dict[str, ModelSpec] = {
	"qwen2.5-0.5b": ModelSpec("Qwen/Qwen2.5-0.5B-Instruct", "qwen2.5"),
	"qwen2.5-1.5b": ModelSpec("Qwen/Qwen2.5-1.5B-Instruct", "qwen2.5"),
	"qwen2.5-3b": ModelSpec("Qwen/Qwen2.5-3B-Instruct", "qwen2.5"),
	"qwen3-1.7b": ModelSpec("Qwen/Qwen3-1.7B", "qwen3"),
	"qwen3-4b": ModelSpec("Qwen/Qwen3-4B", "qwen3"),
	"qwen3-8b": ModelSpec("Qwen/Qwen3-8B", "qwen3"),
	"gemma2-2b": ModelSpec("google/gemma-2-2b-it", "gemma2"),
	"gemma2-9b": ModelSpec("google/gemma-2-9b-it", "gemma2"),
	"gemma3-4b": ModelSpec("google/gemma-3-4b-it", "gemma3"),
}

# Reverse index (hf_id -> generation) so a live participant, which only knows its loaded HF id, can recover
# its generation for round-tripping.
_GENERATION_BY_HF_ID: dict[str, str] = {spec.hf_id: spec.generation for spec in MODELS.values()}


def resolve(id_or_name: str) -> tuple[str, str | None]:
	"""Resolve a short name to ``(hf_id, generation)``. A raw HF id passes through with an unknown generation
	(``None``) — the caller then falls back to the base participant behavior."""
	if id_or_name in MODELS:
		spec = MODELS[id_or_name]
		return spec.hf_id, spec.generation
	return id_or_name, None


def tokenizer_id(id_or_name: str) -> str:
	"""The tokenizer-group key for a model = its ``generation`` (same generation → one tokenizer load). Unknown
	models fall back to their own hf id (no sharing)."""
	if id_or_name in MODELS:
		return MODELS[id_or_name].generation
	return id_or_name


def participant_class(id_or_name: str | None, *, generation: str | None = None) -> type[ModelParticipant]:
	"""The participant class for a model. Resolves by ``generation`` if given, else from the model name. Falls
	back to the base ``ModelParticipant`` for an unrecognized generation (e.g. a raw HF id), logging a warning so
	the silent-default is at least visible — a raw id genuinely can't be mapped, so this is a warn, not a raise."""
	gen = generation if generation is not None else resolve(id_or_name)[1] if id_or_name is not None else None
	if gen is None:
		logger.warning("no known generation for model %r; using base ModelParticipant behavior", id_or_name)
		return ModelParticipant
	if gen not in GENERATIONS:
		logger.warning("unknown generation %r (model %r); using base ModelParticipant behavior", gen, id_or_name)
		return ModelParticipant
	return GENERATIONS[gen].cls


def generation_for_hf_id(hf_id: str) -> str | None:
	"""The generation for a loaded HF id, or ``None`` if it isn't in the registry (a raw external model)."""
	return _GENERATION_BY_HF_ID.get(hf_id)


def generation_for_class(cls: type) -> str | None:
	"""A representative generation key whose class is ``cls`` — used to round-trip a live participant whose model
	id isn't in the registry (any generation mapping to that class reconstructs the same behavior)."""
	for gen, spec in GENERATIONS.items():
		if spec.cls is cls:
			return gen
	return None
