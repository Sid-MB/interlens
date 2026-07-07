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

"""The execution engine behind ``Conversation.rollout`` and ``interlens.run``.

A *job* is a ``(job_id, Conversation)`` pair — an unrun, fully-resolved conversation (lazy participants, no
dataset). ``run_jobs`` runs a list of them across devices with checkpointing, resume, per-job failure isolation,
and (by default) batched co-stepping within each device. Each finished conversation is returned on its
``RunResult`` so it can be sampled/inspected afterwards. The analyzer travels ON each conversation
(``conv._analyzer``) — a callable in-process, or a registered name across a spawn boundary."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .devices import available_devices
from .analyzer_registry import resolve_analyzer
from .worker_init import run_worker_init


@dataclass
class RunResult:
	"""Outcome of one job: the finished ``conversation`` (weightless participants + completed transcript), its
	``transcript`` and (serializable) ``analysis``, or an ``error`` string if it failed. ``conversation`` is the
	object to ``sample()``/inspect after a rollout (the source recipe is never mutated)."""

	job_id: str
	conversation: object = None
	transcript: object = None
	analysis: object = None
	error: str | None = None
	device: str | None = None

	@property
	def tokens_generated(self) -> int:
		"""Total generated tokens in this conversation (summed from each turn's ``metadata['n_tokens']``) — the
		realized compute, for verifying matched-compute comparisons. 0 if the job failed."""
		if self.transcript is None:
			return 0
		return sum(int(m.metadata.get("n_tokens") or 0) for m in self.transcript)


@dataclass
class RunReport:
	"""Aggregate outcome of a run. Failures are isolated, not fatal: ``results`` holds every attempted job,
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

	def conversations(self) -> dict:
		return {jid: r.conversation for jid, r in self.results.items() if r.error is None}


def _already_done(out_dir, job_id) -> bool:
	return out_dir is not None and (Path(out_dir) / job_id / "transcript.json").exists()


def _bind(conv, device):
	"""Bind every participant's lazy load to ``device`` (idempotent; no-op for participants without weights)."""
	for p in conv.participants:
		if hasattr(p, "_bind"):
			p._bind(device)
	return conv


def _finish(job_id, conv, device, out_dir) -> RunResult:
	"""Analyze + checkpoint a conversation that has already been run, into a ``RunResult``. Analyze errors are
	isolated per job. The analyzer is read off the conversation (a callable in-process, or a registered name)."""
	try:
		conv.job_id = job_id
		fn = resolve_analyzer(conv._analyzer)
		analysis = fn(conv) if fn is not None else None
		if out_dir is not None:
			conv.save(Path(out_dir) / job_id)
		return RunResult(job_id, conv, conv.transcript, analysis, None, str(device))
	except Exception as exc:
		return RunResult(job_id, None, None, None, f"{type(exc).__name__}: {exc}", str(device))


def _run_one(job_id, conv, device, out_dir) -> RunResult:
	"""Run → analyze → checkpoint one job, catching *any* error so one bad/OOM job can't take down the others."""
	try:
		_bind(conv, device)
		conv.run(turns=conv._turns)
	except Exception as exc:
		return RunResult(job_id, None, None, None, f"{type(exc).__name__}: {exc}", str(device))
	return _finish(job_id, conv, device, out_dir)


def _run_group(jobs, device, out_dir, max_batch_size) -> dict:
	"""Batched (throughput) path: bind every job on one device (so same-recipe participants share the cached model),
	group by co-step SCHEDULE SIGNATURE (turns + per-position participant identity), co-step each group in lockstep,
	then analyze + checkpoint each. A per-job build/run failure is isolated; a batch-level failure degrades that
	group's jobs to per-job error records."""
	from .batched import co_step, schedule_signature

	results = {}
	by_sig, turns_of = {}, {}
	for job_id, conv in jobs:
		_bind(conv, device)
		turns = conv._turns
		sig = schedule_signature(conv, turns)
		by_sig.setdefault(sig, []).append((job_id, conv))
		turns_of[sig] = turns
	for sig, group in by_sig.items():
		try:
			co_step([conv for _, conv in group], turns_of[sig], max_batch_size=max_batch_size)
		except Exception as exc:  # a batch-level failure shouldn't lose the whole run; degrade to per-job records
			for job_id, _ in group:
				results[job_id] = RunResult(job_id, None, None, None,
				                            f"batched co_step: {type(exc).__name__}: {exc}", str(device))
			continue
		for job_id, conv in group:
			results[job_id] = _finish(job_id, conv, device, out_dir)
	return results


def run_jobs(jobs, devices=None, out_dir=None, resume=False, batched=True, max_batch_size=None) -> RunReport:
	"""Run ``(job_id, Conversation)`` jobs across devices, with checkpointing, resume, and per-job failure isolation.

	Parallel by default on **two** axes: one worker **process per device** (jobs round-robined; multi-GPU spawns via
	``torch.multiprocessing`` since fork+CUDA is broken — a single device runs in-process), and within each device
	**batched co-stepping** (``batched=True``). Jobs are grouped by co-step schedule signature so same-schedule jobs
	batch into one ``model.generate`` — correct for ANY mix. ``batched=False`` gives the DETERMINISTIC path.
	"""
	devices = devices or available_devices()
	pending = [(jid, conv) for jid, conv in jobs if not (resume and _already_done(out_dir, jid))]
	skipped = [jid for jid, conv in jobs if resume and _already_done(out_dir, jid)]

	if len(devices) > 1:
		results = _run_spawn(pending, devices, out_dir, batched, max_batch_size)
	elif batched:
		results = _run_group(pending, devices[0], out_dir, max_batch_size)
	else:
		results = {}
		for i, (jid, conv) in enumerate(pending):
			results[jid] = _run_one(jid, conv, devices[i % len(devices)], out_dir)
	return RunReport(results=results, skipped=skipped)


def run(conversations, devices=None, out_dir=None, resume=False, batched=True, max_batch_size=None) -> RunReport:
	"""Run several conversation lineups in ONE pool — the multi-lineup entry point (e.g. a ladder of model pairs ×
	conditions in one overnight job).

	Each conversation is expanded to its jobs (one per ``data()`` row if it has data, else a single conversation),
	with job ids namespaced by that conversation's ``name`` (default ``conv{i}``) so ids stay unique and resumable.
	All jobs go into one pool, so GPUs stay packed across lineups (no idle tail between sequential rollouts) under a
	single ``out_dir``/resume namespace, returning one merged ``RunReport``. Mixing lineups is safe: batched
	co-stepping groups by schedule signature, so each distinct lineup forms its own batch group.

	``Conversation.rollout`` is the single-lineup sugar for this (``run([conv], ...)``-equivalent via ``run_jobs``).
	"""
	jobs = []
	for i, conv in enumerate(conversations):
		jobs.extend(conv._jobs_for_run(i))
	return run_jobs(jobs, devices=devices, out_dir=out_dir, resume=resume, batched=batched,
	                max_batch_size=max_batch_size)


def _worker(device, shard, out_dir, queue, batched, max_batch_size):
	# Spawned workers inherit no parent runtime state — repopulate registries first (tools/analyzers).
	run_worker_init()
	if batched:
		for r in _run_group(shard, device, out_dir, max_batch_size).values():
			queue.put(r)
	else:
		for jid, conv in shard:
			queue.put(_run_one(jid, conv, device, out_dir))


def _run_spawn(jobs, devices, out_dir, batched=True, max_batch_size=None) -> dict:
	"""Spawn one worker per device, round-robining jobs. Results stream back over a queue as each conversation
	completes (checkpoint-as-you-go). Conversations pickle cheaply (lazy participants ship no weights); a closure
	analyzer won't survive pickling — register it by name for the multi-GPU path."""
	import torch.multiprocessing as mp

	ctx = mp.get_context("spawn")
	queue = ctx.Queue()
	shards = [jobs[i::len(devices)] for i in range(len(devices))]
	procs = []
	for device, shard in zip(devices, shards):
		if not shard:
			continue
		p = ctx.Process(target=_worker, args=(device, shard, out_dir, queue, batched, max_batch_size))
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
