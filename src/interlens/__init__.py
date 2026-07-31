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

# [rational_agents: lazy-imports] 2026-07-31

"""The public ``interlens`` API, exported **lazily**.

Every name below still resolves with a plain ``from interlens import X``; the only thing that changed is *when*
the defining module is imported. Eagerly importing the whole API pulled in ``torch`` and ``transformers`` (~7 s
warm, far worse on a cold NFS mount) even for the many CPU-only entry points that never touch a model —
``interlens.arena.viz`` (reads JSON, writes HTML), ``interlens.arena.negotiation.analysis``, audit scripts. The
table below is the single source of truth: it maps each defining module to the names it exports, ``__getattr__``
(PEP 562) imports that module on **first attribute access** and caches the value in module globals, and
``__all__`` is derived from it. To add an export, add it here and nowhere else.
"""
from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

# module (relative to ``interlens``) -> the public names it defines. Ordered as the API reads, not alphabetically.
_EXPORTS_BY_MODULE: dict[str, tuple[str, ...]] = {
	".message": ("Message",),
	".transcript": ("Transcript",),
	".context_item": ("ContextItem",),
	".functional": ("Functional",),
	".templating": ("dataset_field", "DatasetField"),
	".conversation": ("Conversation",),
	".reasoning_visibility": ("ReasoningVisibility",),
	".execution_mode": ("ExecutionMode",),
	".participant": ("Participant",),
	".participant.participants.model_participant": ("ModelParticipant",),
	".participant.participants.qwen": ("QwenModelParticipant",),
	".participant.participants.gemma": ("GemmaModelParticipant",),
	".participant.participants.llama": ("LlamaModelParticipant",),
	".participant.participants.api_participant": ("APIParticipant", "OpenRouterRouting", "Provider"),
	".participant.participants.scripted_participant": ("ScriptedParticipant",),
	".context": ("ContextPolicy", "ErrorPolicy", "DropOldestPolicy", "SlidingWindowPolicy", "SummarizePolicy"),
	".hooks": ("MessageHook", "MessageHookResult", "HookAction"),
	".stop": ("StopCondition", "AnyStopCondition", "TurnStopCondition", "TokenStopCondition",
	          "ElapsedTimeStopCondition", "StopStringCondition", "TokenBudget"),
	".interp": ("ActivationCache", "CaptureSpec", "SteeringSpec", "Patch", "token_logprobs", "decoder_layers",
	            "GradCaptureSpec", "GradForwardOutput", "forward_with_grad", "continuation_logprob",
	            "soft_embed", "gumbel_softmax_tokens", "LinearBridge"),
	".tools": ("Tool", "ToolCall", "ToolResult", "ToolRegistry", "DEFAULT_REGISTRY"),
	".communication": ("CommunicationPolicy", "RoundRobinPolicy", "DirectPipingPolicy", "MessagingPolicy"),
	".usage": ("UsageMeter", "CostBudget", "register_pricing", "transcript_usage"),
	".runner": ("available_devices", "run", "run_jobs", "RunResult", "RunReport", "register_analyzer",
	            "register_worker_init"),
	".factories": ("conversation_from_models", "conversation_from_ids", "AutoModelParticipant", "ModelLike"),
}

# Inverted lookup used by ``__getattr__``: public name -> defining module.
_MODULE_BY_EXPORT: dict[str, str] = {
	name: module for module, names in _EXPORTS_BY_MODULE.items() for name in names
}

__all__ = list(_MODULE_BY_EXPORT)

if TYPE_CHECKING:
	# Static mirror of the table above — type checkers and IDEs do not execute ``__getattr__``, so the eager
	# imports are kept here (and only here) for them. ``tests/test_lazy_imports.py`` pins this block against
	# ``_EXPORTS_BY_MODULE`` so the two cannot drift.
	from .message import Message
	from .transcript import Transcript
	from .context_item import ContextItem
	from .functional import Functional
	from .templating import dataset_field, DatasetField
	from .conversation import Conversation
	from .reasoning_visibility import ReasoningVisibility
	from .execution_mode import ExecutionMode
	from .participant import Participant
	from .participant.participants.model_participant import ModelParticipant
	from .participant.participants.qwen import QwenModelParticipant
	from .participant.participants.gemma import GemmaModelParticipant
	from .participant.participants.llama import LlamaModelParticipant
	from .participant.participants.api_participant import APIParticipant, OpenRouterRouting, Provider
	from .participant.participants.scripted_participant import ScriptedParticipant
	from .context import ContextPolicy, ErrorPolicy, DropOldestPolicy, SlidingWindowPolicy, SummarizePolicy
	from .hooks import MessageHook, MessageHookResult, HookAction
	from .stop import (StopCondition, AnyStopCondition, TurnStopCondition, TokenStopCondition,
	                   ElapsedTimeStopCondition, StopStringCondition, TokenBudget)
	from .interp import (ActivationCache, CaptureSpec, SteeringSpec, Patch, token_logprobs, decoder_layers,
	                     GradCaptureSpec, GradForwardOutput, forward_with_grad, continuation_logprob,
	                     soft_embed, gumbel_softmax_tokens, LinearBridge)
	from .tools import Tool, ToolCall, ToolResult, ToolRegistry, DEFAULT_REGISTRY
	from .communication import CommunicationPolicy, RoundRobinPolicy, DirectPipingPolicy, MessagingPolicy
	from .usage import UsageMeter, CostBudget, register_pricing, transcript_usage
	from .runner import (available_devices, run, run_jobs, RunResult, RunReport, register_analyzer,
	                     register_worker_init)
	from .factories import conversation_from_models, conversation_from_ids, AutoModelParticipant, ModelLike


def __getattr__(name: str) -> object:
	"""Resolve a public export on first access (PEP 562), importing its defining module then and caching the
	value in ``globals()`` so every later access is an ordinary module-attribute lookup."""
	module = _MODULE_BY_EXPORT.get(name)
	if module is None:
		raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
	value = getattr(import_module(module, __name__), name)
	globals()[name] = value
	return value


def __dir__() -> list[str]:
	"""``dir(interlens)`` lists the full public API even though most of it is not imported yet."""
	return sorted({*globals(), *__all__})
