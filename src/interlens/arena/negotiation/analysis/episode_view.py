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

# [rational_agents restructure: phase-C] 2026-07-24 — moved up from experiments/rational_agents/analysis/:
# negotiation-generic measurement, reusable by any experiment over this game family.
"""``EpisodeView``: a stored arena ``Episode`` JSON parsed into a normalized negotiation action series that the
metrics read instead of raw ``parsed_action`` — an ordered ``TurnView`` list (typed action, deal canonicalized
to an index tuple, offer id, any acceptable-offer/belief note, private thinking), the offer registry, the
per-round standing offer, and the final deal / reached flag.

The field-name maps below are the single adapter for interlens-core's action serialization: tolerant to the
scorable scenario's ``{atype, deal_named, offer}`` shape (offer ids ``P{n}`` in proposal order), the canonical
typed ``{"action": "propose", "deal": [idx...]}`` shape, and the older v1 ``{proposal, support}`` shape.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .game_analysis import GameAnalysis, Deal

# ---- action-schema vocabulary (the reconcile-here maps) ------------------------------
_TYPE_KEYS = ("atype", "type", "action", "act")
_PROPOSE_TYPES = {"propose", "proposal", "offer", "make_offer"}
_ACCEPT_TYPES = {"accept", "support", "respond_accept", "accept_offer"}
_REJECT_TYPES = {"reject", "respond_reject", "reject_offer"}
_WALK_TYPES = {"walk", "quit", "quit_negotiation", "no_deal", "leave"}
_DEAL_KEYS = ("deal_named", "deal", "proposal", "offer_deal", "package")
_OFFER_ID_KEYS = ("offer", "offer_id", "support", "id", "ref", "target")
_ACCEPTABLE_KEYS = ("acceptable_offer", "acceptable", "reservation", "min_acceptable", "would_accept")
_BELIEF_KEYS = ("belief", "beliefs", "estimate", "opponent_estimate", "posterior")


@dataclass
class TurnView:
	"""One turn, normalized. ``action_type`` is the primary typed action; the granular fields coexist so a v1
	turn that both registers a proposal and supports an id populates ``proposed_deal`` and
	``accepted_offer_id`` together."""

	idx: int
	round: int
	seat: str
	action_type: str                 # 'propose' | 'accept' | 'reject' | 'walk' | 'none'
	proposed_deal: Deal | None = None
	accepted_offer_id: Any = None
	rejected_offer_id: Any = None
	walked: bool = False
	stated_offer: Deal | None = None      # LAMEN-style machine-readable acceptable offer, canonicalized
	stated_belief: Any = None
	thinking: str | None = None
	message: str | None = None
	parse_ok: bool = True
	raw_action: Any = None


@dataclass
class EpisodeView:
	"""A parsed episode: seats, the turn series, the offer registry, per-round standing offer, and outcome."""

	episode_id: str
	arm: str
	model: str
	seats: list[str]
	turns: list[TurnView]
	proposals: dict[Any, dict] = field(default_factory=dict)     # offer_id -> {deal, proposer, round, idx}
	final_deal: Deal | None = None
	reached: bool = False
	outcome: dict = field(default_factory=dict)
	standing_offer_by_round: dict[int, Deal | None] = field(default_factory=dict)

	@property
	def n_agents(self) -> int:
		return len(self.seats)

	def seat_index(self, seat: str) -> int:
		return self.seats.index(seat)

	def proposals_by(self, seat: str) -> list[TurnView]:
		"""Every turn on which ``seat`` registered a proposal (in order)."""
		return [t for t in self.turns if t.proposed_deal is not None and t.seat == seat]

	@classmethod
	def from_episode(cls, episode: dict, game: GameAnalysis) -> "EpisodeView":
		"""Parse a stored ``Episode.to_json()`` dict into an ``EpisodeView`` using ``game`` to canonicalize
		deals. Robust to unknown seats (falls back to the episode's ``seats`` list) and to actions that fail to
		canonicalize (kept as a turn with ``parse_ok=False`` and no deal, so nothing is silently dropped)."""
		seats = [s["name"] if isinstance(s, dict) else s for s in episode.get("seats", [])]
		turns: list[TurnView] = []
		proposals: dict[Any, dict] = {}
		# offers are minted "<prefix><n>" in proposal order (scorable uses "P", the canonical OfferRegistry "O");
		# detect the prefix from an accept/reject reference so auto-assigned proposal ids match what accepts cite.
		prefix = _detect_offer_prefix(episode)
		next_auto_id = [1]
		for tr in episode.get("turns", []):
			tv = _parse_turn(tr, game, proposals, next_auto_id, prefix)
			turns.append(tv)
		if not seats:
			seats = sorted({t.seat for t in turns})
		standing = _standing_by_round(turns)
		outcome = episode.get("outcome") or {}
		final_deal, reached = _final_deal(outcome, turns, standing, game)
		return cls(episode_id=episode.get("episode_id", ""), arm=episode.get("arm", ""),
		           model=episode.get("model", ""), seats=seats, turns=turns, proposals=proposals,
		           final_deal=final_deal, reached=reached, outcome=outcome,
		           standing_offer_by_round=standing)


# ------------------------------------------------------------------- turn parsing --
def _first(d: dict, keys) -> Any:
	for k in keys:
		if k in d and d[k] is not None:
			return d[k]
	return None


def _detect_offer_prefix(episode: dict) -> str:
	"""The alphabetic prefix of the offer ids this episode uses ("O" for the canonical OfferRegistry, "P" for
	the current scorable scenario), read off the first accept/reject reference. Defaults to "P"."""
	for tr in episode.get("turns", []):
		pa = tr.get("parsed_action")
		if isinstance(pa, dict):
			ref = _first(pa, _OFFER_ID_KEYS)
			if isinstance(ref, str):
				m = re.match(r"([A-Za-z]+)\d+", ref)
				if m:
					return m.group(1)
	return "P"


def _parse_turn(tr: dict, game: GameAnalysis, proposals: dict, next_auto_id: list, prefix: str = "P") -> TurnView:
	pa = tr.get("parsed_action")
	tv = TurnView(idx=tr.get("idx", len(proposals)), round=tr.get("round", 0), seat=tr.get("seat", ""),
	              action_type="none", thinking=tr.get("reasoning") or None,
	              message=tr.get("content"), parse_ok=bool(tr.get("parse_ok", True)), raw_action=pa)
	if not isinstance(pa, dict):
		return tv
	if pa.get("thinking"):
		tv.thinking = pa["thinking"]           # scorable carries the scratchpad in the parsed action
	if pa.get("message"):
		tv.message = pa["message"]
	kind = str(_first(pa, _TYPE_KEYS) or "").lower()
	deal_raw = _first(pa, _DEAL_KEYS)
	offer_ref = _first(pa, _OFFER_ID_KEYS)
	# proposed deal (typed 'propose', or any turn carrying a full deal, e.g. v1 'proposal')
	if deal_raw is not None and (kind in _PROPOSE_TYPES or not kind or kind in _ACCEPT_TYPES):
		try:
			deal = game.canonical_deal(deal_raw)
			tv.proposed_deal = deal
			tv.action_type = "propose"
			oid = pa.get("offer_id") or f"{prefix}{next_auto_id[0]}"
			next_auto_id[0] += 1
			proposals[oid] = {"deal": deal, "proposer": tv.seat, "round": tv.round, "idx": tv.idx}
		except (ValueError, KeyError, TypeError):
			tv.parse_ok = False
	# accept / support (may co-occur with a proposal in v1)
	if kind in _ACCEPT_TYPES or (offer_ref is not None and kind not in _REJECT_TYPES and not deal_raw):
		tv.accepted_offer_id = offer_ref
		if tv.action_type == "none":
			tv.action_type = "accept"
	if kind in _REJECT_TYPES:
		tv.rejected_offer_id = offer_ref
		tv.action_type = "reject"
	if kind in _WALK_TYPES:
		tv.walked = True
		tv.action_type = "walk"
	# machine-readable notes for faithfulness/calibration metrics
	acc = _first(pa, _ACCEPTABLE_KEYS)
	if acc is not None:
		try:
			tv.stated_offer = game.canonical_deal(acc)
		except (ValueError, KeyError, TypeError):
			tv.stated_offer = None
	tv.stated_belief = _first(pa, _BELIEF_KEYS)
	return tv


def _standing_by_round(turns: list[TurnView]) -> dict[int, Deal | None]:
	"""The tabled deal at the end of each round: the most recent proposal made up to and including that round."""
	rounds = sorted({t.round for t in turns})
	standing: dict[int, Deal | None] = {}
	last: Deal | None = None
	for r in rounds:
		for t in turns:
			if t.round == r and t.proposed_deal is not None:
				last = t.proposed_deal
		standing[r] = last
	return standing


def _final_deal(outcome: dict, turns: list[TurnView], standing: dict, game: GameAnalysis):
	"""The realized deal and whether one was reached. ``deal`` is the bool a deal formed (distinct from
	``success``, True on a correct no-deal); ``deal_named`` carries the deal as ``{issue: option}``. Falls back to
	an explicit ``final_deal`` then the last standing proposal."""
	reached = bool(outcome.get("deal", outcome.get("success")))
	fd_raw = outcome.get("deal_named") or outcome.get("final_deal")
	if isinstance(fd_raw, (dict, list, tuple)):
		try:
			return game.canonical_deal(fd_raw), True
		except (ValueError, KeyError, TypeError):
			pass
	if reached and standing:
		last_round = max(standing)
		return standing[last_round], True
	return None, reached
