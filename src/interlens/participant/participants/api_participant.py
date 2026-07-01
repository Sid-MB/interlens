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

from dataclasses import dataclass, field

from ..participant import Participant
from ...message import Message


_SHARED_CLIENT = None
_SHARED_LOCK = __import__("threading").Lock()


def _anthropic_client(system, messages, model, max_tokens, temperature):
	"""Default Claude client: a process-wide shared :class:`AnthropicClient` (retry/backoff + max-in-flight cap),
	built lazily so the harness never requires ``anthropic`` unless an ``APIParticipant`` actually runs. Sharing
	one instance is what makes the concurrency cap global across every API participant in a rollout."""
	global _SHARED_CLIENT
	if _SHARED_CLIENT is None:
		with _SHARED_LOCK:
			if _SHARED_CLIENT is None:
				from .api_client import AnthropicClient
				_SHARED_CLIENT = AnthropicClient()
	return _SHARED_CLIENT(system, messages, model, max_tokens, temperature)


@dataclass
class APIParticipant(Participant):
	"""A participant backed by a hosted API (Claude via ``anthropic`` by default), for use as a debate opponent,
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
	             return_logprobs: bool = False, turn: int | None = None) -> Message:
		if steering is not None or capture is not None or patch is not None or return_logprobs:
			raise NotImplementedError(
				f"APIParticipant {self.name!r} has no local model: capture/steering/patch/logprobs are not "
				f"available and must not be silently ignored. Use a ModelParticipant for interp."
			)

		# Split the flattened view into the provider's separate system param + user/assistant turns.
		system = "\n\n".join(m["content"] for m in view if m["role"] == "system") or None
		messages = [{"role": m["role"], "content": m["content"]} for m in view if m["role"] != "system"]
		client = self.client or _anthropic_client
		text = client(system=system, messages=messages, model=self.model_id,
		              max_tokens=self.max_tokens, temperature=self.temperature)
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
