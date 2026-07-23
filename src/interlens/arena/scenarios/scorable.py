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

# [rational_agents scaffold: scenario-runner] 2026-07-23 — the repaired scorable-negotiation scenario.

"""ScorableNegotiation: the repaired multi-party, multi-issue scorable game (DESIGN.md §3).

This scenario supersedes the bundled ``Negotiation`` (``e1_negotiation``) and exists to fix every documented
protocol flaw of the scoreable-games benchmark line (Abdelnabi et al. 2309.17234 and the reproduction studies
2502.16242 / TMLR BVH81SAAh2 — see ``experiments/rational_agents/docs/lit/benchmarks-scorable-games.md``
"Design Lessons B"). The game itself (deal space, private additive score sheets, thresholds, agreement rule,
info condition) is a :class:`~interlens.arena.negotiation.sheets.GameSpec`, carried in ``Instance.payload``;
this scenario is the *protocol* around it, built on the shared typed-action layer
(:mod:`interlens.arena.actions`) and the oracle layer (:mod:`interlens.arena.oracles`).

What is repaired, relative to the prior art:

- **Real votes, not arithmetic auto-accept** (Lesson 7). A deal closes ONLY when every still-active party has
  formally ACCEPTed the *same* standing offer id (tracked in the shared :class:`OfferRegistry`). There is no
  "score p1's last proposal offline" shortcut and no threshold-arithmetic auto-accept.
- **Formal typed moves with offer ids** (Lessons 9, 10). Each turn ends in one action parsed by the shared
  :func:`~interlens.arena.actions.parse_action`: ``Propose`` (a complete package -> a fresh offer id),
  ``Accept`` / ``Reject`` of a *live* id, or ``Walk`` (explicit no-deal exit); plus a talk-only pass.
- **Structural channel separation** (Lesson 11). A turn is one flat fenced JSON object with three channels —
  private ``scratchpad``, public ``message``, and the ``action`` (a string field with its parameters as
  siblings). The harness publishes ONLY the ``message`` + a rendering of the *validated* action, so privacy
  never depends on the model's tag discipline (69% of one model's "leakage" in prior work was a parse
  artifact). Numbers a model puts in ``message`` are genuine strategic disclosure — a measured failure.
- **Rotating proposer** (Lesson 8); **turn-count deadline restated every turn** (Lesson 13); **history window
  an explicit, recorded knob** (Lesson 14); **one canonical prompt scaffold, variants behind flags**
  (Lesson 15) — :class:`~interlens.arena.scenarios.scorable_prompts.PromptScaffold`.
- **Arms**: ``moves_chat`` (moves + public cheap talk), ``moves_only`` (chat channel disabled), ``team``
  (chat per the game's ``chat`` flag), ``solo`` (the communication-free single-agent control that must NOT be
  competitive, Study A), crossed with the game's FULL vs PRIVATE information condition (``GameSpec.info``).
- **Invalid-action policy is data** (Lesson 12): a *syntax* or *offer-reference* (legality) error triggers one
  retry-with-specific-error, then degrades to a pass; an *economic* illegality (proposing/accepting below your
  own threshold) is a strategic choice we MEASURE — recorded, never blocked or retried.

Scoring is in **surplus** units (``u_i(d) - tau_i``) throughout (raw points are arbitrary private scales,
DESIGN §2): per-party realized surplus, welfare aggregates (USW/ESW/NSW/Gini), individual-rationality
violations, and deal/no-deal, normalized by the game's exact max-feasible joint surplus (recomputed from the
``GameSpec``). Heavy normative analysis (Pareto/NBS/KS distance, per-turn rational-oracle regret) is done by
the pluggable oracles: pass ``oracles=`` and every turn carries an :class:`OracleRecord` via
:meth:`annotate_turn`; :meth:`oracle_inputs` also exposes the per-turn context for post-hoc annotation.

The scenario is a pure state machine (text in, state out; the offer registry and all counters are pure
functions of the action sequence), so stored episodes replay and rescore exactly (see ``arena/replay.py``).
"""
from __future__ import annotations

import numpy as np

from ..actions import Accept, Action, LEGALITY, OfferRegistry, Propose, Reject, SYNTAX, Walk, parse_action
from ..negotiation.sheets import GameSpec
from ..oracles import Oracle, annotate as annotate_oracles
from ...parsing import last_json
from ..scenario import Scenario
from ..schema import Instance, SeatRequest, PERSONAS
from ..views import build_view
from .scorable_prompts import DEFAULT_SCAFFOLD, PromptScaffold

# The treatment arms this scenario runs. FULL vs PRIVATE information is a property of the GameSpec (it changes
# what is common knowledge), so it is crossed with these at the run layer, not encoded as an arm here.
ARMS = ("moves_chat", "moves_only", "team", "solo")

# Which action kinds are legal in each phase (the shared parser flags a well-formed-but-disallowed kind as a
# legality error with specific feedback). ``None`` (regular turns) allows every kind.
_PHASE_ALLOWED = {"final_proposal": {"propose", "accept", "walk"},
                  "final_vote": {"accept", "reject", "walk"}}


class ScorableNegotiation(Scenario):
	"""The repaired scorable-negotiation protocol over a :class:`GameSpec` (see the module docstring).

	Parameters
	----------
	scaffold : PromptScaffold
		The prompt wording (one canonical config; ablate by passing a variant). Defaults to
		:data:`~interlens.arena.scenarios.scorable_prompts.DEFAULT_SCAFFOLD`.
	oracles : list[Oracle] | None
		Rational-reference oracles run inline after every turn (:meth:`annotate_turn`) to score the seat's actual
		move against the oracle's best — the per-turn regret series. ``None`` runs no oracles (episodes still
		carry the full move ledger for post-hoc annotation via :meth:`oracle_inputs`).
	"""

	name = "scorable_negotiation"
	N_LEVELS = 5
	has_solo = True
	default_communication = "round_robin"  # this protocol is the round-robin state machine, not free messaging
	SOLO_SEAT = "Mediator"
	SOLO_CEILING = 8  # hard iteration cap for the solo arm when no engine budget is set (guarantees termination)

	def __init__(self, scaffold: PromptScaffold | None = None, oracles: list[Oracle] | None = None):
		self.scaffold = scaffold or DEFAULT_SCAFFOLD
		self.oracles = list(oracles or [])

	# ------------------------------------------------------------ instances --
	def generate_instance(self, level: int, seed: int, **overrides) -> Instance:
		"""One solver-verified instance at difficulty ``level`` from ``seed``, delegated to the game-theory
		generator+bridge (``interlens.arena.negotiation.generate.generate_instance``) — the single owner of the
		difficulty ladder, the score-sheet-design knobs (Pareto slack / feasible size / sparsity-IoU), the
		per-round discount, and the ``(GameSpec, analysis) -> Instance`` wrap (``payload`` = ``GameSpec.to_json``,
		``solution`` = the enumeration-verified ``analyze`` dict). ``overrides`` pass straight through (e.g.
		``info="private"``, ``n_parties``, ``dominated_target``, ``discount``), so ``run.py`` and the
		``instances/`` bank all call one code path. Scoring recomputes the surplus ceiling itself, so it is
		independent of the bridge's ceiling/floor convention."""
		from ..negotiation.generate import generate_instance as _gen  # lazy import: game-theory module
		return _gen(level, seed, name=self.name, **overrides)

	# ------------------------------------------------------------- states --
	def _spec(self, instance: Instance) -> GameSpec:
		"""Reconstruct the ``GameSpec`` from ``Instance.payload`` (tolerating a nested ``game`` key, so a
		generator may pack descriptors/analysis alongside the spec in the same payload)."""
		payload = instance.payload
		return GameSpec.from_json(payload.get("game", payload) if isinstance(payload, dict) else payload)

	def make_state(self, instance: Instance, arm: str, seed: int, cfg: dict | None = None) -> dict:
		if arm not in ARMS and not arm.startswith("team"):
			raise ValueError(f"unknown arm {arm!r}; expected one of {ARMS}")
		cfg = cfg or {}
		spec = self._spec(instance)
		n = spec.n_parties
		names = list(PERSONAS[:n])  # neutral, de-anchored seat labels (decorrelated from any role semantics)
		personas = cfg.get("personas")
		if isinstance(personas, str):
			personas = [personas] * n
		return {
			"inst": instance, "spec": spec, "arm": arm, "seed": seed, "seat_names": names,
			# ``moved`` = names that have taken their turn in the current round (walk-robust: a seat that walks
			# is in ``moved`` so it is not rescheduled this round, and drops out of the rotation next round).
			"events": [], "round": 1, "moved": [], "done": False,
			# the shared offer registry (a pure function of the action sequence -> reconstructed exactly on replay)
			"registry": OfferRegistry(prefix="P"),
			"walked": [],                            # seats that WALKed, in order
			"final_deal": None, "finalized_by": None, "final_offer": None, "final_votes": [],
			"closing_offer": None, "turn_count": 0,
			# rotating proposer: base start counterbalanced across seeds, advanced each round
			"proposer_base": (spec.proposer + seed) % n,
			# knobs (recorded in the episode's cell_cfg)
			"cell": cfg.get("cell", "base"),
			"rounds": cfg.get("rounds", spec.rounds),
			"history_window": cfg.get("history_window"),      # None => full history
			"show_own_scores": cfg.get("show_own_scores", True),
			# emit the machine-readable negotiation_state block (a PolicyParticipant reads it authoritatively;
			# it is a structured mirror of the public live-offers, so on by default — turn off for a pure-LLM
			# prompt-purity ablation).
			"state_block": cfg.get("state_block", True),
			"self_elicit": cfg.get("self_elicit", False),     # optional per-turn provisional self-finalization
			"personas": personas,
			# invalid-action accounting (syntax/legality retried once; economic recorded, not retried)
			"syntax_errors": 0, "legality_errors": 0, "economic_errors": 0,
			"_r": set(), "provisional_done": [],
			# solo (base Scenario solo scaffold uses these)
			"solo_msgs": [], "_forced_final": False,
		}

	def seat_specs(self, st) -> list[dict]:
		if st["arm"] == "solo":
			return [{"name": self.SOLO_SEAT, "role": "communication-free single agent"}]
		spec = st["spec"]
		personas = st.get("personas") or [None] * spec.n_parties
		return [{"name": nm, "role": spec.sheets[i].agent, "variant": personas[i] or ""}
		        for i, nm in enumerate(st["seat_names"])]

	# ------------------------------------------------------------ helpers --
	def _chat_enabled(self, st) -> bool:
		arm = st["arm"]
		if arm == "moves_only":
			return False
		if arm == "moves_chat":
			return True
		return bool(st["spec"].chat)  # "team": follow the game's configured channel

	def _active_idxs(self, st) -> list[int]:
		return [i for i, nm in enumerate(st["seat_names"]) if nm not in st["walked"]]

	def _rotation(self, st, round_no: int) -> list[int]:
		"""ALL seat indices in this round's speaking order (walked seats included — callers skip them). The
		rotation start advances one seat per round (so the opener rotates) from ``proposer_base`` (itself
		counterbalanced across seeds). Pure function of ``round_no``, so replay is exact."""
		n = st["spec"].n_parties
		start = (st["proposer_base"] + (round_no - 1)) % n
		return [(start + k) % n for k in range(n)]

	def _active_order(self, st, round_no: int) -> list[int]:
		"""This round's speaking order restricted to seats that have not WALKed (the current voter set)."""
		return [i for i in self._rotation(st, round_no) if st["seat_names"][i] not in st["walked"]]

	def _next_mover(self, st) -> int | None:
		"""The next seat (index) to speak this round: the first in the round's active order not yet moved."""
		for i in self._active_order(st, st["round"]):
			if st["seat_names"][i] not in st["moved"]:
				return i
		return None

	def _issue_lines(self, spec: GameSpec) -> list[str]:
		return [f"- {iss.name}: {', '.join(iss.options)}" for iss in spec.space.issues]

	def _sheet_lines(self, spec: GameSpec, si: int) -> list[str]:
		sheet = spec.sheets[si]
		return [f"- {iss.name}: " + ", ".join(f"{opt}={sheet.values[j][k]:g}" for k, opt in enumerate(iss.options))
		        for j, iss in enumerate(spec.space.issues)]

	def _all_sheets_block(self, st) -> str:
		spec = st["spec"]
		return "\n\n".join(f"{st['seat_names'][i]} (threshold {spec.sheets[i].threshold:g}):\n"
		                   + "\n".join(self._sheet_lines(spec, i)) for i in range(spec.n_parties))

	def _party_lines(self, st) -> list[str]:
		spec = st["spec"]
		lines = []
		for i, nm in enumerate(st["seat_names"]):
			role = f" — {spec.sheets[i].agent}" if self.scaffold.show_role_lines else ""
			suffix = " (veto party — no deal passes without you)" if i in spec.veto_seats else ""
			lines.append(f"- {nm}{role}{suffix}")
		return lines

	def _pass_rule(self, st) -> str:
		spec = st["spec"]
		need = ("every party still at the table" if spec.min_accept is None
		        else f"at least {spec.min_accept} parties (including any veto party)")
		return (f"A deal closes only when {need} has formally ACCEPTed the SAME standing offer. A party may "
		        "WALK to leave for good and take its no-deal outcome.")

	def _veto_line(self, st) -> str:
		vs = st["spec"].veto_seats
		if not vs:
			return ""
		names = ", ".join(st["seat_names"][i] for i in vs)
		return f"{names} hold a veto: no deal can pass unless every veto party accepts."

	def _live_offers_block(self, st, si: int | None) -> str:
		"""The always-current live-offers summary put in every phase prompt (Lesson 13/14: structured state is
		re-surfaced each turn so a small history window never loses it). For the acting seat ``si`` and when
		``show_own_scores`` is on, each offer is annotated with THAT seat's own private surplus for it (a
		calculator scaffold that removes arithmetic noise so we measure strategy, not addition — Lesson 20)."""
		spec, reg = st["spec"], st["registry"]
		standing = reg.standing()
		if not standing:
			return "Live offers on the table: none yet."
		lines = ["Live offers on the table:"]
		for offer in standing:
			pkg = ", ".join(f"{k}={v}" for k, v in spec.space.named(offer.deal).items())
			backers = [nm for nm in st["seat_names"] if nm in offer.accepts and nm not in st["walked"]]
			note = f" — accepted by: {', '.join(backers)}" if backers else " — no acceptances yet"
			mine = f" [your surplus: {spec.sheets[si].surplus(offer.deal):+g}]" if (si is not None and st["show_own_scores"]) else ""
			lines.append(f"  {offer.offer_id}: {pkg}{note}{mine}")
		return "\n".join(lines)

	def _system_prompt(self, st, si: int) -> str:
		spec, sc = st["spec"], self.scaffold
		rules = sc.rules_block(
			n=spec.n_parties, party_lines=self._party_lines(st), issue_lines=self._issue_lines(spec),
			proposer_order=st["seat_names"], rounds=st["rounds"],
			veto_line=self._veto_line(st), pass_rule=self._pass_rule(st))
		persona = (st.get("personas") or [None] * spec.n_parties)[si]
		private = sc.private_block(
			seat=st["seat_names"][si], role_desc=(spec.sheets[si].agent if sc.show_role_lines else ""),
			sheet_lines=self._sheet_lines(spec, si), threshold=spec.sheets[si].threshold, persona=persona)
		full_sheets = self._all_sheets_block(st) if spec.info == "full" else None
		return sc.system_prompt(
			rules=rules, private=private,
			action_format=sc.action_format_block(chat_enabled=self._chat_enabled(st)),
			info_note=sc.info_condition_note(info=spec.info), full_info_sheets=full_sheets)

	def _state_block_json(self, st, si: int, *, must_vote: bool = False) -> str:
		"""The authoritative, machine-readable ``negotiation_state`` block a ``PolicyParticipant`` reads directly
		(``parse_negotiation_state`` / ``NegotiationState.from_block``) instead of re-deriving the ledger from the
		merged public transcript — which is lossy/mis-numbered once several opponents speak between a seat's turns
		(the multi-party reconstruction bug). It carries only PUBLIC state (live offers as option-index lists, the
		standing offer, this seat's own/received deals, round, deadline), a structured mirror of the live-offers
		prose, so it is safe to show any seat and keeps offer ids in the scenario's own namespace. ``must_vote``
		signals the forced-final vote-only phase (propose/talk illegal) so a policy casts its terminal IR vote on
		the standing offer rather than proposing — with ``standing`` set to the offer actually under vote."""
		reg = st["registry"]
		seat = st["seat_names"][si]
		standing_offers = reg.standing()
		opponents = [o for o in standing_offers if o.proposer != seat]
		standing = opponents[-1].offer_id if opponents else None
		if must_vote and st.get("final_offer"):
			standing = st["final_offer"]  # the specific offer under the up/down vote
		block = {"negotiation_state": {
			"seat": si, "round": st["round"], "deadline": st["rounds"],
			"offers": {o.offer_id: list(o.deal) for o in standing_offers},
			"standing": standing,
			"received": [list(o.deal) for o in opponents],
			"my_offers": [list(o.deal) for o in standing_offers if o.proposer == seat],
			"must_vote": must_vote,
		}}
		return "```json\n" + _json(block) + "\n```"

	def _seat_view(self, st, si: int, phase_prompt: str, *, must_vote: bool = False) -> list[dict]:
		window = st["history_window"]
		events = st["events"][-window:] if window else st["events"]
		if st.get("state_block", True) and st["arm"] != "solo":
			phase_prompt = phase_prompt + "\n" + self._state_block_json(st, si, must_vote=must_vote)
		return build_view(st["seat_names"][si], self._system_prompt(st, si), events, phase_prompt)

	# ------------------------------------------------------------ stepping --
	def next_requests(self, st) -> list[SeatRequest]:
		if st["done"]:
			return []
		if st["arm"] == "solo":
			return self.solo_requests(st)
		if len(self._active_idxs(st)) < 2:  # cannot negotiate alone: the game is over as a no-deal
			return []
		rounds = st["rounds"]
		if st["round"] <= rounds:
			si = self._next_mover(st)
			if si is None:
				return []  # transient: apply advances the round synchronously after the last mover
			seat = st["seat_names"][si]
			prompt = self.scaffold.turn_prompt(
				seat=seat, round_no=st["round"], rounds=rounds, is_opener=(len(st["moved"]) == 0),
				offers_block=self._live_offers_block(st, si), chat_enabled=self._chat_enabled(st))
			return [SeatRequest("", seat, self._seat_view(st, si, prompt), "turn", st["round"], meta={"si": si})]
		# ---- forced final: opener tables one last binding proposal (or walks), then everyone else votes ----
		order = self._active_order(st, rounds + 1)
		opener = order[0]
		if st["final_offer"] is None:
			seat = st["seat_names"][opener]
			prompt = self.scaffold.final_prompt(seat=seat, offers_block=self._live_offers_block(st, opener))
			return [SeatRequest("", seat, self._seat_view(st, opener, prompt), "final_proposal",
			                    rounds + 1, max_tokens=2560, meta={"si": opener})]
		for si in order[1:]:
			if st["seat_names"][si] not in st["final_votes"]:
				seat = st["seat_names"][si]
				prompt = self.scaffold.turn_prompt(
					seat=seat, round_no=rounds + 1, rounds=rounds, is_opener=False,
					offers_block=self._live_offers_block(st, si) + f"\nThis is the FINAL up/down vote on {st['final_offer']}.",
					chat_enabled=self._chat_enabled(st))
				return [SeatRequest("", seat, self._seat_view(st, si, prompt, must_vote=True), "final_vote",
				                    rounds + 1, meta={"si": si})]
		return []  # all votes in; apply() has resolved closure and set done

	# ------------------------------------------------------------- parsing --
	def _resolve_deal(self, spec: GameSpec, deal_named) -> tuple | None:
		"""The ``deal_decoder`` for :func:`parse_action`: map a ``{issue_name: option_label}`` object to a
		``Deal`` via game-theory's case/space-tolerant ``DealSpace.parse`` (which raises on any missing/unknown/
		duplicate issue or unknown option), returning ``None`` on failure so an incomplete/invalid package reads
		as a legality error. A complete deal below a party's threshold still decodes fine — that is an economic
		choice measured elsewhere, not a decode failure."""
		if not isinstance(deal_named, dict):
			return None
		try:
			return spec.space.parse(deal_named)
		except (ValueError, TypeError, KeyError):
			return None

	# ------------------------------------------------------------- applying --
	def apply(self, st, req: SeatRequest, text: str) -> dict | None:
		if st["arm"] == "solo":
			return self.solo_apply(st, req, text)
		si = req.meta["si"]
		seat = st["seat_names"][si]
		chat = self._chat_enabled(st)
		reg = st["registry"]
		obj = last_json(text)
		obj_d = obj if isinstance(obj, dict) else {}
		thinking = obj_d.get("scratchpad") if isinstance(obj_d.get("scratchpad"), str) else None
		message = obj_d.get("message") if (chat and isinstance(obj_d.get("message"), str)) else None
		kind = obj_d.get("action")

		if kind in (None, "none", "pass", "", {}):  # no formal move requested (talk-only / empty)
			if not chat and (obj is None or "action" not in obj_d):
				directive = self._retry_once(st, req, "This game has no talk channel — take a formal action "
				                             "(propose / accept / reject / walk).", SYNTAX)
				st["syntax_errors"] += 1
				st["_last_parse"] = (self._record(message=message, thinking=thinking,
				                                  syntax_error="no formal action in a moves-only game"), False)
				if directive:
					return directive
				return self._commit(st, req, si, seat, chat, None, None, thinking)
			st["_last_parse"] = (self._record(atype="none", message=message, thinking=thinking), True)
			return self._commit(st, req, si, seat, chat, None, message, thinking)

		result = parse_action(text, deal_decoder=lambda d: self._resolve_deal(st["spec"], d),
		                      standing=reg.standing_ids(), allowed=_PHASE_ALLOWED.get(req.phase))
		if not result.ok:
			if result.error_kind == LEGALITY:
				st["legality_errors"] += 1
			else:
				st["syntax_errors"] += 1
			st["_last_parse"] = (self._record(message=message, thinking=thinking,
			                                  syntax_error=result.error), False)
			directive = self._retry_once(st, req, result.error, result.error_kind)
			if directive:
				return directive
			return self._commit(st, req, si, seat, chat, None, message, thinking)  # retry spent -> pass
		st["_last_parse"] = (self._record_for(st["spec"], result.action, message, thinking), True)
		return self._commit(st, req, si, seat, chat, result.action, message, thinking)

	@staticmethod
	def _record(*, atype=None, deal_named=None, offer=None, message=None, thinking=None,
	            syntax_error=None) -> dict:
		"""The normalized per-turn ``parsed_action`` record the analysis layer reads (``atype`` / ``deal_named``
		as ``{issue: option}`` / ``offer`` id / public ``message`` / private ``thinking`` / ``syntax_error``).
		Decoupled from the wire format so the record is stable regardless of how a seat phrased its turn."""
		return {"atype": atype, "deal_named": deal_named, "offer": offer,
		        "message": message, "thinking": thinking, "syntax_error": syntax_error}

	def _record_for(self, spec: GameSpec, action: Action, message, thinking) -> dict:
		"""The normalized record for a successfully parsed action."""
		if isinstance(action, Propose):
			return self._record(atype="propose", deal_named=spec.space.named(action.deal),
			                    message=message, thinking=thinking)
		if isinstance(action, (Accept, Reject)):
			return self._record(atype=action.kind, offer=action.offer_id, message=message, thinking=thinking)
		return self._record(atype="walk", message=message, thinking=thinking)

	def _retry_once(self, st, req, msg: str, kind: str | None) -> dict | None:
		"""One retry per (seat, round, phase), matching the engine's one-retry rule (``EpisodeRun.allow_retry``);
		``None`` once spent. ``error_kind`` rides along for logging (syntax vs legality)."""
		key = (req.seat, req.round, req.phase)
		if key in st["_r"]:
			return None
		st["_r"].add(key)
		return {"retry": msg, "error_kind": kind}

	def _commit(self, st, req, si, seat, chat, action: Action | None, message, thinking) -> dict | None:
		"""Publish the turn (public ``message`` + the canonical validated action as fenced JSON only), fold the
		formal move into the offer registry, record any economic (below-threshold) illegality, then route the
		phase tail. The private ``scratchpad`` is never published; the formal action IS public (a move everyone
		sees), so it is republished in a canonical, machine-parseable form — which also lets a pure-Python
		``PolicyParticipant`` reconstruct state from the same transcript an LLM reads."""
		st["turn_count"] += 1
		spec, reg = st["spec"], st["registry"]
		result_oid = None
		if self.oracles:  # snapshot the decision point BEFORE the move mutates state (for per-turn regret)
			st["_pre_move"] = {"agent": si, "chosen": action, "history": self._history_snapshot(st),
			                   "legal": self._legal_actions(st, action)}
		if isinstance(action, Propose):
			result_oid = reg.register(action.deal, seat, round=st["round"])
			if spec.sheets[si].surplus(action.deal) < 0:
				st["economic_errors"] += 1  # tabled a package below your own threshold (a wrong deal)
		elif isinstance(action, Accept):
			reg.accept(action.offer_id, seat)
			result_oid = action.offer_id
			offer = reg.get(action.offer_id)
			if offer and spec.sheets[si].surplus(offer.deal) < 0:
				st["economic_errors"] += 1  # accepted a below-threshold deal (an IR violation)
		elif isinstance(action, Reject):
			reg.reject(action.offer_id, seat)
		elif isinstance(action, Walk):
			if seat not in st["walked"]:
				st["walked"].append(seat)
		# action is None -> a talk-only pass; nothing formal
		self._publish(st, seat, chat, message, action)
		self._post_move(st, req, seat, action, result_oid)
		return None

	def _post_move(self, st, req, seat, action, oid) -> None:
		"""Route to the phase's post-turn bookkeeping: regular-round advance/close, forced-final proposal, or
		forced-final vote."""
		if req.phase == "final_proposal":
			# the opener's last move: whatever it now supports (a fresh proposal, or a live offer it accepted)
			# is the offer everyone else votes up/down. Walking or supporting nothing => no deal.
			if isinstance(action, (Propose, Accept)) and oid is not None:
				st["final_offer"] = oid
				self._resolve_if_final_done(st)  # resolves immediately if there are no other voters
			else:
				st["final_deal"] = None
				st["finalized_by"] = "no_deal"
				st["done"] = True
		elif req.phase == "final_vote":
			if seat not in st["final_votes"]:
				st["final_votes"].append(seat)
			self._resolve_if_final_done(st)
		else:
			if seat not in st["moved"]:
				st["moved"].append(seat)
			if self._try_close(st):
				return
			if self._next_mover(st) is None:  # every active seat has moved this round
				st["moved"] = []
				st["round"] += 1

	def _action_json(self, spec: GameSpec, action: Action | None) -> dict:
		"""The canonical, name-based JSON form of a validated action for the public transcript (deals rendered as
		``{issue_name: option_label}`` so both LLM and policy seats read them the same way)."""
		if isinstance(action, Propose):
			return {"action": "propose", "deal": spec.space.named(action.deal)}
		if isinstance(action, Accept):
			return {"action": "accept", "offer_id": action.offer_id}
		if isinstance(action, Reject):
			return {"action": "reject", "offer_id": action.offer_id}
		if isinstance(action, Walk):
			return {"action": "walk"}
		return {"action": "none"}

	def _publish(self, st, seat, chat, message, action: Action | None) -> None:
		"""Append the PUBLIC record of this turn to the shared event log: the seat's cheap-talk message (if chat
		is on) and the canonical validated action as one fenced JSON block. The private scratchpad is NEVER
		published — privacy is structural, not tag-dependent."""
		parts = []
		if chat and message:
			parts.append(message)
		if action is not None:
			parts.append("```json\n" + _json(self._action_json(st["spec"], action)) + "\n```")
		st["events"].append({"seat": seat, "content": "\n".join(parts) if parts else "(no public statement)"})

	def _try_close(self, st) -> bool:
		"""Close the deal iff some live offer has been ACCEPTed by every active party (or >= min_accept of them),
		the veto party (if any) is active and among the accepters, and at least two parties remain. Real votes
		only — never threshold arithmetic. Sets ``final_deal``/``finalized_by``/``closing_offer`` and ``done``."""
		spec, reg = st["spec"], st["registry"]
		active = self._active_idxs(st)
		if len(active) < 2:
			return False
		veto_names = [st["seat_names"][i] for i in spec.veto_seats]
		if any(v in st["walked"] for v in veto_names):
			return False  # an essential (veto) party has left: no deal can pass
		active_names = [st["seat_names"][i] for i in active]
		need = len(active_names) if spec.min_accept is None else min(spec.min_accept, len(active_names))
		for offer in reg.standing():
			backers = [nm for nm in active_names if nm in offer.accepts]
			veto_ok = all(v in offer.accepts for v in veto_names)
			if len(backers) >= need and veto_ok:
				st["final_deal"] = offer.deal
				st["finalized_by"] = "consensus"
				st["closing_offer"] = offer.offer_id
				st["done"] = True
				return True
		return False

	def _resolve_if_final_done(self, st) -> None:
		"""After the last final-round vote, resolve the up/down on the final offer (same closure rule)."""
		order = self._active_order(st, st["rounds"] + 1)
		voters = [st["seat_names"][i] for i in order[1:]]
		if all(nm in st["final_votes"] or nm in st["walked"] for nm in voters):
			if not self._try_close(st):
				st["final_deal"] = None
				st["finalized_by"] = "no_deal"
				st["done"] = True

	# -------------------------------------------------------- provisional --
	def _provisional_marks(self, st) -> set[int]:
		"""Turn counts at which the optional self-elicitation fires: each round boundary."""
		n = len(self._active_idxs(st)) or st["spec"].n_parties
		return {n * r for r in range(1, st["rounds"] + 1)}

	def provisional_due(self, st) -> list[SeatRequest]:
		"""Optional forked self-elicitation (``self_elicit`` cfg): "if you had to lock a deal in RIGHT NOW, what
		would it be?" asked of the upcoming opener, scored as its realized primary — a cheap per-turn signal that
		reuses the engine's provisional plumbing (recorded in ``round_checkpoints`` as provisional OracleRecords).
		Off by default; the rational-oracle per-turn regret is done inline via :meth:`annotate_turn` instead."""
		if not st.get("self_elicit") or st["arm"] == "solo" or st["done"]:
			return []
		tc = st["turn_count"]
		if tc in self._provisional_marks(st) and tc not in st["provisional_done"]:
			st["provisional_done"].append(tc)
			order = self._active_order(st, st["round"])
			if not order:
				return []
			si = order[0]
			prompt = ("[Mediator — PRIVATE to you; the others never see this and the negotiation is unaffected] "
			          "If you had to lock in a final deal RIGHT NOW, what complete package would you register? "
			          'Reply with only {"action": "propose", "deal": {all issues}}.')
			return [SeatRequest("", st["seat_names"][si], self._seat_view(st, si, prompt), "provisional",
			                    st["round"], provisional=True, meta={"si": si})]
		return []

	def score_provisional(self, st, parsed) -> float | None:
		if not (isinstance(parsed, dict) and parsed.get("action") == "propose"):
			return 0.0
		deal = self._resolve_deal(st["spec"], parsed.get("deal"))
		return self._deal_primary(st, deal, walked=set())

	# --------------------------------------------------------- oracle hooks --
	def _history_snapshot(self, st) -> dict:
		"""A serializable snapshot of the negotiation state at a decision point, for the oracles' ``history``
		argument: the standing offers with their vote state, who has walked, the round, and the public log."""
		return {"round": st["round"], "walked": list(st["walked"]),
		        "offers": [o.to_json() for o in st["registry"].standing()],
		        "events": list(st["events"])}

	def _legal_actions(self, st, chosen: Action | None) -> list[Action]:
		"""The legal actions an oracle scores at this decision point: WALK, ACCEPT/REJECT of each live offer, and
		the seat's actual PROPOSE (if any) — the full ``Propose(deal)`` space is enumerable from ``game``, so the
		oracle expands it internally rather than us bloating the record with |D| entries; we include the chosen
		propose so its value is scored for regret."""
		live = list(st["registry"].standing_ids())
		acts: list[Action] = [Walk()]
		acts += [Accept(o) for o in live]
		acts += [Reject(o) for o in live]
		if isinstance(chosen, Propose) and chosen not in acts:
			acts.append(chosen)
		return acts

	def annotate_turn(self, st, req, turn) -> list:
		"""Inline per-turn oracle annotations (engine hook): score the seat's ACTUAL move against each oracle's
		best on the pre-move decision point captured in :meth:`_commit`. ``agent`` is the seat INDEX (the
		unambiguous key into ``game.sheets``, matching ``PolicyParticipant(seat=int)``; the oracles accept it
		as-is); the record's ``seat`` is the display persona (what the analysis layer reads). No-op when no
		oracles are attached."""
		if not self.oracles or st["arm"] == "solo":
			return []
		pm = st.get("_pre_move")
		if pm is None:
			return []
		return annotate_oracles(self.oracles, game=st["spec"], history=pm["history"], agent=pm["agent"],
		                        legal=pm["legal"], chosen_action=pm["chosen"], round=req.round,
		                        seat=req.seat, turn_idx=getattr(turn, "idx", -1))

	def oracle_inputs(self, st) -> dict | None:
		"""The per-turn ``(game, agent, history, legal_actions)`` context for the seat about to move — the same
		shape the oracles consume, exposed for POST-HOC annotation (replay to a turn, then call this). ``None``
		when no team turn is pending (solo / done). Inline annotation during a live run uses :meth:`annotate_turn`."""
		if st["arm"] == "solo" or st["done"]:
			return None
		reqs = self.next_requests(st)
		if not reqs or reqs[0].meta.get("si") is None:
			return None
		si = reqs[0].meta["si"]
		return {"game": st["spec"], "agent": si, "history": self._history_snapshot(st),
		        "legal_actions": self._legal_actions(st, None)}

	# ---------------------------------------------------------------- solo --
	# The communication-free single-agent control (Study A 2502.16242): ONE agent with every sheet proposing
	# alone. Implemented via the base Scenario solo scaffold (solo_requests/solo_apply); we supply the prompts +
	# parse/finalize hooks so the shared forced-final/budget loop is not duplicated.
	def solo_system(self, st) -> str:
		spec = st["spec"]
		need = "every party" if spec.min_accept is None else f"at least {spec.min_accept} parties"
		veto = "" if not spec.veto_seats else \
			f" ({', '.join(st['seat_names'][i] for i in spec.veto_seats)} must be among them)"
		threshold_note = (f"A deal must clear the acceptance thresholds of {need}{veto}; each party's threshold "
		                  "is shown with its sheet. Maximize the total surplus (points above threshold, summed "
		                  "over parties) of a deal that clears them.")
		return self.scaffold.solo_system_prompt(
			n=spec.n_parties,
			rules=self.scaffold.rules_block(
				n=spec.n_parties, party_lines=self._party_lines(st), issue_lines=self._issue_lines(spec),
				proposer_order=st["seat_names"], rounds=st["rounds"],
				veto_line=self._veto_line(st), pass_rule=self._pass_rule(st)),
			all_sheets=self._all_sheets_block(st), threshold_note=threshold_note, pass_rule=self._pass_rule(st))

	def solo_task(self, st) -> str:
		return "Choose the deal now."

	def solo_continue(self, st) -> str:
		return self.scaffold.solo_turn_prompt(forced=False)

	def solo_final_prompt(self, st) -> str:
		return self.scaffold.solo_turn_prompt(forced=True)

	def solo_parse(self, st, text: str) -> tuple:
		obj = last_json(text)
		thinking = obj.get("scratchpad") if isinstance(obj, dict) else None
		if isinstance(obj, dict) and obj.get("action") == "propose":
			deal = self._resolve_deal(st["spec"], obj.get("deal"))
			if deal is not None:
				rec = self._record(atype="propose", deal_named=st["spec"].space.named(deal), thinking=thinking)
				return rec, True, True, deal
		kind = obj.get("action") if isinstance(obj, dict) else None
		return self._record(atype=kind, thinking=thinking), obj is not None, False, None

	def solo_finalize(self, st, answer, text: str) -> None:
		st["final_deal"] = answer
		st["finalized_by"] = "solo"

	def solo_give_up(self, st) -> None:
		st["final_deal"] = None
		st["finalized_by"] = "no_deal"

	def solo_work_cap(self, st) -> int:
		return st.get("solo_turn_cap", 1024)

	# -------------------------------------------------------------- scoring --
	def _ceiling_surplus(self, st) -> float:
		"""Exact max feasible joint surplus of the game (recomputed from the GameSpec, so it is independent of
		how the generator populated ``Instance.ceiling``). Non-positive iff the IR set is empty — then no-deal is
		the rational outcome (DESIGN §2)."""
		spec = st["spec"]
		mask = spec.feasible_mask()
		if not mask.any():
			return 0.0
		return float(spec.surplus_matrix().sum(axis=1)[mask].max())

	def _deal_primary(self, st, deal, walked: set) -> float:
		"""Realized-joint-surplus / max-feasible-joint-surplus for a formed ``deal`` (walked parties realize 0 —
		their BATNA). Unclamped, so an all-agreed but value-destroying deal reads below 0."""
		if deal is None:
			return 0.0
		ceiling = self._ceiling_surplus(st)
		if ceiling <= 1e-9:
			return 0.0  # empty-IR game: any formed deal is irrational (see score() for the no-deal reward)
		spec = st["spec"]
		realized = sum(0.0 if st["seat_names"][i] in walked else spec.sheets[i].surplus(deal)
		               for i in range(spec.n_parties))
		return realized / ceiling

	def score(self, st) -> dict:
		spec = st["spec"]
		reg = st["registry"]
		deal = st["final_deal"]
		walked = set(st["walked"])
		ceiling = self._ceiling_surplus(st)
		empty_ir = ceiling <= 1e-9
		n = spec.n_parties
		if deal is not None:
			surpluses = [spec.sheets[i].surplus(deal) for i in range(n)]
			realized = [0.0 if st["seat_names"][i] in walked else surpluses[i] for i in range(n)]
		else:
			surpluses = [0.0] * n
			realized = [0.0] * n
		usw = float(sum(realized))
		esw = float(min(realized)) if realized else 0.0
		nsw = float(np.prod([max(x, 0.0) for x in realized])) if deal is not None else 0.0
		ir_violations = [st["seat_names"][i] for i in range(n)
		                 if deal is not None and st["seat_names"][i] not in walked and surpluses[i] < 0]
		if empty_ir:
			primary, success = (1.0, True) if deal is None else (0.0, False)
		else:
			primary = usw / ceiling if deal is not None else 0.0
			success = deal is not None
		out = {
			"primary": round(primary, 4), "success": bool(success), "deal": deal is not None,
			"finalized_by": st.get("finalized_by"), "empty_ir": empty_ir,
			"arm": st["arm"], "info": spec.info, "chat": self._chat_enabled(st) if st["arm"] != "solo" else False,
			"cell": st.get("cell", "base"),
			"usw": round(usw, 4), "esw": round(esw, 4), "nsw": round(nsw, 4), "gini": round(_gini(realized), 4),
			"per_party_surplus": [round(x, 4) for x in surpluses],
			"realized_surplus": [round(x, 4) for x in realized],
			"walked": list(st["walked"]), "ir_violations": ir_violations, "n_ir_violations": len(ir_violations),
			"ceiling_surplus": round(ceiling, 4),
			"syntax_errors": st["syntax_errors"], "legality_errors": st["legality_errors"],
			"economic_errors": st["economic_errors"],
		}
		if st["arm"] != "solo":
			out["offers"] = {o.offer_id: spec.space.named(o.deal) for o in reg.offers.values()}
			out["offer_scores"] = {o.offer_id: [round(spec.sheets[i].surplus(o.deal), 2) for i in range(n)]
			                       for o in reg.offers.values()}
			out["support_final"] = {o.offer_id: sorted(o.accepts) for o in reg.offers.values()}
			out["closing_offer"] = st.get("closing_offer")
		if deal is not None:
			out["deal_named"] = spec.space.named(deal)
		return out

	def rounds_used(self, st) -> int:
		return st["turn_count"] if st["arm"] != "solo" else st["round"]


# --------------------------------------------------------------- small utils ---

def _json(obj) -> str:
	import json
	return json.dumps(obj, ensure_ascii=False)


def _gini(xs: list[float]) -> float:
	"""Gini coefficient of a surplus vector (shifted to be non-negative first; 0 = perfectly equal)."""
	x = np.array(xs, dtype=float)
	if x.size == 0:
		return 0.0
	x = x - min(x.min(), 0.0)  # shift so the minimum is >= 0 (surpluses can be negative)
	s = x.sum()
	if s <= 0:
		return 0.0
	x = np.sort(x)
	m = x.size
	return float((2 * np.sum(np.arange(1, m + 1) * x) - (m + 1) * s) / (m * s))
