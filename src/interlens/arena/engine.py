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

**A failed generation is never silent, and the two drivers are equally honest about it.** Both drivers meet the
same cuDNN/OOM faults under load; what differed was only the REPORTING. ``EpisodePool`` always surfaced a failure
as ``status="error"`` with the traceback — legible, and excluded by any "done" filter. ``BatchedEpisodePool``
instead substituted ``EMPTY_TURN_PLACEHOLDER`` and swallowed the exception, and because that placeholder parses
into a well-formed no-op, a cell in which *every* turn had been fabricated still reported ``status="done"`` and
``parse_ok=True`` throughout; the contamination was found months later, from the outcome numbers.

So the batched driver now recovers from a transient fault by splitting the wave and then retrying the lone
request, and only if that also fails does it fabricate — at which point it logs at ERROR, stamps
``TurnRecord.gen_failed`` with the causing exception, counts it, and RAISES
``GenerationFailureBudgetExceeded`` once such turns exceed ``max_fabricated_fraction`` of the run. A
non-transient error is a bug and always propagates; it is never converted into a turn. Screen stored episodes
with ``gen_failures(episode)`` (it also handles pre-stamp records) and read a run's totals from
``BatchedEpisodePool.fabrication_report()``.

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
import logging
import time
import traceback
from typing import Callable

from ..message import Message
from ..stop import AnyStopCondition, StopCondition
from ..transcript import Transcript
from ..usage import UsageMeter
from .oracles import OracleRecord
from .refusal import REFUSAL_RECOVERY_KEY, RefusalLadder, is_refusal, recovery_record
from .scenario import Scenario
from .schema import Episode, EpisodeStore, Instance, SeatRequest, TurnRecord, new_id
from .views import extract_json, strip_think

# What an empty visible turn is replaced with (a reasoning model can burn its whole cap on hidden thinking;
# an empty message would corrupt other seats' alternating views).
#
# AUDITING GOTCHA — do NOT screen for this failure with ``parse_ok`` or "is the content empty?". Both are
# fooled: this placeholder is a non-empty string that parses cleanly into a well-formed no-op action, so a
# transcript where the model said nothing on most turns reports ``parse_ok=True`` and non-empty content
# throughout. The honest detectors are ``TurnRecord.stop_reason == "max_tokens"`` and a parsed action whose
# type is the no-op ("none"). Measured on claude-opus-5 with adaptive thinking at a 2,048-token per-turn cap:
# 67% of turns were this placeholder and the episode advanced zero rounds, while a naive parse_ok screen
# called the run clean. See the sibling note on APIParticipant.turn_token_floor for the two controls.
EMPTY_TURN_PLACEHOLDER = "(ran out of time this turn and says nothing substantive)"

logger = logging.getLogger(__name__)

# The metadata keys by which a failed generation travels from the driver that fabricated the turn to
# ``EpisodeRun.record_turn``, which stamps them onto the ``TurnRecord``. Named constants because the producer
# (``BatchedEpisodePool._generate_batch``) and the consumer (``record_turn``) are far apart in this file, and a
# typo in either would silently restore the invisible-failure bug this stamp exists to prevent.
GEN_FAILED_KEY = "gen_failed"
GEN_FAILURE_KEY = "gen_failure"

# How many times the batched driver re-attempts a SINGLE request that failed transiently, after batch splitting
# has already narrowed the wave to that one request, before giving up and fabricating a turn. The failures worth
# retrying here are transient by construction (a cuDNN graph blip, a fragmentation-driven OOM that
# ``empty_cache`` may clear), so a couple of cheap attempts rescue them; a context that genuinely does not fit
# will fail all of them and cost only milliseconds.
SINGLE_REQUEST_RETRIES = 2

# Default ceiling on the fraction of a pool's turns the engine may fabricate before it gives up and RAISES
# instead of returning a run full of turns no model ever produced. 10% is already far beyond anything a healthy
# run produces (a healthy run fabricates zero), so tripping this means the run is not measuring model behaviour.
MAX_FABRICATED_FRACTION = 0.10

# The fabrication fraction is only consulted once this many turns have been attempted, so a single transient blip
# in the opening wave of a small run cannot trip a 10% ceiling on a denominator of one or two.
FABRICATION_FLOOR = 20


class GenerationFailureBudgetExceeded(RuntimeError):
	"""Raised by :class:`BatchedEpisodePool` when it has had to fabricate more turns than its budget allows.

	The alternative — which this replaces — is a run that completes, reports ``status="done"`` and
	``parse_ok=True`` on every turn, and contains no model behaviour whatsoever. A campaign cell has been
	observed at 100% fabricated turns while reporting clean. Failing loudly in the first seconds is strictly
	better than discovering it in the analysis, so the budget defaults to ON."""


def _is_transient_gpu_error(error: Exception) -> bool:
	"""Whether a backend ``RuntimeError`` is the kind worth backing off and retrying rather than propagating:
	a CUDA OOM, or the cuDNN graph errors long co-stepped batches produce. Matched on the message because the
	backend raises all of them as plain ``RuntimeError``. One home, so the split path and the single-request
	retry path can never disagree about what counts as transient."""
	text = str(error).lower()
	return ("out of memory" in text or "mha_graph" in text or "cudnn" in text or "is_good()" in text)


def _serving_participant(participant, seat: str | None):
	"""The participant that will actually generate ``seat``'s turn — the batching key for a co-stepped wave.

	A **pure-dispatch** table (one declaring ``participant_for``, i.e. :class:`~interlens.arena.table.SeatRouter`)
	is resolved to the sub-participant owning the seat, because addressing it directly is semantically identical to
	going through the table and it is the only way a heterogeneous lineup batches at all: every episode holds its
	own table, so keying on the table would put a single request in each group.

	Anything else is returned unchanged — a plain model participant (there is nothing to resolve) and, crucially,
	a table that REWRITES the view per seat, such as a planner/advocate wrapper. Those deliberately do not declare
	``participant_for``, so the wave stays addressed to the wrapper and its per-seat conditioning still runs.
	Resolution failures (an unknown seat) also fall back to the table, so the table's own error handling reports
	the problem rather than this helper masking it."""
	resolve = getattr(participant, "participant_for", None)
	if resolve is None or seat is None:
		return participant
	try:
		return resolve(seat)
	except Exception:
		return participant


def _empty_cuda_cache() -> None:
	"""Best-effort ``torch.cuda.empty_cache()`` — what makes a fragmentation-driven OOM worth retrying at all.
	Silent no-op without torch or a GPU, so the engine stays importable on CPU-only machines."""
	try:
		import torch
		torch.cuda.empty_cache()
	except Exception:
		pass


def gen_failures(episode) -> list[dict]:
	"""Every turn of an episode whose text the ENGINE fabricated because generation failed.

	``episode`` is an :class:`~interlens.arena.schema.Episode` or its ``to_json()`` dict. Returns a list of
	``{"idx", "round", "seat", "phase", "reason", "detected_by"}``, one per fabricated turn.

	Use this rather than hand-rolling a screen, because the honest test depends on when the episode was recorded:

	- **v1.2 and later** carry an explicit ``gen_failed`` stamp (``detected_by="stamp"``), which also records the
	  exception that caused it.
	- **Older episodes** have no stamp, so they fall back to the legacy value signature
	  (``detected_by="legacy_signature"``): content is exactly :data:`EMPTY_TURN_PLACEHOLDER`, zero output
	  tokens, AND ``raw is None``.

	The legacy fallback is a conjunction, and it is worth being precise about which clause does what, because
	getting this wrong in either direction has already happened:

	- ``content == EMPTY_TURN_PLACEHOLDER`` does the discriminating work. ``raw is None`` **alone is useless** on
	  local runs — a local non-thinking model's raw completion equals its content, so ``record_turn`` stores
	  ``raw=None`` for essentially every healthy turn too (measured: all 2,683 turns of a clean 32B cell).
	- ``raw is None`` is a GUARD, not the detector. Its job is to exclude the other producer of the same
	  placeholder: a model that genuinely returned empty or reasoning-only text, which ``record_turn`` also
	  replaces with the placeholder but for which ``raw`` holds the non-placeholder text it actually got. That is
	  real model behaviour (a thinking model burning its cap) and a different problem with a different fix, so it
	  must not be counted as an engine failure.

	Because the stamp exists from v1.2 on, this fallback is only for pre-stamp records — do not build new tooling
	on it. And do NOT screen with ``parse_ok`` or "is the content empty": the placeholder is a non-empty string
	that parses into a well-formed no-op action, so a fully fabricated episode passes both."""
	d = episode if isinstance(episode, dict) else episode.to_json()
	out = []
	for t in d.get("turns") or []:
		stamped = bool(t.get(GEN_FAILED_KEY))
		legacy = (GEN_FAILED_KEY not in t
				  and t.get("content") == EMPTY_TURN_PLACEHOLDER
				  and not t.get("n_tokens_out")
				  and t.get("raw") is None)
		if stamped or legacy:
			out.append({"idx": t.get("idx"), "round": t.get("round"), "seat": t.get("seat"),
						"phase": t.get("phase"),
						"reason": t.get(GEN_FAILURE_KEY) or "(not recorded: episode predates the stamp)",
						"detected_by": "stamp" if stamped else "legacy_signature"})
	return out


# The per-turn failure signatures :func:`turn_signatures` can report. Ordered as a reader wants them: the
# placeholder and its two causes, then the cap hit, then the two symptoms that are proxies rather than causes.
TURN_SIGNATURES = ("placeholder", "gen_failed", "empty_gen", "truncated", "noop_action", "parse_failed")

# Provider stop reasons that mean the generation was cut off at the cap rather than finishing.
TRUNCATED_STOPS = frozenset({"max_tokens", "length"})


def turn_signatures(turn: dict, *, engine_fabricated: bool | None = None) -> set[str]:
	"""Every failure signature carried by one stored turn (a ``TurnRecord.to_json()`` dict); ``set()`` if healthy.

	:func:`gen_failures` answers one question — did the ENGINE fabricate this turn — and a run can be perfectly
	clean by that measure while a quarter of its turns say nothing. This separates the causes that wear the same
	:data:`EMPTY_TURN_PLACEHOLDER` string, because each needs a different fix:

	- ``placeholder`` — the turn's content IS the placeholder. Always accompanied by exactly one cause below.
	- ``gen_failed`` — the engine fabricated it (no model was ever successfully called). ``engine_fabricated``
	  is the authority when given; :func:`gen_failures` computes it, reading the v1.2 ``gen_failed`` stamp and
	  falling back to the value signature only on older records. Raising the token cap CANNOT fix this.
	- ``empty_gen`` — generation really happened but reduced to nothing after ``strip_think``: the model spent
	  its whole budget inside an unterminated ``<think>`` block and emitted no visible action. This IS model
	  behaviour and the fix is a larger cap or thinking disabled. **Measured at 24.4% of turns for a thinking-on
	  Qwen3-32B at a 2,048-token cap, against 0.0% with thinking off**, while ``fabrication`` correctly read
	  0.000 throughout — the engine did its job and a quarter of the turns were still silent.
	- ``truncated`` — a genuine cap hit. Note that local ``ModelParticipant``\\ s never populate ``stop_reason``,
	  so on local runs the ``n_tokens_out >= cap`` clause is the only one that fires; a ``cap`` of 0 means
	  "unrecorded" in the schema and never counts as truncation.
	- ``noop_action`` / ``parse_failed`` — behavioural symptoms reported alongside, NOT causes. ``noop_action``
	  also fires on legitimate no-op play, and on some placeholder turns does not fire at all.

	Do NOT screen for any of this with ``parse_ok`` or "is the content empty". Both are fooled: the placeholder
	is a non-empty string that parses into a well-formed no-op, and on a degraded cell ``parse_ok`` is
	*anti*-correlated with turn quality (measured 1.000 on the silent arm against 0.958 on the healthy one,
	because placeholders parse flawlessly and real model prose sometimes does not)."""
	tags: set[str] = set()
	content = turn.get("content") or ""
	tokens = int(turn.get("n_tokens_out") or 0)
	cap = int(turn.get("cap") or 0)
	if turn.get("stop_reason") in TRUNCATED_STOPS or (cap and tokens >= cap):
		tags.add("truncated")
	if EMPTY_TURN_PLACEHOLDER in content:
		tags.add("placeholder")
		# `raw is None` is a GUARD, not the detector — see gen_failures' docstring. Prefer the caller's verdict,
		# which reads the v1.2 stamp; the value signature is the pre-stamp fallback.
		fabricated = (engine_fabricated if engine_fabricated is not None
		              else (tokens == 0 and turn.get("raw") is None))
		tags.add("gen_failed" if fabricated else "empty_gen")
	if ((turn.get("parsed_action") or {}) or {}).get("atype") == "none":
		tags.add("noop_action")
	if not turn.get("parse_ok"):
		tags.add("parse_failed")
	return tags


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
	             budget: StopCondition | list | None = None,
	             capture=None, steering=None, patch=None, record_views: bool = True):
		self.scenario = scenario
		self.instance = instance
		self.participant = participant
		# Record each committed turn's rendered view (the ground-truth prompt) into its TurnRecord (text is
		# cheap); a pool can disable it for a lean run.
		self.record_views = record_views
		# Per-episode interp hooks threaded into each committed turn's generation (local models only; forked
		# provisional probes are left clean). ``capture`` tags activations by this run's turn index.
		self.capture = capture
		self.steering = steering
		self.patch = patch
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
		# The turn's reasoning record: hosted providers set reasoning/reasoning_provenance in metadata; a
		# locally parsed/stripped <think> stream is complete by construction ("full").
		reasoning = message.metadata.get("reasoning") or think or None
		provenance = message.metadata.get("reasoning_provenance") or ("full" if reasoning else "none")
		self.ep.turns.append(TurnRecord(
			idx=self._turn_idx, round=request.round, phase=request.phase, seat=request.seat,
			content=text, parsed_action=parsed, parse_ok=ok,
			n_tokens_out=tokens_out, n_tokens_in=tokens_in,
			stop_reason=message.metadata.get("stop_reason"),
			cap=cap,
			raw=(raw if raw != text or think else None),
			reasoning=reasoning, reasoning_provenance=provenance,
			reasoning_tokens=int(message.metadata.get("reasoning_tokens") or 0),
			# A participant wrapper may add private, per-turn decision support after the scenario creates the
			# request. Persist the exact post-wrapper view when supplied; otherwise keep the scenario view.
			view=(message.metadata.get("conditioned_view", request.view) if self.record_views else None),
			# Carry a driver's generation-failure stamp onto the record. The turn is still applied to the state
			# (the scenario reads the placeholder as a no-op, so the pool keeps moving), but it is now marked as
			# text NO MODEL PRODUCED, so no downstream analysis can mistake it for behaviour.
			gen_failed=bool(message.metadata.get(GEN_FAILED_KEY)),
			gen_failure=message.metadata.get(GEN_FAILURE_KEY),
			refusal_recovery=message.metadata.get(REFUSAL_RECOVERY_KEY),
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
		self.ep.round_checkpoints.append(OracleRecord.provisional(
			round=request.round, seat=request.seat,
			provisional_action=parsed, score=score, content=message.content).to_json())
		self.ep.tokens_in += int(message.metadata.get("n_tokens_in") or 0)
		self.ep.tokens_out += int(message.metadata.get("n_tokens") or 0)
		self.ep.cost_usd += float(message.metadata.get("cost_usd") or 0.0)

	def annotate(self, request: SeatRequest) -> None:
		"""Run the scenario's inline oracles over the turn just committed and append their typed
		``OracleRecord``s to the episode's oracle log. A no-op unless the scenario overrides ``annotate_turn``
		(pure-Python — no extra generation), so scenarios without an oracle stack are unaffected."""
		if not self.ep.turns:
			return
		for record in self.scenario.annotate_turn(self.state, request, self.ep.turns[-1]) or []:
			self.ep.round_checkpoints.append(record.to_json())

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
	             max_concurrent: int = 32, record_views: bool = True,
	             refusal_ladder: RefusalLadder | None = None, wave_parallel: bool = True):
		self.store = store
		self.meter = meter
		self.record_views = record_views   # persist each turn's rendered view into its TurnRecord (default on)
		# Issue a simultaneous-move wave's generations concurrently rather than one seat after another (default
		# on). See ``_generate_wave`` for exactly when it applies and why it cannot change what any seat reads.
		self.wave_parallel = wave_parallel
		# On an API-side refusal (``stop_reason="refusal"``, zero output tokens), re-render the SAME turn under
		# this ladder's content-preserving perturbations and reissue, escalating rung by rung. Off by default,
		# because it is a protocol commitment a campaign must preregister rather than acquire silently; pass
		# ``RefusalLadder()`` to enable it. See ``arena/refusal.py``.
		self.refusal_ladder = refusal_ladder
		self._sem = asyncio.Semaphore(max_concurrent)  # concurrent EPISODES (generation width is the client's)

	async def _generate_once(self, participant, view: list[dict], request: SeatRequest, cap: int, *,
	                         capture=None, steering=None, patch=None, turn: int | None = None) -> Message:
		# ``seat`` is always passed: a participant fronting several seats needs the request's own seat identity
		# rather than having to recover it from the prompt wording.
		kwargs: dict = {"max_new_tokens": cap, "seat": request.seat}
		if steering is not None:
			kwargs["steering"] = steering
		if patch is not None:
			kwargs["patch"] = patch
		if capture is not None:
			kwargs["capture"] = capture
			kwargs["turn"] = turn
		return await asyncio.to_thread(lambda: participant.generate(view, **kwargs))

	async def _generate(self, participant, request: SeatRequest, cap: int, *,
	                    capture=None, steering=None, patch=None, turn: int | None = None) -> Message:
		"""One turn's generation, with refusal recovery when a ``refusal_ladder`` is installed.

		An API-side refusal reproduces deterministically for byte-identical requests, so the ordinary retry
		(same view plus a parser note) cannot clear it. When one arrives, the ladder re-renders the same view
		under a content-preserving perturbation — nonce line, seeded block permutation, alternate section
		framing — and reissues, escalating rung by rung until a completion comes back or the rungs run out.
		The turn that is committed is the one that generated; its exact re-rendered view is recorded as
		``conditioned_view`` so the transcript shows what the seat actually read, and
		``metadata[REFUSAL_RECOVERY_KEY]`` records which rung cleared it (or that none did)."""
		kw = dict(capture=capture, steering=steering, patch=patch, turn=turn)
		message = await self._generate_once(participant, request.view, request, cap, **kw)
		if self.refusal_ladder is None or not is_refusal(message):
			return message
		ladder, attempts = self.refusal_ladder, []
		key = f"{request.episode_id}/{request.seat}/{request.round}/{request.phase}"
		for rung in range(1, len(ladder) + 1):
			view = ladder.perturb(request.view, rung, key=key)
			attempts.append(ladder.rung_name(rung))
			message = await self._generate_once(participant, view, request, cap, **kw)
			if not is_refusal(message):
				message.metadata[REFUSAL_RECOVERY_KEY] = recovery_record("recovered", rung, attempts)
				message.metadata["conditioned_view"] = view
				logger.info("refusal recovered at rung %d (%s) for %s", rung, ladder.rung_name(rung), key)
				return message
		message.metadata[REFUSAL_RECOVERY_KEY] = recovery_record("terminal", None, attempts)
		message.metadata["conditioned_view"] = view
		logger.warning("refusal NOT recovered after %d rungs (%s) for %s", len(ladder), ",".join(attempts), key)
		return message

	def _wave_is_parallelizable(self, run: EpisodeRun, requests: list[SeatRequest]) -> bool:
		"""Whether this wave's generations may be issued concurrently instead of one seat after another.

		Three conditions, each of which is the thing that would otherwise make concurrency observable:

		- **More than one request.** A one-request wave has nothing to overlap.
		- **No interp hooks.** ``capture`` tags activations by ``run._turn_idx``, which is only well defined
		  when turns are generated in the order they are committed; ``steering``/``patch`` are local-model paths
		  where the throughput lever is :class:`BatchedEpisodePool` anyway. So a hooked episode stays serial.
		- **No episode budget.** :meth:`EpisodeRun.turn_cap` reads the budget against the ledger of turns
		  *already committed*, so under a ``TokenBudget(per_conversation=...)`` the second seat of a serial wave
		  is capped by what the first seat just spent. Computing every cap at wave start would be a different
		  (and arguably more correct, since the seats move simultaneously) rule, but it is not the same rule, so
		  a budgeted episode falls back to serial rather than quietly changing its own caps.

		What is deliberately NOT on this list is the scenario: a wave's views are all built by
		``next_requests`` *before* any of them is sent, and a ``SeatRequest`` carries its rendered ``view``, so
		no seat in a wave can read another seat's reply however the generations are ordered. That is a property
		of the ``SeatRequest`` contract, not of any one scenario. Turns are still recorded in request order, so
		the stored episode is identical regardless of which generation returns first."""
		return (self.wave_parallel and len(requests) > 1
		        and run.capture is None and run.steering is None and run.patch is None
		        and run.budget is None)

	async def _generate_wave(self, run: EpisodeRun, requests: list[SeatRequest],
	                         caps: list[int]) -> list[Message]:
		"""Every request of one wave generated concurrently, returned **in request order**.

		Each element goes through the same :meth:`_generate` as the serial path, so the refusal ladder, its
		per-turn recovery record, and usage accounting are unchanged. Concurrency here multiplies the requests
		in flight by the wave width; the shared API client's ``max_in_flight`` (or an installed rate-limit
		governor) is what actually bounds them, exactly as it bounds concurrent episodes."""
		return list(await asyncio.gather(*(
			self._generate(run.participant, request, cap) for request, cap in zip(requests, caps))))

	async def run_episode(self, scenario: Scenario, instance: Instance, arm: str, participant, *,
	                      seed: int = 0, cfg: dict | None = None, gen_config: dict | None = None,
	                      budget: StopCondition | list | None = None,
	                      estimated_cost: float | None = None,
	                      capture=None, steering=None, patch=None,
	                      gate: Callable[[], bool] | None = None) -> Episode | None:
		"""Play one episode to completion. Returns the ``Episode`` (status ``done`` or ``error``), or ``None``
		when the episode never started: its cost reservation didn't fit under the meter's budget, the meter was
		already exhausted, or ``gate()`` returned True. The launch gates are evaluated once the episode acquires
		a concurrency slot (``max_concurrent`` bounds episodes in flight), so a queued episode really is stopped
		by spend that accumulated while it waited — in-flight episodes finish, new ones don't start.

		``capture`` / ``steering`` / ``patch`` are per-turn interp hooks threaded into every committed
		generation (local ``ModelParticipant`` only — API/scripted participants raise on interp requests);
		``capture`` (a ``CaptureRequest``) tags activations by this episode's turn index, so per-turn activation
		capture *inside* a structured episode works. Forked provisional probes are left clean (no capture/steer)."""
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
				                 cfg=cfg, gen_config=gen_config, budget=budget,
				                 capture=capture, steering=steering, patch=patch,
				                 record_views=self.record_views)
				try:
					while True:
						requests = run.pending()
						if not requests:
							break
						# A simultaneous-move wave is issued concurrently when nothing in the episode depends on
						# generation ORDER (see _wave_is_parallelizable) — the ~wave-width wall-clock win on
						# hosted seats. Turns are committed in request order either way, so the stored episode
						# does not depend on which generation returns first.
						if self._wave_is_parallelizable(run, requests):
							caps = [run.turn_cap(q) for q in requests]
							wave: list[Message | None] = list(await self._generate_wave(run, requests, caps))
						else:
							caps, wave = [0] * len(requests), [None] * len(requests)
						for i, request in enumerate(requests):
							if wave[i] is None:
								caps[i] = run.turn_cap(request)
								wave[i] = await self._generate(participant, request, caps[i],
								                               capture=run.capture, steering=run.steering,
								                               patch=run.patch, turn=run._turn_idx)
							cap, message = caps[i], wave[i]
							directive = run.record_turn(request, message, cap=cap)
							while directive and "retry" in directive and run.allow_retry(request):
								retry = run.retry_request(request, message.content, directive["retry"])
								cap = run.turn_cap(retry)
								message = await self._generate(participant, retry, cap, capture=run.capture,
								                               steering=run.steering, patch=run.patch,
								                               turn=run._turn_idx)
								directive = run.record_turn(retry, message, cap=cap)
							# inline pure-Python oracle annotations of the committed turn (no extra generation)
							run.annotate(request)
						# Forked provisional elicitations. Their responses never enter the state, so they are issued
						# together under the same rule as the wave and recorded in request order.
						probes = list(scenario.provisional_due(run.state))
						for provisional in probes:
							provisional.episode_id = run.ep.episode_id
						if self._wave_is_parallelizable(run, probes):
							replies = await self._generate_wave(run, probes, [p.max_tokens for p in probes])
						else:
							replies = [await self._generate(participant, p, p.max_tokens) for p in probes]
						for provisional, message in zip(probes, replies):
							parsed, score = run.score_provisional(message)
							run.record_provisional(provisional, message, parsed, score)
						run.save()
					return run.finalize()
				except Exception:
					# NOT a silent swallow: the episode is finalized with status="error" and the traceback, so it
					# is legible in the store and excluded by any "done" filter. Logged as well, because a run of
					# 120 episodes where a third errored should say so while it is running, not only on inspection.
					logger.exception("episode %s (%s, seat model %s) failed and is recorded as status=error",
					                 run.ep.episode_id, run.ep.arm, run.ep.model)
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
	retried down to single episodes, then that single request is retried a bounded number of times. Only if all of
	that fails does the pool fabricate a placeholder turn so it can keep moving — and a fabricated turn is LOGGED
	at error level and STAMPED (``TurnRecord.gen_failed``), because text no model produced must never be
	mistaken for model behaviour. Past ``max_fabricated_fraction`` of the pool's turns the run RAISES instead.

	Parameters
	----------
	store : EpisodeStore | None
		Where to persist each episode after every applied wave.
	record_views : bool
		Persist each turn's rendered view into its ``TurnRecord`` (default on).
	max_fabricated_fraction : float
		The fraction of attempted turns the engine may fabricate before raising
		:class:`GenerationFailureBudgetExceeded` (default :data:`MAX_FABRICATED_FRACTION`, 10%). A healthy run
		fabricates none, so any nonzero rate is already a defect; the ceiling exists to stop a broken run in its
		first seconds rather than at analysis time. Set it to ``1.0`` to never raise (the old behaviour) — which
		is only defensible if something downstream screens ``gen_failed``.
	fabrication_floor : int
		Attempted turns required before the fraction is consulted (default :data:`FABRICATION_FLOOR`), so one
		transient blip in a tiny run cannot trip the ceiling on a denominator of one.
	single_request_retries : int
		Re-attempts of a lone failing request after splitting has narrowed the wave to it, before fabricating
		(default :data:`SINGLE_REQUEST_RETRIES`).
	"""

	def __init__(self, store: EpisodeStore | None = None, *, record_views: bool = True,
	             max_fabricated_fraction: float = MAX_FABRICATED_FRACTION,
	             fabrication_floor: int = FABRICATION_FLOOR,
	             single_request_retries: int = SINGLE_REQUEST_RETRIES):
		self.store = store
		self.record_views = record_views   # persist each turn's rendered view into its TurnRecord (default on)
		self.max_fabricated_fraction = max_fabricated_fraction
		self.fabrication_floor = fabrication_floor
		self.single_request_retries = single_request_retries
		self.attempted_turns = 0        # requests this pool has tried to generate (the fabrication denominator)
		self.fabricated_turns = 0       # of those, the ones no model ever produced
		self.failures: list[dict] = []  # one record per fabrication: {episode_id, seat, round, phase, reason}
		# The runs of the wave in flight, so that a fabrication-budget abort can finalize them as errored on its
		# way out. Held on the pool because the raise happens deep inside the generate call stack, far from the
		# loop that owns the live set.
		self._abort_runs: list[EpisodeRun] = []

	def fabrication_report(self) -> dict:
		"""How much of this pool's output the engine had to fabricate: ``{attempted, fabricated, fraction,
		failures}``. A caller should log this at the end of a run — ``fraction == 0.0`` is the only healthy
		value, and anything else bounds how much of the run is not model behaviour.

		This is the ONLY complete account of a run's fabrications, and it is why the report exists alongside the
		per-turn stamp. Committed turns carry ``TurnRecord.gen_failed``, but a forked **provisional** probe is
		stored as an ``OracleRecord`` rather than a ``TurnRecord``, so it has nowhere to carry the stamp: a
		fabricated provisional shows up here and in ``failures`` (with ``phase == "provisional"``), and in the
		stored record only as ``content == EMPTY_TURN_PLACEHOLDER``. So ``fabricated`` can legitimately exceed the
		number of ``gen_failed`` turns in the episodes; the difference is fabricated provisional probes, whose
		``score`` should be treated as contaminated."""
		frac = (self.fabricated_turns / self.attempted_turns) if self.attempted_turns else 0.0
		return {"attempted": self.attempted_turns, "fabricated": self.fabricated_turns,
		        "fraction": round(frac, 6), "failures": list(self.failures)}

	def run_pool(self, jobs: list[dict], progress: Callable[[int, int], None] | None = None) -> list[Episode]:
		runs = [EpisodeRun(j["scenario"], j["instance"], j["arm"], j["participant"],
		                   j.get("seed", 0), self.store, cfg=j.get("cfg"),
		                   gen_config=j.get("gen_config"), budget=j.get("budget"),
		                   record_views=self.record_views) for j in jobs]
		live = {r.ep.episode_id: r for r in runs}
		self._abort_runs = runs
		tick = 0
		while live:
			wave: list[tuple[EpisodeRun, SeatRequest]] = []
			for run in list(live.values()):
				try:
					requests = run.pending()
				except Exception:
					logger.exception("episode %s: scenario failed to produce the next requests; "
					                 "recorded as status=error", run.ep.episode_id)
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
			# Group the wave by the participant that will actually SERVE each request, not by the table object
			# fronting it. For a homogeneous table those are the same object. For a heterogeneous one they are
			# not, and the difference is the whole point: every episode gets its OWN table (policy seats hold
			# per-episode state), so grouping by table puts one request in each group and batches nothing,
			# while grouping by owner collects the model seats of every live episode — which do share one
			# cached model participant — into a single real batch. See ``SeatRouter.participant_for``.
			by_participant: dict[int, tuple[object, list[tuple[EpisodeRun, SeatRequest]]]] = {}
			for run, request in wave:
				target = _serving_participant(run.participant, request.seat)
				by_participant.setdefault(id(target), (target, []))[1].append((run, request))
			for participant, pairs in by_participant.values():
				capped = [(r.turn_cap(q), q) for r, q in pairs]
				# Unrecoverable failures are logged, the live episodes flushed as errored, and the exception
				# re-raised inside _generate_batch (one home covering both the wave and the provisional probes),
				# so there is deliberately nothing to catch here.
				messages = self._generate_batch(participant, capped)
				for (run, request), (cap, _q), message in zip(pairs, capped, messages):
					try:
						directive = run.record_turn(request, message, cap=cap)
						if directive and "retry" in directive and run.allow_retry(request):
							retry = run.retry_request(request, message.content, directive["retry"])
							retry_cap = run.turn_cap(retry)
							retry_message = self._generate_batch(participant, [(retry_cap, retry)])[0]
							run.record_turn(retry, retry_message, cap=retry_cap)
						run.annotate(request)  # inline oracle annotations (no extra generation)
					except Exception:
						logger.exception("episode %s: applying seat %s's turn failed; recorded as status=error",
						                 run.ep.episode_id, request.seat)
						run.finalize(error=traceback.format_exc()[-2000:])
						live.pop(run.ep.episode_id, None)
			# Forked provisional elicitations. Gathered ONCE per episode across the whole wave — an episode with
			# requests in several participant groups (any heterogeneous table) would otherwise be probed once per
			# group — and then grouped by serving participant like the wave itself, so a probe for seat X is never
			# sent to the participant that owns seat Y.
			provisionals: list[tuple[EpisodeRun, SeatRequest]] = []
			seen: set[str] = set()
			for run, _request in wave:
				if run.ep.episode_id in seen or run.ep.episode_id not in live:
					continue
				seen.add(run.ep.episode_id)
				for provisional in run.scenario.provisional_due(run.state):
					provisional.episode_id = run.ep.episode_id
					provisionals.append((run, provisional))
			by_prov: dict[int, tuple[object, list[tuple[EpisodeRun, SeatRequest]]]] = {}
			for run, provisional in provisionals:
				target = _serving_participant(run.participant, provisional.seat)
				by_prov.setdefault(id(target), (target, []))[1].append((run, provisional))
			for participant, group in by_prov.values():
				messages = self._generate_batch(participant, [(q.max_tokens, q) for _r, q in group])
				for (run, provisional), message in zip(group, messages):
					parsed, score = run.score_provisional(message)
					run.record_provisional(provisional, message, parsed, score)
			for run in live.values():
				run.save()
			tick += 1
			if progress is not None:
				progress(tick, len(live))
		return [r.ep for r in runs]

	def _call_batch(self, participant, requests: list[SeatRequest], cap: int) -> list[Message]:
		"""The one place a participant's batched generate is actually invoked, preferring the seat-aware entry
		point when the participant has one (a table fronting several seats needs each request's own seat).

		A participant with NO batched entry point is driven one request at a time in order. That is what lets a
		heterogeneous table co-step: a computable ``PolicyParticipant`` seat is pure Python with nothing to batch,
		so looping it is both correct and already optimal, while the model seats of the same wave go through a real
		batch. Order is preserved, so a policy holding state across calls (a seeded RNG, a belief update) sees
		exactly the sequence it would have seen unbatched."""
		views = [q.view for q in requests]
		if hasattr(participant, "generate_batch_with_seats"):
			return participant.generate_batch_with_seats(views, [q.seat for q in requests], max_new_tokens=cap)
		if hasattr(participant, "generate_batch"):
			return participant.generate_batch(views, max_new_tokens=cap)
		return [participant.generate(q.view, seat=q.seat, max_new_tokens=cap) for q in requests]

	def _generate_batch(self, participant, capped_requests: list[tuple[int, SeatRequest]],
	                    *, wave_width: int | None = None) -> list[Message]:
		"""One batched generate over the wave, surviving OOM / transient cuDNN graph errors by splitting and
		retrying down to single requests. Long multi-agent transcripts make peak KV vary across a co-stepped
		batch, so no fixed width is safe everywhere; back off on demand.

		``wave_width`` is the width of the ORIGINAL wave, threaded down through the recursive splits so a failure
		is reported against the batch it started in — the width at the leaf is always 1, which says nothing about
		what went wrong. Callers leave it unset; only the recursion passes it.

		An UNRECOVERABLE error (anything not transient — i.e. a real bug) is never converted into a turn: it is
		logged, every live episode is finalized as errored so the partial run is legible on disk, and it is
		re-raised. That happens in the outermost frame only, which is why it lives here rather than at each call
		site: the wave and the provisional probes both come through this method."""
		if not capped_requests:
			return []
		if wave_width is None:                     # a top-level call: this is the fabrication denominator
			wave_width = len(capped_requests)
			self.attempted_turns += len(capped_requests)
			try:
				return self._generate_batch(participant, capped_requests, wave_width=wave_width)
			except GenerationFailureBudgetExceeded:
				raise                              # already logged, and already flushed the runs as errored
			except Exception:
				detail = traceback.format_exc()[-2000:]
				logger.exception("%s: generation failed unrecoverably on a wave of %d request(s); aborting the "
				                 "pool. This is NOT turned into placeholder turns.",
				                 participant.name, len(capped_requests))
				self._abort_all(detail)
				raise
		cap = max(c for c, _q in capped_requests)
		try:
			return self._call_batch(participant, [q for _c, q in capped_requests], cap)
		except RuntimeError as e:
			if not _is_transient_gpu_error(e):
				raise
			_empty_cuda_cache()
			if len(capped_requests) == 1:
				return [self._retry_or_fabricate(participant, capped_requests[0][1], cap, e, wave_width)]
			mid = len(capped_requests) // 2
			return (self._generate_batch(participant, capped_requests[:mid], wave_width=wave_width)
			        + self._generate_batch(participant, capped_requests[mid:], wave_width=wave_width))

	def _retry_or_fabricate(self, participant, request: SeatRequest, cap: int, error: Exception,
	                        wave_width: int) -> Message:
		"""Last resort for a request that failed transiently even alone: retry it a bounded number of times, and
		only if every attempt fails fabricate a placeholder turn — loudly.

		Fabricating is what keeps a long co-stepped run alive when one episode's context genuinely will not fit,
		but it produces text NO MODEL WROTE. So every attempt and the final give-up are logged with the exception,
		the participant, the episode/seat/round, and the width of the wave the failure started in; the returned
		message carries the :data:`GEN_FAILED_KEY` stamp that ``record_turn`` puts on the ``TurnRecord``; and the
		pool's fabrication budget is checked, so a systematically broken run stops instead of quietly filling up
		with non-behaviour. Retrying is cheap and worth it: these errors are transient by construction, and a
		context that truly does not fit fails every attempt in milliseconds."""
		last = error
		for attempt in range(1, self.single_request_retries + 1):
			logger.warning(
				"%s: generation failed for episode %s seat %s (round %s, phase %s) at batch width 1 "
				"(wave was %d); retry %d/%d after %r",
				participant.name, request.episode_id, request.seat, request.round, request.phase,
				wave_width, attempt, self.single_request_retries, last)
			try:
				return self._call_batch(participant, [request], cap)[0]
			except RuntimeError as e:
				if not _is_transient_gpu_error(e):
					raise
				last = e
				_empty_cuda_cache()

		reason = f"{type(last).__name__}: {last}"
		self.fabricated_turns += 1
		self.failures.append({"episode_id": request.episode_id, "seat": request.seat, "round": request.round,
		                      "phase": request.phase, "wave_width": wave_width, "reason": reason})
		logger.error(
			"%s: FABRICATING an empty turn for episode %s seat %s (round %s, phase %s) — generation failed alone "
			"after %d retries (wave was %d): %s. This turn is NOT model behaviour; it is stamped gen_failed=True. "
			"Pool so far: %d/%d turns fabricated (%.1f%%).",
			participant.name, request.episode_id, request.seat, request.round, request.phase,
			self.single_request_retries, wave_width, reason,
			self.fabricated_turns, self.attempted_turns,
			100.0 * self.fabricated_turns / max(1, self.attempted_turns))
		self._check_fabrication_budget()
		return Message(author=participant.name, content=EMPTY_TURN_PLACEHOLDER,
		               metadata={"n_tokens": 0, "oom_skip": True,
		                         GEN_FAILED_KEY: True, GEN_FAILURE_KEY: reason})

	def _abort_all(self, error: str) -> None:
		"""Finalize every still-running episode with ``error`` and flush it to the store.

		Called on the way out of an unrecoverable generation failure so the partial run is on disk as a FAILED
		run. Without this, an exception escaping the wave loop leaves those episodes at ``status="running"`` —
		which a later "is this cell done?" check cannot distinguish from a crashed job that never wrote them."""
		for run in self._abort_runs:
			if run.ep.status == "running":
				run.finalize(error=error)

	def _check_fabrication_budget(self) -> None:
		"""Raise :class:`GenerationFailureBudgetExceeded` once fabricated turns exceed
		``max_fabricated_fraction`` of the attempted ones, provided at least ``fabrication_floor`` turns have been
		attempted. Any episodes still live are finalized as errored and flushed to disk before the exception
		leaves, so the partial run is on disk as a FAILED run rather than looking like a short clean one."""
		if self.attempted_turns < self.fabrication_floor:
			return
		fraction = self.fabricated_turns / self.attempted_turns
		if fraction <= self.max_fabricated_fraction:
			return
		message = (
			f"generation failed on {self.fabricated_turns} of {self.attempted_turns} attempted turns "
			f"({100.0 * fraction:.1f}%), over the {100.0 * self.max_fabricated_fraction:.1f}% ceiling — this run "
			f"is not measuring model behaviour. Every failure was a transient GPU/backend error that survived "
			f"batch splitting and {self.single_request_retries} single-request retries; the last was: "
			f"{self.failures[-1]['reason'] if self.failures else 'unknown'}. Fix the backend (a chat-template or "
			f"EOS mismatch and a genuinely oversized context both land here), or run this cell through "
			f"EpisodePool instead of co-stepping. Raise max_fabricated_fraction only if you intend to keep the "
			f"fabricated turns and screen them downstream with arena.engine.gen_failures.")
		logger.error("%s: %s", type(self).__name__, message)
		self._abort_all(f"GenerationFailureBudgetExceeded: {message}")
		raise GenerationFailureBudgetExceeded(message)
