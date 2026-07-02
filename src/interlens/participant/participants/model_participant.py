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

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import torch
from transformers import PreTrainedModel, PreTrainedTokenizerBase

from ..participant import Participant
from ...message import Message
from ...interp.activation_cache import ActivationRecord
from ...interp.capture import capture_activations
from ...interp.logprobs import token_logprobs

logger = logging.getLogger(__name__)

# Matches a leading ``<think> ... </think>`` reasoning block emitted by thinking models (Qwen3, R1-style).
# Kept as a base-class default; families whose delimiters differ override ``split_reasoning``.
_THINK_RE = re.compile(r"^\s*<think>(.*?)</think>\s*", re.DOTALL)

# Hermes/Qwen tool-call format: ``<tool_call>{"name": ..., "arguments": {...}}</tool_call>``.
_TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)


def _common_prefix_len(cached, prompt_ids) -> int:
	"""Length of the shared leading token run between a cached id list and the new prompt id tensor."""
	prompt = prompt_ids.tolist() if hasattr(prompt_ids, "tolist") else list(prompt_ids)
	n = 0
	for a, b in zip(cached, prompt):
		if a != b:
			break
		n += 1
	return n


@dataclass
class _GenResult:
	"""Internal bookkeeping for one generation pass, threaded through the tool loop."""

	raw: str
	full_ids: "torch.Tensor"
	prompt_len: int
	new_tokens: "torch.Tensor"
	n_tokens: int
	scores: object | None


@dataclass
class ModelParticipant(Participant):
	"""A conversation participant backed by a local HuggingFace causal LM.

	Generation flow: the ``Conversation`` hands us a ``view`` — the transcript rendered from *our* perspective,
	already context-fitted and flattened by ``finalize_view`` into ``[{role, content}]``. We apply this model's
	own chat template to it, generate, decode only the newly produced tokens, and split any ``<think>``
	reasoning out of the visible content. Only the visible answer becomes ``Message.content``;
	the parsed reasoning and raw completion live in ``metadata`` under neutral keys, so hidden generated text is
	never fed back into other participants' views (it's stripped from history automatically because
	``render_roles`` uses ``content``).

	The raw ``model`` is exposed deliberately: interpretability experiments register forward hooks on it
	directly, so we don't hide it behind wrapper indirection.
	"""

	model: PreTrainedModel
	tokenizer: PreTrainedTokenizerBase
	name: str
	device: str | torch.device | None = None
	max_new_tokens: int = 512
	temperature: float = 0.8
	top_p: float = 0.95
	seed: int | None = None
	# Reasoning control: 'auto' defers to the template default; a bool forces enable_thinking where supported.
	thinking: bool | str = "auto"
	# Private framing (only this participant sees these; never enters the shared transcript).
	system_prompt: str | None = None
	private_context: tuple = ()
	# Private capabilities: tools only this participant may invoke; the loop is bounded by max_tool_iters.
	tools: tuple = ()
	max_tool_iters: int = 4
	# Cross-turn KV prefix reuse. ``'auto'`` (default) enables it wherever it is safe; ``True``/``False`` force it.
	# It is doubly guarded regardless: reused only when the new prompt extends the cached tokens exactly, and never
	# under steering/patch (whose effect wasn't in the cached KV) or batched generation. Any failure falls back to a
	# full prefill, so it is never wrong-by-default — but it can perturb outputs at the FP level vs. a full prefill,
	# so reproducibility-critical / determinism-mode experiments should pin ``kv_reuse=False``.
	kv_reuse: bool | str = "auto"

	@classmethod
	def from_model(cls, model: PreTrainedModel, tokenizer: PreTrainedTokenizerBase | None = None, *, name: str,
	               device: str | torch.device | None = None, **participant_kwargs) -> Self:
		"""Build a participant of THIS class from an already-loaded ``model`` (e.g. to share weights between
		speakers). ``tokenizer`` is optional — when omitted it is inferred from ``model.config._name_or_path``. The
		chat-template flags (``supports_system_role`` / ``requires_alternating_roles``) are derived from the
		tokenizer's own template, so no per-family configuration is needed. Because it constructs ``cls``, calling
		it on a subclass (``QwenModelParticipant.from_model(...)``) returns that subclass — use
		``AutoModelParticipant.from_model`` instead to have the family resolved from ``config.model_type``."""
		from ...loading import load_tokenizer, derive_chat_flags  # lazy: loading imports this module
		if tokenizer is None:
			hf_id = getattr(model.config, "_name_or_path", None)
			if not hf_id:
				raise ValueError("cannot infer a tokenizer: model.config._name_or_path is empty; pass tokenizer=")
			tokenizer = load_tokenizer(hf_id)
		supports_system, requires_alt = derive_chat_flags(tokenizer)
		p = cls(model=model, tokenizer=tokenizer, name=name, device=device, **participant_kwargs)
		p.supports_system_role = supports_system
		p.requires_alternating_roles = requires_alt
		return p

	@classmethod
	def from_pretrained(cls, id_or_path: str | Path, *, name: str, device: str | torch.device = "cuda",
	                    load_kwargs: dict | None = None, **participant_kwargs) -> Self:
		"""Load ``id_or_path`` (an HF id or local path) and build a participant of THIS class. ``load_kwargs`` are
		forwarded to ``load_model`` (``dtype`` / ``attn`` / ``quant`` / ``revision`` — their defaults live there);
		``participant_kwargs`` (``temperature``, ``max_new_tokens``, ``system_prompt``, ``tools``, ``kv_reuse``, …)
		go to the participant. Weight loads are process-cached, so calling this twice with the same id/device/dtype
		shares ONE model object. As with ``from_model``, the class is ``cls`` — use ``AutoModelParticipant`` to
		resolve the family from ``config.model_type`` instead."""
		from ...loading import load_model  # lazy: loading imports this module
		model, tokenizer = load_model(id_or_path, device=device, **(load_kwargs or {}))
		return cls.from_model(model, tokenizer, name=name, device=device, **participant_kwargs)

	def __post_init__(self):
		# Default to wherever the model already lives, so callers rarely have to think about placement.
		if self.device is None:
			self.device = self.model.device
		self._kv_cache = None       # DynamicCache from the last generation
		self._cached_tokens = None  # the full token ids that produced _kv_cache
		self._kv_reuse_enabled = self._resolve_kv_reuse()
		logger.info("%s: cross-turn KV reuse %s (kv_reuse=%r)", self.name,
		            "ENABLED" if self._kv_reuse_enabled else "disabled", self.kv_reuse)

	def _resolve_kv_reuse(self) -> bool:
		"""Resolve the ``kv_reuse`` setting to a boolean. ``'auto'`` enables reuse because it is runtime-guarded
		(exact-prefix check + safe fallback) and self-disables under steering/patch; an explicit bool forces it."""
		if isinstance(self.kv_reuse, str):
			if self.kv_reuse == "auto":
				return True
			raise ValueError(f"kv_reuse must be a bool or 'auto', got {self.kv_reuse!r}")
		return bool(self.kv_reuse)

	def split_reasoning(self, text: str) -> tuple[str, str | None]:
		"""Split a raw completion into ``(visible_content, parsed_think)``. Base handles the ``<think>...</think>``
		convention; families with other delimiters override this."""
		match = _THINK_RE.match(text)
		if not match:
			return text.strip(), None
		return text[match.end():].strip(), match.group(1).strip()

	def generate(self, view: list[dict], *, steering=None, capture=None, patch=None,
	             return_logprobs: bool = False, turn: int | None = None,
	             max_new_tokens: int | None = None) -> Message:
		if self.seed is not None:
			torch.manual_seed(self.seed)

		schemas = [t.schema for t in self.tools] or None
		# The tool loop runs on a *private* working copy of the view: the assistant's tool-call text and the
		# tool results are appended here so the model can react to them, but only the FINAL natural-language
		# message reaches the shared transcript. The call/result trail is kept private in metadata['tool_trail'].
		working = list(view)
		tool_trail: list[dict] = []
		result = None  # last _GenResult

		for iteration in range(self.max_tool_iters + 1):
			result = self._run_model(working, schemas, steering, patch, return_logprobs, max_new_tokens)
			calls = self.parse_tool_calls(result.raw) if self.tools else []
			if not calls or iteration == self.max_tool_iters:
				if calls:
					# Hit the iteration bound with a pending call — surface it rather than loop forever.
					tool_trail.append({"note": "max_tool_iters reached with unresolved tool call"})
				break
			working = working + [{"role": self.self_role, "content": result.raw}]
			for call in calls:
				tool_result = self._execute(call)
				tool_trail.append({"name": call.name, "arguments": call.arguments,
				                   "output": tool_result.output, "error": tool_result.error})
				working = working + [self.render_tool_result(call, tool_result)]

		content, parsed_think = self.split_reasoning(result.raw)
		metadata = {"raw_completion": result.raw, "parsed_think": parsed_think, "n_tokens": result.n_tokens}
		if steering is not None:
			metadata["steering"] = steering.summary()
		if return_logprobs:
			metadata.update(token_logprobs(result.scores, result.new_tokens))
		if tool_trail:
			metadata["tool_trail"] = tool_trail

		if capture is not None:
			self._capture(capture, result.full_ids, result.prompt_len, result.raw, parsed_think, turn)

		return Message(author=self.name, content=content, metadata=metadata)

	def generate_batch(self, views: list[list[dict]], *, turn: int | None = None,
	                   group_seed: int | None = None) -> list[Message]:
		"""Batched generation for many independent conversations that share THIS model (``throughput`` mode).

		Renders each ``view`` with this model's chat template and runs **one** ``model.generate`` over the
		left-padded batch, returning one ``Message`` per view — the co-stepping throughput win (5-20x on a
		rollout). **No tools/steering/capture/logprobs** here: callers needing those fall back to the
		per-conversation ``generate``. Tokens are **not** guaranteed identical to unbatched — batch composition
		and the single global RNG perturb rows (see PLAN §Execution modes); only distributional reproducibility
		holds. ``metadata['batched']`` marks these turns; ``metadata['shared_prefill']`` marks the fast path.
		"""
		if not views:
			return []
		seed = group_seed if group_seed is not None else self.seed
		if seed is not None:
			torch.manual_seed(seed)

		template_kwargs = {}
		if isinstance(self.thinking, bool):
			template_kwargs["enable_thinking"] = self.thinking
		prompts = [self.tokenizer.apply_chat_template(v, tokenize=False, add_generation_prompt=True,
		                                              **template_kwargs) for v in views]

		do_sample = bool(self.temperature and self.temperature > 0)
		gen = dict(max_new_tokens=self.max_new_tokens, do_sample=do_sample,
		           pad_token_id=self.tokenizer.pad_token_id)
		if do_sample:
			gen.update(temperature=self.temperature, top_p=self.top_p)

		# Shared-scenario fast path: when every rendered prompt is token-identical (turn 1 of a rollout off one
		# scenario), prefill the shared prefix ONCE and fork to N samples via ``num_return_sequences`` instead of
		# N redundant prefills — the "prefill the shared prefix once per participant" win (PLAN §Shared-scenario
		# reuse). Only valid when sampling (identical greedy rows would be identical, so batching is pointless).
		shared_prefill = do_sample and len(views) > 1 and len(set(prompts)) == 1
		if shared_prefill:
			enc = self.tokenizer(prompts[0], return_tensors="pt", add_special_tokens=False).to(self.device)
			prompt_len = enc["input_ids"].shape[1]
			with torch.inference_mode():
				out = self.model.generate(**enc, num_return_sequences=len(views), **gen)
			new = out[:, prompt_len:]
		else:
			prev_side = self.tokenizer.padding_side
			self.tokenizer.padding_side = "left"
			try:
				enc = self.tokenizer(prompts, return_tensors="pt", padding=True,
				                     add_special_tokens=False).to(self.device)
			finally:
				self.tokenizer.padding_side = prev_side
			prompt_len = enc["input_ids"].shape[1]
			with torch.inference_mode():
				out = self.model.generate(**enc, **gen)
			new = out[:, prompt_len:]

		pad_id = self.tokenizer.pad_token_id
		messages = []
		for row in new:
			# Trailing pad ids appear once a row hits EOS before its peers; strip them for an honest token count.
			keep = row[row != pad_id] if pad_id is not None else row
			raw = self.tokenizer.decode(keep, skip_special_tokens=True)
			content, parsed_think = self.split_reasoning(raw)
			messages.append(Message(author=self.name, content=content, metadata={
				"raw_completion": raw, "parsed_think": parsed_think, "n_tokens": int(keep.shape[0]),
				"batched": True, "shared_prefill": shared_prefill,
			}))
		return messages

	def _run_model(self, messages, schemas, steering, patch, return_logprobs, max_new_tokens=None):
		"""One generation over ``messages`` (a flattened view), with the current model's chat template + tool
		schemas and any steering/patch hooks. Returns a ``_GenResult`` with the decoded text and token bookkeeping.
		Steering/patch apply to *every* generation inside the tool loop, per the interp contract."""
		template_kwargs = {}
		if isinstance(self.thinking, bool):
			template_kwargs["enable_thinking"] = self.thinking
		rendered = self.tokenizer.apply_chat_template(
			messages, tokenize=False, add_generation_prompt=True, tools=schemas, **template_kwargs
		)
		enc = self.tokenizer(rendered, return_tensors="pt", add_special_tokens=False).to(self.device)
		prompt_len = enc["input_ids"].shape[1]

		do_sample = bool(self.temperature and self.temperature > 0)
		kwargs = dict(max_new_tokens=max_new_tokens if max_new_tokens is not None else self.max_new_tokens,
		              do_sample=do_sample, pad_token_id=self.tokenizer.pad_token_id)
		if do_sample:
			kwargs.update(temperature=self.temperature, top_p=self.top_p)
		if return_logprobs:
			kwargs.update(output_scores=True, return_dict_in_generate=True)

		# Guarded cross-turn KV reuse: only when enabled AND no steering/patch (their effect wasn't in the cached
		# KV). We ask generate for the resulting cache so we can extend it next turn. Any failure → full prefill.
		want_cache = self._kv_reuse_enabled and steering is None and patch is None
		reused = self._maybe_reuse_cache(enc["input_ids"][0]) if want_cache else None
		if reused is not None:
			kwargs["past_key_values"] = reused
		if want_cache:
			kwargs["return_dict_in_generate"] = True

		handles = []
		if steering is not None:
			handles += steering.register(self.model)
		if patch is not None:
			handles += patch.register(self.model)
		try:
			with torch.inference_mode():
				out = self.model.generate(**enc, **kwargs)
		except Exception:
			# Reuse can be version-fragile; on any failure, retry once with a clean full prefill.
			if reused is None:
				raise
			kwargs.pop("past_key_values", None)
			self._kv_cache = self._cached_tokens = None
			with torch.inference_mode():
				out = self.model.generate(**enc, **kwargs)

		is_dict = return_logprobs or want_cache
		sequences = out.sequences if is_dict else out
		full_ids = sequences[0]
		if want_cache:
			self._store_cache(full_ids, getattr(out, "past_key_values", None))
		new_tokens = full_ids[prompt_len:]
		raw = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
		return _GenResult(
			raw=raw, full_ids=full_ids, prompt_len=prompt_len, new_tokens=new_tokens,
			n_tokens=int(new_tokens.shape[0]), scores=out.scores if return_logprobs else None,
		)

	def _maybe_reuse_cache(self, prompt_ids):
		"""Return a cropped KV cache to reuse iff the cached tokens are an exact prefix of ``prompt_ids`` (the
		conversation grew by appending). Otherwise (prompt reformatted, reasoning stripped, first turn) → None,
		i.e. a full prefill. Chat templates aren't guaranteed prefix-stable, so this exact-prefix check is the
		safety guard."""
		if self._kv_cache is None or self._cached_tokens is None:
			return None
		cached = self._cached_tokens
		lcp = _common_prefix_len(cached, prompt_ids)
		# Reuse only when the ENTIRE cached prefix matches and there is a genuine suffix to still prefill.
		if lcp != len(cached) or lcp == 0 or lcp >= len(prompt_ids):
			return None
		try:
			self._kv_cache.crop(lcp)  # keep only the matched prefix positions
			logger.debug("%s: KV reuse engaged — reusing %d cached tokens, prefilling %d new",
			             self.name, lcp, len(prompt_ids) - lcp)
			return self._kv_cache
		except Exception:
			logger.debug("KV-cache crop failed; degrading to full prefill", exc_info=True)
			return None

	def _store_cache(self, full_ids, cache) -> None:
		if cache is None:
			self._kv_cache = self._cached_tokens = None
		else:
			self._kv_cache = cache
			self._cached_tokens = full_ids.detach().to("cpu").tolist()

	# --- tool calling (uniform loop; per-family parse) -----------------------------------------------------

	def parse_tool_calls(self, text: str) -> list:
		"""Parse tool calls out of a generation. Base handles the common Hermes/Qwen ``<tool_call>{json}</tool_call>``
		format; families with other formats (Gemma's ```` ```tool_code ````, Llama's ``<|python_tag|>``) override
		this. An unrecognized/absent call yields ``[]`` so the loop treats the output as a final message."""
		from ...tools.tool_call import ToolCall

		calls = []
		for match in _TOOL_CALL_RE.finditer(text):
			try:
				data = json.loads(match.group(1))
				calls.append(ToolCall(name=data["name"], arguments=data.get("arguments", {}), raw=match.group(0)))
			except (json.JSONDecodeError, KeyError) as exc:
				logger.debug("dropping malformed tool call %r: %s", match.group(0), exc)
				continue
		return calls

	def render_tool_result(self, call, result) -> dict:
		"""Render a tool result as the standard structured ``tool`` message; the tokenizer's own template turns it
		into the family-native format."""
		return {"role": "tool", "name": result.name, "content": result.output}

	def _execute(self, call):
		"""Execute a parsed call against this participant's tools, capturing errors as a result rather than raising
		(so a bad call doesn't abort the turn)."""
		from ...tools.tool_call import ToolResult

		tool = next((t for t in self.tools if t.name == call.name), None)
		if tool is None:
			return ToolResult(name=call.name, output=f"error: no such tool {call.name!r}", error=True)
		try:
			return ToolResult(name=call.name, output=str(tool(**call.arguments)))
		except Exception as exc:  # tool failures are data, not crashes
			return ToolResult(name=call.name, output=f"error: {exc}", error=True)

	def _capture(self, request, full_ids, prompt_len, raw, parsed_think, turn) -> None:
		"""Run the capture pass over the full (prompt + generated) sequence and add tagged records to the cache,
		with phase spans (prompt / reasoning / answer) computed from the think/answer token boundary."""
		seq_len = int(full_ids.shape[0])
		phases = {"prompt": (0, prompt_len)}
		if parsed_think and "</think>" in raw:
			think_prefix = raw[: raw.index("</think>") + len("</think>")]
			think_tok = len(self.tokenizer(think_prefix, add_special_tokens=False).input_ids)
			boundary = min(prompt_len + think_tok, seq_len)
			phases["reasoning"] = (prompt_len, boundary)
			phases["answer"] = (boundary, seq_len)
		else:
			phases["answer"] = (prompt_len, seq_len)

		input_ids = full_ids.unsqueeze(0).to(self.device)
		# Build all records first, then offload their tensors in ONE batched pinned transfer (add_batch) instead of
		# a per-record GPU->CPU copy.
		records = [
			ActivationRecord(
				participant=self.name,
				message_idx=turn if turn is not None else -1,
				layer=layer,
				site=site,
				tensor=tensor,
				token_span=(prompt_len, seq_len),
				phases=dict(phases),
			)
			for layer, site, tensor in capture_activations(self.model, input_ids, request.spec)
		]
		request.cache.add_batch(records)

	def to_config(self):
		"""Reconstruct a serializable ``ModelParticipantConfig`` from this live participant, for round-tripping.

		The model id and dtype are read back from the loaded model (``config._name_or_path`` / ``model.dtype``),
		so a manually-constructed participant round-trips without the caller threading its id separately.
		"""
		from ..config.model_participant_config import ModelParticipantConfig, dtype_to_str

		hf_id = getattr(self.model.config, "_name_or_path", "")
		return ModelParticipantConfig(
			name=self.name,
			system_prompt=self.system_prompt,
			private_context=tuple(self.private_context),
			model=hf_id,
			dtype=dtype_to_str(self.model.dtype),
			max_new_tokens=self.max_new_tokens,
			temperature=self.temperature,
			top_p=self.top_p,
			seed=self.seed,
			thinking=self.thinking,
			tool_names=tuple(t.name for t in self.tools),
			max_tool_iters=self.max_tool_iters,
			kv_reuse=self.kv_reuse,
		)
