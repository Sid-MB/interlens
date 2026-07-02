# interlens: type stub for factories.py
# Copyright (C) 2026 Siddharth M. Bhatia — AGPL-3.0-only
#
# Why a stub: the runtime `AutoModelParticipant.from_pretrained` / `from_` resolve the concrete participant
# subclass dynamically from `config.model_type`, so their true return type is the base `ModelParticipant`. These
# @overloads recover a *statically-known* subclass when the caller passes a KNOWN id string literal, without any
# id->class table in the runtime code. Unknown ids (and non-literal `str`) fall through to the `str` overload ->
# `ModelParticipant`, which is always correct. The literal groups mirror the family self-registry (each subclass's
# `MODEL_TYPES`, resolved at runtime by `ModelParticipant.for_model_type`); ids here are the ones actually used in
# this repo — extend as needed. (For a guaranteed static type regardless of the id, name the class directly:
# `QwenModelParticipant.from_pretrained(...)`.)

from pathlib import Path
from typing import Any, Literal, overload

import torch
from transformers import PreTrainedModel, PreTrainedTokenizerBase

from .conversation import Conversation, PromptLike
from .participant.participants.model_participant import ModelParticipant
from .participant.participants.gemma import GemmaModelParticipant
from .participant.participants.llama import LlamaModelParticipant
from .participant.participants.qwen import QwenModelParticipant

ModelLike = str | Path | PreTrainedModel

_QwenId = Literal[
	"Qwen/Qwen2.5-0.5B-Instruct",
	"Qwen/Qwen2.5-1.5B-Instruct",
	"Qwen/Qwen2.5-3B-Instruct",
	"Qwen/Qwen2.5-7B-Instruct",
	"Qwen/Qwen3-4B",
	"Qwen/Qwen3-8B",
]
_GemmaId = Literal[
	"google/gemma-2-2b-it",
	"google/gemma-2-9b-it",
	"google/gemma-3-4b-it",
]
_LlamaId = Literal[
	"meta-llama/Llama-3.1-8B-Instruct",
	"meta-llama/Llama-3.1-70B-Instruct",
]

class AutoModelParticipant:
	@overload
	@staticmethod
	def from_pretrained(id_or_path: _QwenId, *, name: str, device: str | torch.device = ..., load_kwargs: dict | None = ..., **participant_kwargs: Any) -> QwenModelParticipant: ...
	@overload
	@staticmethod
	def from_pretrained(id_or_path: _GemmaId, *, name: str, device: str | torch.device = ..., load_kwargs: dict | None = ..., **participant_kwargs: Any) -> GemmaModelParticipant: ...
	@overload
	@staticmethod
	def from_pretrained(id_or_path: _LlamaId, *, name: str, device: str | torch.device = ..., load_kwargs: dict | None = ..., **participant_kwargs: Any) -> LlamaModelParticipant: ...
	@overload
	@staticmethod
	def from_pretrained(id_or_path: str | Path, *, name: str, device: str | torch.device = ..., load_kwargs: dict | None = ..., **participant_kwargs: Any) -> ModelParticipant: ...

	@overload
	@staticmethod
	def from_(model: _QwenId, *, name: str, tokenizer: PreTrainedTokenizerBase | None = ..., device: str | torch.device = ..., load_kwargs: dict | None = ..., **participant_kwargs: Any) -> QwenModelParticipant: ...
	@overload
	@staticmethod
	def from_(model: _GemmaId, *, name: str, tokenizer: PreTrainedTokenizerBase | None = ..., device: str | torch.device = ..., load_kwargs: dict | None = ..., **participant_kwargs: Any) -> GemmaModelParticipant: ...
	@overload
	@staticmethod
	def from_(model: _LlamaId, *, name: str, tokenizer: PreTrainedTokenizerBase | None = ..., device: str | torch.device = ..., load_kwargs: dict | None = ..., **participant_kwargs: Any) -> LlamaModelParticipant: ...
	@overload
	@staticmethod
	def from_(model: ModelLike, *, name: str, tokenizer: PreTrainedTokenizerBase | None = ..., device: str | torch.device = ..., load_kwargs: dict | None = ..., **participant_kwargs: Any) -> ModelParticipant: ...

	@staticmethod
	def from_model(model: PreTrainedModel, tokenizer: PreTrainedTokenizerBase | None = ..., *, name: str, device: str | torch.device | None = ..., **participant_kwargs: Any) -> ModelParticipant: ...

def conversation_from_models(
	models: tuple[ModelLike, ...],
	names: tuple[str, ...] = ...,
	device: str | torch.device = ...,
	dtype: torch.dtype = ...,
	shared_context: str | None = ...,
	shared_system_prompt: str | None = ...,
	prompt: PromptLike = ...,
	**gen_kwargs: Any,
) -> Conversation: ...

def conversation_from_ids(ids: tuple[ModelLike, ...], **kwargs: Any) -> Conversation: ...
