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


class Completion(str):
	"""A completion string that also carries the call's **usage telemetry** as attributes: ``input_tokens`` /
	``output_tokens`` (0 when the provider reported none), ``stop_reason`` (the provider's native stop/finish
	reason, ``None`` when unreported), and ``batched`` (served via a provider batch API at discount pricing).

	Subclassing ``str`` keeps the documented client contract — ``callable(...) -> str`` — fully intact for
	existing callers and injected test clients, while letting ``APIParticipant`` read the telemetry off the
	return value to record per-turn usage (``Message.metadata``) and report into a ``UsageMeter``."""

	input_tokens: int
	output_tokens: int
	stop_reason: str | None
	batched: bool

	def __new__(cls, text: str, *, input_tokens: int = 0, output_tokens: int = 0,
	            stop_reason: str | None = None, batched: bool = False) -> "Completion":
		self = super().__new__(cls, text)
		self.input_tokens = input_tokens
		self.output_tokens = output_tokens
		self.stop_reason = stop_reason
		self.batched = batched
		return self


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

	def _call_once(self, system, messages, model, max_tokens, temperature, thinking=None) -> "Completion":
		raise NotImplementedError

	def __call__(self, system, messages, model, max_tokens, temperature, thinking=None) -> "Completion":
		attempt = 0
		while True:
			try:
				with self._sem:  # bound concurrent in-flight requests across all caller threads
					return self._call_once(system, messages, model, max_tokens, temperature, thinking)
			except Exception as exc:
				attempt += 1
				if attempt > self.max_retries or not self._transient(exc):
					raise
				delay = min(self.max_delay, self.base_delay * (2 ** (attempt - 1)))
				time.sleep(delay + random.uniform(0, delay))  # full jitter

	def submit_batch(self, requests: list[dict], *, poll_interval: float = 30.0) -> "list[Completion]":
		"""Submit many independent generations through the provider's asynchronous **batch API** and block until
		all complete, returning one completion string per request **in input order**.

		``requests`` is a list of ``{"system", "messages", "model", "max_tokens", "temperature"}`` dicts (same
		fields as ``__call__``). Batch APIs trade latency (minutes–hours, polled every ``poll_interval`` s) for
		~50% cost and far higher throughput/rate limits — the point of a *large* rollout. The base implementation
		**raises**: a provider without a batch endpoint (e.g. OpenRouter) must fail loudly rather than silently
		fall back to serial calls, so the caller knows batch mode was not honored."""
		raise NotImplementedError(
			f"{type(self).__name__} has no batch API: batch mode is unavailable for this provider. "
			f"Use an 'anthropic' or 'openai' participant for batch mode, or set batch=False.")


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

	@staticmethod
	def _thinking_param(thinking):
		"""Map the participant-level ``thinking`` value to Anthropic's request param: ``"disabled"`` turns
		adaptive thinking off, an int is an explicit thinking budget, a dict passes through verbatim, ``None``
		leaves the model's default (adaptive on current Claude models)."""
		if thinking is None:
			return None
		if thinking == "disabled":
			return {"type": "disabled"}
		if isinstance(thinking, int):
			return {"type": "enabled", "budget_tokens": thinking}
		if isinstance(thinking, dict):
			return thinking
		raise ValueError(f"thinking must be None, 'disabled', an int budget, or a dict; got {thinking!r}")

	def _call_once(self, system, messages, model, max_tokens, temperature, thinking=None) -> "Completion":
		# Newer models (e.g. Opus 4.8) DEPRECATE the `temperature` param and 400 if it is sent at all. Omit it when
		# None so callers can opt out; pass it through otherwise.
		kw = dict(model=model, system=system if system else self._anthropic.NOT_GIVEN, messages=messages,
		          max_tokens=max_tokens)
		if temperature is not None:
			kw["temperature"] = temperature
		if thinking is not None:
			kw["thinking"] = self._thinking_param(thinking)
		resp = self._client.messages.create(**kw)
		text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
		usage = getattr(resp, "usage", None)
		return Completion(text,
		                  input_tokens=getattr(usage, "input_tokens", 0) or 0,
		                  output_tokens=getattr(usage, "output_tokens", 0) or 0,
		                  stop_reason=getattr(resp, "stop_reason", None))

	def submit_batch(self, requests: list[dict], *, poll_interval: float = 30.0) -> "list[Completion]":
		"""Anthropic **Message Batches API**: one ``messages.batches.create`` submits every request (tagged with a
		positional ``custom_id``), then poll ``retrieve`` until ``processing_status == 'ended'`` and stream
		``results`` back, reassembled into input order. A non-succeeded per-request result raises."""
		batch = self._client.messages.batches.create(requests=[
			{"custom_id": f"req-{i}",
			 "params": {"model": r["model"], "max_tokens": r["max_tokens"], "messages": r["messages"],
			            # omit temperature when None (newer models 400 on an explicit temperature)
			            **({"temperature": r["temperature"]} if r.get("temperature") is not None else {}),
			            **({"thinking": self._thinking_param(r["thinking"])}
			               if r.get("thinking") is not None else {}),
			            **({"system": r["system"]} if r.get("system") else {})}}
			for i, r in enumerate(requests)])
		while self._client.messages.batches.retrieve(batch.id).processing_status != "ended":
			time.sleep(poll_interval)  # await external batch completion (not a fixed delay)
		texts: dict[str, Completion] = {}
		for entry in self._client.messages.batches.results(batch.id):
			if entry.result.type != "succeeded":
				raise RuntimeError(f"Anthropic batch request {entry.custom_id} did not succeed: {entry.result.type}")
			msg = entry.result.message
			usage = getattr(msg, "usage", None)
			texts[entry.custom_id] = Completion(
				"".join(b.text for b in msg.content if getattr(b, "type", None) == "text"),
				input_tokens=getattr(usage, "input_tokens", 0) or 0,
				output_tokens=getattr(usage, "output_tokens", 0) or 0,
				stop_reason=getattr(msg, "stop_reason", None), batched=True)
		return [texts[f"req-{i}"] for i in range(len(requests))]


class _OpenAICompatClient(_RetryingClient):
	"""Shared base for clients speaking the OpenAI ``chat.completions`` schema (OpenAI itself + OpenRouter). The
	schema has no separate system param, so ``system`` is folded in as a leading ``system`` message. Subclasses
	set the endpoint (``_base_url``), API-key env var (``_api_key_env``), and a human ``_label`` for errors."""

	_base_url: str | None = None      # None -> the openai SDK's default (api.openai.com)
	_api_key_env: str = ""
	_label: str = "OpenAI-compatible"
	# the request field carrying the output-token cap. Classic chat.completions uses ``max_tokens``; OpenAI's
	# newer reasoning models (gpt-5, o-series) reject it and require ``max_completion_tokens``. Subclasses that
	# target those models override this so the same call path serves both without per-call branching.
	_tokens_param: str = "max_tokens"

	def __init__(self, base_url: str | None = None, api_key: str | None = None, **kwargs):
		super().__init__(**kwargs)
		import openai

		self._openai = openai
		key = api_key or os.environ.get(self._api_key_env)
		if not key:
			raise RuntimeError(f"{self._label} needs {self._api_key_env} in the environment (or pass api_key=).")
		self._client = openai.OpenAI(base_url=base_url or self._base_url, api_key=key, max_retries=0)

	def _transient(self, exc) -> bool:
		o = self._openai
		return isinstance(exc, (o.RateLimitError, o.APIConnectionError, o.InternalServerError)) or (
			isinstance(exc, o.APIStatusError) and getattr(exc, "status_code", None) in (429, 500, 502, 503, 529))

	@staticmethod
	def _full_messages(system, messages) -> list[dict]:
		return ([{"role": "system", "content": system}] if system else []) + list(messages)

	def _call_once(self, system, messages, model, max_tokens, temperature, thinking=None) -> "Completion":
		if thinking is not None:
			raise NotImplementedError(
				f"{self._label} does not support the 'thinking' control (Anthropic-only); leave thinking=None.")
		# Some models (e.g. GPT-5) only accept the default temperature; omit the param when None to avoid a 400.
		kw = {self._tokens_param: max_tokens}
		if temperature is not None:
			kw["temperature"] = temperature
		resp = self._client.chat.completions.create(
			model=model, messages=self._full_messages(system, messages), **kw)
		choice = resp.choices[0]
		usage = getattr(resp, "usage", None)
		return Completion(choice.message.content or "",
		                  input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
		                  output_tokens=getattr(usage, "completion_tokens", 0) or 0,
		                  stop_reason=getattr(choice, "finish_reason", None))


class OpenAIClient(_OpenAICompatClient):
	"""OpenAI directly via the ``openai`` SDK (``provider="openai"``). Reads ``OPENAI_API_KEY``. Supports the
	asynchronous **Batch API** for large rollouts."""

	_api_key_env = "OPENAI_API_KEY"
	_label = "OpenAI"
	_tokens_param = "max_completion_tokens"   # gpt-5 / o-series reject the legacy ``max_tokens``

	def submit_batch(self, requests: list[dict], *, poll_interval: float = 30.0) -> "list[Completion]":
		"""OpenAI **Batch API**: upload a JSONL of ``/v1/chat/completions`` requests (positional ``custom_id``),
		``batches.create`` with a 24h window, poll until ``status == 'completed'``, then download + parse the
		output file back into input order. A failed/expired/cancelled batch raises."""
		import io
		import json

		if any(r.get("thinking") is not None for r in requests):
			raise NotImplementedError(
				"OpenAI does not support the 'thinking' control (Anthropic-only); leave thinking=None.")
		lines = [json.dumps({
			"custom_id": f"req-{i}", "method": "POST", "url": "/v1/chat/completions",
			"body": {"model": r["model"], self._tokens_param: r["max_tokens"],
			         **({"temperature": r["temperature"]} if r.get("temperature") is not None else {}),
			         "messages": self._full_messages(r.get("system"), r["messages"])}})
			for i, r in enumerate(requests)]
		upload = self._client.files.create(
			file=("batch.jsonl", io.BytesIO("\n".join(lines).encode())), purpose="batch")
		batch = self._client.batches.create(
			input_file_id=upload.id, endpoint="/v1/chat/completions", completion_window="24h")
		while True:
			batch = self._client.batches.retrieve(batch.id)
			if batch.status == "completed":
				break
			if batch.status in ("failed", "expired", "cancelled", "cancelling"):
				raise RuntimeError(f"OpenAI batch {batch.id} ended as {batch.status}")
			time.sleep(poll_interval)  # await external batch completion (not a fixed delay)
		texts: dict[str, Completion] = {}
		content = self._client.files.content(batch.output_file_id).text
		for line in content.splitlines():
			if not line.strip():
				continue
			obj = json.loads(line)
			body = obj["response"]["body"]
			choice = body["choices"][0]
			usage = body.get("usage") or {}
			texts[obj["custom_id"]] = Completion(
				choice["message"]["content"] or "",
				input_tokens=usage.get("prompt_tokens", 0) or 0,
				output_tokens=usage.get("completion_tokens", 0) or 0,
				stop_reason=choice.get("finish_reason"), batched=True)
		return [texts[f"req-{i}"] for i in range(len(requests))]


class OpenRouterClient(_OpenAICompatClient):
	"""OpenRouter (https://openrouter.ai) via the OpenAI-compatible ``openai`` SDK — one endpoint proxying many
	providers' models (e.g. ``anthropic/claude-sonnet-5``, ``openai/gpt-5``, ``meta-llama/llama-3.1-70b-instruct``).
	Reads ``OPENROUTER_API_KEY``. OpenRouter has **no batch API**, so ``submit_batch`` inherits the base's raise —
	requesting batch mode on an OpenRouter participant fails loudly."""

	_base_url = "https://openrouter.ai/api/v1"
	_api_key_env = "OPENROUTER_API_KEY"
	_label = "OpenRouter"
