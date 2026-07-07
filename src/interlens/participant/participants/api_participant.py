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
	             max_new_tokens: int | None = None) -> Message:
		if steering is not None or capture is not None or patch is not None or return_logprobs:
			raise NotImplementedError(
				f"APIParticipant {self.name!r} has no local model: capture/steering/patch/logprobs are not "
				f"available and must not be silently ignored. Use a ModelParticipant for interp."
			)

		system, messages = self._split_view(view)
		client = self.client or _default_client(self.provider)
		max_tokens = max_new_tokens if max_new_tokens is not None else self.max_tokens
		text = client(system=system, messages=messages, model=self.model_id,
		              max_tokens=max_tokens, temperature=self.temperature)
		return Message(author=self.name, content=text, metadata={"provider": self.provider, "model": self.model_id})

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
		max_tokens = max_new_tokens if max_new_tokens is not None else self.max_tokens
		requests = []
		for view in views:
			system, messages = self._split_view(view)
			requests.append(dict(system=system, messages=messages, model=self.model_id,
			                     max_tokens=max_tokens, temperature=self.temperature))
		if self.batch:
			if not hasattr(client, "submit_batch"):
				raise NotImplementedError(
					f"APIParticipant {self.name!r} has batch=True but its client {type(client).__name__} exposes "
					f"no submit_batch; batch mode is unavailable for provider {self.provider!r}.")
			texts = client.submit_batch(requests)
		else:
			texts = [client(**r) for r in requests]
		return [Message(author=self.name, content=t,
		                metadata={"provider": self.provider, "model": self.model_id, "batched": True})
		        for t in texts]

	def __getstate__(self) -> dict:
		# The client is a live SDK/network object (often unpicklable) and is reconstructed lazily per provider via
		# ``_default_client`` — drop it on pickle. An injected test client is dropped too (tests run in-process).
		state = self.__dict__.copy()
		state["client"] = None
		return state

	def _after_set(self, original) -> None:
		# API participants carry no volatile per-conversation state; nothing to reset.
		pass
