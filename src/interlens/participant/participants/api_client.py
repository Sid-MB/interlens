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

# Shared hosted-API clients with retry/backoff + a max-in-flight cap. API-heavy rollouts (e.g. 50 Claude-vs-Claude
# conversations) must not hammer the endpoint: one shared client bounds concurrency with a semaphore and retries
# transient failures (429 / overloaded / connection) with exponential backoff + jitter. Injected as
# ``APIParticipant.client`` so the participant stays provider-agnostic; each provider SDK is imported lazily.
from __future__ import annotations

import os
import random
import threading
import time


class _RetryingClient:
	"""Shared machinery for hosted-API clients: a global ``max_in_flight`` semaphore (so N caller threads can't all
	hit the endpoint at once) + exponential backoff with full jitter on transient errors. Subclasses implement
	``_transient(exc)`` and ``_call_once(...)`` and lazily import their SDK, so the harness never requires a
	provider package unless that provider actually runs. All clients are callables with the signature
	``(system, messages, model, max_tokens, temperature) -> str``."""

	def __init__(self, max_in_flight: int = 4, max_retries: int = 6, base_delay: float = 1.0, max_delay: float = 30.0):
		self._sem = threading.Semaphore(max_in_flight)
		self.max_retries = max_retries
		self.base_delay = base_delay
		self.max_delay = max_delay

	def _transient(self, exc) -> bool:
		raise NotImplementedError

	def _call_once(self, system, messages, model, max_tokens, temperature) -> str:
		raise NotImplementedError

	def __call__(self, system, messages, model, max_tokens, temperature) -> str:
		attempt = 0
		while True:
			try:
				with self._sem:  # bound concurrent in-flight requests across all caller threads
					return self._call_once(system, messages, model, max_tokens, temperature)
			except Exception as exc:
				attempt += 1
				if attempt > self.max_retries or not self._transient(exc):
					raise
				delay = min(self.max_delay, self.base_delay * (2 ** (attempt - 1)))
				time.sleep(delay + random.uniform(0, delay))  # full jitter


class AnthropicClient(_RetryingClient):
	"""Claude via the ``anthropic`` SDK (the default provider). Uses Anthropic's separate ``system`` param."""

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		import anthropic

		self._anthropic = anthropic
		self._client = anthropic.Anthropic(max_retries=0)  # we own the retry loop, disable the SDK's

	def _transient(self, exc) -> bool:
		a = self._anthropic
		return isinstance(exc, (a.RateLimitError, a.APIConnectionError, a.InternalServerError)) or (
			isinstance(exc, a.APIStatusError) and getattr(exc, "status_code", None) in (429, 500, 502, 503, 529))

	def _call_once(self, system, messages, model, max_tokens, temperature) -> str:
		resp = self._client.messages.create(
			model=model,
			system=system if system else self._anthropic.NOT_GIVEN,
			messages=messages,
			max_tokens=max_tokens,
			temperature=temperature,
		)
		return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")


class OpenRouterClient(_RetryingClient):
	"""OpenRouter (https://openrouter.ai) via the OpenAI-compatible ``openai`` SDK — one endpoint proxying many
	providers' models (e.g. ``anthropic/claude-sonnet-5``, ``openai/gpt-5``, ``meta-llama/llama-3.1-70b-instruct``).
	Reads ``OPENROUTER_API_KEY`` (or pass ``api_key=``). OpenAI's schema has no separate system param, so the
	``system`` string is folded in as a leading ``system`` message."""

	def __init__(self, base_url: str = "https://openrouter.ai/api/v1", api_key: str | None = None, **kwargs):
		super().__init__(**kwargs)
		import openai

		self._openai = openai
		key = api_key or os.environ.get("OPENROUTER_API_KEY")
		if not key:
			raise RuntimeError("OpenRouter needs OPENROUTER_API_KEY in the environment (or pass api_key=).")
		self._client = openai.OpenAI(base_url=base_url, api_key=key, max_retries=0)

	def _transient(self, exc) -> bool:
		o = self._openai
		return isinstance(exc, (o.RateLimitError, o.APIConnectionError, o.InternalServerError)) or (
			isinstance(exc, o.APIStatusError) and getattr(exc, "status_code", None) in (429, 500, 502, 503, 529))

	def _call_once(self, system, messages, model, max_tokens, temperature) -> str:
		full = ([{"role": "system", "content": system}] if system else []) + list(messages)
		resp = self._client.chat.completions.create(
			model=model, messages=full, max_tokens=max_tokens, temperature=temperature)
		return resp.choices[0].message.content or ""
