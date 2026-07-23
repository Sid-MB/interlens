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

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Self

import torch
from transformers import PreTrainedModel, PreTrainedTokenizerBase

from ..participant import Participant
from ...functional import Functional
from ...message import Message
from ...parsing import iter_tagged_json, split_leading_think
from ...interp.activation_cache import ActivationRecord
from ...interp.capture import capture_activations
from ...interp.logprobs import token_logprobs

logger = logging.getLogger(__name__)

# Named dtypes for serialization/lazy-load (the participant stores its dtype as a str so it round-trips and
# pickles without a torch handle). This is the single source of the name<->dtype mapping.
_DTYPES = {"float32": torch.float32, "float16": torch.float16, "bfloat16": torch.bfloat16}


def dtype_to_str(dtype) -> str:
	"""``torch.bfloat16`` -> ``'bfloat16'`` (accepts a str unchanged)."""
	return dtype if isinstance(dtype, str) else str(dtype).replace("torch.", "")


def str_to_dtype(name) -> "torch.dtype":
	"""``'bfloat16'`` -> ``torch.bfloat16`` (accepts a ``torch.dtype`` unchanged)."""
	return name if isinstance(name, torch.dtype) else _DTYPES[name]

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
class ModelParticipant(Functional, Participant):
	"""A conversation participant backed by a local HuggingFace causal LM.

	Generation flow: the ``Conversation`` hands us a ``view`` — the transcript rendered from *our* perspective,
	already context-fitted and flattened by ``finalize_view`` into ``[{role, content}]``. We apply this model's
	own chat template to it, generate, decode only the newly produced tokens, and split any ``<think>``
	reasoning out of the visible content. Only the visible answer becomes ``Message.content``;
	the parsed reasoning and raw completion live in ``metadata`` under neutral keys, so hidden generated text is
	never fed back into other participants' views (it's stripped from history automatically because
	``render_roles`` uses ``content``).

	**The participant is its own recipe.** It stores *what to load* (``hf_id`` + dtype/attn/quant/revision) and
	loads the weights **lazily on first use** through the process-wide model cache — so an unrun participant is
	cheap (KBs), pickles across a spawn boundary without shipping weights, and ``.set(...)`` copies share one
	loaded model object by reference (the co-stepping batch win). ``model``/``tokenizer`` are properties that
	trigger the load; the raw ``model`` is exposed deliberately (interp experiments register forward hooks on it).
	Weight loads are keyed on ``(hf_id, device, dtype, attn, quant, revision)`` and cached, so all same-recipe
	participants on one device share ONE object. Build via ``from_pretrained`` (lazy) or ``from_model`` (eager,
	from an already-loaded model); ``.set()`` (from ``Functional``) makes copy-on-write clones with fresh KV state.
	"""

	name: str = ""
	# What to load (weights are pulled lazily on first ``model``/``tokenizer`` access). ``weights_path`` overrides
	# ``hf_id`` as the load source (e.g. a merged-LoRA checkpoint) while ``hf_id`` still names the base for the
	# tokenizer/config; dtype is stored as a str so the participant serializes and pickles without a torch handle.
	hf_id: str | None = None
	weights_path: str | None = None
	dtype: str = "bfloat16"
	attn: str = "flash_attention_2"
	quant: str | None = None
	revision: str | None = None
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
	# Default steering applied to EVERY ``generate`` for this participant when the call doesn't pass its own
	# ``steering=`` (a per-call arg still overrides). Lets a caller attach a persistent intervention to a specific
	# participant (e.g. steer one debater and not the other) without threading it through ``conv.run``. ``None`` =
	# no steering. Excluded from equality/repr (a tensor isn't hashable and shouldn't gate the weight cache).
	steering: object = field(default=None, compare=False, repr=False)
	# Loaded weights/tokenizer — populated lazily (or eagerly by ``from_model``). Not part of equality/repr, and
	# dropped on pickle (see ``__getstate__``); ``.set()`` shares them by reference.
	_model: "PreTrainedModel | None" = field(default=None, compare=False, repr=False)
	_tokenizer: "PreTrainedTokenizerBase | None" = field(default=None, compare=False, repr=False)

	# Family self-registration. Each subclass lists the transformers ``config.model_type`` values it handles in
	# ``MODEL_TYPES``; ``__init_subclass__`` records them in ``_REGISTRY`` so ``AutoModelParticipant`` can resolve a
	# loaded model to its class with NO central table — the family knowledge lives on the class that needs it (next
	# to its ``parse_tool_calls`` override). Unlisted types fall back to base ``ModelParticipant``. ``ClassVar`` keeps
	# both out of the dataclass field set.
	MODEL_TYPES: ClassVar[frozenset[str]] = frozenset()
	_REGISTRY: ClassVar[dict[str, type["ModelParticipant"]]] = {}

	def __init_subclass__(cls, **kwargs):
		super().__init_subclass__(**kwargs)
		for model_type in cls.MODEL_TYPES:
			prior = ModelParticipant._REGISTRY.get(model_type)
			if prior is not None and prior is not cls:
				raise ValueError(f"model_type {model_type!r} is already registered to {prior.__name__}; "
				                 f"{cls.__name__} cannot also claim it")
			ModelParticipant._REGISTRY[model_type] = cls

	@classmethod
	def for_model_type(cls, model_type: str | None) -> type["ModelParticipant"]:
		"""The registered participant class for a transformers ``config.model_type`` (e.g. ``qwen2``, ``gemma2``),
		falling back to base ``ModelParticipant`` for any family that declares no specialized subclass."""
		return cls._REGISTRY.get(model_type or "", ModelParticipant)

	@classmethod
	def from_model(cls, model: PreTrainedModel, tokenizer: PreTrainedTokenizerBase | None = None, *, name: str,
	               device: str | torch.device | None = None, **participant_kwargs) -> Self:
		"""Build a participant of THIS class from an already-loaded ``model`` (the eager path — e.g. to wrap a model
		you already hold, or share weights between speakers). ``tokenizer`` is optional — when omitted it is inferred
		from ``model.config._name_or_path``. The chat-template flags (``supports_system_role`` /
		``requires_alternating_roles``) are derived from the tokenizer's own template. ``hf_id``/``dtype`` are read
		back from the model so the participant can still be pickled + re-loaded on a spawn worker. Because it
		constructs ``cls``, calling it on a subclass returns that subclass — use ``AutoModelParticipant.from_model``
		to have the family resolved from ``config.model_type``."""
		from ...loading import load_tokenizer, derive_chat_flags  # lazy: loading imports this module
		hf_id = getattr(model.config, "_name_or_path", None) or None
		if tokenizer is None:
			if not hf_id:
				raise ValueError("cannot infer a tokenizer: model.config._name_or_path is empty; pass tokenizer=")
			tokenizer = load_tokenizer(hf_id)
		supports_system, requires_alt = derive_chat_flags(tokenizer)
		p = cls(name=name, device=device, hf_id=hf_id, dtype=dtype_to_str(model.dtype),
		        attn=getattr(model, "_resolved_attn", "flash_attention_2"), **participant_kwargs)
		p._model = model
		p._tokenizer = tokenizer
		p.supports_system_role = supports_system
		p.requires_alternating_roles = requires_alt
		if p.device is None:
			p.device = model.device
		return p

	@classmethod
	def from_pretrained(cls, id_or_path: str | Path, *, name: str, device: str | torch.device = "cuda",
	                    load_kwargs: dict | None = None, **participant_kwargs) -> Self:
		"""Build a participant of THIS class that will load ``id_or_path`` (an HF id or local path) **lazily on first
		use** — no weights are touched here. ``load_kwargs`` (``dtype`` / ``attn`` / ``quant`` / ``revision`` /
		``weights_path``) are recorded for that deferred load; ``participant_kwargs`` (``temperature``,
		``max_new_tokens``, ``system_prompt``, ``tools``, ``kv_reuse``, …) go to the participant. When the load fires
		it is process-cached, so all same-(id, device, dtype, …) participants share ONE model object. As with
		``from_model``, the class is ``cls`` — use ``AutoModelParticipant.from_pretrained`` to resolve the family
		from ``config.model_type`` (it reads only the config, still no weights)."""
		lk = dict(load_kwargs or {})
		return cls(name=name, device=device, hf_id=str(id_or_path),
		           weights_path=lk.get("weights_path"), dtype=dtype_to_str(lk.get("dtype", torch.bfloat16)),
		           attn=lk.get("attn", "flash_attention_2"), quant=lk.get("quant"), revision=lk.get("revision"),
		           **participant_kwargs)

	def __post_init__(self):
		# Adopt the model's device if one is already loaded (eager ``from_model`` path); otherwise the device is
		# bound (default 'cuda') and the model loads there lazily on first ``model``/``tokenizer`` access.
		if self.device is None and self._model is not None:
			self.device = self._model.device
		self._kv_cache = None       # DynamicCache from the last generation
		self._cached_tokens = None  # the full token ids that produced _kv_cache
		self._kv_reuse_enabled = self._resolve_kv_reuse()

	# --- lazy loading --------------------------------------------------------------------------------------

	@property
	def model(self) -> "PreTrainedModel":
		"""The loaded HF model, loading it on first access (cached process-wide). The raw model is exposed so interp
		experiments can register forward hooks directly."""
		if self._model is None:
			self._ensure_loaded()
		return self._model

	@property
	def tokenizer(self) -> "PreTrainedTokenizerBase":
		"""The loaded tokenizer, loading the model+tokenizer on first access (cached process-wide)."""
		if self._tokenizer is None:
			self._ensure_loaded()
		return self._tokenizer

	def _bind(self, device) -> "ModelParticipant":
		"""Bind the device the lazy load will target (the runner calls this per worker/GPU before stepping). Returns
		self for chaining. Only meaningful before the first load."""
		self.device = str(device) if device is not None else None
		return self

	def _ensure_loaded(self) -> None:
		"""Load weights + tokenizer onto the bound device via the process cache, then derive chat-template flags.
		Requires a device: uses ``self.device``, else defaults to ``cuda`` when available, else raises."""
		if self._model is not None and self._tokenizer is not None:
			return
		source = self.weights_path or self.hf_id
		if not source:
			raise RuntimeError(f"participant {self.name!r} has no loaded model and no hf_id/weights_path to load "
			                   f"from; build it with from_pretrained(...) or from_model(...).")
		device = self.device
		if device is None:
			device = "cuda" if torch.cuda.is_available() else None
			if device is None:
				raise RuntimeError(f"participant {self.name!r}: no device bound and CUDA is unavailable; "
				                   f"call ._bind(device) (the runner does this per worker).")
			self.device = device
		from ...loading import load_model, derive_chat_flags  # lazy: loading imports this module
		model, tokenizer = load_model(source, device=device, dtype=str_to_dtype(self.dtype), attn=self.attn,
		                              quant=self.quant, revision=self.revision)
		self._model = model
		self._tokenizer = tokenizer
		self.supports_system_role, self.requires_alternating_roles = derive_chat_flags(tokenizer)
		logger.info("%s: loaded %s on %s (kv_reuse %s)", self.name, source, device,
		            "ENABLED" if self._kv_reuse_enabled else "disabled")

	def batch_signature(self) -> tuple:
		"""Key identifying which model this participant would batch AS (used by the co-stepper). When loaded, the
		cached model object's identity is authoritative; when not yet loaded, the load recipe is (the cache
		guarantees same recipe on one device -> same object), so participants can be grouped WITHOUT forcing a
		load."""
		if self._model is not None:
			return ("model", id(self._model))
		return ("model", self.weights_path or self.hf_id, str(self.device), self.dtype, self.attn, self.quant,
		        self.revision)

	def __getstate__(self) -> dict:
		# Drop the heavy/device-bound state on pickle: weights (reloaded lazily on the worker's device via hf_id),
		# tokenizer, and the KV cache (GPU tensors tied to a device the other process doesn't have).
		state = self.__dict__.copy()
		state["_model"] = None
		state["_tokenizer"] = None
		state["_kv_cache"] = None
		state["_cached_tokens"] = None
		return state

	def __setstate__(self, state: dict) -> None:
		self.__dict__.update(state)  # volatile/heavy fields are None; first ``model`` access reloads lazily

	def _after_set(self, original) -> None:
		# A copy-on-write clone shares the loaded model/tokenizer (by reference, via copy.copy) but must NOT inherit
		# the original's KV cache — its transcript/history differs, so reuse would be wrong.
		self._kv_cache = None
		self._cached_tokens = None

	def _resolve_kv_reuse(self) -> bool:
		"""Resolve the ``kv_reuse`` setting to a boolean. ``'auto'`` enables reuse because it is runtime-guarded
		(exact-prefix check + safe fallback) and self-disables under steering/patch; an explicit bool forces it."""
		if isinstance(self.kv_reuse, str):
			if self.kv_reuse == "auto":
				return True
			raise ValueError(f"kv_reuse must be a bool or 'auto', got {self.kv_reuse!r}")
		return bool(self.kv_reuse)

	def split_reasoning(self, text: str) -> tuple[str, str | None]:
		"""Split a raw completion into ``(visible_content, parsed_think)``. Base handles the leading
		``<think>...</think>`` convention (via :func:`interlens.parsing.split_leading_think`); families with
		other delimiters override this."""
		return split_leading_think(text)

	def generate(self, view: list[dict], *, steering=None, capture=None, patch=None,
	             return_logprobs: bool = False, turn: int | None = None,
	             max_new_tokens: int | None = None) -> Message:
		# Fall back to this participant's default steering when the call didn't pass its own (per-call wins).
		if steering is None:
			steering = self.steering
		if self.seed is not None:
			torch.manual_seed(self.seed)

		# An empty view has nothing to condition on: chat templates index conversation[0] unguarded and raise an
		# opaque IndexError deep in transformers. This is almost always the FIRST speaker starting into an empty
		# transcript with no framing. We can't lean on the template injecting a default system turn — newer
		# families (e.g. Qwen-3) drop default system messages and rely on a zero-shot user turn — so any of the
		# framing knobs (or a seeded transcript) is a valid fix, we just need at least one message present.
		if not view:
			raise ValueError(
				f"Participant {self.name!r} was asked to generate with an empty view — nothing to respond to. "
				"This happens when the first speaker starts into an empty transcript with no framing. Provide at "
				"least one of: shared_context=/shared_system_prompt= (Conversation.from_models), a system_prompt "
				"or private_context on the participant, a prompt= to run(), or a pre-seeded transcript. Note an "
				"empty string \"\" counts as no framing."
			)

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
		if parsed_think:
			# a locally captured <think> stream is the model's complete reasoning, recorded verbatim
			metadata["reasoning"] = parsed_think
			metadata["reasoning_provenance"] = "full"
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
	                   group_seed: int | None = None, max_new_tokens: int | None = None) -> list[Message]:
		"""Batched generation for many independent conversations that share THIS model (``throughput`` mode).

		Renders each ``view`` with this model's chat template and runs **one** ``model.generate`` over the
		left-padded batch, returning one ``Message`` per view — the co-stepping throughput win (5-20x on a
		rollout). ``max_new_tokens`` overrides this participant's per-turn cap for the batch (the co-stepper passes a
		``turn_cap`` here so a ``TokenBudget`` can shrink the final round). **No tools/steering/capture/logprobs**
		here: callers needing those fall back to the per-conversation ``generate``. Tokens are **not** guaranteed
		identical to unbatched — batch composition and the single global RNG perturb rows (see PLAN §Execution
		modes); only distributional reproducibility holds. ``metadata['batched']`` marks these turns;
		``metadata['shared_prefill']`` marks the fast path.
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
		gen = dict(max_new_tokens=max_new_tokens if max_new_tokens is not None else self.max_new_tokens,
		           do_sample=do_sample, pad_token_id=self.tokenizer.pad_token_id)
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
			metadata = {
				"raw_completion": raw, "parsed_think": parsed_think, "n_tokens": int(keep.shape[0]),
				"batched": True, "shared_prefill": shared_prefill,
			}
			if parsed_think:
				metadata["reasoning"] = parsed_think        # complete local <think> stream, verbatim
				metadata["reasoning_provenance"] = "full"
			messages.append(Message(author=self.name, content=content, metadata=metadata))
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
		# The steering/patch hooks MUST be removed after this generation — otherwise they persist on the
		# (process-cached) model and silently contaminate every later generation (e.g. a coef sweep would
		# accumulate hooks and collapse). The outer finally guarantees removal on every exit path.
		try:
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
		finally:
			for h in handles:
				h.remove()

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
		format (JSON extraction via :func:`interlens.parsing.iter_tagged_json`); families with other formats
		(Gemma's ```` ```tool_code ````, Llama's ``<|python_tag|>``) override this. An unrecognized/absent call
		yields ``[]`` so the loop treats the output as a final message."""
		from ...tools.tool_call import ToolCall

		calls = []
		for data, raw in iter_tagged_json(text, "tool_call"):
			try:
				calls.append(ToolCall(name=data["name"], arguments=data.get("arguments", {}), raw=raw))
			except KeyError as exc:
				logger.debug("dropping malformed tool call %r: %s", raw, exc)
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
