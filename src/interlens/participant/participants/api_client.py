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

from ..governor import current_governor


# Per-turn reasoning provenance marker values (``Completion.reasoning_provenance``):
#   "none"                    — the provider produced no reasoning for this turn
#   "withheld_or_summarized"  — the model reasoned, but the provider returned a summary, redacted blocks,
#                               or nothing readable (Anthropic summarized/redacted thinking; OpenAI
#                               reasoning models, which count reasoning tokens but withhold the stream)
#   "full"                    — the complete reasoning stream is recorded verbatim (raw reasoning fields
#                               on OpenAI-compatible providers; local-model ``<think>`` capture)
REASONING_NONE = "none"
REASONING_WITHHELD = "withheld_or_summarized"
REASONING_FULL = "full"


class Completion(str):
	"""A completion string that also carries the call's **usage telemetry** as attributes: ``input_tokens`` /
	``output_tokens`` (0 when the provider reported none), ``stop_reason`` (the provider's native stop/finish
	reason, ``None`` when unreported), ``batched`` (served via a provider batch API at discount pricing),
	``cache_read_tokens`` / ``cache_write_tokens`` (Anthropic prompt-cache accounting: tokens served from a cache
	entry, and tokens written into one — both EXCLUDED from ``input_tokens``, which is the full-price remainder),
	and the call's **reasoning record**: ``reasoning`` (whatever reasoning text the provider returned — Anthropic
	thinking blocks including summarized ones, OpenAI-compatible ``reasoning``/``reasoning_content`` fields —
	or ``None``) with ``reasoning_provenance`` marking how complete that record is (see the marker constants
	above). OpenAI-compatible responses also preserve ``upstream_provider``, ``response_model``, and
	``generation_id`` when reported; these make OpenRouter routing auditable.

	Subclassing ``str`` keeps the documented client contract — ``callable(...) -> str`` — fully intact for
	existing callers and injected test clients, while letting ``APIParticipant`` read the telemetry off the
	return value to record per-turn usage (``Message.metadata``) and report into a ``UsageMeter``."""

	input_tokens: int
	output_tokens: int
	stop_reason: str | None
	batched: bool
	cache_read_tokens: int
	cache_write_tokens: int
	reasoning: str | None
	reasoning_provenance: str
	reasoning_tokens: int
	upstream_provider: str | None
	response_model: str | None
	generation_id: str | None

	def __new__(cls, text: str, *, input_tokens: int = 0, output_tokens: int = 0,
	            stop_reason: str | None = None, batched: bool = False,
	            cache_read_tokens: int = 0, cache_write_tokens: int = 0,
	            reasoning: str | None = None, reasoning_provenance: str = REASONING_NONE,
	            reasoning_tokens: int = 0,
	            upstream_provider: str | None = None, response_model: str | None = None,
	            generation_id: str | None = None) -> "Completion":
		self = super().__new__(cls, text)
		self.input_tokens = input_tokens
		self.output_tokens = output_tokens
		self.stop_reason = stop_reason
		self.batched = batched
		self.cache_read_tokens = cache_read_tokens
		self.cache_write_tokens = cache_write_tokens
		self.reasoning = reasoning
		self.reasoning_provenance = reasoning_provenance
		self.reasoning_tokens = reasoning_tokens
		self.upstream_provider = upstream_provider
		self.response_model = response_model
		self.generation_id = generation_id
		return self


def anthropic_reasoning(content_blocks) -> tuple[str | None, str]:
	"""Extract the reasoning record from an Anthropic ``content`` block list: ``(reasoning_text, provenance)``.

	``thinking`` blocks are persisted verbatim as returned — but current Claude models return **summarized**
	thinking over the API, and ``redacted_thinking`` blocks carry no readable text at all, so any
	thinking-bearing response is marked ``withheld_or_summarized`` rather than ``full``: the model's actual
	reasoning stream is longer than what the provider hands back. No thinking blocks → ``none``."""
	thinking = [getattr(b, "thinking", "") for b in content_blocks
	            if getattr(b, "type", None) == "thinking"]
	redacted = any(getattr(b, "type", None) == "redacted_thinking" for b in content_blocks)
	if not thinking and not redacted:
		return None, REASONING_NONE
	text = "\n\n".join(t for t in thinking if t) or None
	return text, REASONING_WITHHELD


def openai_reasoning(message, usage) -> tuple[str | None, str]:
	"""Extract the reasoning record from an OpenAI-schema ``choices[0].message`` (+ ``usage``):
	``(reasoning_text, provenance)``. Works with SDK objects and plain dicts (the batch-API path).

	OpenRouter/DeepSeek-style ``reasoning`` / ``reasoning_content`` fields carry the model's raw reasoning
	stream → ``full``. OpenAI's own reasoning models withhold the stream but count it in
	``usage.completion_tokens_details.reasoning_tokens`` → ``withheld_or_summarized`` with no text."""
	get = message.get if isinstance(message, dict) else lambda k, d=None: getattr(message, k, d)
	text = get("reasoning") or get("reasoning_content") or None
	if isinstance(text, str) and text.strip():
		return text, REASONING_FULL
	details = (usage.get("completion_tokens_details") if isinstance(usage, dict)
	           else getattr(usage, "completion_tokens_details", None)) if usage is not None else None
	rtok = (details.get("reasoning_tokens") if isinstance(details, dict)
	        else getattr(details, "reasoning_tokens", 0)) if details is not None else 0
	if rtok:
		return None, REASONING_WITHHELD
	return None, REASONING_NONE


class _RetryingClient:
	"""Shared machinery for hosted-API clients: a global ``max_in_flight`` semaphore (so N caller threads can't all
	hit the endpoint at once) + exponential backoff with full jitter on transient errors. Subclasses implement
	``_transient(exc)`` and ``_call_once(...)`` and lazily import their SDK, so the harness never requires a
	provider package unless that provider actually runs. All clients are callables with the signature
	``(system, messages, model, max_tokens, temperature) -> str``."""

	def __init__(self, max_in_flight: int = 4, max_retries: int = 6, base_delay: float = 1.0, max_delay: float = 30.0):
		self._sem = threading.Semaphore(max_in_flight)
		self._last_headers: dict[int, object] = {}  # calling thread -> that call's response headers (governor feed)
		self.max_retries = max_retries
		self.base_delay = base_delay
		self.max_delay = max_delay

	def _transient(self, exc) -> bool:
		raise NotImplementedError

	def _call_once(self, system, messages, model, max_tokens, temperature, thinking=None,
	               provider_routing=None, output_config=None) -> "Completion":
		raise NotImplementedError

	def __call__(self, system, messages, model, max_tokens, temperature, thinking=None,
	             provider_routing=None, output_config=None) -> "Completion":
		# With a governor installed (``participant.governor.install_governor``) admission is paced by the
		# provider's rate-limit headers instead of the fixed ``max_in_flight`` semaphore — the semaphore would
		# otherwise cap the whole campaign at 4 and defeat the point. The governor sits in FRONT of this retry
		# loop and consumes its signals; the backoff below is unchanged.
		attempt = 0
		while True:
			governor = current_governor()
			gate = governor.admit() if governor is not None else self._sem
			try:
				with gate:
					completion = self._call_once(system, messages, model, max_tokens, temperature, thinking,
					                             provider_routing, output_config=output_config)
			except Exception as exc:
				if governor is not None:
					governor.note_exception(exc)
				attempt += 1
				if attempt > self.max_retries or not self._transient(exc):
					raise
				delay = min(self.max_delay, self.base_delay * (2 ** (attempt - 1)))
				time.sleep(delay + random.uniform(0, delay))  # full jitter
			else:
				if governor is not None:
					governor.note_success(headers=self._last_headers.pop(threading.get_ident(), None),
					                      tokens_in=completion.input_tokens, tokens_out=completion.output_tokens)
				return completion

	def _record_headers(self, headers) -> None:
		"""Stash one response's headers for the calling thread so ``__call__`` can hand them to the governor.
		Per-thread rather than per-client because one shared client serves every concurrent caller. Subclasses
		whose SDK exposes response headers call this from ``_call_once``; those that do not simply never do, and
		the governor degrades to header-blind AIMD."""
		self._last_headers[threading.get_ident()] = headers

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

	@staticmethod
	def _cache_tokens(usage) -> tuple[int, int]:
		"""``(cache_read_input_tokens, cache_creation_input_tokens)`` off an Anthropic ``usage`` object.

		Both are 0 when the request carried no ``cache_control`` breakpoint and — the trap — ALSO when it carried
		one that did not take: a prefix under the model's minimum cacheable length (512 tokens on claude-opus-5)
		is silently not cached, with no error. So zero reads across repeated identical prefixes is the signature
		of a breakpoint that is not where the caller thinks it is, not of caching being off."""
		if usage is None:
			return 0, 0
		return (int(getattr(usage, "cache_read_input_tokens", 0) or 0),
		        int(getattr(usage, "cache_creation_input_tokens", 0) or 0))

	@staticmethod
	def _thinking_tokens(usage) -> int:
		"""Hidden reasoning tokens the provider billed for this call, from
		``usage.output_tokens_details.thinking_tokens``.

		This is the **auditable evidence that thinking actually happened** on models whose reasoning text is
		sealed: current Claude models never return the raw chain of thought, so a run that wants to prove its
		thinking condition was live cannot do it from the text. It is 0 on a thinking-disabled call and on
		providers that report no details, which makes it a clean on/off discriminator as well as a volume
		measure."""
		details = getattr(usage, "output_tokens_details", None) if usage is not None else None
		return int(getattr(details, "thinking_tokens", 0) or 0)

	def _call_once(self, system, messages, model, max_tokens, temperature, thinking=None,
	               provider_routing=None, output_config=None) -> "Completion":
		if provider_routing is not None:
			raise ValueError("provider_routing is OpenRouter-only; Anthropic does not accept it.")
		# Newer models (e.g. Opus 4.8) DEPRECATE the `temperature` param and 400 if it is sent at all. Omit it when
		# None so callers can opt out; pass it through otherwise.
		kw = dict(model=model, system=system if system else self._anthropic.NOT_GIVEN, messages=messages,
		          max_tokens=max_tokens)
		if temperature is not None:
			kw["temperature"] = temperature
		if thinking is not None:
			kw["thinking"] = self._thinking_param(thinking)
		# `output_config` carries the reasoning-effort control (`{"effort": "low"|...|"max"}`) that replaced the
		# removed `budget_tokens` on current Claude models. Passed verbatim so a caller can also set other
		# output-config keys without a library change.
		if output_config is not None:
			kw["output_config"] = output_config
		# ``with_raw_response`` returns the parsed message AND the HTTP response headers, which carry the
		# ``anthropic-ratelimit-*`` ceilings the governor paces against. Parsing is otherwise identical.
		raw = self._client.messages.with_raw_response.create(**kw)
		self._record_headers(getattr(raw, "headers", None))
		resp = raw.parse()
		text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
		usage = getattr(resp, "usage", None)
		reasoning, provenance = anthropic_reasoning(resp.content)
		cache_read, cache_write = self._cache_tokens(usage)
		return Completion(text,
		                  input_tokens=getattr(usage, "input_tokens", 0) or 0,
		                  output_tokens=getattr(usage, "output_tokens", 0) or 0,
		                  stop_reason=getattr(resp, "stop_reason", None),
		                  cache_read_tokens=cache_read, cache_write_tokens=cache_write,
		                  reasoning=reasoning, reasoning_provenance=provenance,
		                  reasoning_tokens=self._thinking_tokens(usage))

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
			            **({"output_config": r["output_config"]} if r.get("output_config") is not None else {}),
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
			reasoning, provenance = anthropic_reasoning(msg.content)
			cache_read, cache_write = self._cache_tokens(usage)
			texts[entry.custom_id] = Completion(
				"".join(b.text for b in msg.content if getattr(b, "type", None) == "text"),
				input_tokens=getattr(usage, "input_tokens", 0) or 0,
				output_tokens=getattr(usage, "output_tokens", 0) or 0,
				stop_reason=getattr(msg, "stop_reason", None), batched=True,
				cache_read_tokens=cache_read, cache_write_tokens=cache_write,
				reasoning=reasoning, reasoning_provenance=provenance,
				reasoning_tokens=self._thinking_tokens(usage))
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

	def _call_once(self, system, messages, model, max_tokens, temperature, thinking=None,
	               provider_routing=None, output_config=None) -> "Completion":
		if thinking is not None:
			raise NotImplementedError(
				f"{self._label} does not support the 'thinking' control (Anthropic-only); leave thinking=None.")
		if output_config is not None:
			raise NotImplementedError(
				f"{self._label} does not support 'output_config' (Anthropic-only; it carries the reasoning "
				f"effort level); leave output_config=None rather than having it silently dropped.")
		# Some models (e.g. GPT-5) only accept the default temperature; omit the param when None to avoid a 400.
		kw = {self._tokens_param: max_tokens}
		if temperature is not None:
			kw["temperature"] = temperature
		if provider_routing is not None:
			# ``provider`` is an OpenRouter extension, not part of OpenAI's typed SDK surface. ``extra_body``
			# preserves the exact routing object in the JSON request without relying on undocumented kwargs.
			kw["extra_body"] = {"provider": provider_routing}
		resp = self._client.chat.completions.create(
			model=model, messages=self._full_messages(system, messages), **kw)
		choice = resp.choices[0]
		usage = getattr(resp, "usage", None)
		reasoning, provenance = openai_reasoning(choice.message, usage)
		return Completion(choice.message.content or "",
		                  input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
		                  output_tokens=getattr(usage, "completion_tokens", 0) or 0,
		                  stop_reason=getattr(choice, "finish_reason", None),
		                  reasoning=reasoning, reasoning_provenance=provenance,
		                  upstream_provider=getattr(resp, "provider", None),
		                  response_model=getattr(resp, "model", None),
		                  generation_id=getattr(resp, "id", None))


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
			reasoning, provenance = openai_reasoning(choice["message"], usage)
			texts[obj["custom_id"]] = Completion(
				choice["message"]["content"] or "",
				input_tokens=usage.get("prompt_tokens", 0) or 0,
				output_tokens=usage.get("completion_tokens", 0) or 0,
				stop_reason=choice.get("finish_reason"), batched=True,
				reasoning=reasoning, reasoning_provenance=provenance)
		return [texts[f"req-{i}"] for i in range(len(requests))]


class OpenRouterClient(_OpenAICompatClient):
	"""OpenRouter (https://openrouter.ai) via the OpenAI-compatible ``openai`` SDK — one endpoint proxying many
	providers' models (e.g. ``anthropic/claude-sonnet-5``, ``openai/gpt-5``, ``meta-llama/llama-3.1-70b-instruct``).
	Reads ``OPENROUTER_API_KEY``. OpenRouter has **no batch API**, so ``submit_batch`` inherits the base's raise —
	requesting batch mode on an OpenRouter participant fails loudly."""

	_base_url = "https://openrouter.ai/api/v1"
	_api_key_env = "OPENROUTER_API_KEY"
	_label = "OpenRouter"
