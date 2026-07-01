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

# [complete-chat-harness]: shared Anthropic client with retry/backoff + a max-in-flight cap (PLAN P4).
# API-heavy rollouts (e.g. 50 Claude-vs-Claude conversations) must not hammer the endpoint: a shared client
# bounds concurrency with a semaphore and retries transient failures (429 / overloaded / connection) with
# exponential backoff + jitter. Injected as APIParticipant.client so the participant stays provider-agnostic.
from __future__ import annotations

import random
import threading
import time


class AnthropicClient:
	"""Callable ``(system, messages, model, max_tokens, temperature) -> str`` backed by the ``anthropic`` SDK.

	One shared instance across an API rollout gives a single connection pool, a global ``max_in_flight`` cap
	(so N threads can't all hit the endpoint at once), and exponential backoff with jitter on transient errors.
	The SDK is imported lazily so the harness never requires ``anthropic`` unless an API participant actually runs.
	"""

	def __init__(self, max_in_flight: int = 4, max_retries: int = 6, base_delay: float = 1.0,
	             max_delay: float = 30.0):
		import anthropic

		self._anthropic = anthropic
		self._client = anthropic.Anthropic(max_retries=0)  # we own the retry loop, disable the SDK's
		self._sem = threading.Semaphore(max_in_flight)
		self.max_retries = max_retries
		self.base_delay = base_delay
		self.max_delay = max_delay

	def _transient(self, exc) -> bool:
		a = self._anthropic
		return isinstance(exc, (a.RateLimitError, a.APIConnectionError, a.InternalServerError)) or (
			isinstance(exc, a.APIStatusError) and getattr(exc, "status_code", None) in (429, 500, 502, 503, 529))

	def __call__(self, system, messages, model, max_tokens, temperature) -> str:
		attempt = 0
		while True:
			try:
				with self._sem:  # bound concurrent in-flight requests across all caller threads
					resp = self._client.messages.create(
						model=model,
						system=system if system else self._anthropic.NOT_GIVEN,
						messages=messages,
						max_tokens=max_tokens,
						temperature=temperature,
					)
				return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
			except Exception as exc:
				attempt += 1
				if attempt > self.max_retries or not self._transient(exc):
					raise
				delay = min(self.max_delay, self.base_delay * (2 ** (attempt - 1)))
				time.sleep(delay + random.uniform(0, delay))  # full jitter
