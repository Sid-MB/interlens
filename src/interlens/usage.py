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

"""Usage accounting: token/cost metering for hosted-API participants.

Hosted-API turns cost real money, and a large rollout can outrun a budget *while it is running* — the failure
mode this module exists to prevent is N concurrent conversations each individually under budget that together
blow past the cap before any of them finishes. Three pieces:

- **Per-turn usage** is recorded by ``APIParticipant`` into ``Message.metadata`` (``n_tokens``, ``n_tokens_in``,
  ``cost_usd``, ``stop_reason``) — the same convention ``ModelParticipant`` uses for ``n_tokens``, so
  ``TokenBudget`` and transcript-level aggregation work identically for local and hosted turns.
- **``UsageMeter``** is the live, run-level ledger: every metered participant reports each API call into one
  shared meter, which tracks cumulative dollars per model, supports **reservation-style gating** (claim an
  estimated cost *before* launching work, so concurrent conversations cannot collectively overrun the cap),
  and optionally persists to disk after every add (crash-safe: a restarted run resumes the ledger).
- **``CostBudget``** is the dollar-denominated ``StopCondition``: the per-conversation analogue of
  ``TokenBudget``, reading each committed turn's recorded ``metadata['cost_usd']``.

Pricing is a $/Mtok table keyed by model id. The bundled defaults are deliberately conservative (high) so the
meter over- rather than under-counts; register exact prices with ``register_pricing`` or pass a table to the
meter. An unknown model uses ``FALLBACK_PRICING`` (higher than any bundled entry) rather than silently costing $0.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
	from .conversation import Conversation
	from .message import Message
	from .transcript import Transcript

from .stop.stop_condition import StopCondition

# $/Mtok defaults, keyed by model id (Anthropic ids bundled; OpenRouter-style ids can be registered).
# Deliberately conservative (high) so an unpriced assumption overestimates spend. Override or extend via
# ``register_pricing`` / a meter-local ``pricing=`` table.
DEFAULT_PRICING: dict[str, dict[str, float]] = {
	"claude-fable-5": {"in": 10.0, "out": 50.0},
	"claude-sonnet-5": {"in": 3.0, "out": 15.0},
	"claude-opus-4-8": {"in": 5.0, "out": 25.0},
}
# Used for any model with no pricing entry: higher than every bundled price, so unknown-model spend is
# overstated, never understated.
FALLBACK_PRICING = {"in": 25.0, "out": 100.0}

_REGISTERED: dict[str, dict[str, float]] = {}


def register_pricing(model_id: str, *, input_per_mtok: float, output_per_mtok: float) -> None:
	"""Register (or override) the $/Mtok pricing for ``model_id``, process-wide. Meters constructed afterwards
	pick it up; a meter-local ``pricing=`` table still wins for that meter."""
	_REGISTERED[model_id] = {"in": input_per_mtok, "out": output_per_mtok}


def resolve_pricing(pricing: dict | None = None) -> dict[str, dict[str, float]]:
	"""The effective pricing table: bundled defaults, overlaid with ``register_pricing`` entries, overlaid with
	the caller's ``pricing`` dict (each value ``{"in": $/Mtok, "out": $/Mtok}``)."""
	table = dict(DEFAULT_PRICING)
	table.update(_REGISTERED)
	if pricing:
		table.update(pricing)
	return table


class UsageMeter:
	"""A cumulative, thread-safe dollar ledger shared by every metered participant in a run.

	``add`` records one API call (tokens in/out at ``price_multiplier`` — 0.5 for batch-API-served responses)
	and returns that call's cost. ``reserve``/``settle`` implement reservation-style gating: claim an estimated
	cost *before* launching an episode/conversation so concurrent work cannot collectively outrun ``budget``
	(the post-overrun fix from the arena experiments: a pure post-hoc meter let in-flight episodes blow past the
	cap). ``exhausted`` is the launch gate — in-flight work finishes, new work doesn't start.

	With ``path=`` the ledger is persisted atomically after every add, so a crashed/restarted run resumes with
	its spend intact. Refusal telemetry rides along: ``add(..., refusal=True)`` counts hosted-API refusals per
	model (a seat-selective refusal pattern silently biases multi-agent results; the counter makes it visible).
	"""

	def __init__(self, budget: float | None = None, *, path: str | Path | None = None,
	             pricing: dict | None = None):
		self.budget = budget
		self.path = Path(path) if path is not None else None
		self.pricing = resolve_pricing(pricing)
		self.total_usd = 0.0
		self.reserved_usd = 0.0  # in-flight reservations; never persisted (they re-form on restart)
		self.by_model: dict[str, dict] = {}
		self._lock = threading.Lock()
		if self.path is not None and self.path.exists():
			state = json.loads(self.path.read_text())
			self.total_usd = state["total_usd"]
			self.by_model = state["by_model"]

	# --- pricing -------------------------------------------------------------------------------------------

	def price(self, model: str, tokens_in: int, tokens_out: int) -> float:
		"""Dollar cost of one call at full (non-batch) price. Unknown models use ``FALLBACK_PRICING``."""
		p = self.pricing.get(model, FALLBACK_PRICING)
		return tokens_in * p["in"] / 1e6 + tokens_out * p["out"] / 1e6

	# --- recording -----------------------------------------------------------------------------------------

	def add(self, model: str, tokens_in: int, tokens_out: int, *, price_multiplier: float = 1.0,
	        refusal: bool = False) -> float:
		"""Record one completed API call; returns its cost in dollars. ``price_multiplier`` scales the price for
		discounted billing paths (0.5 = provider batch API). Thread-safe; persists when ``path`` is set."""
		cost = self.price(model, tokens_in, tokens_out) * price_multiplier
		with self._lock:
			self.total_usd += cost
			m = self.by_model.setdefault(model, {"in": 0, "out": 0, "usd": 0.0, "calls": 0, "refusals": 0})
			m["in"] += tokens_in
			m["out"] += tokens_out
			m["usd"] += cost
			m["calls"] += 1
			if refusal:
				m["refusals"] += 1
			self._persist()
		return cost

	def _persist(self) -> None:
		if self.path is None:
			return
		self.path.parent.mkdir(parents=True, exist_ok=True)
		tmp = self.path.with_suffix(".tmp")
		tmp.write_text(json.dumps({"total_usd": self.total_usd, "by_model": self.by_model}))
		os.replace(tmp, self.path)

	# --- reservation gating ----------------------------------------------------------------------------------

	def reserve(self, usd: float) -> bool:
		"""Claim ``usd`` of estimated future spend. Returns ``False`` (claiming nothing) when spent + already
		reserved + this claim would exceed the budget — the caller should then not launch the work. With no
		``budget``, reservations always succeed (the ledger still tracks them)."""
		with self._lock:
			if self.budget is not None and self.total_usd + self.reserved_usd + usd > self.budget:
				return False
			self.reserved_usd += usd
			return True

	def settle(self, usd: float) -> None:
		"""Release a prior reservation (call once the work's actual spend has been metered via ``add``)."""
		with self._lock:
			self.reserved_usd = max(0.0, self.reserved_usd - usd)

	@property
	def exhausted(self) -> bool:
		"""True once actual spend has reached the budget — the gate for launching NEW work (in-flight work is
		allowed to finish; that is the reservation's job to have pre-counted)."""
		return self.budget is not None and self.total_usd >= self.budget

	# --- reporting -----------------------------------------------------------------------------------------

	def snapshot(self) -> dict:
		"""A JSON-serializable copy of the ledger: totals, reservations, and the per-model breakdown."""
		with self._lock:
			return {"total_usd": self.total_usd, "reserved_usd": self.reserved_usd, "budget": self.budget,
			        "by_model": {k: dict(v) for k, v in self.by_model.items()}}

	def summary(self) -> str:
		"""A printable run-spend summary: one line per model (calls, tokens, refusals, dollars) plus the total
		against the budget."""
		snap = self.snapshot()
		lines = []
		for model, m in sorted(snap["by_model"].items()):
			refusal_note = f", {m['refusals']} refusals" if m.get("refusals") else ""
			lines.append(f"  {model}: {m['calls']} calls, {m['in']:,} in / {m['out']:,} out tokens"
			             f"{refusal_note} — ${m['usd']:.2f}")
		budget_note = f" of ${snap['budget']:.2f} budget" if snap["budget"] is not None else ""
		reserved_note = f" (+${snap['reserved_usd']:.2f} reserved)" if snap["reserved_usd"] else ""
		lines.append(f"  total: ${snap['total_usd']:.2f}{budget_note}{reserved_note}")
		return "Usage:\n" + "\n".join(lines) if lines else "Usage: (no metered calls)"

	# --- pickling (participants may hold a meter across the spawn boundary) ---------------------------------

	def __getstate__(self) -> dict:
		state = self.__dict__.copy()
		del state["_lock"]
		return state

	def __setstate__(self, state: dict) -> None:
		self.__dict__.update(state)
		self._lock = threading.Lock()


def transcript_usage(transcript: "Transcript | Iterable[Message]") -> dict:
	"""Aggregate the recorded usage of one transcript: total generated/input tokens, dollar cost, and a
	per-author breakdown — read from each committed message's metadata (``n_tokens`` / ``n_tokens_in`` /
	``cost_usd``), the same source of truth ``TokenBudget`` and ``CostBudget`` use. Turns without records
	(seeded/moderator/scripted) contribute 0."""
	total = {"tokens_out": 0, "tokens_in": 0, "cost_usd": 0.0, "by_author": {}}
	for m in transcript:
		out = int(m.metadata.get("n_tokens") or 0)
		inn = int(m.metadata.get("n_tokens_in") or 0)
		usd = float(m.metadata.get("cost_usd") or 0.0)
		total["tokens_out"] += out
		total["tokens_in"] += inn
		total["cost_usd"] += usd
		a = total["by_author"].setdefault(m.author, {"tokens_out": 0, "tokens_in": 0, "cost_usd": 0.0, "turns": 0})
		a["tokens_out"] += out
		a["tokens_in"] += inn
		a["cost_usd"] += usd
		a["turns"] += 1
	return total


class CostBudget(StopCondition):
	"""A per-conversation **dollar** budget — the cost-denominated sibling of ``TokenBudget``.

	Stops a conversation once its own cumulative recorded turn cost (``metadata['cost_usd']``, written by
	metered ``APIParticipant``s) reaches ``per_conversation`` dollars. Stateless like ``TokenBudget`` (spend is
	re-read from the transcript), so it works installed directly or ambiently and each rollout copy
	independently gets the full budget. Turns without a cost record (local models, scripted participants)
	contribute $0 — this budget only constrains metered hosted-API spend."""

	def __init__(self, per_conversation: float):
		self.per_conversation = per_conversation

	def should_stop(self, conversation: "Conversation", last_message: "Message") -> bool:
		spent = sum(float(m.metadata.get("cost_usd") or 0.0) for m in conversation.transcript)
		return spent >= self.per_conversation
