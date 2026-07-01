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

from dataclasses import dataclass, field
from pathlib import Path

from .devices import available_devices
from .analyzer_registry import resolve_analyzer
from .worker_init import run_worker_init


@dataclass
class RunResult:
	"""Outcome of one spec: its transcript + the (serializable) analyze output, or an error string if it failed."""

	job_id: str
	transcript: object = None
	analysis: object = None
	error: str | None = None
	device: str | None = None


@dataclass
class RunReport:
	"""Aggregate outcome of a run. Failures are isolated, not fatal: ``results`` holds every attempted spec,
	``failed`` lists the ones that errored, ``skipped`` lists resume-skipped (already-checkpointed) ids."""

	results: dict = field(default_factory=dict)
	skipped: list = field(default_factory=list)

	@property
	def failed(self) -> list:
		return [jid for jid, r in self.results.items() if r.error]

	def transcripts(self) -> dict:
		return {jid: r.transcript for jid, r in self.results.items() if r.error is None}

	def analyses(self) -> dict:
		return {jid: r.analysis for jid, r in self.results.items() if r.error is None}


def _already_done(out_dir, job_id) -> bool:
	return out_dir is not None and (Path(out_dir) / job_id / "transcript.json").exists()


def _run_one(spec, device, analyze, out_dir, registry) -> RunResult:
	"""Build → run → analyze → checkpoint one spec, catching *any* error so one bad/OOM spec can't take down the
	others. ``analyze`` runs in-process here while the models are resident, so it can sample/branch/read
	activations on the live conversation; only its serializable return value is kept."""
	try:
		fn = resolve_analyzer(analyze)
		conv = spec.template.build(devices=device, registry=registry)
		turns = spec.turns if spec.turns is not None else spec.template.turns
		conv.run(turns=turns)
		analysis = fn(conv) if fn is not None else None
		if out_dir is not None:
			conv.save(Path(out_dir) / spec.job_id)
		return RunResult(spec.job_id, conv.transcript, analysis, None, str(device))
	except Exception as exc:
		return RunResult(spec.job_id, None, None, f"{type(exc).__name__}: {exc}", str(device))


def _run_group(specs, device, analyze, out_dir, registry, max_batch_size):
	"""Batched (throughput-mode) path: build every spec on one device (so they share the cached model), co-step
	them in lockstep batching same-position turns, then analyze + checkpoint each. Build/analyze errors are
	isolated per job id exactly like ``_run_one``; a per-spec build failure just drops that spec from the group."""
	from .batched import co_step

	fn = resolve_analyzer(analyze)
	results, built = {}, {}
	for spec in specs:
		try:
			built[spec.job_id] = (spec, spec.template.build(devices=device, registry=registry))
		except Exception as exc:
			results[spec.job_id] = RunResult(spec.job_id, None, None, f"{type(exc).__name__}: {exc}", str(device))

	# Group by effective turn count so a co-stepped wave shares one round schedule.
	by_turns: dict[int, list] = {}
	for jid, (spec, conv) in built.items():
		turns = spec.turns if spec.turns is not None else spec.template.turns
		by_turns.setdefault(int(turns), []).append((jid, conv))
	for turns, group in by_turns.items():
		try:
			co_step([conv for _, conv in group], turns, max_batch_size=max_batch_size)
		except Exception as exc:  # a batch-level failure shouldn't lose the whole run; degrade to per-conv record
			for jid, _ in group:
				results[jid] = RunResult(jid, None, None, f"batched co_step: {type(exc).__name__}: {exc}", str(device))
			continue
		for jid, conv in group:
			try:
				analysis = fn(conv) if fn is not None else None
				if out_dir is not None:
					conv.save(Path(out_dir) / jid)
				results[jid] = RunResult(jid, conv.transcript, analysis, None, str(device))
			except Exception as exc:
				results[jid] = RunResult(jid, None, None, f"{type(exc).__name__}: {exc}", str(device))
	return results


def run_conversations(specs, devices=None, analyze=None, out_dir=None, resume=False,
                      registry=None, in_process=None, batched=False, max_batch_size=None) -> RunReport:
	"""Run many conversation specs across devices, with checkpointing, resume, and per-spec failure isolation.

	One worker per device; specs round-robined across them. With a single device (or ``in_process=True``) runs
	sequentially in this process — the path exercised on non-multi-GPU machines. With multiple devices it spawns
	one process per GPU (``torch.multiprocessing``, since fork+CUDA is broken). Each completed conversation is
	saved under ``out_dir/<job_id>/`` as it finishes; ``resume=True`` skips job ids already checkpointed there.
	"""
	devices = devices or available_devices()
	pending = [s for s in specs if not (resume and _already_done(out_dir, s.job_id))]
	skipped = [s.job_id for s in specs if resume and _already_done(out_dir, s.job_id)]

	use_spawn = (in_process is False) or (in_process is None and len(devices) > 1)
	if use_spawn:
		results = _run_spawn(pending, devices, analyze, out_dir, registry, batched, max_batch_size)
	elif batched:
		# One device (or forced in-process): build the whole shard on it and co-step as a batched group.
		results = _run_group(pending, devices[0], analyze, out_dir, registry, max_batch_size)
	else:
		results = {}
		for i, spec in enumerate(pending):
			results[spec.job_id] = _run_one(spec, devices[i % len(devices)], analyze, out_dir, registry)
	return RunReport(results=results, skipped=skipped)


def _worker(device, shard, analyze, out_dir, registry, queue, batched, max_batch_size):
	# Spawned workers inherit no parent state — repopulate registries first (tools/analyzers/config kinds).
	run_worker_init()
	if batched:
		for r in _run_group(shard, device, analyze, out_dir, registry, max_batch_size).values():
			queue.put(r)
	else:
		for spec in shard:
			queue.put(_run_one(spec, device, analyze, out_dir, registry))


def _run_spawn(specs, devices, analyze, out_dir, registry, batched=False, max_batch_size=None) -> dict:
	"""Spawn one worker per device, round-robining specs. Results stream back over a queue as each conversation
	completes (checkpoint-as-you-go). ``analyze`` must be a top-level callable or a registered name to survive
	pickling into the worker; a closure will fail fast."""
	import torch.multiprocessing as mp

	ctx = mp.get_context("spawn")
	queue = ctx.Queue()
	shards = [specs[i::len(devices)] for i in range(len(devices))]
	procs = []
	for device, shard in zip(devices, shards):
		if not shard:
			continue
		p = ctx.Process(target=_worker, args=(device, shard, analyze, out_dir, registry, queue, batched, max_batch_size))
		p.start()
		procs.append(p)

	results = {}
	expected = sum(len(s) for s in shards)
	for _ in range(expected):
		r = queue.get()  # blocks until a worker posts a result
		results[r.job_id] = r
	for p in procs:
		p.join()
	return results
