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

import threading
from dataclasses import dataclass, field
from typing import Literal

from ..participant import Participant
from ...functional import Functional
from ...message import Message

# The set of hosted API backends. ``anthropic`` calls Claude directly via the ``anthropic`` SDK; ``openai`` calls
# OpenAI directly via the ``openai`` SDK; ``openrouter`` reaches any model behind openrouter.ai through one
# OpenAI-compatible endpoint. ``anthropic`` and ``openai`` expose asynchronous batch APIs (``batch=True``);
# ``openrouter`` does not. This is the canonical list — both ``_CLIENT_CLASSES`` (runtime) and every ``provider``
# field annotation derive from it.
Provider = Literal["anthropic", "openai", "openrouter"]
OpenRouterQuantization = Literal["int4", "int8", "fp4", "fp6", "fp8", "fp16", "bf16", "fp32", "unknown"]
_OPENROUTER_QUANTIZATIONS = {"int4", "int8", "fp4", "fp6", "fp8", "fp16", "bf16", "fp32", "unknown"}


@dataclass(frozen=True)
class OpenRouterRouting:
	"""Reproducible OpenRouter routing for research.

	``upstream_provider`` is the OpenRouter provider slug (for example ``"together"`` or ``"deepinfra"``).
	A pinned request sends both ``only=[slug]`` and ``order=[slug]``, disables fallbacks, and requires support
	for every supplied generation parameter. ``quantizations`` should also be set for open-weight models when
	the endpoint offers multiple precisions. ``data_collection="deny"`` excludes providers that may retain or
	train on prompts.

	Use :meth:`unpinned` only for exploratory traffic where provider variance is intentionally acceptable.
	Requiring that explicit opt-out prevents an uncontrolled request from looking like a reproducible run.
	"""

	upstream_provider: str | None
	quantizations: tuple[OpenRouterQuantization, ...] = ()
	data_collection: Literal["allow", "deny"] | None = None
	allow_unpinned: bool = False

	def __post_init__(self) -> None:
		if self.upstream_provider is not None and not self.upstream_provider.strip():
			raise ValueError("OpenRouter upstream_provider must be a non-empty provider slug.")
		if self.upstream_provider is None and not self.allow_unpinned:
			raise ValueError(
				"OpenRouter routing must pin an upstream_provider. For intentionally uncontrolled exploratory "
				"traffic, use OpenRouterRouting.unpinned().")
		unknown = set(self.quantizations) - _OPENROUTER_QUANTIZATIONS
		if unknown:
			raise ValueError(f"unknown OpenRouter quantization(s) {sorted(unknown)}; "
			                 f"expected values from {sorted(_OPENROUTER_QUANTIZATIONS)}")
		if self.data_collection not in (None, "allow", "deny"):
			raise ValueError("data_collection must be None, 'allow', or 'deny'.")

	@classmethod
	def unpinned(cls, *, data_collection: Literal["allow", "deny"] | None = None) -> "OpenRouterRouting":
		"""Explicitly opt into OpenRouter's variable default provider routing for exploratory, non-reproducible use."""
		return cls(upstream_provider=None, data_collection=data_collection, allow_unpinned=True)

	def request_dict(self) -> dict:
		"""Return the exact OpenRouter ``provider`` request object."""
		request = {"require_parameters": True}
		if self.upstream_provider is not None:
			request.update(order=[self.upstream_provider], only=[self.upstream_provider], allow_fallbacks=False)
		if self.quantizations:
			request["quantizations"] = list(self.quantizations)
		if self.data_collection is not None:
			request["data_collection"] = self.data_collection
		return request

# provider name -> client class in api_client. Each provider gets ONE process-wide shared client (retry/backoff +
# a global max-in-flight cap), so the concurrency cap holds across every API participant in a rollout.
_CLIENT_CLASSES = {"anthropic": "AnthropicClient", "openai": "OpenAIClient", "openrouter": "OpenRouterClient"}
_SHARED_CLIENTS: dict[str, object] = {}
_SHARED_LOCK = threading.Lock()


def _default_client(provider: str):
	"""The process-wide shared client for ``provider`` (built lazily so the harness never imports a provider SDK
	unless that provider actually runs). Raises on an unknown provider rather than silently defaulting. The
	max-in-flight cap defaults to 4 but is overridable via ``INTERLENS_API_MAX_IN_FLIGHT`` so a caller that
	thread-pools many independent rollouts can widen the concurrency to match (bounded by provider rate limits)."""
	if provider not in _SHARED_CLIENTS:
		with _SHARED_LOCK:
			if provider not in _SHARED_CLIENTS:
				if provider not in _CLIENT_CLASSES:
					raise ValueError(f"unknown API provider {provider!r}; expected one of {sorted(_CLIENT_CLASSES)}")
				import os
				from . import api_client
				kw = {}
				if os.environ.get("INTERLENS_API_MAX_IN_FLIGHT"):
					kw["max_in_flight"] = int(os.environ["INTERLENS_API_MAX_IN_FLIGHT"])
				_SHARED_CLIENTS[provider] = getattr(api_client, _CLIENT_CLASSES[provider])(**kw)
	return _SHARED_CLIENTS[provider]


@dataclass
class APIParticipant(Functional, Participant):
	"""A participant backed by a hosted API — Claude via ``anthropic`` (``provider="anthropic"``, the default) or
	any model behind OpenRouter (``provider="openrouter"``, OpenAI-compatible) — for use as a debate opponent,
	moderator, or the classifier inside an ``analyze`` callback.

	It is a full participant for *conversation* purposes but has **no local model** — so there is no device,
	no activations, and no steering. Any interp request (``capture``/``steering``/``patch``/``return_logprobs``)
	**raises** rather than silently no-op'ing: in a measurement harness, a steering sweep that quietly did
	nothing on an API participant would produce a false "no effect" conclusion. Seeds don't bind hosted models,
	so API turns are excluded from the identical-replay guarantee.

	Concurrency is network-bound, so pure-API conversations run thread-pooled rather than process-per-GPU
	(handled by the runner). The ``client`` callable is injectable for testing.
	"""

	name: str = ""
	model_id: str = ""
	provider: Provider = "anthropic"
	system_prompt: str | None = None
	private_context: tuple = ()
	max_tokens: int = 512
	temperature: float = 1.0
	batch: bool = False  # route ``generate_batch`` through the provider's async batch API (anthropic/openai only)
	client: object = None  # callable(system, messages, model, max_tokens, temperature) -> str
	openrouter_routing: OpenRouterRouting | None = None
	"""Required for ``provider="openrouter"``. Pin an upstream endpoint for research, or explicitly pass
	``OpenRouterRouting.unpinned()`` for exploratory use where variable routing is acceptable."""

	meter: object = None
	"""Optional ``interlens.usage.UsageMeter``: every call this participant makes is reported into it (tokens,
	dollars at the actual billing multiplier — batch-served turns bill at 0.5× — and refusal counts), so one
	shared meter across participants gives a live, run-level spend ledger with reservation gating. Per-turn
	usage is recorded in ``Message.metadata`` regardless; the meter adds the cross-conversation aggregate."""

	turn_token_floor: int | None = None
	"""Thinking-aware lower bound on an externally imposed per-turn cap. Models with adaptive or always-on
	reasoning spend hidden thinking tokens **out of ``max_tokens``**: an innocently small per-turn cap (a
	``TokenBudget(per_turn=500)``) then silently yields EMPTY visible turns — thinking consumes the whole
	budget (observed at 58% empty turns in the arena experiments). Setting a floor (e.g. 2048) keeps every
	turn generable: an external ``max_new_tokens`` below the floor is raised to it. The tradeoff is deliberate
	— a budget's final turn may overshoot by up to the floor, which is measurable; an empty turn corrupts the
	conversation, which is not. On long contexts adaptive thinking can outgrow ANY fixed floor — for models
	that allow it, ``thinking="disabled"`` (or an explicit int budget) is the reliable control; the floor is
	the guard for models whose thinking cannot be disabled."""

	thinking: object = None
	"""Reasoning control, Anthropic only: ``None`` keeps the model's default (adaptive thinking on current
	Claude models — which spends from ``max_tokens``), ``"disabled"`` turns thinking off, an ``int`` sets an
	explicit thinking budget, and a dict passes through verbatim. Non-Anthropic providers raise on a non-None
	value rather than silently ignoring it."""

	# Anthropic needs strictly alternating user/assistant turns, so reuse the same merge the local families use.
	requires_alternating_roles: bool = True

	# Placeholder for an empty turn (a model can legitimately return "" — e.g. a reasoning model that spends its
	# whole budget on hidden thinking). Hosted APIs reject empty message content, so we substitute this rather
	# than crash the whole rollout on one blank turn. The nudge turns a trailing assistant turn into a request
	# that ends on a user message.
	_EMPTY_PLACEHOLDER = "(no response)"
	_CONTINUE_NUDGE = "Please continue."

	def _split_view(self, view: list[dict]) -> tuple[str | None, list[dict]]:
		"""Split a flattened view into the provider's separate ``system`` string + user/assistant turns, with two
		hosted-API repairs: (1) empty/whitespace content is replaced with ``_EMPTY_PLACEHOLDER`` (Anthropic and
		OpenAI both 400 on empty message content); (2) if the view ends on an *assistant* turn — which happens
		when a participant continues itself (solo / self-refine loops) — a minimal user turn is appended, because
		``generate`` must produce the NEXT turn and several hosted models (Claude Opus 4.8, OpenAI reasoning
		models) reject a trailing assistant turn sent as a prefill ("conversation must end with a user message")."""
		system = "\n\n".join(m["content"] for m in view if m["role"] == "system") or None
		messages = [{"role": m["role"], "content": (m["content"] if (m["content"] or "").strip() else self._EMPTY_PLACEHOLDER)}
		            for m in view if m["role"] != "system"]
		if messages and messages[-1]["role"] == "assistant":
			messages.append({"role": "user", "content": self._CONTINUE_NUDGE})
		return system, messages

	def generate(self, view: list[dict], *, steering=None, capture=None, patch=None,
	             return_logprobs: bool = False, turn: int | None = None,
	             max_new_tokens: int | None = None, seat: str | None = None) -> Message:
		if steering is not None or capture is not None or patch is not None or return_logprobs:
			raise NotImplementedError(
				f"APIParticipant {self.name!r} has no local model: capture/steering/patch/logprobs are not "
				f"available and must not be silently ignored. Use a ModelParticipant for interp."
			)

		system, messages = self._split_view(view)
		client = self.client or _default_client(self.provider)
		max_tokens = self._effective_cap(max_new_tokens)
		kw = {"thinking": self.thinking} if self.thinking is not None else {}
		kw.update(self._routing_kwargs())
		text = client(system=system, messages=messages, model=self.model_id,
		              max_tokens=max_tokens, temperature=self.temperature, **kw)
		self._validate_openrouter_response(text)
		return Message(author=self.name, content=str(text), metadata=self._usage_metadata(text))

	def generate_batch(self, views: list[list[dict]], *, turn: int | None = None,
	                   group_seed: int | None = None, max_new_tokens: int | None = None) -> list[Message]:
		"""Generate one turn for many independent conversations at once — the API analogue of
		``ModelParticipant.generate_batch``, driven by the runner's co-stepper (``rollout(..., batched=True)``) to
		make large API rollouts cheap and throughput-bound.

		With ``batch=True`` every view is sent as one **asynchronous provider batch** (Anthropic Message Batches /
		OpenAI Batch API) via ``client.submit_batch`` — ~50% cost and much higher throughput, at the price of
		batch-window latency. **If the provider has no batch API (e.g. OpenRouter) this raises** rather than
		silently degrading, so a requested batch is never quietly run as serial calls. With ``batch=False`` it
		falls back to sequential per-view calls (correct, just no batch discount). Interp is unavailable here, as
		for ``generate``. ``turn``/``group_seed`` are accepted for co-stepper compatibility but unused (seeds do
		not bind hosted models). ``metadata['batched']`` marks these turns."""
		if not views:
			return []
		client = self.client or _default_client(self.provider)
		max_tokens = self._effective_cap(max_new_tokens)
		requests = []
		for view in views:
			system, messages = self._split_view(view)
			requests.append(dict(system=system, messages=messages, model=self.model_id,
			                     max_tokens=max_tokens, temperature=self.temperature,
			                     **({"thinking": self.thinking} if self.thinking is not None else {}),
			                     **self._routing_kwargs()))
		if self.batch:
			if not hasattr(client, "submit_batch"):
				raise NotImplementedError(
					f"APIParticipant {self.name!r} has batch=True but its client {type(client).__name__} exposes "
					f"no submit_batch; batch mode is unavailable for provider {self.provider!r}.")
			texts = client.submit_batch(requests)
		else:
			texts = [client(**r) for r in requests]
		for text in texts:
			self._validate_openrouter_response(text)
		return [Message(author=self.name, content=str(t),
		                metadata=self._usage_metadata(t) | {"batched": True})
		        for t in texts]

	def _effective_cap(self, max_new_tokens: int | None) -> int:
		"""The output-token cap actually sent: the caller's ``max_new_tokens`` (else this participant's
		``max_tokens``), raised to ``turn_token_floor`` when one is set — the thinking-aware guard against an
		external per-turn cap starving a reasoning model's visible output (see the field docstring)."""
		cap = max_new_tokens if max_new_tokens is not None else self.max_tokens
		if self.turn_token_floor is not None:
			cap = max(cap, self.turn_token_floor)
		return cap

	def _routing_kwargs(self) -> dict:
		if self.provider != "openrouter":
			if self.openrouter_routing is not None:
				raise ValueError("openrouter_routing may only be set when provider='openrouter'.")
			return {}
		if self.openrouter_routing is None:
			raise ValueError(
				"OpenRouter requests require explicit routing so research cannot silently mix inference "
				"providers. Pass OpenRouterRouting(upstream_provider='...') to pin one endpoint, or explicitly "
				"pass OpenRouterRouting.unpinned() for exploratory traffic.")
		return {"provider_routing": self.openrouter_routing.request_dict()}

	@staticmethod
	def _normalized_provider(value: str) -> str:
		# OpenRouter accepts slugs (``google-vertex``) but reports display names (``Google Vertex``). Provider
		# variants such as ``deepinfra/turbo`` still identify the same upstream before the slash.
		return "".join(c for c in value.split("/", 1)[0].lower() if c.isalnum())

	def _validate_openrouter_response(self, completion) -> None:
		if self.provider != "openrouter" or self.openrouter_routing is None:
			return
		pinned = self.openrouter_routing.upstream_provider
		if pinned is None:
			return
		served = getattr(completion, "upstream_provider", None)
		if not served:
			raise RuntimeError(
				"OpenRouter did not report the upstream provider for a pinned request; refusing to record this "
				"turn as research-safe because the routing constraint cannot be audited.")
		if self._normalized_provider(served) != self._normalized_provider(pinned):
			raise RuntimeError(
				f"OpenRouter routing violation: requested upstream provider {pinned!r}, but response reports "
				f"{served!r}. The turn was not committed.")

	def _usage_metadata(self, completion) -> dict:
		"""Per-turn usage metadata from a client return value, plus the ``meter`` report. Works with a plain
		``str`` (an injected test client; usage reads as 0) or an ``api_client.Completion`` (real telemetry).
		Records the same ``n_tokens`` key ``ModelParticipant`` uses, so ``TokenBudget`` counts hosted turns
		natively, plus ``n_tokens_in`` / ``cost_usd`` / ``stop_reason`` / ``refusal`` for cost budgets and refusal
		telemetry."""
		tokens_in = int(getattr(completion, "input_tokens", 0) or 0)
		tokens_out = int(getattr(completion, "output_tokens", 0) or 0)
		stop_reason = getattr(completion, "stop_reason", None)
		batched = bool(getattr(completion, "batched", False))
		# "refusal" is Anthropic's native refusal stop; "content_filter" is the OpenAI-schema analogue.
		refusal = stop_reason in ("refusal", "content_filter")
		metadata = {"provider": self.provider, "model": self.model_id,
		            "n_tokens": tokens_out, "n_tokens_in": tokens_in, "stop_reason": stop_reason}
		if self.provider == "openrouter" and self.openrouter_routing is not None:
			metadata["provider_routing"] = self.openrouter_routing.request_dict()
			metadata["upstream_provider"] = getattr(completion, "upstream_provider", None)
			metadata["response_model"] = getattr(completion, "response_model", None)
			metadata["generation_id"] = getattr(completion, "generation_id", None)
		# The turn's reasoning record (see api_client marker constants): persisted whenever the provider
		# produced any, so downstream turn records carry reasoning + its provenance first-class.
		provenance = getattr(completion, "reasoning_provenance", None)
		if provenance and provenance != "none":
			metadata["reasoning"] = getattr(completion, "reasoning", None)
			metadata["reasoning_provenance"] = provenance
		if refusal:
			metadata["refusal"] = True
		if self.meter is not None:
			mult = 0.5 if batched else 1.0  # provider batch APIs bill at half price
			metadata["cost_usd"] = self.meter.add(self.model_id, tokens_in, tokens_out,
			                                      price_multiplier=mult, refusal=refusal)
			if batched:
				metadata["price_multiplier"] = mult
		return metadata

	def __getstate__(self) -> dict:
		# The client is a live SDK/network object (often unpicklable) and is reconstructed lazily per provider via
		# ``_default_client`` — drop it on pickle. An injected test client is dropped too (tests run in-process).
		# The meter survives pickling (UsageMeter re-creates its lock), so spawned workers keep reporting usage.
		state = self.__dict__.copy()
		state["client"] = None
		return state

	def _after_set(self, original) -> None:
		# API participants carry no volatile per-conversation state; nothing to reset.
		pass
