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

"""Adaptive rate-limit governor: admission control paced by the provider's own rate-limit headers.

Written for build item 10 of ``experiments/rational_agents/auction/docs/design.md`` §12 ("Throughput: max out
the rate limit"). The stack it replaces is reactive-only — a fixed ``max_in_flight`` semaphore in
``api_client.py`` plus 429 exponential backoff — which runs far below the org ceiling because the ceiling is
never read. A governed run has **no fixed concurrency knob**: every episode of every cell in the process shares
one governor, and the rate-limit headers are the throttle.

Three signals drive admission:

- **Bucket headroom.** Every response (success *and* error) carries ``anthropic-ratelimit-{requests,
  input-tokens,output-tokens,tokens}-{limit,remaining,reset}``. The governor projects each bucket's remaining
  capacity forward by what the requests admitted since that header snapshot are expected to consume, and admits
  while every bucket's projection stays above a safety floor (default 10% of the bucket's limit). A caller that
  would breach the floor sleeps until the earliest bucket reset and is woken there.
- **AIMD.** Any 429 multiplicatively cuts the admission target (×0.5) and, when the response carries
  ``retry-after``, blocks readmission until that deadline. Each clean completion adds 1 back. This is the whole
  control loop when headers are missing (older SDK, a proxy that strips them): the governor logs that it is
  **header-blind** and falls back to pure AIMD seeded at ``blind_target`` (8) concurrent.
- **Live in-flight count.** ``live_in_flight`` is the number of requests actually in flight right now, exported
  so the campaign's working-capital guard (``experiments/rational_agents/api_request_budget.py``) can size its
  worst-case reservations against the real concurrency rather than a static parameter — a static ×120
  reservation against the committed budget would starve the tail cells (design.md §11).

The core is a ``threading.Condition``, not an asyncio primitive, because the actual call site is a **worker
thread**: ``EpisodePool`` runs episodes as asyncio tasks but each participant call goes through
``asyncio.to_thread`` into the synchronous provider SDK. A condition variable is admissible from both worlds;
:meth:`admit_async` is the awaitable wrapper for callers already on an event loop.

Usage::

    from interlens.participant.governor import RateLimitGovernor, install_governor, governor_report

    install_governor(RateLimitGovernor())        # process-wide, before launching any cell
    ...                                          # every Anthropic request now passes through it
    print(governor_report())                     # into run.log: observed ceilings + AIMD history
"""
from __future__ import annotations

import threading
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone

# The rate-limit buckets Anthropic reports, as ``bucket name -> header prefix``. A bucket only exists for the
# governor once a response has reported it, so an org/model whose plan exposes a different subset is handled
# without configuration.
BUCKET_PREFIXES = {
	"requests": "anthropic-ratelimit-requests",
	"input_tokens": "anthropic-ratelimit-input-tokens",
	"output_tokens": "anthropic-ratelimit-output-tokens",
	"tokens": "anthropic-ratelimit-tokens",
}
RETRY_AFTER_HEADER = "retry-after"


@dataclass
class Bucket:
	"""One rate-limit bucket as last reported by the provider, plus the consumption the governor has admitted
	since that report. ``limit``/``remaining`` are in the bucket's own units (requests, or tokens);
	``reset_monotonic`` is the refill deadline translated onto the local monotonic clock (the header is an
	RFC3339 wall-clock timestamp, which is unusable for scheduling across clock skew).

	Measured on this org (2026-08-15): an **un-depleted** bucket reports its reset as the current second, so a
	healthy bucket's deadline is already in the past and only a drawn-down one names a future time."""

	limit: float
	remaining: float
	reset_monotonic: float
	spent_since_report: float = 0.0

	def projected_remaining(self, now: float) -> float:
		"""Capacity expected to be left if every request admitted since the report consumes its estimate. Past
		the reset deadline the bucket has refilled, so the projection restarts from the full limit less what has
		been admitted since (the conservative reading — the real refill may be more recent than the deadline)."""
		base = self.limit if now >= self.reset_monotonic else self.remaining
		return base - self.spent_since_report


@dataclass
class TokenEstimate:
	"""Exponentially weighted per-request token consumption, used to project the token buckets forward between
	header reports. Seeded high (a fresh run has no observations and should under- rather than over-admit) and
	updated from every response that reports usage."""

	input_tokens: float = 8000.0
	output_tokens: float = 2000.0
	weight: float = 0.2

	def observe(self, tokens_in: int, tokens_out: int) -> None:
		if tokens_in:
			self.input_tokens = (1 - self.weight) * self.input_tokens + self.weight * tokens_in
		if tokens_out:
			self.output_tokens = (1 - self.weight) * self.output_tokens + self.weight * tokens_out

	def per_bucket(self) -> dict[str, float]:
		"""The estimated consumption one admitted request charges to each token bucket. The undifferentiated
		``tokens`` bucket (reported on some plans instead of the split pair) is charged the sum."""
		return {"input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
		        "tokens": self.input_tokens + self.output_tokens, "requests": 1.0}


class RateLimitGovernor:
	"""Process-wide admission controller for one provider+org, paced by rate-limit headers with an AIMD fallback.

	One governor per provider+org and one per process: it is shared by every participant, episode, and cell, so
	total in-flight requests are bounded by the measured header ceiling rather than by any per-cell knob.

	:param floor_fraction: admit only while every bucket's projected remaining exceeds this fraction of its
		limit. 0.10 keeps a 10% cushion for requests already in flight whose usage has not been reported yet;
		raise it for a run that must never see a 429, lower it to squeeze the ceiling harder.
	:param blind_target: the AIMD admission target used before any header has been seen, and the permanent
		ceiling if headers never arrive (header-blind mode). 8 is deliberately modest — it recovers upward by
		one per clean completion, so a genuinely wide limit is discovered within seconds.
	:param max_target: hard ceiling on the AIMD target, a safety stop against unbounded additive growth when a
		provider reports enormous buckets. ``None`` leaves growth bounded only by the buckets.
	:param min_target: floor the multiplicative cut cannot go below, so a burst of 429s cannot wedge the run at
		zero concurrency.
	:param cut_factor: the multiplicative decrease applied to the target on each 429 (0.5 = halve).
	:param recovery: the additive increase per clean completion (1 request).
	:param clock: monotonic time source, injectable so tests can drive resets without sleeping.
	"""

	def __init__(self, *, floor_fraction: float = 0.10, blind_target: float = 8.0,
	             max_target: float | None = 512.0, min_target: float = 1.0,
	             cut_factor: float = 0.5, recovery: float = 1.0, clock=time.monotonic):
		if not 0.0 <= floor_fraction < 1.0:
			raise ValueError(f"floor_fraction must be in [0, 1); got {floor_fraction}")
		if not 0.0 < cut_factor < 1.0:
			raise ValueError(f"cut_factor must be in (0, 1); got {cut_factor}")
		self.floor_fraction = floor_fraction
		self.blind_target = blind_target
		self.max_target = max_target
		self.min_target = min_target
		self.cut_factor = cut_factor
		self.recovery = recovery
		self._clock = clock
		self._cond = threading.Condition()
		self._in_flight = 0
		self._target = blind_target
		self._buckets: dict[str, Bucket] = {}
		self._estimate = TokenEstimate()
		self._last_headers: dict[str, str] = {}
		self._retry_until: float | None = None
		self._header_reports = 0
		self._seeded = False
		self.cuts = 0
		self.recoveries = 0
		self.admitted = 0
		self.waits = 0
		self.rate_limited = 0

	# --- admission -------------------------------------------------------------------------------------------

	@property
	def live_in_flight(self) -> int:
		"""Requests admitted and not yet released, right now. The working-capital guard sizes its worst-case
		reservation against this rather than a static concurrency parameter (design.md §11)."""
		with self._cond:
			return self._in_flight

	@property
	def header_blind(self) -> bool:
		"""True while no response has reported a rate-limit header — the governor is running on pure AIMD and
		says so in :meth:`governor_report`, because a header-blind run cannot claim to have found the ceiling."""
		return self._header_reports == 0

	def acquire(self, timeout: float | None = None) -> None:
		"""Block until admission is granted, then count the request as in flight. ``timeout`` (seconds) raises
		``TimeoutError`` rather than admitting — leave it ``None`` for campaign traffic, where waiting for the
		bucket to refill is the correct behaviour and giving up would just drop an episode."""
		# The caller's timeout is real elapsed time (``time.monotonic``), never ``self._clock``: the injectable
		# clock exists to drive bucket resets deterministically in tests, and a frozen clock must not turn a
		# bounded wait into an infinite one.
		deadline = None if timeout is None else time.monotonic() + timeout
		with self._cond:
			waited = False
			while True:
				wait_for = self._blocked_until(self._clock())
				if wait_for is None:
					break
				if not waited:
					self.waits += 1
					waited = True
				if deadline is not None and time.monotonic() >= deadline:
					raise TimeoutError("rate-limit governor did not admit within the timeout")
				# Sleepers wake at the earliest bucket reset / retry-after deadline; the 1s ceiling re-checks
				# state that changes without a notify (a bucket refilling while nothing else completes).
				patience = min(wait_for, 1.0) if wait_for > 0 else 0.05
				if deadline is not None:
					patience = min(patience, max(0.001, deadline - time.monotonic()))
				self._cond.wait(patience)
			self._in_flight += 1
			self.admitted += 1
			charge = self._estimate.per_bucket()
			for name, bucket in self._buckets.items():
				bucket.spent_since_report += charge.get(name, 0.0)

	def release(self) -> None:
		"""Mark one in-flight request finished and wake a waiter. Always pair with :meth:`acquire` (use
		:meth:`admit` / :meth:`admit_async` rather than calling either by hand)."""
		with self._cond:
			self._in_flight = max(0, self._in_flight - 1)
			self._cond.notify()

	@contextmanager
	def admit(self, timeout: float | None = None):
		"""Synchronous admission scope: ``with governor.admit(): ...`` around one provider request. This is the
		form the client uses, because provider SDK calls run in worker threads."""
		self.acquire(timeout)
		try:
			yield self
		finally:
			self.release()

	@asynccontextmanager
	async def admit_async(self, timeout: float | None = None):
		"""Awaitable admission scope for callers already on an event loop: ``async with governor.admit_async():``.
		The blocking wait is offloaded with ``asyncio.to_thread`` so the loop is never stalled by a sleeper."""
		import asyncio

		await asyncio.to_thread(self.acquire, timeout)
		try:
			yield self
		finally:
			self.release()

	def _blocked_until(self, now: float) -> float | None:
		"""``None`` when a request may be admitted now; otherwise the seconds until the soonest event that could
		change that (a retry-after deadline or a bucket reset). Caller holds the lock."""
		if self._retry_until is not None and now < self._retry_until:
			return self._retry_until - now
		if self._in_flight >= self._target:
			return 0.0  # waiting on a completion, which arrives via notify()
		soonest = None
		for name, bucket in self._buckets.items():
			if bucket.projected_remaining(now) > self.floor_fraction * bucket.limit:
				continue
			delay = max(0.0, bucket.reset_monotonic - now)
			soonest = delay if soonest is None else min(soonest, delay)
		return soonest

	# --- provider feedback -----------------------------------------------------------------------------------

	def note_headers(self, headers, *, tokens_in: int = 0, tokens_out: int = 0, seed: bool = True) -> None:
		"""Absorb one response's rate-limit headers — from a **success or an error**, since a 429's headers are
		the most informative ones in the run. ``headers`` is any mapping (httpx ``Headers``, a plain dict);
		absent or unparseable headers are ignored, leaving the governor in header-blind AIMD. ``tokens_in`` /
		``tokens_out`` update the per-request estimate that projects token buckets between reports.

		``seed=False`` absorbs the buckets without letting them re-seed the AIMD target; the 429 path uses it so
		a cut is never undone by the very response that reported the overshoot."""
		parsed = self._parse(headers)
		with self._cond:
			self._estimate.observe(tokens_in, tokens_out)
			if not parsed:
				return
			self._header_reports += 1
			self._last_headers = {k: v for k, v in parsed["raw"].items()}
			for name, bucket in parsed["buckets"].items():
				self._buckets[name] = bucket
			if seed:
				self._seed_target_from_buckets()
			self._cond.notify_all()

	def note_success(self, *, headers=None, tokens_in: int = 0, tokens_out: int = 0) -> None:
		"""One clean completion: additive recovery of the AIMD target (+``recovery``), plus header absorption."""
		if headers is not None:
			self.note_headers(headers, tokens_in=tokens_in, tokens_out=tokens_out)
		with self._cond:
			ceiling = self._target + self.recovery
			if self.max_target is not None:
				ceiling = min(ceiling, self.max_target)
			if ceiling > self._target:
				self._target = ceiling
				self.recoveries += 1
				self._cond.notify()

	def note_rate_limited(self, *, headers=None, retry_after: float | None = None) -> None:
		"""One 429 (or other rate-limit signal): multiplicative cut of the AIMD target and, when the response
		carries ``retry-after`` (explicit argument wins, else read from ``headers``), a hard block on readmission
		until that deadline passes. Headers are absorbed first, so the cut is recorded against fresh ceilings."""
		if headers is not None:
			self.note_headers(headers, seed=False)
			if retry_after is None:
				retry_after = _float_or_none(_get_header(headers, RETRY_AFTER_HEADER))
		with self._cond:
			self.rate_limited += 1
			self.cuts += 1
			self._target = max(self.min_target, self._target * self.cut_factor)
			if retry_after is not None and retry_after > 0:
				self._retry_until = self._clock() + retry_after

	def note_exception(self, exc) -> None:
		"""Feed one provider exception to the governor without the caller having to know the SDK's exception
		classes: any exception carrying an HTTP response contributes its headers, and a 429 additionally triggers
		the AIMD cut. Anything else (a connection error, a 500) is ignored — those are the retry loop's business,
		not the rate limiter's."""
		response = getattr(exc, "response", None)
		headers = getattr(response, "headers", None)
		status = getattr(exc, "status_code", None) or getattr(response, "status_code", None)
		if status == 429:
			self.note_rate_limited(headers=headers)
		elif headers is not None:
			self.note_headers(headers)

	def _seed_target_from_buckets(self) -> None:
		"""On the **first clean header report only**, raise the AIMD target from the blind seed to the concurrency
		the reported request bucket can support, so a governed run does not crawl up from 8 one completion at a
		time when the org's real ceiling is known from the first response.

		Deliberately once: letting every subsequent report re-seed would erase a 429's multiplicative cut on the
		next successful response, which is exactly the reactive-only behaviour the governor replaces. After a cut
		the target only comes back through additive recovery. Caller holds the lock."""
		requests = self._buckets.get("requests")
		if self._seeded or self.cuts or requests is None or requests.limit <= 0:
			return
		self._seeded = True
		supported = max(self.min_target, requests.limit * (1.0 - self.floor_fraction))
		if self.max_target is not None:
			supported = min(supported, self.max_target)
		if supported > self._target:
			self._target = supported

	def _parse(self, headers) -> dict | None:
		"""Translate a response's headers into buckets on the monotonic clock. Returns ``None`` when no
		rate-limit header is present (header-blind), never raising: a proxy that strips or mangles headers must
		degrade the governor to AIMD, not fail the run."""
		if headers is None:
			return None
		buckets: dict[str, Bucket] = {}
		raw: dict[str, str] = {}
		now = self._clock()
		for name, prefix in BUCKET_PREFIXES.items():
			limit = _float_or_none(_get_header(headers, f"{prefix}-limit"))
			remaining = _float_or_none(_get_header(headers, f"{prefix}-remaining"))
			if limit is None or remaining is None:
				continue
			reset_raw = _get_header(headers, f"{prefix}-reset")
			reset_in = _seconds_until(reset_raw)
			buckets[name] = Bucket(limit=limit, remaining=remaining,
			                       reset_monotonic=now + (reset_in if reset_in is not None else 60.0))
			for suffix in ("limit", "remaining", "reset"):
				value = _get_header(headers, f"{prefix}-{suffix}")
				if value is not None:
					raw[f"{prefix}-{suffix}"] = str(value)
		retry_after = _get_header(headers, RETRY_AFTER_HEADER)
		if retry_after is not None:
			raw[RETRY_AFTER_HEADER] = str(retry_after)
		if not buckets:
			return None
		return {"buckets": buckets, "raw": raw}

	# --- reporting -------------------------------------------------------------------------------------------

	def snapshot(self) -> dict:
		"""A JSON-serializable view of the control state: live in-flight count, the AIMD target, whether the
		governor is header-blind, per-bucket ceilings with their projections, the raw last-seen headers, and the
		cut/recovery/wait counters. The pilot writes this into ``run.log`` so the confirmatory launch confirms
		rather than discovers where the ceiling sits (design.md §12 item 10)."""
		with self._cond:
			now = self._clock()
			return {
				"in_flight": self._in_flight,
				"target": round(self._target, 2),
				"header_blind": self._header_reports == 0,
				"header_reports": self._header_reports,
				"retry_after_remaining": (round(self._retry_until - now, 2)
				                          if self._retry_until is not None and self._retry_until > now else 0.0),
				"buckets": {name: {"limit": b.limit, "remaining": b.remaining,
				                   "projected_remaining": round(b.projected_remaining(now), 1),
				                   "floor": self.floor_fraction * b.limit,
				                   "reset_in_s": round(max(0.0, b.reset_monotonic - now), 1)}
				            for name, b in self._buckets.items()},
				"estimate": {"input_tokens": round(self._estimate.input_tokens, 1),
				             "output_tokens": round(self._estimate.output_tokens, 1)},
				"counters": {"admitted": self.admitted, "waits": self.waits, "cuts": self.cuts,
				             "recoveries": self.recoveries, "rate_limited": self.rate_limited},
				"last_headers": dict(self._last_headers),
			}

	def report(self) -> str:
		"""The :meth:`snapshot` formatted for ``run.log`` — one header line plus one line per observed bucket."""
		snap = self.snapshot()
		lines = [f"RateLimitGovernor: in_flight={snap['in_flight']} target={snap['target']} "
		         f"admitted={snap['counters']['admitted']} waits={snap['counters']['waits']} "
		         f"cuts={snap['counters']['cuts']} recoveries={snap['counters']['recoveries']} "
		         f"429s={snap['counters']['rate_limited']}"]
		if snap["header_blind"]:
			lines.append("  HEADER-BLIND: no anthropic-ratelimit-* headers seen; pacing on AIMD alone "
			             f"(seeded at {self.blind_target:g} concurrent). Observed ceilings are NOT available.")
		else:
			for name, b in sorted(snap["buckets"].items()):
				lines.append(f"  {name}: limit={b['limit']:g} remaining={b['remaining']:g} "
				             f"projected={b['projected_remaining']:g} floor={b['floor']:g} "
				             f"reset_in={b['reset_in_s']:g}s")
			lines.append(f"  per-request estimate: {snap['estimate']['input_tokens']:g} in / "
			             f"{snap['estimate']['output_tokens']:g} out tokens")
		if snap["retry_after_remaining"]:
			lines.append(f"  retry-after: readmission blocked for {snap['retry_after_remaining']:g}s")
		return "\n".join(lines)


# --- process-wide installation ---------------------------------------------------------------------------------
# One governor per provider+org, and campaigns run one org per process, so the installed governor is a module
# global rather than something threaded through every participant constructor: the client path reads it with
# ``current_governor()`` and behaves exactly as before when none is installed.

_GOVERNOR: RateLimitGovernor | None = None
_INSTALL_LOCK = threading.Lock()


def install_governor(governor: RateLimitGovernor | None = None) -> RateLimitGovernor | None:
	"""Install (or with ``None``, remove) the process-wide governor and return it. Every hosted-API request
	issued afterwards passes through it, from any thread or event loop. Called once by the campaign launcher
	before any cell starts; installing replaces any previous governor rather than stacking."""
	global _GOVERNOR
	with _INSTALL_LOCK:
		_GOVERNOR = governor
	return _GOVERNOR


def current_governor() -> RateLimitGovernor | None:
	"""The installed process-wide governor, or ``None`` when the run is ungoverned (the pre-existing behaviour:
	the client's own ``max_in_flight`` semaphore is then the only concurrency bound)."""
	return _GOVERNOR


def governor_report() -> str:
	"""The installed governor's :meth:`RateLimitGovernor.report`, or a one-line notice when none is installed —
	safe to call unconditionally from a run's logging path."""
	governor = current_governor()
	if governor is None:
		return "RateLimitGovernor: not installed (requests are paced only by the client's max_in_flight cap)."
	return governor.report()


# --- header helpers --------------------------------------------------------------------------------------------

def _get_header(headers, name: str):
	"""Case-insensitive lookup across httpx ``Headers``, plain dicts, and anything else with ``get``."""
	if headers is None:
		return None
	getter = getattr(headers, "get", None)
	if getter is None:
		return None
	value = getter(name)
	if value is None:
		value = getter(name.lower())
	if value is None:
		for key, candidate in (headers.items() if hasattr(headers, "items") else ()):
			if str(key).lower() == name.lower():
				return candidate
	return value


def _float_or_none(value) -> float | None:
	if value is None:
		return None
	try:
		return float(value)
	except (TypeError, ValueError):
		return None


def _seconds_until(value) -> float | None:
	"""Seconds from now until an RFC3339 reset timestamp (``2026-08-15T12:00:00Z``), which is how Anthropic
	reports bucket resets. A bare number is taken as a delay in seconds (other providers report it that way);
	anything unparseable returns ``None`` so the caller can fall back to a conservative default."""
	if value is None:
		return None
	numeric = _float_or_none(value)
	if numeric is not None:
		return max(0.0, numeric)
	try:
		reset = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
	except ValueError:
		return None
	if reset.tzinfo is None:
		reset = reset.replace(tzinfo=timezone.utc)
	return max(0.0, (reset - datetime.now(timezone.utc)).total_seconds())
