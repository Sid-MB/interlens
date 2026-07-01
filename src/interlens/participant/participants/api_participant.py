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

from ..participant import Participant
from ...message import Message

# provider name -> client class in api_client. Each provider gets ONE process-wide shared client (retry/backoff +
# a global max-in-flight cap), so the concurrency cap holds across every API participant in a rollout.
_CLIENT_CLASSES = {"anthropic": "AnthropicClient", "openrouter": "OpenRouterClient"}
_SHARED_CLIENTS: dict[str, object] = {}
_SHARED_LOCK = threading.Lock()


def _default_client(provider: str):
	"""The process-wide shared client for ``provider`` (built lazily so the harness never imports a provider SDK
	unless that provider actually runs). Raises on an unknown provider rather than silently defaulting."""
	if provider not in _SHARED_CLIENTS:
		with _SHARED_LOCK:
			if provider not in _SHARED_CLIENTS:
				if provider not in _CLIENT_CLASSES:
					raise ValueError(f"unknown API provider {provider!r}; expected one of {sorted(_CLIENT_CLASSES)}")
				from . import api_client
				_SHARED_CLIENTS[provider] = getattr(api_client, _CLIENT_CLASSES[provider])()
	return _SHARED_CLIENTS[provider]


@dataclass
class APIParticipant(Participant):
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
	provider: str = "anthropic"
	system_prompt: str | None = None
	private_context: tuple = ()
	max_tokens: int = 512
	temperature: float = 1.0
	client: object = None  # callable(system, messages, model, max_tokens, temperature) -> str

	# Anthropic needs strictly alternating user/assistant turns, so reuse the same merge the local families use.
	requires_alternating_roles: bool = True

	def generate(self, view: list[dict], *, steering=None, capture=None, patch=None,
	             return_logprobs: bool = False, turn: int | None = None,
	             max_new_tokens: int | None = None) -> Message:
		if steering is not None or capture is not None or patch is not None or return_logprobs:
			raise NotImplementedError(
				f"APIParticipant {self.name!r} has no local model: capture/steering/patch/logprobs are not "
				f"available and must not be silently ignored. Use a ModelParticipant for interp."
			)

		# Split the flattened view into the provider's separate system param + user/assistant turns.
		system = "\n\n".join(m["content"] for m in view if m["role"] == "system") or None
		messages = [{"role": m["role"], "content": m["content"]} for m in view if m["role"] != "system"]
		client = self.client or _default_client(self.provider)
		max_tokens = max_new_tokens if max_new_tokens is not None else self.max_tokens
		text = client(system=system, messages=messages, model=self.model_id,
		              max_tokens=max_tokens, temperature=self.temperature)
		return Message(author=self.name, content=text, metadata={"provider": self.provider, "model": self.model_id})

	def to_config(self):
		from ..config.api_participant_config import APIParticipantConfig

		return APIParticipantConfig(
			name=self.name,
			system_prompt=self.system_prompt,
			private_context=tuple(self.private_context),
			model_id=self.model_id,
			provider=self.provider,
			max_tokens=self.max_tokens,
			temperature=self.temperature,
		)
