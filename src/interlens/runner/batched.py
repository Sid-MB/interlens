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

# [complete-chat-harness]: co-stepping batched runner (PLAN item 5 / CLUSTER_NEXT_STEPS item 5).
# Steps a group of independent conversations that SHARE participant/model objects in lockstep, batching each
# round's same-position turns into ONE model.generate — the biggest rollout throughput win. Throughput mode
# only: batch composition + the global RNG perturb rows, so tokens are NOT identical to unbatched (PLAN
# §Execution modes). Conversations that can't batch (tools, non-ModelParticipant speaker) fall back to the
# per-conversation .step within the same round, so a mixed group still runs correctly.
from __future__ import annotations

from ..participant.participants.model_participant import ModelParticipant


def _participant_signature(p):
	"""A key identifying what a participant would batch AS. Two participants share a key only when co-stepping
	them in one batch is correct: local models must resolve to the SAME cached weight object — but we key on the
	load recipe (``batch_signature``) when the weights aren't loaded yet, so grouping never *forces* a load; API
	participants must hit the same provider+model+batch mode; anything else (tools/human/non-batch API) is per-conv
	so keyed by role."""
	if isinstance(p, ModelParticipant):
		return p.batch_signature()
	if type(p).__name__ == "APIParticipant":
		return ("api", getattr(p, "provider", None), getattr(p, "model_id", None), bool(getattr(p, "batch", False)))
	return ("other", type(p).__name__, getattr(p, "name", None))


def schedule_signature(conv, turns: int):
	"""The full co-step schedule of a conversation: its turn count + the per-position participant signatures. Convs
	that share a signature have an identical speaker/model schedule, so ``co_step`` can batch each round's
	same-position turns across them safely. Grouping specs by this (instead of by turn count alone) makes batched
	execution correct for ANY mix of specs — a heterogeneous lineup simply forms its own group."""
	return (int(turns), tuple(_participant_signature(p) for p in conv.participants))


def _chunks(items, size):
	if not size or size <= 0 or size >= len(items):
		return [items]
	return [items[i:i + size] for i in range(0, len(items), size)]


def _batchable(participant) -> bool:
	# ANY local ModelParticipant (base or any family subclass — qwen/gemma/llama/…) always batches locally: they
	# all inherit ``generate_batch``, so the check is capability-based (isinstance), never a per-family allowlist a
	# new family could silently fall out of. An APIParticipant batches only with batch=True (its provider async
	# batch API). Tool loops take the per-conv path regardless (the batched path has no tools loop).
	if getattr(participant, "tools", ()):
		return False
	if isinstance(participant, ModelParticipant):
		return True
	return type(participant).__name__ == "APIParticipant" and getattr(participant, "batch", False)


def _turn_cap(conv, stop, participant) -> int | None:
	"""The stop-condition token cap for ``conv``'s next turn, bounded by the speaker's own cap (a budget never
	*raises* a participant's limit). ``None`` = no cap."""
	if stop is None:
		return None
	cap = stop.turn_cap(conv)
	if cap is None:
		return None
	own = getattr(participant, "max_new_tokens", None)
	return cap if own is None else min(own, cap)


def co_step(convs, turns: int | None, *, max_batch_size: int | None = None, group_seed: int = 0):
	"""Co-step ``convs`` (a shared turn schedule) in lockstep, batching each round's same-position turns.

	Each round: every conversation's current speaker is the same schedule position, so their views are gathered
	and generated in one left-padded batch (sub-batched into ``max_batch_size`` waves). The representative
	participant drives the batch — safe because same-schedule participants wrap the *same* cached model + tokenizer.
	Message hooks run per conversation before commit.

	Stop conditions are honored on the batched path too: each conversation's combined stop (its ``run_until`` /
	ambient budget, resolved once) can cap the round's ``max_new_tokens`` (the wave uses the conservative min so no
	conversation overshoots its budget) and drops a conversation from later rounds once it fires. ``turns`` may be
	``None`` for a purely stop-driven run (e.g. a matched-compute ``TokenBudget``), bounded by a large safety cap.
	"""
	if not convs:
		return convs
	stops = {}
	for c in convs:
		s = c._resolve_stop(None)
		if s is not None:
			s.reset()
		stops[id(c)] = s
	n_parts = len(convs[0].participants)
	active = list(convs)
	_SAFETY_ROUNDS = 100_000  # bound a stop-only (turns=None) run so a never-firing condition can't loop forever
	i = 0
	while active and (turns is None or i < turns) and i < _SAFETY_ROUNDS:
		spk = i % n_parts
		batch_convs = [c for c in active if _batchable(c.participants[spk])]
		other_convs = [c for c in active if not _batchable(c.participants[spk])]
		for wave in _chunks(batch_convs, max_batch_size):
			if not wave:  # this round has no batchable speaker (e.g. an all-API/non-batch group) — nothing to fuse
				continue
			rep = wave[0].participants[spk]
			caps = [_turn_cap(c, stops[id(c)], c.participants[spk]) for c in wave]
			caps = [x for x in caps if x is not None]
			mnt = min(caps) if caps else None
			views = [c._view(c.participants[spk]) for c in wave]
			msgs = rep.generate_batch(views, turn=i, group_seed=group_seed + i, max_new_tokens=mnt)
			for c, msg in zip(wave, msgs):
				msg = c._apply_hooks(msg)
				if msg is not None:
					c.transcript.messages.append(msg)
		for c in other_convs:  # tools / API / human: correctness over throughput
			c.step(c.participants[spk], max_new_tokens=_turn_cap(c, stops[id(c)], c.participants[spk]))
		for c in list(active):  # drop conversations whose stop condition has now fired
			s = stops[id(c)]
			if s is not None and len(c.transcript) and s.should_stop(c, c.transcript[-1]):
				active.remove(c)
		i += 1
	return convs
