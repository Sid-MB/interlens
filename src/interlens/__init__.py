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
from .participant.participants.api_participant import APIParticipant, Provider
from .context import ContextPolicy, ErrorPolicy, DropOldestPolicy, SlidingWindowPolicy, SummarizePolicy
from .hooks import MessageHook, MessageHookResult, HookAction
from .stop import (
	StopCondition,
	AnyStopCondition,
	TurnStopCondition,
	TokenStopCondition,
	ElapsedTimeStopCondition,
	StopStringCondition,
	TokenBudget,
)
from .interp import (
	ActivationCache, CaptureSpec, SteeringSpec, Patch, token_logprobs, decoder_layers,
	GradCaptureSpec, GradForwardOutput, forward_with_grad, continuation_logprob,
	soft_embed, gumbel_softmax_tokens, LinearBridge,
)
from .tools import Tool, ToolCall, ToolResult, ToolRegistry, DEFAULT_REGISTRY
from .runner import (
	available_devices, run, run_jobs, RunResult, RunReport,
	register_analyzer, register_worker_init,
)
from .factories import conversation_from_models, conversation_from_ids, AutoModelParticipant, ModelLike

__all__ = [
	"Message",
	"Transcript",
	"ContextItem",
	"Functional",
	"dataset_field",
	"DatasetField",
	"Conversation",
	"ReasoningVisibility",
	"ExecutionMode",
	"Participant",
	"ModelParticipant",
	"QwenModelParticipant",
	"GemmaModelParticipant",
	"LlamaModelParticipant",
	"APIParticipant",
	"Provider",
	"ContextPolicy",
	"ErrorPolicy",
	"DropOldestPolicy",
	"SlidingWindowPolicy",
	"SummarizePolicy",
	"MessageHook",
	"MessageHookResult",
	"HookAction",
	"StopCondition",
	"AnyStopCondition",
	"TurnStopCondition",
	"TokenStopCondition",
	"ElapsedTimeStopCondition",
	"StopStringCondition",
	"TokenBudget",
	"ActivationCache",
	"CaptureSpec",
	"SteeringSpec",
	"Patch",
	"token_logprobs",
	"decoder_layers",
	"GradCaptureSpec",
	"GradForwardOutput",
	"forward_with_grad",
	"continuation_logprob",
	"soft_embed",
	"gumbel_softmax_tokens",
	"LinearBridge",
	"Tool",
	"ToolCall",
	"ToolResult",
	"ToolRegistry",
	"DEFAULT_REGISTRY",
	"available_devices",
	"run",
	"run_jobs",
	"RunResult",
	"RunReport",
	"register_analyzer",
	"register_worker_init",
	"conversation_from_models",
	"conversation_from_ids",
	"AutoModelParticipant",
	"ModelLike",
]
