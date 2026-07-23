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

# [rational_agents scaffold: interlens-core] 2026-07-23

"""The process-local model/tokenizer cache under concurrency.

Regression for the pilot bug: with several rollout worker threads requesting the SAME uncached weight key at
once, the old unlocked check-then-set let every thread run the loader, and a concurrent ``transformers``
meta-device load + ``.to(device)`` raced into "Cannot copy out of meta tensor; no data!". The cache now
serializes same-key loads with a per-key lock (double-checked), so the loader runs exactly once and all callers
get the one fully-materialized object. Stub loaders — no weights, no GPU."""
from __future__ import annotations

import threading
import time

import pytest

from interlens.loading import model_cache


@pytest.fixture(autouse=True)
def _clean_cache():
	model_cache.free()
	yield
	model_cache.free()


def _run_concurrently(fn, n):
	"""Run ``fn`` on ``n`` threads released simultaneously (a barrier maximizes the race window)."""
	ready = threading.Barrier(n)

	def worker():
		ready.wait()
		fn()

	threads = [threading.Thread(target=worker) for _ in range(n)]
	for t in threads:
		t.start()
	for t in threads:
		t.join()


def test_cached_model_loads_once_under_concurrent_same_key():
	n = 8
	loads, results = [], []
	lock = threading.Lock()
	sentinel = object()

	def loader():
		with lock:
			loads.append(1)
		time.sleep(0.03)          # hold the per-key lock long enough that every peer thread must block on it
		return sentinel

	def call():
		obj = model_cache.cached_model(("qwen3-4b", "cuda", "bf16"), loader)
		with lock:
			results.append(obj)

	_run_concurrently(call, n)
	assert len(loads) == 1                                    # loader ran exactly once despite 8 racing threads
	assert len(results) == n and all(r is sentinel for r in results)   # all got the same materialized object


def test_cached_tokenizer_loads_once_under_concurrency():
	n = 6
	loads, results = [], []
	lock = threading.Lock()
	tok = object()

	def loader():
		with lock:
			loads.append(1)
		time.sleep(0.02)
		return tok

	def call():
		obj = model_cache.cached_tokenizer("qwen3-4b", loader)
		with lock:
			results.append(obj)

	_run_concurrently(call, n)
	assert len(loads) == 1
	assert len(results) == n and all(r is tok for r in results)


def test_distinct_keys_each_load_once():
	"""Different keys don't share a lock, so each loads exactly once (and concurrently — only same-key loads
	serialize)."""
	loads: dict[int, int] = {}
	results: dict[tuple, list] = {}
	lock = threading.Lock()
	keys = [("m", i) for i in range(4)]

	def make_call(key):
		def loader():
			with lock:
				loads[key[1]] = loads.get(key[1], 0) + 1
			time.sleep(0.02)
			return key[1]

		def call():
			obj = model_cache.cached_model(key, loader)
			with lock:
				results.setdefault(key, []).append(obj)
		return call

	ready = threading.Barrier(len(keys) * 2)

	def worker(call):
		ready.wait()
		call()

	threads = [threading.Thread(target=worker, args=(make_call(k),)) for k in keys for _ in range(2)]
	for t in threads:
		t.start()
	for t in threads:
		t.join()

	assert all(loads[i] == 1 for i in range(4))              # each distinct key loaded exactly once
	for k in keys:
		assert results[k] == [k[1], k[1]]                    # both callers of a key got that key's object


def test_cached_result_reused_without_relocking():
	"""Once cached, the fast path returns the same object on subsequent calls (loader not re-run)."""
	loads = []
	obj = object()

	def loader():
		loads.append(1)
		return obj

	first = model_cache.cached_model(("k",), loader)
	second = model_cache.cached_model(("k",), loader)
	assert first is second is obj and len(loads) == 1
