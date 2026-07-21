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

"""Episode drivers: play ``Scenario`` instances through ``Participant``s.

The scenario is a pure state machine (it emits ``SeatRequest``s and consumes text); the engine owns everything
around it — driving the participant, per-episode persistence (atomic write after every applied wave), the
one-retry rule, forked provisional elicitations (whose responses never enter state or any transcript), budget
enforcement, and usage accounting.

Two drivers, two throughput regimes:

- ``EpisodePool`` — episodes as independent ``asyncio`` tasks over any participant (API participants are
  network-bound; each blocking ``generate`` runs in a worker thread, so the pool is fully concurrent and its
  width is bounded by the shared API client's ``max_in_flight``). Fully async and free of shared mutable
  state across episodes, so it also serves as the Inspect solver's engine.
- ``BatchedEpisodePool`` — synchronous co-stepping for **local** model participants: each tick collects the
  pending requests of every live episode and runs them as ONE batched ``generate_batch`` per participant
  (the 5–20× rollout win), with adaptive batch splitting on GPU OOM.

**Budgets are stop conditions, not ad-hoc counters.** An episode's budget is any ``StopCondition``
(``TokenBudget``, ``CostBudget``, a list of both): the engine records each committed turn as an interlens
``Message`` (usage metadata included) on an internal transcript, checks the condition against it, and applies
``turn_cap`` to each generation. When the budget fires, the engine sets ``state['budget_exhausted']`` so the
scenario steers to a forced finalization — the matched-compute semantics from the arena experiments (a solo
baseline gets the team's median token budget, then must answer with what it has).

**Spend is gated by reservation, not post-hoc.** Pass a ``UsageMeter`` and per-job ``estimated_cost``: the
pool claims the estimate *before* launching each episode and settles it after, so N concurrent episodes can
never collectively overrun the meter's budget (in-flight episodes finish; new ones don't start).
"""
from __future__ import annotations

import asyncio
import time
import traceback
from typing import Callable

from ..message import Message
from ..stop import AnyStopCondition, StopCondition
from ..transcript import Transcript
from ..usage import UsageMeter
from .scenario import Scenario
from .schema import Episode, EpisodeStore, Instance, SeatRequest, TurnRecord, new_id
from .views import extract_json, strip_think

# What an empty visible turn is replaced with (a reasoning model can burn its whole cap on hidden thinking;
# an empty message would corrupt other seats' alternating views).
EMPTY_TURN_PLACEHOLDER = "(ran out of time this turn and says nothing substantive)"


class _BudgetLedger:
	"""A minimal ``Conversation``-shaped object for ``StopCondition``s: just a transcript of the episode's
	committed turns (as ``Message``s carrying usage metadata), so ``TokenBudget``/``CostBudget`` read spend
	from the same source of truth they use on real conversations."""

	def __init__(self):
		self.transcript = Transcript()


def _participant_model_id(participant) -> str:
	return getattr(participant, "model_id", "") or getattr(participant, "model_name", "") or participant.name


def _gen_provenance(participant) -> dict:
	"""Provenance recorded on every episode: where the turns came from and under what sampling config."""
	out = {"participant": type(participant).__name__, "model": _participant_model_id(participant)}
	for key in ("provider", "temperature", "top_p", "max_tokens", "max_new_tokens", "turn_token_floor", "batch"):
		value = getattr(participant, key, None)
		if value is not None:
			out[key] = value
	return out


class EpisodeRun:
	"""Per-episode bookkeeping shared by both drivers: state stepping, turn recording, budget checks,
	retries, and finalization. Driver-agnostic — it never talks to a participant itself."""

	def __init__(self, scenario: Scenario, instance: Instance, arm: str, participant, seed: int,
	             store: EpisodeStore | None, *, cfg: dict | None = None, gen_config: dict | None = None,
	             budget: StopCondition | list | None = None):
		self.scenario = scenario
		self.instance = instance
		self.participant = participant
		cfg = dict(cfg or {})
		self.ep = Episode(
			episode_id=new_id(f"{scenario.name}-{arm}"),
			scenario=scenario.name, arm=arm, model=_participant_model_id(participant),
			level=instance.level, instance_id=instance.instance_id, seed=seed, seats=[],
			cell=cfg.get("cell", "base"), cell_cfg=cfg,
			gen_config=_gen_provenance(participant) | dict(gen_config or {}),
		)
		try:
			self.state = scenario.make_state(instance, arm, seed, cfg=cfg)
		except TypeError:  # scenarios without sweep-cfg support
			self.state = scenario.make_state(instance, arm, seed)
		if cfg and self.state.get("personas"):
			self.ep.cell_cfg = cfg | {"personas_resolved": self.state["personas"]}
		self.ep.seats = scenario.seat_specs(self.state)
		self.store = store
		self.budget = self._resolve_budget(budget)
		self.ledger = _BudgetLedger()
		self.retries: set[tuple] = set()
		self._turn_idx = 0

	@staticmethod
	def _resolve_budget(budget) -> StopCondition | None:
		if budget is None:
			return None
		if isinstance(budget, (list, tuple)):
			budget = AnyStopCondition(list(budget))
		budget.reset()
		return budget

	# --- stepping ------------------------------------------------------------------------------------------

	def pending(self) -> list[SeatRequest]:
		if self.state.get("done"):
			return []
		requests = self.scenario.next_requests(self.state)
		for r in requests:
			r.episode_id = self.ep.episode_id
		return requests

	def turn_cap(self, request: SeatRequest) -> int:
		"""The output cap for one generation: the request's own cap, shrunk by the budget's ``turn_cap`` (a
		``TokenBudget`` lands the final turn on budget). A participant-level ``turn_token_floor`` may raise it
		back — the thinking-aware tradeoff documented on ``APIParticipant``."""
		cap = request.max_tokens
		if self.budget is not None:
			budget_cap = self.budget.turn_cap(self.ledger)
			if budget_cap is not None:
				cap = min(cap, max(1, budget_cap))
		return cap

	def record_turn(self, request: SeatRequest, message: Message, cap: int = 0) -> dict | None:
		"""Commit one generated turn: strip any leaked reasoning, apply it to the scenario state, log the
		``TurnRecord``, accumulate usage, and check the budget. Returns the scenario's retry directive, if any."""
		raw = message.metadata.get("raw_completion") or message.content
		think = message.metadata.get("parsed_think")
		# Defensive re-strip: a generation truncated mid-<think> can reach content with reasoning attached,
		# which would leak private reasoning into other seats' views.
		text, stripped_think = strip_think(message.content)
		think = think or stripped_think
		if not text.strip():
			text = EMPTY_TURN_PLACEHOLDER
		directive = self.scenario.apply(self.state, request, text)
		parsed, ok = self.state.get("_last_parse", (None, False))
		tokens_out = int(message.metadata.get("n_tokens") or 0)
		tokens_in = int(message.metadata.get("n_tokens_in") or 0)
		self.ep.turns.append(TurnRecord(
			idx=self._turn_idx, round=request.round, phase=request.phase, seat=request.seat,
			content=text, parsed_action=parsed, parse_ok=ok,
			n_tokens_out=tokens_out, n_tokens_in=tokens_in,
			stop_reason=message.metadata.get("stop_reason"),
			cap=cap,
			raw=(raw if raw != text or think else None),
		))
		self._turn_idx += 1
		self.ep.tokens_in += tokens_in
		self.ep.tokens_out += tokens_out
		self.ep.cost_usd += float(message.metadata.get("cost_usd") or 0.0)
		# budget check on the committed turn (message metadata is the source of truth for spend)
		self.ledger.transcript.messages.append(message)
		if self.budget is not None and self.budget.should_stop(self.ledger, message):
			self.state["budget_exhausted"] = True
		return directive

	def record_provisional(self, request: SeatRequest, message: Message, parsed, score) -> None:
		self.ep.round_checkpoints.append({
			"round": request.round, "seat": request.seat,
			"provisional_action": parsed, "score": score,
			"content": message.content,
		})
		self.ep.tokens_in += int(message.metadata.get("n_tokens_in") or 0)
		self.ep.tokens_out += int(message.metadata.get("n_tokens") or 0)
		self.ep.cost_usd += float(message.metadata.get("cost_usd") or 0.0)

	def score_provisional(self, message: Message) -> tuple:
		parsed = extract_json(message.content)
		if hasattr(self.scenario, "score_provisional_text"):
			score = self.scenario.score_provisional_text(self.state, message.content)
		else:
			score = self.scenario.score_provisional(self.state, parsed)
		return parsed, score

	def allow_retry(self, request: SeatRequest) -> bool:
		key = (request.seat, request.round, request.phase)
		if key in self.retries:
			return False
		self.retries.add(key)
		return True

	@staticmethod
	def retry_request(request: SeatRequest, prior_text: str, retry_prompt: str) -> SeatRequest:
		return SeatRequest(
			episode_id=request.episode_id, seat=request.seat,
			view=request.view + [{"role": "assistant", "content": prior_text},
			                     {"role": "user", "content": retry_prompt}],
			phase=request.phase, round=request.round,
			max_tokens=request.max_tokens, meta=request.meta)

	def save(self) -> None:
		if self.store is not None:
			self.store.save(self.ep)

	def finalize(self, error: str | None = None) -> Episode:
		if error:
			self.ep.status = "error"
			self.ep.error = error
		else:
			self.ep.outcome = self.scenario.score(self.state)
			self.ep.rounds_used = self.scenario.rounds_used(self.state)
			self.ep.status = "done"
			# scenario-defined outcome refinement (e.g. the distributed long-context truncation/capitulation
			# classes) — pure in (state, turns, outcome), so replay recomputes it identically
			self.ep.outcome.update(
				self.scenario.classify_outcome(self.state, self.ep.turns, self.ep.outcome) or {})
		self.ep.ended_at = time.time()
		self.save()
		return self.ep


class EpisodePool:
	"""Concurrent episodes as independent asyncio tasks — one participant call at a time per episode, many
	episodes in flight. Each blocking ``Participant.generate`` runs in a worker thread, so hosted-API episodes
	are throughput-bound by the shared client's ``max_in_flight`` cap, not by the event loop.

	``meter`` (a ``UsageMeter``) adds run-level spend control: jobs carrying ``estimated_cost`` are
	reservation-gated (an episode that doesn't fit under the budget is skipped, returned as ``None``), and
	every episode re-checks the meter's ``exhausted`` state when it acquires its concurrency slot, so spend
	accumulated while it queued genuinely stops it from starting."""

	def __init__(self, store: EpisodeStore | None = None, *, meter: UsageMeter | None = None,
	             max_concurrent: int = 32):
		self.store = store
		self.meter = meter
		self._sem = asyncio.Semaphore(max_concurrent)  # concurrent EPISODES (generation width is the client's)

	async def _generate(self, participant, request: SeatRequest, cap: int) -> Message:
		return await asyncio.to_thread(participant.generate, request.view, max_new_tokens=cap)

	async def run_episode(self, scenario: Scenario, instance: Instance, arm: str, participant, *,
	                      seed: int = 0, cfg: dict | None = None, gen_config: dict | None = None,
	                      budget: StopCondition | list | None = None,
	                      estimated_cost: float | None = None,
	                      gate: Callable[[], bool] | None = None) -> Episode | None:
		"""Play one episode to completion. Returns the ``Episode`` (status ``done`` or ``error``), or ``None``
		when the episode never started: its cost reservation didn't fit under the meter's budget, the meter was
		already exhausted, or ``gate()`` returned True. The launch gates are evaluated once the episode acquires
		a concurrency slot (``max_concurrent`` bounds episodes in flight), so a queued episode really is stopped
		by spend that accumulated while it waited — in-flight episodes finish, new ones don't start."""
		async with self._sem:
			if gate is not None and gate():
				return None
			if self.meter is not None and self.meter.exhausted:
				return None
			if self.meter is not None and estimated_cost is not None:
				if not self.meter.reserve(estimated_cost):
					return None
			try:
				run = EpisodeRun(scenario, instance, arm, participant, seed, self.store,
				                 cfg=cfg, gen_config=gen_config, budget=budget)
				try:
					while True:
						requests = run.pending()
						if not requests:
							break
						for request in requests:
							cap = run.turn_cap(request)
							message = await self._generate(participant, request, cap)
							directive = run.record_turn(request, message, cap=cap)
							while directive and "retry" in directive and run.allow_retry(request):
								retry = run.retry_request(request, message.content, directive["retry"])
								cap = run.turn_cap(retry)
								message = await self._generate(participant, retry, cap)
								directive = run.record_turn(retry, message, cap=cap)
						# forked provisional elicitations (state is never mutated by their responses)
						for provisional in scenario.provisional_due(run.state):
							provisional.episode_id = run.ep.episode_id
							message = await self._generate(participant, provisional, provisional.max_tokens)
							parsed, score = run.score_provisional(message)
							run.record_provisional(provisional, message, parsed, score)
						run.save()
					return run.finalize()
				except Exception:
					return run.finalize(error=traceback.format_exc()[-2000:])
			finally:
				if self.meter is not None and estimated_cost is not None:
					self.meter.settle(estimated_cost)

	async def run_pool(self, jobs: list[dict], stop_check: Callable[[], bool] | None = None) -> list[Episode]:
		"""Run many episodes concurrently (``max_concurrent`` in flight). Each job is the ``run_episode``
		kwargs (``{scenario, instance, arm, participant, seed?, cfg?, gen_config?, budget?, estimated_cost?}``).
		``stop_check() -> bool`` and the meter's ``exhausted`` state are evaluated when each episode acquires
		its slot — not at submission — so once either fires, queued episodes are skipped while in-flight ones
		finish. Skipped episodes are omitted from the result."""
		tasks = [asyncio.create_task(self.run_episode(**job, gate=stop_check)) for job in jobs]
		results = [await t for t in tasks]
		return [ep for ep in results if ep is not None]


class BatchedEpisodePool:
	"""Synchronous co-stepping for local model participants: each tick gathers every live episode's pending
	requests and runs them as one batched ``generate_batch`` per participant — the local-GPU throughput path.

	On CUDA OOM (or the transient cuDNN graph errors long co-stepped batches produce), the wave is split and
	retried down to single episodes; a single episode whose context alone OOMs yields a placeholder empty turn
	so the pool keeps moving."""

	def __init__(self, store: EpisodeStore | None = None):
		self.store = store

	def run_pool(self, jobs: list[dict], progress: Callable[[int, int], None] | None = None) -> list[Episode]:
		runs = [EpisodeRun(j["scenario"], j["instance"], j["arm"], j["participant"],
		                   j.get("seed", 0), self.store, cfg=j.get("cfg"),
		                   gen_config=j.get("gen_config"), budget=j.get("budget")) for j in jobs]
		live = {r.ep.episode_id: r for r in runs}
		tick = 0
		while live:
			wave: list[tuple[EpisodeRun, SeatRequest]] = []
			for run in list(live.values()):
				try:
					requests = run.pending()
				except Exception:
					run.finalize(error=traceback.format_exc()[-2000:])
					del live[run.ep.episode_id]
					continue
				if not requests:
					run.finalize()
					del live[run.ep.episode_id]
					continue
				wave.extend((run, request) for request in requests)
			if not wave:
				break
			by_participant: dict[int, list[tuple[EpisodeRun, SeatRequest]]] = {}
			for run, request in wave:
				by_participant.setdefault(id(run.participant), []).append((run, request))
			for pairs in by_participant.values():
				participant = pairs[0][0].participant
				capped = [(r.turn_cap(q), q) for r, q in pairs]
				messages = self._generate_batch(participant, capped)
				for (run, request), (cap, _q), message in zip(pairs, capped, messages):
					try:
						directive = run.record_turn(request, message, cap=cap)
						if directive and "retry" in directive and run.allow_retry(request):
							retry = run.retry_request(request, message.content, directive["retry"])
							retry_cap = run.turn_cap(retry)
							retry_message = self._generate_batch(participant, [(retry_cap, retry)])[0]
							run.record_turn(retry, retry_message, cap=retry_cap)
					except Exception:
						run.finalize(error=traceback.format_exc()[-2000:])
						live.pop(run.ep.episode_id, None)
			# provisional elicitations, batched per participant as well
			for pairs in by_participant.values():
				participant = pairs[0][0].participant
				provisionals: list[tuple[EpisodeRun, SeatRequest]] = []
				seen: set[str] = set()
				for run, _request in pairs:
					if run.ep.episode_id in seen or run.ep.episode_id not in live:
						continue
					seen.add(run.ep.episode_id)
					for provisional in run.scenario.provisional_due(run.state):
						provisional.episode_id = run.ep.episode_id
						provisionals.append((run, provisional))
				if provisionals:
					messages = self._generate_batch(participant,
					                                [(q.max_tokens, q) for _r, q in provisionals])
					for (run, provisional), message in zip(provisionals, messages):
						parsed, score = run.score_provisional(message)
						run.record_provisional(provisional, message, parsed, score)
			for run in live.values():
				run.save()
			tick += 1
			if progress is not None:
				progress(tick, len(live))
		return [r.ep for r in runs]

	def _generate_batch(self, participant, capped_requests: list[tuple[int, SeatRequest]]) -> list[Message]:
		"""One batched generate over the wave, surviving OOM / transient cuDNN graph errors by splitting and
		retrying down to single requests. Long multi-agent transcripts make peak KV vary across a co-stepped
		batch, so no fixed width is safe everywhere; back off on demand."""
		if not capped_requests:
			return []
		cap = max(c for c, _q in capped_requests)
		views = [q.view for _c, q in capped_requests]
		try:
			return participant.generate_batch(views, max_new_tokens=cap)
		except RuntimeError as e:
			text = str(e).lower()
			transient = ("out of memory" in text or "mha_graph" in text
			             or "cudnn" in text or "is_good()" in text)
			if not transient:
				raise
			try:
				import torch
				torch.cuda.empty_cache()
			except Exception:
				pass
			if len(capped_requests) == 1:
				# one episode's context is too large even alone: emit an empty turn so the pool keeps moving
				return [Message(author=participant.name, content=EMPTY_TURN_PLACEHOLDER,
				                metadata={"n_tokens": 0, "oom_skip": True})]
			mid = len(capped_requests) // 2
			return (self._generate_batch(participant, capped_requests[:mid])
			        + self._generate_batch(participant, capped_requests[mid:]))
