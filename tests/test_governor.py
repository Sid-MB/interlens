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

"""Tests for the adaptive rate-limit governor (design.md §12 item 10). No network: a fake clock drives bucket
resets and a fake client stands in for the SDK.

Live smoke evidence, 2026-08-15 — 5 concurrent ``claude-haiku-4-5-20251001`` calls (max_tokens=10, no
temperature param) through a governed ``APIParticipant`` on this org's key, ``governor_report()`` verbatim:

    RateLimitGovernor: in_flight=0 target=512.0 admitted=5 waits=0 cuts=0 recoveries=0 429s=0
      input_tokens: limit=2.44e+07 remaining=2.44e+07 projected=2.44e+07 floor=2.44e+06 reset_in=0s
      output_tokens: limit=2.5e+06 remaining=2.5e+06 projected=2.5e+06 floor=250000 reset_in=0s
      requests: limit=30000 remaining=29998 projected=30000 floor=3000 reset_in=0s
      tokens: limit=2.69e+07 remaining=2.69e+07 projected=2.69e+07 floor=2.69e+06 reset_in=0s
      per-request estimate: 2628.2 in / 658.7 out tokens

All four buckets are reported, the combined ``anthropic-ratelimit-tokens-*`` one included, each as the
``-limit`` / ``-remaining`` / ``-reset`` triple the parser expects. The target lands at ``max_target`` (512)
rather than the request bucket's 27000, which is the intended safety stop. No ``retry-after`` appears on a
clean call. The org's identity travels in separate ``anthropic-organization-id`` / ``anthropic-workspace-id``
headers that the governor never reads or stores, so nothing here needed redaction.

``reset_in=0s`` is real, not a parse failure: a follow-up probe showed Anthropic reporting
``anthropic-ratelimit-*-reset = 2026-08-15T09:27:55Z`` against a response ``date`` of ``09:27:55 GMT`` — an
un-depleted bucket reports its reset as *now*, and only a drawn-down bucket names a future deadline. The
RFC3339 parse itself is covered by ``test_rfc3339_reset_timestamp_is_parsed``.
"""
from __future__ import annotations

import asyncio
import threading

import pytest

from interlens.participant.governor import (
	RateLimitGovernor,
	current_governor,
	governor_report,
	install_governor,
)


class FakeClock:
	"""A monotonic clock the test advances by hand, so bucket resets and retry-after deadlines are exercised
	without any real sleeping."""

	def __init__(self, now: float = 1000.0):
		self.now = now

	def __call__(self) -> float:
		return self.now

	def advance(self, seconds: float) -> None:
		self.now += seconds


def headers(requests_limit=100, requests_remaining=100, reset_in=60, tokens_limit=1_000_000,
            tokens_remaining=1_000_000, retry_after=None) -> dict:
	"""A rate-limit header set in Anthropic's shape. ``reset`` is sent as a bare seconds value here (the parser
	accepts both that and the RFC3339 timestamp the live API sends — covered separately)."""
	h = {
		"anthropic-ratelimit-requests-limit": str(requests_limit),
		"anthropic-ratelimit-requests-remaining": str(requests_remaining),
		"anthropic-ratelimit-requests-reset": str(reset_in),
		"anthropic-ratelimit-input-tokens-limit": str(tokens_limit),
		"anthropic-ratelimit-input-tokens-remaining": str(tokens_remaining),
		"anthropic-ratelimit-input-tokens-reset": str(reset_in),
	}
	if retry_after is not None:
		h["retry-after"] = str(retry_after)
	return h


@pytest.fixture(autouse=True)
def _uninstall():
	"""No test may leak a governor into the next one (or into the rest of the suite: it is process-wide)."""
	yield
	install_governor(None)


# --- admission -------------------------------------------------------------------------------------------------

def test_admits_freely_while_buckets_are_healthy():
	clock = FakeClock()
	gov = RateLimitGovernor(clock=clock)
	gov.note_headers(headers(), tokens_in=100, tokens_out=100)
	for _ in range(20):
		gov.acquire(timeout=0.1)
	assert gov.live_in_flight == 20
	assert gov.snapshot()["counters"]["waits"] == 0


def test_blocks_below_the_floor_and_wakes_at_reset():
	clock = FakeClock()
	gov = RateLimitGovernor(clock=clock)
	# 10 requests left of a 100 limit: the 10% floor is already reached, so nothing may be admitted.
	gov.note_headers(headers(requests_remaining=10, reset_in=30))
	with pytest.raises(TimeoutError):
		gov.acquire(timeout=0.05)
	assert gov.snapshot()["counters"]["waits"] == 1

	admitted = threading.Event()

	def worker():
		gov.acquire()
		admitted.set()

	t = threading.Thread(target=worker, daemon=True)
	t.start()
	assert not admitted.wait(0.2), "governor admitted while the bucket was below its floor"
	clock.advance(31)  # past the reset: the bucket has refilled
	assert admitted.wait(2.0), "governor did not wake its sleeper at the bucket reset"
	t.join(1.0)


def test_token_bucket_alone_can_block_admission():
	clock = FakeClock()
	gov = RateLimitGovernor(clock=clock)
	gov.note_headers(headers(tokens_limit=1_000_000, tokens_remaining=50_000), tokens_in=8000, tokens_out=1000)
	# The request bucket is wide open, but the input-token bucket is under its 100k floor.
	with pytest.raises(TimeoutError):
		gov.acquire(timeout=0.05)


def test_in_flight_projection_consumes_headroom_between_reports():
	clock = FakeClock()
	# A wide AIMD target isolates the bucket-projection rule as the only thing that can block admission.
	gov = RateLimitGovernor(clock=clock, blind_target=1000.0, max_target=1000.0)
	gov.note_headers(headers(requests_limit=20, requests_remaining=20, reset_in=60))
	for _ in range(18):  # projected remaining falls to 2, i.e. the 10% floor of 20
		gov.acquire(timeout=0.1)
	with pytest.raises(TimeoutError):
		gov.acquire(timeout=0.05)
	gov.note_headers(headers(requests_limit=20, requests_remaining=20, reset_in=60))  # fresh report clears it
	gov.acquire(timeout=0.1)


def test_rfc3339_reset_timestamp_is_parsed():
	from datetime import datetime, timedelta, timezone

	gov = RateLimitGovernor()
	stamp = (datetime.now(timezone.utc) + timedelta(seconds=45)).isoformat().replace("+00:00", "Z")
	gov.note_headers(dict(headers(), **{"anthropic-ratelimit-requests-reset": stamp}))
	assert 30 <= gov.snapshot()["buckets"]["requests"]["reset_in_s"] <= 50


# --- AIMD ------------------------------------------------------------------------------------------------------

def test_429_cuts_multiplicatively_then_recovers_additively():
	clock = FakeClock()
	gov = RateLimitGovernor(clock=clock, blind_target=16.0)
	gov.note_rate_limited()
	assert gov.snapshot()["target"] == 8.0
	gov.note_rate_limited()
	assert gov.snapshot()["target"] == 4.0
	assert gov.snapshot()["counters"]["cuts"] == 2
	for _ in range(3):
		gov.note_success()
	assert gov.snapshot()["target"] == 7.0
	assert gov.snapshot()["counters"]["recoveries"] == 3


def test_cut_target_actually_bounds_concurrency():
	clock = FakeClock()
	gov = RateLimitGovernor(clock=clock, blind_target=4.0)
	gov.note_rate_limited()  # target 2
	gov.acquire(timeout=0.1)
	gov.acquire(timeout=0.1)
	with pytest.raises(TimeoutError):
		gov.acquire(timeout=0.05)
	gov.release()
	gov.acquire(timeout=0.5)


def test_retry_after_is_honored_before_readmission():
	clock = FakeClock()
	gov = RateLimitGovernor(clock=clock)
	gov.note_rate_limited(headers=headers(retry_after=5), retry_after=None)
	assert gov.snapshot()["retry_after_remaining"] == 5.0
	with pytest.raises(TimeoutError):
		gov.acquire(timeout=0.05)
	clock.advance(5.1)
	gov.acquire(timeout=0.5)


def test_note_exception_routes_429s_and_absorbs_error_headers():
	class FakeResponse:
		status_code = 429
		headers = headers(requests_remaining=0, retry_after=2)

	class FakeError(Exception):
		status_code = 429
		response = FakeResponse()

	clock = FakeClock()
	gov = RateLimitGovernor(clock=clock, blind_target=8.0)
	gov.note_exception(FakeError())
	snap = gov.snapshot()
	assert snap["target"] == 4.0
	assert snap["counters"]["rate_limited"] == 1
	assert snap["retry_after_remaining"] == 2.0
	assert snap["buckets"]["requests"]["remaining"] == 0.0  # the 429's own headers were absorbed
	assert not snap["header_blind"]


def test_non_rate_limit_exception_does_not_cut():
	gov = RateLimitGovernor(blind_target=8.0)
	gov.note_exception(RuntimeError("connection reset"))
	assert gov.snapshot()["target"] == 8.0
	assert gov.snapshot()["counters"]["cuts"] == 0


def test_first_clean_header_report_seeds_the_target_and_later_ones_do_not():
	gov = RateLimitGovernor(blind_target=8.0)
	assert gov.snapshot()["target"] == 8.0
	gov.note_headers(headers(requests_limit=200, requests_remaining=200))
	assert gov.snapshot()["target"] == 180.0  # limit less the 10% floor
	gov.note_rate_limited()
	assert gov.snapshot()["target"] == 90.0
	# The cut must survive the next successful response: re-seeding here would erase AIMD entirely.
	gov.note_success(headers=headers(requests_limit=200, requests_remaining=200))
	assert gov.snapshot()["target"] == 91.0


def test_a_429s_own_headers_never_seed_the_target():
	gov = RateLimitGovernor(blind_target=8.0)
	gov.note_rate_limited(headers=headers(requests_limit=200, requests_remaining=0))
	assert gov.snapshot()["target"] == 4.0                      # cut from the blind seed, not from 180
	assert gov.snapshot()["buckets"]["requests"]["limit"] == 200.0   # the buckets were still absorbed


# --- header-blind fallback -------------------------------------------------------------------------------------

def test_header_blind_falls_back_to_aimd_and_says_so():
	gov = RateLimitGovernor(blind_target=8.0)
	assert gov.header_blind
	for _ in range(8):
		gov.acquire(timeout=0.1)
	with pytest.raises(TimeoutError):
		gov.acquire(timeout=0.05)  # the seed is the only ceiling
	assert "HEADER-BLIND" in gov.report()
	gov.note_headers({"content-type": "application/json"})  # a proxy that strips rate-limit headers
	assert gov.header_blind
	gov.note_headers(None)
	assert gov.header_blind


def test_report_and_snapshot_shapes():
	gov = RateLimitGovernor()
	assert "not installed" in governor_report()
	install_governor(gov)
	assert current_governor() is gov
	gov.note_headers(headers(), tokens_in=1200, tokens_out=300)
	report = governor_report()
	assert "requests: limit=100" in report
	assert "HEADER-BLIND" not in report
	snap = gov.snapshot()
	assert set(snap) >= {"in_flight", "target", "header_blind", "buckets", "counters", "last_headers"}
	assert snap["last_headers"]["anthropic-ratelimit-requests-limit"] == "100"


# --- concurrency -----------------------------------------------------------------------------------------------

def test_live_in_flight_is_exact_under_concurrent_load():
	"""50 fake requests through the governor at once: the in-flight count must never exceed what the buckets
	allow, must reach the ceiling, and must land back at zero. This is the number the working-capital guard
	sizes its reservations against, so an off-by-one here is money."""
	gov = RateLimitGovernor(blind_target=12.0, max_target=12.0)
	gov.note_headers(headers(requests_limit=1000, requests_remaining=1000))
	peak = 0
	peak_lock = threading.Lock()

	async def fake_request():
		async with gov.admit_async():
			nonlocal peak
			with peak_lock:
				peak = max(peak, gov.live_in_flight)
			await asyncio.sleep(0.01)

	async def main():
		await asyncio.gather(*[fake_request() for _ in range(50)])

	asyncio.run(main())
	assert gov.live_in_flight == 0
	assert peak <= 12, f"governor admitted {peak} concurrently against a target of 12"
	assert peak > 1, "the 50 gathered requests never actually overlapped; the test proves nothing"
	assert gov.snapshot()["counters"]["admitted"] == 50


def test_sync_admit_context_releases_on_error():
	gov = RateLimitGovernor()
	with pytest.raises(ValueError):
		with gov.admit():
			assert gov.live_in_flight == 1
			raise ValueError("boom")
	assert gov.live_in_flight == 0


# --- client integration ----------------------------------------------------------------------------------------

def test_client_call_path_passes_through_the_installed_governor():
	"""The one-line hook in ``_RetryingClient.__call__``: with a governor installed every request is admitted
	through it, its headers are absorbed, and a 429 both cuts the target and is still retried by the client's
	own backoff (which the governor does not replace)."""
	from interlens.participant.participants.api_client import Completion, _RetryingClient

	class FakeRateLimit(Exception):
		status_code = 429

		class response:  # noqa: N801 — stands in for the SDK's httpx response
			status_code = 429
			headers = headers(requests_remaining=1, retry_after=0)

	class FakeClient(_RetryingClient):
		def __init__(self):
			super().__init__(max_in_flight=1, base_delay=0.001, max_delay=0.001)
			self.calls = 0

		def _transient(self, exc):
			return isinstance(exc, FakeRateLimit)

		def _call_once(self, system, messages, model, max_tokens, temperature, thinking=None,
		               provider_routing=None, output_config=None):
			self.calls += 1
			if self.calls == 1:
				raise FakeRateLimit()
			self._record_headers(headers(requests_limit=100, requests_remaining=90))
			return Completion("ok", input_tokens=1500, output_tokens=40)

	gov = RateLimitGovernor(blind_target=8.0)
	install_governor(gov)
	client = FakeClient()
	assert str(client(system=None, messages=[], model="m", max_tokens=10, temperature=None)) == "ok"
	snap = gov.snapshot()
	assert snap["counters"]["rate_limited"] == 1
	assert snap["counters"]["admitted"] == 2      # the retry is admitted through the governor too
	assert snap["in_flight"] == 0
	assert snap["buckets"]["requests"]["remaining"] == 90.0
	assert snap["estimate"]["output_tokens"] < 2000.0   # the success updated the per-request estimate


def test_ungoverned_client_still_uses_its_semaphore():
	"""Nothing changes for a run with no governor installed — the pre-existing max_in_flight path is intact."""
	from interlens.participant.participants.api_client import Completion, _RetryingClient

	class FakeClient(_RetryingClient):
		def _transient(self, exc):
			return False

		def _call_once(self, *a, **kw):
			return Completion("ok")

	assert current_governor() is None
	client = FakeClient(max_in_flight=2)
	assert str(client(system=None, messages=[], model="m", max_tokens=10, temperature=None)) == "ok"
