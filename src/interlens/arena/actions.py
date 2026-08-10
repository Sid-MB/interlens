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

"""Typed formal-action layer for structured negotiation turns.

A scenario that wants *binding moves* (not just free text) gives each turn one formal action drawn from the
package-deal protocol — ``Propose`` a complete deal (which the registry stamps with a monotonic ``offer_id``),
``Accept`` / ``Reject`` a specific live offer by id, or ``Walk`` (an explicit no-deal exit). Referencing offers
by id removes the "I accept" ambiguity that breaks down with two live proposals on the table.

Three pieces:

- **The action dataclasses** (``Propose`` / ``Accept`` / ``Reject`` / ``Walk``), all frozen and
  JSON-round-trippable — the frozen team contract's move vocabulary. A ``Deal`` is a tuple of option indices
  (one per issue); deals are decoded from a model's ``{"Site": "...", ...}`` object by a scenario-supplied
  ``deal_decoder``, so this module stays free of any specific game's issue set.
- **``OfferRegistry``** — monotonic ids and standing-offer tracking (accept/reject sets per offer, withdrawal),
  serializable for the episode record and reconstructable by replay (it is a pure function of the action
  sequence).
- **``parse_action``** — the single consolidated JSON-extraction-and-validation entry point. It returns a
  ``ParseResult`` distinguishing a **syntax** violation (no well-formed action could be read) from an
  **economic-legality** violation (well-formed but references a dead offer / an infeasible deal), so a scenario
  can retry once with specific feedback and log the two failure classes separately as data.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, ClassVar, Container

from ..parsing import last_json

# One deal = one option index per issue (the frozen team contract's ``Deal = tuple[int, ...]``). Decoding a
# model's issue-name->option-name object into this tuple is a scenario concern (it owns the issue set).
Deal = tuple[int, ...]
OfferId = str

# Error classes for the retry-with-feedback protocol, logged separately as data.
SYNTAX = "syntax"        # no well-formed action could be parsed (bad/absent JSON, unknown kind, missing field)
LEGALITY = "legality"    # well-formed but economically illegal (dead offer id, infeasible/malformed deal)

#: Proposer id for an offer tabled by the protocol itself rather than by a seat — a neutral mediator/scheduling
#: office whose package is on the table before anyone speaks (``ScorableNegotiation``'s ``seeded_offer`` knob).
#: It is deliberately NOT a seat name: it holds no sheet, casts no vote, and counts toward no quorum, so every
#: ACCEPT on such an offer is a real party's decision. Consumers that map a proposer to a seat index use
#: :data:`FACILITATOR_SEAT`.
FACILITATOR = "Facilitator"
#: The seat index a facilitator proposer serializes to in a ``negotiation_state`` block: ``-1``, i.e. "no seat".
#: A reader must translate it back to "no implicit supporter" rather than indexing a seat array with it.
FACILITATOR_SEAT = -1


# ----------------------------------------------------------------- actions ---

@dataclass(frozen=True)
class Action:
	"""Base class for the four formal moves. ``kind`` is the wire tag; ``to_json`` is the canonical surface a
	model emits inside a fenced ``{"action": ...}`` object."""

	kind: ClassVar[str] = ""

	def to_json(self) -> dict:
		return {"action": self.kind}


@dataclass(frozen=True)
class Propose(Action):
	"""Register a complete deal. The registry assigns the ``offer_id`` on registration — it is not chosen by the
	model — so ids are monotonic and unambiguous. ``deal`` is the decoded option-index tuple."""

	kind: ClassVar[str] = "propose"
	deal: Deal

	def to_json(self) -> dict:
		return {"action": self.kind, "deal": list(self.deal)}


@dataclass(frozen=True)
class Accept(Action):
	"""Accept a specific standing offer by id (an ``ACCEPT`` vote on that exact deal)."""

	kind: ClassVar[str] = "accept"
	offer_id: OfferId

	def to_json(self) -> dict:
		return {"action": self.kind, "offer_id": self.offer_id}


@dataclass(frozen=True)
class Reject(Action):
	"""Reject a specific standing offer by id."""

	kind: ClassVar[str] = "reject"
	offer_id: OfferId

	def to_json(self) -> dict:
		return {"action": self.kind, "offer_id": self.offer_id}


@dataclass(frozen=True)
class Walk(Action):
	"""Explicit no-deal exit — a decision, not a timeout."""

	kind: ClassVar[str] = "walk"


@dataclass(frozen=True)
class Pass(Action):
	"""Take NO formal move this turn — the typed form of the talk-only pass a scenario already accepts as
	``{"action": "none"}``.

	It is not part of the package-deal move vocabulary :func:`parse_action` validates: a scenario recognizes the
	``none``/``pass`` wire tag BEFORE it reaches the parser (``ScorableNegotiation.apply``), records the turn as
	``atype="none"``, and charges neither a syntax nor a legality error. It exists so a
	``PolicyParticipant`` can express "stand pat" in the same typed vocabulary as the other moves instead of
	being forced into a move it does not want — the alternatives are all worse: ``Walk`` permanently removes the
	seat (and kills the deal outright if it holds a veto), ``Reject`` needs a live offer id and is illegal in the
	forced-final proposal phase, and re-``Propose``-ing a deal already on the table mints a SECOND offer id for
	it, splitting the accept votes across two ids so neither can reach unanimity.

	One caveat, from the same short-circuit: a MOVES-ONLY game (no talk channel) treats a turn with no formal
	action as a syntax error, so a policy that can emit ``Pass`` belongs in a chat-enabled arm."""

	kind: ClassVar[str] = "none"


def action_from_json(d: dict) -> Action:
	"""Reconstruct a typed :class:`Action` from its stored dict — the inverse of ``Action.to_json()``. Accepts
	the kind under ``"action"`` / ``"type"`` / ``"kind"`` (so it reads both the canonical flat form and a stored
	nested action object). Used to round-trip verdicts and to rebuild the action series from stored episodes.
	Raises ``ValueError`` if ``d`` doesn't name a known action kind."""
	kind = d.get("action") or d.get("type") or d.get("kind")
	kind = str(kind).strip().lower() if isinstance(kind, str) else None
	if kind == Propose.kind:
		return Propose(deal=tuple(d.get("deal", ())))
	if kind == Accept.kind:
		return Accept(offer_id=str(d.get("offer_id") or d.get("id") or d.get("offer")))
	if kind == Reject.kind:
		return Reject(offer_id=str(d.get("offer_id") or d.get("id") or d.get("offer")))
	if kind == Walk.kind:
		return Walk()
	if kind in (Pass.kind, "pass"):
		return Pass()
	raise ValueError(f"not a serialized action: {d!r}")


# ----------------------------------------------------------------- offers ---

@dataclass
class Offer:
	"""One registered offer and its live vote state. ``live`` flips to False on withdrawal/supersession; the
	accept/reject sets are the votes gathered so far (closure semantics — unanimity vs veto-weighted — are the
	scenario's call, computed off these sets)."""

	offer_id: OfferId
	deal: Deal
	proposer: str
	round: int = 0
	accepts: set[str] = field(default_factory=set)
	rejects: set[str] = field(default_factory=set)
	live: bool = True

	def to_json(self) -> dict:
		return {"offer_id": self.offer_id, "deal": list(self.deal), "proposer": self.proposer,
		        "round": self.round, "accepts": sorted(self.accepts), "rejects": sorted(self.rejects),
		        "live": self.live}

	@staticmethod
	def from_json(d: dict) -> "Offer":
		return Offer(offer_id=d["offer_id"], deal=tuple(d["deal"]), proposer=d["proposer"],
		             round=d.get("round", 0), accepts=set(d.get("accepts", [])),
		             rejects=set(d.get("rejects", [])), live=d.get("live", True))


class OfferRegistry:
	"""Monotonic offer ids + standing-offer tracking for the formal protocol.

	``register`` mints ``{prefix}{n}`` ids (``O1``, ``O2``, ...); the proposer is recorded as an implicit accept
	of its own offer (proposing implies supporting it). ``accept`` / ``reject`` record a seat's vote on a live
	offer (a vote on a dead/unknown offer is refused and returns False). Withdrawing an offer marks it not-live
	without deleting it, so the ledger stays complete for the record. The registry is a pure function of the
	action sequence, so replay reconstructs it identically; ``to_json`` / ``from_json`` also persist it directly.
	"""

	def __init__(self, prefix: str = "O"):
		self.prefix = prefix
		self.offers: dict[OfferId, Offer] = {}
		self._counter = 0

	def register(self, deal: Deal, proposer: str, *, round: int = 0, implicit_accept: bool = True) -> OfferId:
		"""Mint a new live offer for ``deal`` by ``proposer`` and return its id. The proposer implicitly accepts.

		``implicit_accept=False`` registers the offer with an EMPTY accept set — the explicit no-vote path for a
		proposer that is not a party to the deal (:data:`FACILITATOR`). Without it a mediator's own id would sit
		in ``accepts`` and any closure rule that counts the accept set (or renders "accepted by: ...") would
		report a vote nobody cast."""
		self._counter += 1
		offer_id = f"{self.prefix}{self._counter}"
		offer = Offer(offer_id=offer_id, deal=tuple(deal), proposer=proposer, round=round)
		if implicit_accept:
			offer.accepts.add(proposer)
		self.offers[offer_id] = offer
		return offer_id

	def get(self, offer_id: OfferId) -> Offer | None:
		return self.offers.get(offer_id)

	def is_live(self, offer_id: OfferId) -> bool:
		offer = self.offers.get(offer_id)
		return bool(offer and offer.live)

	def standing(self) -> list[Offer]:
		"""Live offers, in registration order."""
		return [o for o in self.offers.values() if o.live]

	def standing_ids(self) -> list[OfferId]:
		"""Live offer ids in REGISTRATION order (same order as :meth:`standing`).

		A list, not a set, deliberately: callers build ordered things out of it — the legal-action set an oracle
		scores, and hence the stored verdict — and a set's iteration order varies with ``PYTHONHASHSEED``, which
		used to make a saved annotation differ run to run. Membership tests (``offer_id in standing_ids()``, how
		:func:`parse_action` gates accept/reject) read the same either way."""
		return [o.offer_id for o in self.offers.values() if o.live]

	def accept(self, offer_id: OfferId, agent: str) -> bool:
		"""Record ``agent``'s ACCEPT of a live offer; a reject by the same agent is cleared. Returns False (no
		effect) when the offer is unknown or dead."""
		offer = self.offers.get(offer_id)
		if offer is None or not offer.live:
			return False
		offer.rejects.discard(agent)
		offer.accepts.add(agent)
		return True

	def reject(self, offer_id: OfferId, agent: str) -> bool:
		"""Record ``agent``'s REJECT of a live offer; an accept by the same agent is cleared. Returns False when
		the offer is unknown or dead."""
		offer = self.offers.get(offer_id)
		if offer is None or not offer.live:
			return False
		offer.accepts.discard(agent)
		offer.rejects.add(agent)
		return True

	def withdraw(self, offer_id: OfferId) -> bool:
		offer = self.offers.get(offer_id)
		if offer is None or not offer.live:
			return False
		offer.live = False
		return True

	def apply(self, action: Action, agent: str, *, round: int = 0) -> OfferId | None:
		"""Fold one parsed ``action`` into the registry: ``Propose`` registers (returns the new id), ``Accept`` /
		``Reject`` record the vote, ``Walk`` is a no-op here (the scenario handles the exit). Returns the new
		offer id for a ``Propose``, else ``None``."""
		if isinstance(action, Propose):
			return self.register(action.deal, agent, round=round)
		if isinstance(action, Accept):
			self.accept(action.offer_id, agent)
		elif isinstance(action, Reject):
			self.reject(action.offer_id, agent)
		return None

	def to_json(self) -> dict:
		return {"prefix": self.prefix, "counter": self._counter,
		        "offers": [o.to_json() for o in self.offers.values()]}

	@staticmethod
	def from_json(d: dict) -> "OfferRegistry":
		reg = OfferRegistry(prefix=d.get("prefix", "O"))
		reg._counter = d.get("counter", 0)
		for od in d.get("offers", []):
			offer = Offer.from_json(od)
			reg.offers[offer.offer_id] = offer
		return reg


# ------------------------------------------------------------- parse/retry ---

@dataclass
class ParseResult:
	"""The outcome of reading one formal action from a model's turn.

	``ok`` with an ``action`` on success; on failure ``action`` is ``None``, ``error`` is a specific,
	model-facing message for the one retry, and ``error_kind`` is :data:`SYNTAX` or :data:`LEGALITY` — the two
	failure classes the arena logs separately as data (AucArena's retry-once pattern)."""

	action: Action | None = None
	ok: bool = False
	error: str | None = None
	error_kind: str | None = None
	raw: Any = None            # the extracted JSON object (or None), kept for the turn log

	@staticmethod
	def good(action: Action, raw: Any = None) -> "ParseResult":
		return ParseResult(action=action, ok=True, raw=raw)

	@staticmethod
	def bad(kind: str, error: str, raw: Any = None) -> "ParseResult":
		return ParseResult(action=None, ok=False, error=error, error_kind=kind, raw=raw)

	def retry_directive(self) -> dict | None:
		"""``{'retry': <error>, 'error_kind': <kind>}`` on failure (the scenario returns this from ``apply`` to
		trigger the engine's one re-prompt), else ``None``. The engine reads ``'retry'``; ``'error_kind'`` rides
		along for logging."""
		if self.ok:
			return None
		return {"retry": self.error, "error_kind": self.error_kind}


def _holder_and_kind(obj: dict) -> tuple[dict, str | None, bool]:
	"""Locate the action within a parsed object and its kind string. Two wire shapes are accepted:

	- **flat** — ``{"action": "propose", "deal": ...}`` (the kind is the ``"action"`` string, fields alongside);
	- **nested** — ``{"message": "...", "action": {"type": "propose", ...}}`` (the ``"action"`` value is the
	  action object; the kind is its ``"type"`` / ``"action"`` / ``"kind"``) — the shape used when a turn carries
	  public cheap talk AND a move together.

	``"move"`` is accepted as an alias for the ``"action"`` key. Returns ``(holder, kind, has_action)``: the dict
	the action's fields live on, the lowercased kind (or ``None`` if unreadable), and whether an action key was
	present at all (so a pure cheap-talk turn is distinguishable from a malformed one)."""
	has_action = "action" in obj or "move" in obj
	field = obj.get("action")
	if field is None:
		field = obj.get("move")
	if isinstance(field, dict):
		kind = field.get("action") or field.get("type") or field.get("kind")
		return field, (kind.strip().lower() if isinstance(kind, str) else None), has_action
	if isinstance(field, str):
		return obj, field.strip().lower(), has_action
	return obj, None, has_action


def _action_from_holder(holder: dict, kind: str, *, deal_decoder, standing, allowed) -> ParseResult:
	"""Validate one action given its kind and the dict its fields live on (the shared core of ``parse_action``)."""
	if allowed is not None and kind not in allowed:
		return ParseResult.bad(LEGALITY, f'The action "{kind}" is not allowed on this turn '
		                       f'(allowed: {", ".join(sorted(allowed))}).', raw=holder)
	if kind == Walk.kind:
		return ParseResult.good(Walk(), raw=holder)
	if kind == Propose.kind:
		deal_obj = holder.get("deal")
		if deal_obj is None:
			return ParseResult.bad(SYNTAX, 'A "propose" action needs a "deal" object setting every issue.',
			                       raw=holder)
		if deal_decoder is not None:
			deal = deal_decoder(deal_obj)
		elif isinstance(deal_obj, (list, tuple)) and all(isinstance(i, int) for i in deal_obj):
			deal = tuple(deal_obj)
		else:
			deal = None
		if deal is None:
			return ParseResult.bad(LEGALITY, "That deal is not a valid complete deal (set every issue to a "
			                       "valid option).", raw=holder)
		return ParseResult.good(Propose(deal=deal), raw=holder)
	if kind in (Accept.kind, Reject.kind):
		offer_id = holder.get("offer_id") or holder.get("id") or holder.get("offer")
		if not offer_id:
			return ParseResult.bad(SYNTAX, f'An "{kind}" action needs an "offer_id" naming a standing offer '
			                       "(e.g. \"O1\").", raw=holder)
		offer_id = str(offer_id).strip()
		if standing is not None and offer_id not in standing:
			return ParseResult.bad(LEGALITY, f'Offer "{offer_id}" is not a standing offer you can {kind}.',
			                       raw=holder)
		action = Accept(offer_id=offer_id) if kind == Accept.kind else Reject(offer_id=offer_id)
		return ParseResult.good(action, raw=holder)
	return ParseResult.bad(SYNTAX, f'Unknown action "{kind}". Use one of "propose", "accept", "reject", '
	                       '"walk".', raw=holder)


def parse_action(text: str, *, deal_decoder: Callable[[Any], Deal | None] | None = None,
                 standing: Container[OfferId] | None = None,
                 allowed: Container[str] | None = None) -> ParseResult:
	"""Read ONE formal action from ``text`` (its last fenced/balanced JSON object), validated into a typed
	``Action`` or a classified failure.

	- ``deal_decoder`` maps a ``Propose``'s ``"deal"`` object to a :data:`Deal` tuple, returning ``None`` for a
	  malformed/infeasible deal (an economic-legality failure). When omitted, a deal given as a list of option
	  indices is accepted as-is; any other shape is a legality failure.
	- ``standing`` (the live offer ids, e.g. ``registry.standing_ids()``) gates ``Accept`` / ``Reject``: a
	  reference to an id not in it is an economic-legality failure. When omitted, id existence is not checked
	  here (the scenario/registry can check on apply).
	- ``allowed`` optionally restricts which action kinds are legal at this point (e.g. only ``accept`` on a
	  finalization turn); a disallowed-but-well-formed kind is a legality failure.

	Accepts both the flat wire form ``{"action": "propose"|"accept"|"reject"|"walk", ...}`` and the nested form
	``{"action": {"type": "propose", ...}}`` (see :func:`_holder_and_kind`); ``"offer_id"`` also accepts the
	aliases ``"id"`` / ``"offer"``. A turn that mixes cheap talk with a move carries both in one object; the
	scenario reads the ``message`` field itself and calls this for the action."""
	obj = last_json(text)
	if not isinstance(obj, dict):
		return ParseResult.bad(SYNTAX, "No JSON action found. End your turn with one fenced JSON object, e.g. "
		                       '```json\n{"action": "accept", "offer_id": "O1"}\n```.', raw=obj)
	holder, kind, _ = _holder_and_kind(obj)
	if kind is None:
		return ParseResult.bad(SYNTAX, 'The JSON action must name a kind '
		                       '(one of "propose", "accept", "reject", "walk").', raw=obj)
	return _action_from_holder(holder, kind, deal_decoder=deal_decoder, standing=standing, allowed=allowed)


# --------------------------------------------------------------- action as a stable key ---

def action_key(action: Action | None) -> str | None:
	"""The canonical STRING an action serializes to when it must be a JSON object key or a sort key — its
	``to_json()`` dumped with sorted keys (``'{"action": "accept", "offer_id": "O1"}'``). ``None`` maps to
	``None``.

	One definition serves two needs that must agree: an ``OracleVerdict``'s ``action_values`` is keyed by action,
	and JSON object keys must be strings; and the oracles sort their scored actions by this key so a stored
	verdict is byte-reproducible regardless of the order the legal actions arrived in. :func:`action_from_key`
	is the exact inverse."""
	return None if action is None else json.dumps(action.to_json(), sort_keys=True)


def action_from_key(key: str | None) -> Action | None:
	"""Rebuild the :class:`Action` a :func:`action_key` string names; ``None``/unparseable → ``None``."""
	if not isinstance(key, str):
		return None
	try:
		return action_from_json(json.loads(key))
	except (json.JSONDecodeError, ValueError, TypeError):
		return None


# ------------------------------------------------------------- action -> message envelope ---

def action_message(action: Action, space=None, *, preface: str = "", message: str | None = None) -> str:
	"""Render ``action`` as a message body: an optional free-text ``preface``, then the fenced ``json`` action
	block — the exact envelope an LLM seat produces, so a transcript is symmetric across seat types (a
	``PolicyParticipant`` emits through here).

	The action serializes through its own :meth:`Action.to_json` — the ONE action serializer — so ``deal`` is a
	list of option indices. Pass ``space`` (anything with a ``named(deal)`` method, i.e. a
	:class:`~interlens.arena.negotiation.space.DealSpace`) to render a ``Propose``'s deal as
	``{issue_name: option_label}`` instead, which is what an LLM-legible transcript wants; ``DealSpace.parse`` is
	the inverse when reading one back. ``space`` is duck-typed, so this module keeps no dependency on the
	negotiation package.

	``message`` puts public cheap talk INSIDE the envelope, under the ``"message"`` key an LLM seat uses and a
	chat-enabled scenario republishes to every other seat. That is the only speaking channel a scripted seat
	has: ``preface`` is free text OUTSIDE the fence, which the scenario's parser never reads, so a preface is
	transcript decoration whereas a ``message`` is an actual public statement. Key order matches the LLM
	envelope (message first, then the formal action) so the two are indistinguishable on the wire. A
	moves-only game has no talk channel and drops the key, so a speaking policy belongs in a chat arm."""
	payload = action.to_json()
	if space is not None and isinstance(action, Propose):
		payload = {**payload, "deal": space.named(action.deal)}
	if message:
		payload = {"message": message, **payload}
	body = "```json\n" + json.dumps(payload) + "\n```"
	return f"{preface}\n{body}" if preface else body
