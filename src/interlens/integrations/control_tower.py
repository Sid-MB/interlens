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

"""Run a local Interlens participant behind Control Tower's untrusted-policy boundary.

Control Tower loads :func:`interlens_untrusted_policy` as an external ``module:function`` policy. The returned
generate function has Inspect's normal model signature, so blue protocols see and control every generated tool
call. Interlens owns local generation and interpretability; Control Tower owns tool execution, monitoring,
auditing, sandboxing, and trajectory storage.
"""
from __future__ import annotations

import asyncio
import importlib
import threading
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

try:
	from inspect_ai.model import (ChatCompletionChoice, ChatMessage, ChatMessageAssistant, ChatMessageTool,
	                              GenerateConfig, ModelOutput, ModelUsage)
	from inspect_ai.solver import TaskState
	from inspect_ai.tool import Tool, ToolCall, ToolChoice, ToolDef, ToolFunction
except ImportError as _err:  # pragma: no cover - exercised only without the optional dependency
	raise ImportError(
		"interlens.integrations.control_tower requires Inspect AI. "
		"Install it with: pip install 'interlens[inspect]' control-tower"
	) from _err

from ..message import Message

InterlensGenerateFn = Callable[
	[list[ChatMessage], list[Tool], ToolChoice | None, GenerateConfig],
	Awaitable[ModelOutput],
]

_LOCKS_GUARD = threading.Lock()
_GENERATION_LOCKS: dict[tuple, threading.Lock] = {}


def _load_factory(reference: str) -> Callable[[], Any]:
	"""Resolve a ``module:function`` reference to a zero-argument participant factory.

	Args:
		reference: Import reference such as ``"my_project.policies:local_qwen"``. Use a zero-argument factory so
			Control Tower constructs a fresh participant for each sample and no model state leaks across trajectories.

	Returns:
		The referenced callable.
	"""
	if ":" not in reference:
		raise ValueError(
			f"participant_factory must be a 'module:function' reference, got {reference!r}")
	module_name, attribute = reference.split(":", 1)
	factory = getattr(importlib.import_module(module_name), attribute)
	if not callable(factory):
		raise TypeError(f"participant factory {reference!r} is not callable")
	return factory


def _message_text(message: ChatMessage) -> str:
	"""Return the visible text of an Inspect message and reject unsupported multimodal blocks.

	Args:
		message: Inspect chat message to translate. Plain text and reasoning blocks are supported; image, audio,
			video, document, data, and provider-hosted tool-use content are rejected because local Hugging Face chat
			templates cannot represent them faithfully.

	Returns:
		The message's visible text.
	"""
	content = message.content
	if isinstance(content, list):
		unsupported = [getattr(block, "type", type(block).__name__)
		               for block in content if getattr(block, "type", None) not in ("text", "reasoning")]
		if unsupported:
			raise NotImplementedError(
				f"Interlens local participants only support text/reasoning Inspect content; got {unsupported}")
	return message.text


def _inspect_messages_to_view(messages: list[ChatMessage]) -> list[dict]:
	"""Translate Inspect messages into the structured view consumed by a local participant.

	Args:
		messages: Current Control Tower/Inspect model history, including earlier assistant tool calls and tool results.

	Returns:
		A chat-template-compatible list of message dictionaries.
	"""
	view = []
	for message in messages:
		item: dict[str, Any] = {"role": message.role, "content": _message_text(message)}
		if isinstance(message, ChatMessageAssistant) and message.tool_calls:
			item["tool_calls"] = [
				{"id": call.id, "type": call.type,
				 "function": {"name": call.function, "arguments": call.arguments}}
				for call in message.tool_calls
			]
		elif isinstance(message, ChatMessageTool):
			if message.tool_call_id is not None:
				item["tool_call_id"] = message.tool_call_id
			if message.function is not None:
				item["name"] = message.function
		view.append(item)
	return view


def _inspect_tool_schemas(tools: list[Tool]) -> list[dict]:
	"""Convert Inspect tool definitions to the schemas rendered by Interlens chat templates.

	Args:
		tools: Inspect tools offered by the active Control Tower protocol. Their callables are never invoked here.

	Returns:
		OpenAI-style function schemas containing each tool's name, description, and JSON parameters.
	"""
	schemas = []
	for tool in tools:
		definition = ToolDef(tool)
		schemas.append({
			"type": "function",
			"function": {
				"name": definition.name,
				"description": definition.description,
				"parameters": definition.parameters.model_dump(exclude_none=True),
			},
		})
	return schemas


def _tool_choice_schemas(tools: list[Tool], tool_choice: ToolChoice | None) -> list[dict]:
	"""Apply the supported Inspect tool-choice mode and return schemas for this call.

	Args:
		tools: Inspect tools available to the model.
		tool_choice: ``None``/``"auto"`` allows optional calls; ``"none"`` hides tools. ``"any"`` and a forced
			``ToolFunction`` are rejected because Hugging Face chat templates expose schemas but cannot reliably
			enforce a required call.

	Returns:
		The schemas to pass to the Interlens participant.
	"""
	if tool_choice == "none":
		return []
	if tool_choice in (None, "auto"):
		return _inspect_tool_schemas(tools)
	if tool_choice == "any" or isinstance(tool_choice, ToolFunction):
		raise NotImplementedError(
			"Interlens local participants support Inspect tool_choice='auto' or 'none'; "
			"required/forced tool calls are not enforceable through Hugging Face chat templates.")
	raise ValueError(f"unknown Inspect tool_choice {tool_choice!r}")


def _model_id(participant: Any) -> str:
	"""Return the stable model identifier recorded in Inspect trajectories.

	Args:
		participant: Interlens participant being adapted.

	Returns:
		``model_id``, then ``hf_id``, then the participant name/type as a fallback.
	"""
	return (getattr(participant, "model_id", None) or getattr(participant, "hf_id", None)
	        or getattr(participant, "name", None) or type(participant).__name__)


def _generation_lock(participant: Any) -> threading.Lock:
	"""Return the process-wide lock for a participant's shared local model.

	Args:
		participant: Interlens participant whose model recipe or loaded-object identity determines lock sharing.

	Returns:
		A lock shared by adapters backed by the same cached model. Control Tower may run samples concurrently, while
		Hugging Face ``generate`` mutates model/cache state and is not safe to call concurrently on one model object.
	"""
	signature = getattr(participant, "batch_signature", None)
	key = tuple(signature()) if callable(signature) else ("participant", _model_id(participant))
	with _LOCKS_GUARD:
		return _GENERATION_LOCKS.setdefault(key, threading.Lock())


def _inspect_output(participant: Any, message: Message) -> ModelOutput:
	"""Translate one Interlens generation step into an Inspect model output.

	Args:
		participant: Participant that generated ``message``.
		message: Interlens message whose metadata may contain parsed tool calls, reasoning, usage, and cost.

	Returns:
		A normal Inspect ``ModelOutput`` consumed unchanged by Control Tower blue protocols.
	"""
	model = _model_id(participant)
	tool_calls = [
		ToolCall(id=str(uuid.uuid4()), function=call["name"], arguments=call.get("arguments") or {})
		for call in message.metadata.get("tool_calls", [])
	]
	assistant = ChatMessageAssistant(
		content=message.content, tool_calls=tool_calls or None, model=model,
		metadata={"interlens": True},
	)
	tokens_in = int(message.metadata.get("n_tokens_in") or 0)
	tokens_out = int(message.metadata.get("n_tokens") or 0)
	stop_reason = "tool_calls" if tool_calls else message.metadata.get("stop_reason", "stop")
	if stop_reason not in {"stop", "max_tokens", "model_length", "tool_calls", "content_filter", "unknown"}:
		stop_reason = "unknown"
	return ModelOutput(
		model=model,
		choices=[ChatCompletionChoice(message=assistant, stop_reason=stop_reason)],
		usage=ModelUsage(
			input_tokens=tokens_in,
			output_tokens=tokens_out,
			total_tokens=tokens_in + tokens_out,
			total_cost=message.metadata.get("cost_usd"),
		),
		metadata={
			"interlens": {
				"reasoning_provenance": message.metadata.get("reasoning_provenance", "none"),
				"steering": message.metadata.get("steering"),
			},
		},
	)


def participant_generate(participant: Any, *, steering=None, capture=None, patch=None,
	                     return_logprobs: bool = False) -> InterlensGenerateFn:
	"""Adapt one local Interlens participant to Inspect's model-generation protocol.

	Args:
		participant: Participant implementing ``generate_step``. Normally this is a ``ModelParticipant`` returned by
			``AutoModelParticipant.from_pretrained``. A single instance is used for one Control Tower sample.
		steering: Optional Interlens steering spec applied to every model call. ``None`` uses the participant default.
		capture: Optional Interlens capture request applied to every model call.
		patch: Optional Interlens activation patch applied to every model call.
		return_logprobs: Whether Interlens should collect generated-token log probabilities. Enable only when later
			analysis needs them because it increases memory use.

	Returns:
		An async function with the ``UntrustedPolicyGenerateFn`` signature expected by Control Tower.
	"""
	if not callable(getattr(participant, "generate_step", None)):
		raise TypeError(
			f"{type(participant).__name__} does not implement generate_step; "
			"Control Tower requires a local ModelParticipant-style one-step generator.")
	generation_lock = _generation_lock(participant)

	async def generate(input: list[ChatMessage], tools: list[Tool], tool_choice: ToolChoice | None,
	                   config: GenerateConfig) -> ModelOutput:
		"""Generate one proposed action while leaving all tool execution to Control Tower."""
		view = _inspect_messages_to_view(input)
		schemas = _tool_choice_schemas(tools, tool_choice)
		max_tokens = getattr(config, "max_tokens", None)

		def run_step() -> Message:
			"""Serialize generation on a process-cached model while keeping the event loop responsive."""
			with generation_lock:
				return participant.generate_step(
					view,
					tool_schemas=schemas,
					steering=steering,
					capture=capture,
					patch=patch,
					return_logprobs=return_logprobs,
					max_new_tokens=max_tokens,
				)

		message = await asyncio.to_thread(run_step)
		return _inspect_output(participant, message)

	return generate


def interlens_untrusted_policy(state: TaskState, participant_factory: str) -> InterlensGenerateFn:
	"""Control Tower external untrusted policy backed by a local Interlens participant.

	Select this function with
	``--untrusted-policy interlens.integrations.control_tower:interlens_untrusted_policy``.

	Args:
		state: Current Control Tower sample state. It establishes the per-sample factory lifetime; task content itself
			arrives through the generate function's messages.
		participant_factory: Zero-argument ``module:function`` reference returning a fresh local Interlens participant,
			for example ``"my_project.policies:local_qwen"``.

	Returns:
		The adapted participant's Inspect-compatible generate function.
	"""
	del state
	participant = _load_factory(participant_factory)()
	return participant_generate(participant)


__all__ = ["InterlensGenerateFn", "participant_generate", "interlens_untrusted_policy"]
