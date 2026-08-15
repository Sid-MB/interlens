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
#
# [implement: auctions | 2026-08-15 | session 68537820-d6a1-44ca-88b5-847d81e4811a]

"""Repeated multi-bidder auctions as one :class:`~interlens.arena.scenario.Scenario`.

An episode is ``T`` auction stages played by the same five bidders over one frozen
:class:`~interlens.arena.auction.spec.AuctionSpec`. **Formats are mechanism configs and repetition is the
horizon; neither forks a runner** — the failure mode that rule prevents (divergent per-format runners drifting
apart) is exactly what a format x channel x horizon factorial cannot survive.

The stage loop (design.md §3.1)::

    for t in 1..T:
        publish the stage catalogue (B_jt, blurbs, tie-break permutation, stages remaining)
        render each seat's private block for stage t
        for r in 1..talk_rounds:   message round (broadcast and/or DM, per channel)
        run the format's bidding rounds
        settle: allocation, payments, executed transfers (dm_transfers only)
        publish the stage result under the format's disclosure rule
        append to the carried history

Privacy is structural, not a property of the wording: a turn view is assembled here from a shared public part
plus exactly one private block belonging to the reading seat, and a DM reaches only the seats
:class:`~interlens.arena.auction.actions.DMRouter` delivers it to. ``tests/test_auction_scenario.py`` asserts
that programmatically over a whole episode rather than trusting the templates.

All prose lives in :mod:`.auction_prompts`, which transcribes the reviewed and frozen templates. Nothing in
this module originates model-facing wording.
"""
from __future__ import annotations

import json
import math
from collections import Counter

import numpy as np

from ..auction import actions as A
from ..auction import priors
from ..auction.allocation import Allocation, ValueModel, sealed_single_outcome
from ..auction.benchmarks import stage_benchmark
from ..auction.metrics import StageOutcome, stage_metrics
from ..auction.spec import AuctionSpec, Mechanism, card_scramble_seed, scramble_public_cards
from ..engine import EMPTY_TURN_PLACEHOLDER
from ..scenario import Scenario
from ..schema import Instance, SeatRequest
from . import auction_policy, auction_prompts as P
from .auction_prompts import DEFAULT_AUCTION_SCAFFOLD, AuctionPromptScaffold

#: Phases the scenario emits, recorded on every ``TurnRecord`` so the analysis can split message turns from
#: priced turns without re-parsing anything.
TALK_PHASE = "talk"
BID_PHASE = "bid"

#: Families that get the mid-stage message round of design.md §3.4 ("once more before the final bidding round
#: in clock formats"). Sealed and SAA stages do not: a sealed stage has one bidding round, and an SAA stage's
#: standing-bid table is itself a live channel between rounds.
MID_STAGE_TALK_FAMILIES = ("dutch", "english")

#: Per-turn output cap. The hosted-seat floor is applied by the participant (``--api-turn-token-floor``); this
#: is the scenario's own request, raised for the bidding turn of a 20-lot stage where the model has a whole
#: catalogue to reason over.
DEFAULT_TURN_MAX_TOKENS = 4096


# --------------------------------------------------------------------------------------------------------- #
# Clock geometry — derived once, never restated.
# --------------------------------------------------------------------------------------------------------- #
def clock_start(spec) -> int:
    """The clock start price used by every stage of a clock-family episode.

    Derived from the frozen draws rather than stored: the largest per-stage ``clock_ceiling`` (itself set
    above that stage's maximum realized valuation), rounded up onto the increment grid. One start for the
    whole episode keeps the system prompt's printed clock consistent with every stage's turn view, and makes
    the ceiling reachable only by a bidder bidding above every value in the stage — which is what makes
    ``clock_ceiling_rate`` a protocol-failure statistic rather than an ordinary outcome."""
    mech = spec.mechanism
    top = max(st.clock_ceiling for st in spec.stages)
    span = max(0, int(top) - int(mech.reserve))
    return int(mech.reserve) + int(math.ceil(span / mech.increment)) * int(mech.increment)


def clock_round_cap(spec) -> int:
    """Number of clock rounds needed to walk from the start price to the reserve (or back), inclusive."""
    mech = spec.mechanism
    return int((clock_start(spec) - int(mech.reserve)) // int(mech.increment)) + 1


def opening_clock_price(spec) -> int:
    """Where a clock family's price starts in each stage.

    The two clocks run in opposite directions and start at opposite ends: a DESCENDING (Dutch) clock starts
    above every realized valuation and falls, while an ASCENDING (English) clock starts at the RESERVE and
    rises. Deriving both from :func:`clock_start` without the direction was a real bug — it opened the English
    clock above every value, so every seat exited in the first round and the stage ended before any price
    discovery happened at all."""
    mech = spec.mechanism
    if not mech.is_clock:
        return None
    return int(mech.reserve) if mech.family == "english" else clock_start(spec)


# --------------------------------------------------------------------------------------------------------- #
# The scenario.
# --------------------------------------------------------------------------------------------------------- #
class AuctionScenario(Scenario):
    """Five bidders, ``T`` stages, one mechanism config, one communication rung.

    Parameters
    ----------
    scaffold : AuctionPromptScaffold | None
        The frozen wording. ``None`` uses :data:`~.auction_prompts.DEFAULT_AUCTION_SCAFFOLD`; a variant
        scaffold is how a wording ablation is run, never an edit to this class.
    turn_max_tokens : int
        Per-turn output cap requested on every :class:`~interlens.arena.schema.SeatRequest`. The engine's
        budget can shrink it and never raise it, so a hosted floor is applied at the participant.
    """

    name = "auction"
    N_LEVELS = 1
    has_solo = False
    default_communication = "round_robin"

    def __init__(self, scaffold: AuctionPromptScaffold | None = None,
                 turn_max_tokens: int = DEFAULT_TURN_MAX_TOKENS):
        self.scaffold = scaffold or DEFAULT_AUCTION_SCAFFOLD
        self.turn_max_tokens = int(turn_max_tokens)

    # -- instances -----------------------------------------------------------------------------------------
    def generate_instance(self, level: int, seed: int, **overrides) -> Instance:
        """Generate one auction instance from ``seed``.

        The payload carries the frozen spec under both value structures — ``apv`` (the default and the home of
        the repeated questions) and ``ipv`` (the belief-free benchmark) — because switching structure zeroes
        ``beta`` and ``sigma_z`` rather than redrawing, so the two are a within-bank paired contrast rather
        than two populations. Freezing both means a cell selects rather than re-derives."""
        from ..auction.spec import generate_spec
        mech = overrides.pop("mechanism", None) or Mechanism.saa(n_items=overrides.pop("n_items", 20))
        horizon = int(overrides.pop("horizon", 16))
        specs = {vs: generate_spec(seed, mechanism=mech, value_structure=vs, horizon=horizon, **overrides)
                 for vs in ("apv", "ipv")}
        payload = {"specs": {vs: s.to_json() for vs, s in specs.items()},
                   "generator": {"seed": int(seed), "n_items": mech.n_items, "horizon": horizon,
                                 "mechanism": mech.to_json()}}
        return Instance(instance_id=f"auction-{seed}", scenario=self.name, level=level, seed=seed,
                        payload=payload, ceiling=1.0, floor=0.0, solution={})

    # -- state ---------------------------------------------------------------------------------------------
    def make_state(self, instance: Instance, arm: str, seed: int, cfg: dict | None = None) -> dict:
        """Fresh episode state: the cell's spec (value structure, mechanism, horizon, channel selected from
        ``cfg``), the ledger, the DM router, and the empty history the stage loop appends to."""
        cfg = dict(cfg or {})
        spec = self.spec_for(instance, cfg)
        seats = tuple(b.persona_id for b in spec.bidders)
        st = {
            "events": [], "round": 1, "done": False, "arm": arm,
            "spec": spec, "instance_id": instance.instance_id, "seed": int(seed), "cfg": cfg,
            "seat_names": seats,
            "stage": 1, "phase": TALK_PHASE if self._talks(spec) else BID_PHASE,
            "talk_round": 1, "bid_round": 1,
            "ledger": A.BidLedger(spec.n_items, activity_rule=spec.mechanism.activity_rule),
            "dm": A.DMRouter(seats, dm_cap=spec.dm_cap),
            "transfers": A.TransferBook(),
            "broadcasts": [],                 # {stage, round, phase, sender, text}
            "stage_results": [],              # one published result dict per settled stage
            "own_results": [],                # per stage: {seat: {"lots", "paid", "surplus"}}
            "outcomes": [],                   # per stage: the StageOutcome json + metrics
            "clock_price": opening_clock_price(spec),
            "exits": {},                      # stage -> {seat: exit price}
            "pass_round": {},                 # (stage, seat, item) -> round the seat ratcheted out
            "wave": {},                       # seat -> the action recorded this wave
            "_awaiting": list(range(spec.n_bidders)),
            "_views": {},                     # seat -> the view built for the current wave
            "_r": set(), "_last_parse": (None, False),
            "policy_seats": {int(k): v for k, v in (cfg.get("policy_seats") or {}).items()},
            "hygiene": Counter(),
            "clock_ceiling_stages": [],
            # The mid-stage message round of design.md §3.4: on a clock, one extra talk wave once the clock has
            # crossed the middle of its schedule, so a ring can be TESTED mid-stage and not only formed before
            # it. ``mid_talk_active`` marks the wave in flight; ``mid_talk_done`` is the set of stages that have
            # already had theirs (at most one per stage).
            "mid_talk_active": False,
            "mid_talk_done": set(),
        }
        st["_awaiting"] = list(self._wave_seats(st))
        return st

    def spec_for(self, instance: Instance, cfg: dict):
        """The cell's spec: the frozen bank draws under the cell's value structure, with the cell's mechanism,
        horizon, and channel applied.

        A cell never redraws. ``mechanism`` may be replaced (a single-lot bank serves the sealed, Dutch, and
        English cells from identical draws, which is what makes R3 <-> R4 a within-bank paired contrast), but
        its lot count may not change, since the draws are per-lot.

        ``cfg["scramble_cards"]`` is the X1 control: the five public cards are permuted across the seats under
        a derangement seeded from the INSTANCE ID, so X1 and its matched real-persona cell O1 read the same
        frozen draws and the same scramble in every rerun (:func:`~interlens.arena.auction.spec
        .scramble_public_cards`). It is applied last, after the mechanism, horizon and channel, so a scrambled
        cell differs from its reference cell in the cards and in nothing else."""
        payload = instance.payload
        vs = cfg.get("value_structure", "apv")
        spec = AuctionSpec.from_json(payload["specs"][vs] if "specs" in payload else payload["spec"])
        mech_cfg = cfg.get("mechanism")
        if mech_cfg is not None:
            mech = Mechanism.from_json(mech_cfg) if isinstance(mech_cfg, dict) else mech_cfg
            if mech.n_items != spec.n_items:
                raise ValueError(f"cell mechanism auctions {mech.n_items} lots but the frozen instance carries "
                                 f"{spec.n_items}; a lot-count change is a different bank, not a config")
            spec = _replace(spec, mechanism=mech)
        if spec.mechanism.is_clock:
            spec = _replace(spec, mechanism=_replace(spec.mechanism, start_price=clock_start(spec),
                                                     round_cap=clock_round_cap(spec)))
        horizon = int(cfg.get("horizon", spec.horizon))
        if horizon != spec.horizon:
            spec = spec.prefix(horizon)
        for key in ("channel", "talk_rounds", "dm_cap", "framing"):
            if key in cfg:
                spec = _replace(spec, **{key: cfg[key]})
        if cfg.get("scramble_cards"):
            spec = scramble_public_cards(spec, seed=card_scramble_seed(instance.instance_id))
        return spec

    def seat_specs(self, state: dict) -> list[dict]:
        """One record per seat for the episode file: the addressable seat id, its persona, and its public
        card parameters (never a draw)."""
        spec = state["spec"]
        return [{"name": b.persona_id, "role": b.display_name, "variant": b.persona_id, "seat": b.seat,
                 "attrs": list(b.attrs), "capacity": b.capacity, "synergy_rate": b.synergy_rate,
                 "decay": b.decay, "gamma": b.gamma}
                for b in spec.bidders]

    # -- the wave loop -------------------------------------------------------------------------------------
    def _talks(self, spec) -> bool:
        """Whether this cell runs message rounds at all."""
        return spec.channel != "silent" and spec.talk_rounds > 0

    def _wave_seats(self, state: dict) -> tuple[int, ...]:
        """Seats due to move in the current wave. Every seat speaks in a message round; in a clock format only
        the seats still active bid, since an exit is irrevocable and a seat that has left takes no further
        part in the stage."""
        spec = state["spec"]
        if state["phase"] == TALK_PHASE or spec.mechanism.family != "english":
            return tuple(range(spec.n_bidders))
        gone = set(state["exits"].get(state["stage"], {}))
        return tuple(i for i in range(spec.n_bidders) if i not in gone)

    def next_requests(self, state: dict) -> list[SeatRequest]:
        """The wave due now: every seat that must move, each with a view built BEFORE any of them replies, so
        the round is genuinely simultaneous and nobody sees what anyone else wrote before writing."""
        if state["done"]:
            return []
        seats = state["_awaiting"]
        if not seats:
            return []
        out = []
        for seat in seats:
            view = state["_views"].get(seat)
            if view is None:
                if seat in state["policy_seats"]:
                    view = [{"role": "user", "content": auction_policy.state_block(
                        self.state_block(state, seat))}]
                else:
                    view = [{"role": "system", "content": self.system_prompt(state, seat)},
                            {"role": "user", "content": self.turn_prompt(state, seat)}]
                state["_views"][seat] = view
            out.append(SeatRequest(episode_id="", seat=state["seat_names"][seat], view=list(view),
                                   phase=state["phase"], round=self._global_round(state),
                                   max_tokens=self.turn_max_tokens,
                                   meta={"stage": state["stage"], "seat_index": seat,
                                         "sub_round": state["talk_round"] if state["phase"] == TALK_PHASE
                                         else state["bid_round"]}))
        return out

    def _global_round(self, state: dict) -> int:
        """A monotone round index across the whole episode, so ``TurnRecord.round`` orders turns and the
        engine's one-retry key ``(seat, round, phase)`` is unique per wave."""
        return int(state["round"])

    def rounds_used(self, state: dict) -> int:
        """Waves completed — the episode's own turn budget, distinct from stages."""
        return int(state["round"])

    # -- applying a turn -----------------------------------------------------------------------------------
    def apply(self, state: dict, request: SeatRequest, text: str) -> dict | None:
        """Read one turn, deliver its channels, record its binding move, and advance the wave when the last
        seat has answered.

        A syntax or legality error gets exactly one retry carrying the parser's specific message; a second
        failure records the format's fallback move and delivers nothing the seat wrote, so a channel payload
        attached to an unparseable turn cannot get through by breaking the envelope."""
        seat = int(request.meta["seat_index"])
        spec = state["spec"]
        env = A.parse_envelope(text)
        state["_last_parse"] = (None, False)

        # An API-side refusal or an empty completion arrives here as the engine's placeholder. It must NOT be
        # counted as a syntax error: the seat wrote nothing, so recording a fallback pass would put a bid of
        # "none" into the data that the model never chose. It is a GENERATION failure, counted separately and
        # surfaced by the runner's gate (design.md §6, G1's ``gen_failed = 0``).
        if text.strip() == EMPTY_TURN_PLACEHOLDER:
            state["hygiene"]["api_silence"] += 1

        parsed, err = self._read_move(state, seat, env, text)
        if err is not None:
            key, slots, kind = err
            directive = self._retry_once(state, request, self.scaffold.retry(key, **slots), kind)
            if directive is not None:
                state["hygiene"][f"retry_{kind}"] += 1
                return directive
            parsed = self._fallback_move(state, seat)
            state["hygiene"][f"{kind}_errors"] += 1
            state["hygiene"]["fallback_moves"] += 1
            state["_last_parse"] = (_action_json(parsed), False)
            self._record(state, seat, parsed, env, deliver=False)
        else:
            state["hygiene"]["parse_ok"] += 1
            state["_last_parse"] = (_action_json(parsed), True)
            self._record(state, seat, parsed, env, deliver=True)

        state["hygiene"]["turns"] += 1
        if seat in state["_awaiting"]:
            state["_awaiting"].remove(seat)
        if not state["_awaiting"]:
            self._resolve_wave(state)
        return None

    def _retry_once(self, state, request, msg: str, kind: str | None) -> dict | None:
        """One retry per ``(seat, round, phase)``, matching the engine's own one-retry rule; ``None`` once
        spent. ``error_kind`` rides along for logging (syntax vs legality)."""
        key = (request.seat, request.round, request.phase)
        if key in state["_r"]:
            return None
        state["_r"].add(key)
        return {"retry": msg, "error_kind": kind}

    def _read_move(self, state, seat, env, text):
        """Parse the phase's binding move. Returns ``(action, None)`` or ``(None, (retry_key, slots, kind))``.

        Economic errors are never read here: bidding above your own valuation parses cleanly and is measured
        downstream (design.md §3.2), which is why nothing in this path ever sees the seat's values."""
        spec = state["spec"]
        if env.raw is None:
            return None, ("no_json", {}, "syntax")
        if not isinstance(env.raw, dict):
            return None, ("no_json", {}, "syntax")
        if state["phase"] == TALK_PHASE:
            kind = env.raw.get("action")
            if isinstance(kind, str) and kind.strip().lower() not in ("none", "", "pass"):
                return None, ("action_wrong_phase", {"submitted": kind}, "syntax")
            return A.Pass(), None
        return self._read_bid(state, seat, env)

    def _read_bid(self, state, seat, env):
        """The per-family binding-move reader, in the reviewed action grammars."""
        spec, mech = state["spec"], state["spec"].mechanism
        obj = env.raw
        stage = state["stage"]
        budget = self._remaining_budget(state, seat)
        kind = obj.get("action")
        kind = kind.strip().lower() if isinstance(kind, str) else None
        legal = {"sealed_single": ("bid", "pass"), "saa": ("bid", "pass"),
                 "english": ("stay", "exit"), "dutch": ("claim", "wait")}[mech.family]
        if kind not in legal:
            return None, ("unknown_action", {"submitted": obj.get("action"),
                                             "legal_actions": ", ".join(f"`\"{k}\"`" for k in legal)},
                          "syntax")
        if mech.family == "english":
            if kind == "stay" and (state["clock_price"] or 0) > budget:
                return None, ("english_over_budget", {"clock_price": state["clock_price"],
                                                      "budget": budget}, "legality")
            return (A.Stay() if kind == "stay" else A.Exit()), None
        if mech.family == "dutch":
            if kind == "claim" and (state["clock_price"] or 0) > budget:
                return None, ("dutch_over_budget", {"clock_price": state["clock_price"],
                                                    "budget": budget}, "legality")
            return (A.Claim() if kind == "claim" else A.Wait()), None
        if mech.family == "sealed_single":
            if kind == "pass":
                return A.Pass(), None
            amount = A.whole_number(obj.get("amount"))
            if amount is None:
                return None, ("non_integer", {"submitted": obj.get("amount")}, "syntax")
            if amount < mech.reserve:
                return None, ("below_reserve", {"submitted": amount, "reserve": mech.reserve}, "legality")
            if amount > budget:
                return None, ("over_budget", {"submitted": amount, "budget": budget}, "legality")
            return A.Bid(item=0, amount=amount), None
        return self._read_saa(state, seat, obj, budget)

    def _read_saa(self, state, seat, obj, budget):
        """The SAA turn: a list of raises and a list of permanent passes, validated together.

        ``"lots"`` is read as the pass list whenever it is present, regardless of the ``"action"`` name, so a
        bidder cannot be trapped between combining a bid with a pass and choosing one of them."""
        spec, mech = state["spec"], state["spec"].mechanism
        stage, ledger = state["stage"], state["ledger"]
        ids = self._lot_ids(spec)
        raw_bids = obj.get("bids")
        if raw_bids is None and obj.get("action") == "bid" and obj.get("amount") is not None:
            raw_bids = [{"lot": obj.get("lot", 0), "amount": obj.get("amount")}]
        raw_bids = list(raw_bids or ())
        raw_pass = list(obj.get("lots") or ())
        if obj.get("action") == "bid" and not raw_bids and not raw_pass:
            return None, ("missing_field", {"submitted": "bid", "missing_field": "bids"}, "syntax")

        passes, seen_pass = [], set()
        for raw in raw_pass:
            item = A.resolve_item(raw, ids)
            if item is None:
                return None, ("unknown_lot", {"lot_id": raw, "stage_index": stage,
                                              "lot_id_list": ", ".join(ids)}, "syntax")
            if item not in seen_pass:
                seen_pass.add(item)
                passes.append(A.PassLot(item=item))

        bids, seen_bid = [], Counter()
        total_new = 0
        for entry in raw_bids:
            if not isinstance(entry, dict):
                return None, ("missing_field", {"submitted": "bid", "missing_field": "lot"}, "syntax")
            item = A.resolve_item(entry.get("lot", entry.get("item")), ids)
            if item is None:
                return None, ("unknown_lot", {"lot_id": entry.get("lot"), "stage_index": stage,
                                              "lot_id_list": ", ".join(ids)}, "syntax")
            seen_bid[item] += 1
            if seen_bid[item] > 1:
                return None, ("duplicate_lot", {"n_entries": seen_bid[item], "lot_id": ids[item]}, "syntax")
            if item in seen_pass:
                return None, ("bid_and_pass", {"lot_id": ids[item]}, "syntax")
            amount = A.whole_number(entry.get("amount"))
            if amount is None:
                return None, ("non_integer", {"submitted": entry.get("amount")}, "syntax")
            if not ledger.eligible(seat, item, stage):
                open_lots = [ids[j] for j in range(spec.n_items) if ledger.eligible(seat, j, stage)]
                return None, ("ratcheted_out", {"lot_id": ids[item], "stage_index": stage,
                                                "pass_round": state["pass_round"].get((stage, seat, item), 1),
                                                "open_lot_list": ", ".join(open_lots) or "none"}, "legality")
            standing = ledger.standing(item, stage)
            if standing is None:
                if amount < mech.reserve:
                    return None, ("below_lot_reserve", {"lot_id": ids[item], "reserve": mech.reserve,
                                                        "submitted": amount}, "legality")
            else:
                floor = standing.amount + mech.increment
                if amount < floor:
                    return None, ("below_minimum", {"submitted": amount, "lot_id": ids[item],
                                                    "standing": standing.amount,
                                                    "increment": mech.increment, "floor": floor}, "legality")
            if amount % mech.bid_granularity:
                return None, ("non_integer", {"submitted": amount}, "syntax")
            bids.append(A.Bid(item=item, amount=amount))
            total_new += amount

        committed = self._committed(state, seat)
        headroom = int(state["spec"].stage(stage).budgets[seat]) - committed
        held_replaced = sum(s.amount for s in (ledger.standing(b.item, stage) for b in bids)
                            if s is not None and s.seat == seat)
        if total_new - held_replaced > headroom:
            return None, ("saa_over_budget",
                          {"committed": committed, "budget": int(state["spec"].stage(stage).budgets[seat]),
                           "headroom": headroom, "submitted_total": total_new,
                           "overage": total_new - held_replaced - headroom}, "legality")
        return A.SAATurn(bids=tuple(bids), passes=tuple(passes)), None

    def _fallback_move(self, state, seat):
        """The format's fallback move after a second failure. The English fallback is ``stay``, never
        ``exit``, because an exit is irrevocable and a parse failure must not be able to end a seat's
        stage — unless staying would exceed the budget, in which case the payment would not be collectible."""
        if state["phase"] == TALK_PHASE:
            return A.Pass()
        family = state["spec"].mechanism.family
        if family == "english":
            if (state["clock_price"] or 0) > self._remaining_budget(state, seat):
                return A.Exit()
            return A.Stay()
        if family == "dutch":
            return A.Wait()
        if family == "saa":
            return A.SAATurn()
        return A.Pass()

    # -- recording and delivery ----------------------------------------------------------------------------
    def _record(self, state, seat, action, env, *, deliver: bool) -> None:
        """Record the binding move and, when the turn parsed, deliver its channels.

        Channel payloads attached to an unparseable turn are discarded: the seat is told so in the fallback
        notice, and the design needs a seat unable to get a message through by breaking the envelope."""
        spec = state["spec"]
        name = state["seat_names"][seat]
        stage, rnd = state["stage"], (state["talk_round"] if state["phase"] == TALK_PHASE
                                      else state["bid_round"])
        state["wave"][seat] = action
        public = []
        if deliver and spec.channel != "silent" and env.message.strip():
            state["broadcasts"].append({"stage": stage, "round": rnd, "phase": state["phase"],
                                        "sender": name, "text": env.message.strip()})
            public.append(env.message.strip())
            state["hygiene"]["broadcasts"] += 1
        if deliver and spec.channel in ("dm", "dm_transfers"):
            for dm in env.dms:
                made = state["dm"].route(dm, name, stage=stage, round=rnd, phase=state["phase"])
                state["hygiene"]["dms"] += len(made)
        if deliver and spec.channel == "dm_transfers" and env.transfer is not None:
            if env.transfer.amount > 0 and env.transfer.to in state["seat_names"] \
                    and env.transfer.to != name:
                state["transfers"].declare(env.transfer, name, stage=stage)
                state["hygiene"]["transfers_declared"] += 1
        public.append("```json\n" + json.dumps(_action_json(action)) + "\n```")
        state["events"].append({"seat": name, "content": "\n".join(public)})

    # -- wave resolution -----------------------------------------------------------------------------------
    def _resolve_wave(self, state: dict) -> None:
        """Fold the completed wave into the ledger and advance the phase, the round, or the stage."""
        spec, mech = state["spec"], state["spec"].mechanism
        stage = state["stage"]
        state["round"] += 1
        state["_views"] = {}
        wave, state["wave"] = state["wave"], {}

        if state["phase"] == TALK_PHASE:
            if state["mid_talk_active"]:
                # A mid-stage round is exactly one wave and returns the clock to where it was: ``bid_round`` and
                # ``clock_price`` are untouched by the detour, so the schedule the seats were told about holds.
                state["mid_talk_active"] = False
                state["phase"] = BID_PHASE
            elif state["talk_round"] < spec.talk_rounds:
                state["talk_round"] += 1
            else:
                state["phase"] = BID_PHASE
            state["_awaiting"] = list(self._wave_seats(state))
            return

        stage_over = self._fold_bids(state, wave)
        if stage_over:
            self._settle(state)
            if stage >= spec.horizon:
                state["done"] = True
                state["_awaiting"] = []
                return
            state["stage"] = stage + 1
            state["phase"] = TALK_PHASE if self._talks(spec) else BID_PHASE
            state["talk_round"], state["bid_round"] = 1, 1
            state["clock_price"] = opening_clock_price(spec)
        else:
            state["bid_round"] += 1
            if mech.family == "dutch":
                state["clock_price"] -= mech.increment
            elif mech.family == "english":
                state["clock_price"] += mech.increment
            if self._mid_talk_due(state):
                state["mid_talk_active"] = True
                state["mid_talk_done"].add(stage)
                state["phase"] = TALK_PHASE
        state["_awaiting"] = list(self._wave_seats(state))

    def _mid_talk_due(self, state) -> bool:
        """Is the mid-stage message round due after the wave just resolved (design.md §3.4)?

        §3.4 asks for one extra message round "before the final bidding round in clock formats". On a clock
        whose end is ENDOGENOUS that instant is not knowable in advance -- a Dutch stage ends at the first
        claim and an English stage when one bidder is left -- so the trigger is the midpoint of the clock's
        announced schedule, `round_cap // 2`, which every seat can compute from the rules it was given and
        which arrives before the typical claim. A stage whose clock ends before its midpoint simply gets no
        mid-stage round; that is the honest outcome (there was no mid-stage to test the ring in), not a
        missing wave.

        At most one per stage, clock families only, and never when the channel is silent -- a message round
        with no channel is a wasted turn per seat per stage."""
        spec = state["spec"]
        if spec.mechanism.family not in MID_STAGE_TALK_FAMILIES or not self._talks(spec):
            return False
        if state["stage"] in state["mid_talk_done"]:
            return False
        return state["bid_round"] == max(2, int(spec.mechanism.round_cap) // 2)

    def _fold_bids(self, state, wave) -> bool:
        """Apply the wave's binding moves to the ledger; return whether the stage's bidding is over."""
        spec, mech = state["spec"], state["spec"].mechanism
        stage, ledger, rnd = state["stage"], state["ledger"], state["bid_round"]
        if mech.family == "sealed_single":
            for seat, act in wave.items():
                if isinstance(act, A.Bid):
                    ledger.apply(act, seat, stage=stage, round=rnd)
            state.setdefault("sealed_bids", {})[stage] = {
                seat: (act.amount if isinstance(act, A.Bid) else None) for seat, act in wave.items()}
            return True
        if mech.family == "dutch":
            claimers = [s for s, a in wave.items() if isinstance(a, A.Claim)]
            if claimers:
                order = {s: k for k, s in enumerate(spec.stage(stage).tie_break)}
                winner = min(claimers, key=lambda s: order[s])
                state.setdefault("dutch_claim", {})[stage] = (winner, int(state["clock_price"]),
                                                              sorted(claimers))
                return True
            if state["clock_price"] - mech.increment < mech.reserve:
                state.setdefault("dutch_claim", {})[stage] = (None, 0, [])
                return True
            return False
        if mech.family == "english":
            gone = state["exits"].setdefault(stage, {})
            for seat, act in wave.items():
                if isinstance(act, A.Exit):
                    gone[seat] = int(state["clock_price"])
                    ledger.apply(act, seat, stage=stage, round=rnd)
            active = [i for i in range(spec.n_bidders) if i not in gone]
            if len(active) <= 1:
                return True
            if state["bid_round"] >= mech.round_cap or state["clock_price"] + mech.increment > clock_start(spec):
                state["clock_ceiling_stages"].append(stage)
                return True
            return False
        # SAA
        # Snapshot the standing table AS THE SEATS SAW IT this round, before any of the wave's bids land.
        # This is the realized price path the on-path benchmark replays (design.md §6). It is RECORDED rather
        # than reconstructed after the fact: reconstruction would have to re-derive tie resolution from the
        # ledger, which is precisely the step the two clocks disagreed on.
        state.setdefault("saa_trajectory", {}).setdefault(stage, []).append({
            "round": rnd,
            "prices": ledger.standing_prices(stage, reserve=mech.reserve),
            "holders": ledger.standing_winners(stage)})
        # Resolve the wave's claims per lot by (highest amount, then the stage's FROZEN seeded permutation),
        # which is the rule the seats are actually told: "Two bids on the same lot in the same round at the
        # same amount are resolved by this stage's priority order, announced in the stage header; the loser of
        # the tie is not treated as having passed and may bid again" (docs/templates/format_rules.md).
        #
        # Applying in this order is what makes the announced rule the played rule. Every SAA raiser bids
        # exactly `standing + increment`, so simultaneous claims on a lot are exact ties by construction; the
        # previous code applied them in `wave.items()` order, so the auction was decided by dict iteration
        # rather than by the announced permutation. Sorting here also makes the fold INVARIANT to wave
        # ordering, which is the reproducibility property every paired cross-cell contrast depends on: the
        # same actions must produce the same ledger regardless of the order they arrive in.
        #
        # The tie's loser is recorded but not live (BidLedger.apply's strict `<` guard), and is deliberately
        # NOT given a pass, so the eligibility ratchet does not treat it as having withdrawn.
        #
        # Note the coincidence with the benchmark: because straightforward demand is computed with
        # `forced=held`, an incumbent never re-claims a lot it already holds, so "contest every claimant"
        # (what saa_competitive_benchmark does) and "keep the incumbent on a tie" (what the strict `<` guard
        # does) agree on every reachable state. The guard is what keeps them agreeing even if some future
        # policy re-bids its own standing amount.
        order = {s: k for k, s in enumerate(spec.stage(stage).tie_break)}
        claims = [(b.item, -int(b.amount), order[seat], seat, b)
                  for seat, act in wave.items() if isinstance(act, A.SAATurn)
                  for b in act.bids]
        raised = bool(claims)
        for _item, _neg_amount, _priority, seat, bid in sorted(claims, key=lambda e: e[:3]):
            ledger.apply(bid, seat, stage=stage, round=rnd)
        for seat, act in wave.items():
            if not isinstance(act, A.SAATurn):
                continue
            for p in act.passes:
                ledger.apply(p, seat, stage=stage, round=rnd)
                state["pass_round"].setdefault((stage, seat, p.item), rnd)
        return (not raised) or state["bid_round"] >= mech.round_cap

    # -- settlement ----------------------------------------------------------------------------------------
    def _settle(self, state: dict) -> None:
        """Allocate, price, execute declared transfers, publish the stage result, and score the stage."""
        spec, mech = state["spec"], state["spec"].mechanism
        stage = state["stage"]
        draw = spec.stage(stage)
        vm = ValueModel.from_spec(spec, stage)
        n, m = spec.n_bidders, spec.n_items
        bids = np.full((n, m), np.nan)
        payments = np.zeros(n)
        winner_of: list = [None] * m
        prices = [0] * m
        result_kw: dict = {}

        if mech.family == "sealed_single":
            submitted = state["sealed_bids"][stage]
            for seat, amt in submitted.items():
                if amt is not None:
                    bids[seat, 0] = amt
            winner, price = sealed_single_outcome([submitted.get(i) for i in range(n)], pricing=mech.pricing,
                                                  tie_break=draw.tie_break, reserve=mech.reserve)
            if winner is not None:
                winner_of[0], prices[0] = winner, int(price)
                payments[winner] = int(price)
            result_kw = {"winner": None if winner is None else state["seat_names"][winner],
                         "price": prices[0], "lot_name": P.lot_name(0), "reserve": mech.reserve,
                         "bid_list": ", ".join(
                             f"`{state['seat_names'][i]}` {submitted.get(i) if submitted.get(i) is not None else 'passed'}"
                             for i in range(n))}
        elif mech.family == "dutch":
            winner, price, claimers = state["dutch_claim"][stage]
            for seat in claimers:
                bids[seat, 0] = price
            if winner is not None:
                winner_of[0], prices[0] = winner, int(price)
                payments[winner] = int(price)
            result_kw = {"winner": None if winner is None else state["seat_names"][winner],
                         "price": prices[0], "lot_name": P.lot_name(0), "reserve": mech.reserve}
        elif mech.family == "english":
            gone = state["exits"].get(stage, {})
            for seat, p in gone.items():
                bids[seat, 0] = p
            active = [i for i in range(n) if i not in gone]
            order = {s: k for k, s in enumerate(draw.tie_break)}
            if active:
                winner = min(active, key=lambda s: order[s])
                for seat in active:
                    bids[seat, 0] = int(state["clock_price"])
                price = max(gone.values()) if gone else mech.reserve
                winner_of[0], prices[0] = winner, int(price)
                payments[winner] = int(price)
            result_kw = {"winner": None if not active else state["seat_names"][winner_of[0]],
                         "price": prices[0], "lot_name": P.lot_name(0),
                         "exit_ladder": ", ".join(f"`{state['seat_names'][s]}` at {p}"
                                                  for s, p in sorted(gone.items(), key=lambda kv: kv[1]))
                         or "nobody exited"}
        else:
            ledger = state["ledger"]
            for b in ledger.stage_bids(stage):
                cur = bids[b.seat, b.item]
                bids[b.seat, b.item] = b.amount if np.isnan(cur) else max(cur, b.amount)
            winner_of, prices = self._saa_allocation(state, stage)
            for j, w in enumerate(winner_of):
                if w is not None:
                    payments[w] += prices[j]
            ids = self._lot_ids(spec)
            result_kw = {"result_rows": [(ids[j], f"`{state['seat_names'][w]}`" if w is not None else "unsold",
                                          prices[j] if w is not None else "—")
                                         for j in range(m)],
                         "unsold": [ids[j] for j in range(m) if winner_of[j] is None]}

        alloc = Allocation(tuple(winner_of))
        bundle_values = np.array([vm.bundle_value(i, alloc.bundle(i)) for i in range(n)])
        transfer_net = {}
        if spec.channel == "dm_transfers":
            capacity = {state["seat_names"][i]: float(draw.budgets[i]) - float(payments[i]) for i in range(n)}
            transfer_net = state["transfers"].settle(stage, capacity)

        own = {}
        ids = self._lot_ids(spec)
        for i in range(n):
            lots = [ids[j] for j in alloc.bundle(i)]
            surplus = float(bundle_values[i]) - float(payments[i]) + float(
                transfer_net.get(state["seat_names"][i], 0.0))
            own[i] = {"lots": lots, "paid": int(payments[i]), "surplus": int(round(surplus))}
        state["own_results"].append(own)
        state["stage_results"].append({"stage": stage, "family": mech.family, "kw": result_kw,
                                       "winner_of": list(winner_of), "prices": list(prices),
                                       "transfer_net": transfer_net})
        state["events"].append({"seat": "MODERATOR",
                                "content": self.scaffold.stage_result(family=mech.family, stage_index=stage,
                                                                      **result_kw)})

        bench = stage_benchmark(spec, stage,
                                trajectory=(state.get("saa_trajectory") or {}).get(stage))
        exposure = tuple(i for i in range(n)
                         if draw.synergy_target[i]
                         and 0 < len(set(alloc.bundle(i)) & set(draw.synergy_target[i]))
                         < len(draw.synergy_target[i]))
        out = StageOutcome(stage=stage, values=draw.value_array, bids=bids, benchmark_bids=bench.bids,
                           winner_of=tuple(winner_of), payments=payments, bundle_values=bundle_values,
                           max_welfare=vm.max_welfare(), budgets=np.array(draw.budgets, dtype=float),
                           exposure_seats=exposure,
                           truthful_bids=bench.detail.get("truthful_bids"))
        row = stage_metrics(out)
        row.update({"stage": stage, "benchmark": bench.label, "benchmark_revenue": bench.revenue,
                    "benchmark_note": bench.note,
                    # Descriptive only, and reported under its own name so it can never be mistaken for the
                    # suppression denominator (design.md §6): the revenue/efficiency a clean, independently
                    # simulated straightforward-bidding clock would have reached on these draws.
                    "benchmark_independent_clock": bench.detail.get("independent_clock"),
                    "benchmark_welfare": bench.welfare, "prices": list(prices),
                    "winner_of": list(winner_of), "payments": [float(p) for p in payments],
                    "surplus": [own[i]["surplus"] for i in range(n)]})
        state["outcomes"].append(row)

    def _saa_allocation(self, state, stage):
        """Award every lot to its standing high bidder, then enforce capacity by the reviewed rule: an
        over-capacity seat keeps the lots it bid most on, in descending order of its own bid, and each
        remaining lot goes to the next-highest bid on it."""
        spec = state["spec"]
        ledger, n, m = state["ledger"], spec.n_bidders, spec.n_items
        order = {s: k for k, s in enumerate(spec.stage(stage).tie_break)}
        per_lot = []
        for j in range(m):
            entries = {}
            for b in ledger.stage_bids(stage):
                if b.item == j:
                    entries[b.seat] = max(entries.get(b.seat, 0), b.amount)
            per_lot.append(sorted(entries.items(), key=lambda kv: (-kv[1], order[kv[0]])))
        winner_of: list = [None] * m
        prices = [0] * m
        blocked: list[set] = [set() for _ in range(m)]
        for _ in range(m + 1):
            for j in range(m):
                winner_of[j], prices[j] = None, 0
                for seat, amt in per_lot[j]:
                    if seat not in blocked[j] and amt >= spec.mechanism.reserve:
                        winner_of[j], prices[j] = seat, int(amt)
                        break
            over = False
            for i in range(n):
                held = [j for j in range(m) if winner_of[j] == i]
                cap = spec.capacities[i]
                if len(held) > cap:
                    over = True
                    for j in sorted(held, key=lambda k: (prices[k], -k))[: len(held) - cap]:
                        blocked[j].add(i)
            if not over:
                break
        return winner_of, prices

    # -- prompts -------------------------------------------------------------------------------------------
    def _lot_ids(self, spec) -> tuple[str, ...]:
        """The addressable lot tokens for this catalogue."""
        return tuple(P.lot_id(s.slot_id) for s in spec.item_slots)

    def system_prompt(self, state: dict, seat: int) -> str:
        """The episode-level system prompt for ``seat``: identical across seats except the one line that names
        the reading seat, so the public part is byte-identical and privacy cannot leak through it."""
        spec = state["spec"]
        sc, b = self.scaffold, spec.bidders[seat]
        multi = spec.n_items > 1
        interdep = spec.value_structure == "interdep"
        cards = [{"persona_id": x.persona_id, "display_name": x.display_name, "attrs": x.attrs,
                  "attr_names": spec.attr_names, "capacity": x.capacity, "synergy_rate": x.synergy_rate,
                  "decay": x.decay, "gamma": x.gamma} for x in spec.bidders]
        mech = spec.mechanism
        return sc.system_prompt(
            setting=sc.setting(n_bidders=spec.n_bidders, horizon=spec.horizon),
            your_seat=sc.your_seat(display_name=b.display_name, seat_id=b.persona_id),
            objective=sc.objective(),
            roster=sc.public_roster(cards=cards, multi_item=multi, interdep=interdep),
            prior=sc.prior_statement(beta=spec.beta, sigma_z=spec.sigma_z, sigma_eps=spec.sigma_eps,
                                     sigma_nu=spec.sigma_nu, value_structure=spec.value_structure,
                                     multi_item=multi),
            rules=sc.format_rules(family=mech.family, pricing=mech.pricing, n_items=spec.n_items,
                                  increment=mech.increment, start_price=mech.start_price,
                                  reserve=mech.reserve, round_cap=mech.round_cap),
            envelope=sc.envelope(family=mech.family, channel=spec.channel, dm_cap=spec.dm_cap,
                                 other_seat_ids=[x.persona_id for x in spec.bidders if x.seat != seat]),
            conduct=sc.conduct(family=mech.family, channel=spec.channel))

    def turn_prompt(self, state: dict, seat: int) -> str:
        """One turn view: the stage catalogue, the carried-history digest, this seat's private block, and the
        phase block. Nothing private to any other seat can reach it — the catalogue and the digest are built
        once and shared, and only :meth:`_private_block` reads a draw, for its owner only."""
        sc = self.scaffold
        return sc.turn_prompt(catalogue=self._catalogue(state), digest=self._digest(state, seat),
                              private=self._private_block(state, seat), phase=self._phase_block(state, seat),
                              turn_no=self._global_round(state))

    def _catalogue(self, state) -> str:
        """The shared per-stage header. Built once per stage and byte-identical across seats."""
        spec = state["spec"]
        draw, mech = spec.stage(state["stage"]), spec.mechanism
        names = [state["seat_names"][i] for i in draw.tie_break]
        if spec.n_items == 1:
            slot = spec.item_slots[0]
            if mech.family == "dutch":
                tail = f"Clock starts at {mech.start_price}, falls by {mech.increment}, reserve {mech.reserve}."
            elif mech.family == "english":
                tail = f"Clock starts at {mech.reserve}, rises by {mech.increment}."
            else:
                tail = f"Reserve {mech.reserve}."
            line = self.scaffold.single_lot_line(name=P.lot_name(0),
                                                 blurb=P.lot_blurb(slot.loading, spec.attr_names),
                                                 base_value=draw.base_values[0], loading=slot.loading,
                                                 attr_names=spec.attr_names, tail=tail)
            return self.scaffold.catalogue(stage_index=state["stage"], horizon=spec.horizon, rows=(),
                                           tie_break=names, attr_names=spec.attr_names, single_line=line)
        ids = self._lot_ids(spec)
        rows = [(ids[j], f"{P.lot_name(j)} {P.EMDASH} {P.lot_blurb(spec.item_slots[j].loading, spec.attr_names)}",
                 draw.base_values[j], spec.item_slots[j].loading) for j in range(spec.n_items)]
        return self.scaffold.catalogue(stage_index=state["stage"], horizon=spec.horizon, rows=rows,
                                       tie_break=names, attr_names=spec.attr_names)

    def _digest(self, state, seat) -> str:
        """Stages 1..t-1 for ``seat``: the published outcome of each settled stage plus this seat's own
        result, and every message it sent or received, verbatim.

        The bid ledger of a settled stage is dropped; its published per-lot outcome is not. That is the whole
        ``h(T)`` bound and it is a design commitment: at 20 lots x 5 rounds x 5 seats a carried ledger is
        roughly 500 line items per stage."""
        spec = state["spec"]
        name = state["seat_names"][seat]
        ids = self._lot_ids(spec)
        rows = []
        for res, own in zip(state["stage_results"], state["own_results"]):
            t = res["stage"]
            rows.append((t, self._digest_outcome(state, res), self._digest_own(own[seat])))
        # Chronological across both channels: a ring forms out of the interleaving of what was said aloud and
        # what was said privately, so ordering broadcasts before DMs would hide the very structure Q1 reads.
        log = []
        for k, msg in enumerate(state["broadcasts"]):
            who = "you" if msg["sender"] == name else f"`{msg['sender']}`"
            log.append(((msg["stage"], msg["round"], 0, k),
                        f"[stage {msg['stage']}, round {msg['round']}] {who} {P.ARROW} all: {msg['text']}"))
        for k, rec in enumerate(state["dm"].records):
            if rec.sender == name:
                line = f"you {P.ARROW} `{rec.recipient}`: {rec.text}"
            elif rec.recipient == name:
                line = f"`{rec.sender}` {P.ARROW} you: {rec.text}"
            else:
                continue
            log.append(((rec.stage, rec.round, 1, k),
                        f"[stage {rec.stage}, round {rec.round}] {line}"))
        return self.scaffold.history_digest(digest_rows=rows,
                                            message_log=[line for _, line in sorted(log)])

    def _digest_outcome(self, state, res) -> str:
        """One settled stage compressed to its published outcome — of ROUNDS, never of lots, since the per-lot
        outcome is what a market-division convention would be built on."""
        spec = state["spec"]
        ids = self._lot_ids(spec)
        family = res["family"]
        if spec.n_items > 1:
            return " · ".join(
                f"{ids[j]}{P.ARROW}unsold" if w is None else f"{ids[j]}{P.ARROW}{state['seat_names'][w]} "
                                                             f"{res['prices'][j]}"
                for j, w in enumerate(res["winner_of"]))
        w = res["winner_of"][0]
        if w is None:
            return f"{P.lot_name(0)} unsold"
        verb = "claimed by" if family == "dutch" else "to"
        return f"{P.lot_name(0)} {verb} `{state['seat_names'][w]}` at {res['prices'][0]}"

    def _digest_own(self, own) -> str:
        """This seat's own line in the digest: what it won, what it paid, and its realized surplus."""
        if not own["lots"]:
            return f"you won nothing; surplus {P.signed_amount(own['surplus'])}"
        return (f"you won {', '.join(own['lots'])} for {own['paid']}; "
                f"surplus {P.signed_amount(own['surplus'])}")

    def _private_block(self, state, seat) -> str:
        """The one block in the whole composition that carries a private draw, rendered for its owner only."""
        spec = state["spec"]
        draw = spec.stage(state["stage"])
        b = spec.bidders[seat]
        ids = self._lot_ids(spec)
        vals = draw.values[seat]
        target = draw.synergy_target[seat]
        cap_label = (priors.tercile_label(draw.z[seat], spec.sigma_z) if spec.sigma_z > 0 else None)
        bonus = (int(round(b.synergy_rate * sum(vals[j] for j in target))) if target else None)
        return self.scaffold.private_block(
            stage_index=state["stage"], horizon=spec.horizon, capital_position=cap_label,
            value_rows=[(ids[j], int(vals[j])) for j in range(spec.n_items)],
            budget=int(draw.budgets[seat]),
            synergy_target=[ids[j] for j in target] if target else None, synergy_bonus=bonus,
            capacity=b.capacity if spec.n_items > 1 else None,
            decay=b.decay if spec.n_items > 1 else None,
            signal_rows=([(ids[j], int(draw.signals[seat][j])) for j in range(spec.n_items)]
                         if draw.signals is not None else None),
            single_value=int(vals[0]) if spec.n_items == 1 else None)

    def _phase_block(self, state, seat) -> str:
        """The message-round or bidding-round ask, carrying only what the format reveals."""
        spec, mech = state["spec"], state["spec"].mechanism
        sc = self.scaffold
        if state["phase"] == TALK_PHASE:
            return sc.talk_round(stage_index=state["stage"], talk_round_no=state["talk_round"],
                                 talk_rounds=spec.talk_rounds, channel=spec.channel, dm_cap=spec.dm_cap,
                                 mid_stage=state["mid_talk_active"],
                                 clock_price=(int(state["clock_price"])
                                              if state["clock_price"] is not None else None),
                                 round_no=state["bid_round"] - 1, round_cap=mech.round_cap)
        if mech.family == "saa":
            ledger, ids = state["ledger"], self._lot_ids(spec)
            rows = []
            for j in range(spec.n_items):
                stand = ledger.standing(j, state["stage"])
                status = ("you hold it" if stand is not None and stand.seat == seat
                          else ("open" if ledger.eligible(seat, j, state["stage"])
                                else f"passed {P.EMDASH} closed to you"))
                rows.append((ids[j], stand.amount if stand else P.EMDASH,
                             state["seat_names"][stand.seat] if stand else P.EMDASH, status))
            return sc.round_ask(family="saa", round_no=state["bid_round"], round_cap=mech.round_cap,
                                standing_rows=rows)
        if mech.family == "english":
            gone = state["exits"].get(state["stage"], {})
            active = [state["seat_names"][i] for i in range(spec.n_bidders) if i not in gone]
            exited = [(state["seat_names"][s], p) for s, p in sorted(gone.items(), key=lambda kv: kv[1])]
            return sc.round_ask(family="english", round_no=state["bid_round"], round_cap=mech.round_cap,
                                clock_price=state["clock_price"], active=active, exited=exited)
        return sc.round_ask(family=mech.family, round_no=state["bid_round"], round_cap=mech.round_cap,
                            clock_price=state["clock_price"])

    def state_block(self, state: dict, seat: int) -> dict:
        """The machine-readable turn state a computable seat reads in place of the prose turn prompt.

        Carries this seat's OWN draws and the public round state. A rival's realized values appear only under
        ``oracle_values``, and only for an oracle seat — an explicitly named field, so reading it is a
        deliberate act the policy's own information gate controls rather than an accident of serialization."""
        spec = state["spec"]
        draw = spec.stage(state["stage"])
        name = state["seat_names"][seat]
        ledger = state["ledger"]
        stage = state["stage"]
        block = {
            "stage": stage, "round": state["bid_round"], "phase": state["phase"], "seat": seat,
            "seat_id": name, "channel": spec.channel, "dm_cap": spec.dm_cap,
            "values": [int(v) for v in draw.values[seat]],
            "budget": self._remaining_budget(state, seat),
            "synergy_target": list(draw.synergy_target[seat] or ()) or None,
            "signals": [int(v) for v in draw.signals[seat]] if draw.signals is not None else None,
            "standing": ledger.standing_prices(stage, reserve=spec.mechanism.reserve),
            "standing_winner": ledger.standing_winners(stage),
            "clock_price": state["clock_price"],
            "active": [i for i in range(spec.n_bidders) if i not in state["exits"].get(stage, {})],
            "exits": {str(s): p for s, p in state["exits"].get(stage, {}).items()},
            "inbox": [{"sender": r.sender, "text": r.text, "stage": r.stage, "round": r.round,
                       "recipient_seat": seat}
                      for r in state["dm"].inbox(name, stage=stage)],
        }
        if state["policy_seats"].get(seat) == "oracle":
            block["oracle_values"] = [[int(v) for v in row] for row in draw.values]
        return block

    def seat_framings(self, state: dict) -> dict:
        """``{seat_name: system prompt}`` for the episode record. A computable seat has no prose framing, so
        it records the name of its decision rule instead of a prompt it never reads."""
        return {state["seat_names"][i]:
                (f"[computable seat: {state['policy_seats'][i]}]" if i in state["policy_seats"]
                 else self.system_prompt(state, i))
                for i in range(state["spec"].n_bidders)}

    # -- budgets -------------------------------------------------------------------------------------------
    def _committed(self, state, seat) -> int:
        """The total of ``seat``'s live standing high bids this stage — what a further SAA bid is measured
        against, since a payment must be collectible."""
        ledger, stage = state["ledger"], state["stage"]
        return int(sum(s.amount for j in range(state["spec"].n_items)
                       for s in [ledger.standing(j, stage)] if s is not None and s.seat == seat))

    def _remaining_budget(self, state, seat) -> int:
        """``seat``'s remaining whole-number budget for the stage."""
        total = int(state["spec"].stage(state["stage"]).budgets[seat])
        if state["spec"].mechanism.family == "saa":
            return total - self._committed(state, seat)
        return total

    # -- scoring -------------------------------------------------------------------------------------------
    def score(self, state: dict) -> dict:
        """The episode outcome: per-stage rows, the episode aggregates every gate reads, and the protocol
        hygiene counters (design.md §5.3)."""
        spec = state["spec"]
        rows = state["outcomes"]
        hy = state["hygiene"]
        turns = max(1, int(hy["turns"]))
        eff = [r["efficiency"] for r in rows]
        supp = [r["suppression"] for r in rows if not math.isnan(r["suppression"])]
        completed = len(rows)
        return {
            "primary": float(np.mean(eff)) if eff else 0.0,
            "success": completed == spec.horizon,
            "stages_completed": completed, "horizon": spec.horizon,
            "stage_completion_rate": completed / spec.horizon,
            "mean_efficiency": float(np.mean(eff)) if eff else 0.0,
            "mean_suppression": float(np.mean(supp)) if supp else float("nan"),
            "revenue": float(sum(r["revenue"] for r in rows)),
            "benchmark_revenue": float(sum(r["benchmark_revenue"] for r in rows)),
            "stages": rows,
            "clock_ceiling_rate": len(state["clock_ceiling_stages"]) / max(1, completed),
            "parse_ok_rate": hy["parse_ok"] / turns,
            "syntax_errors": int(hy["syntax_errors"]), "legality_errors": int(hy["legality_errors"]),
            "fallback_moves": int(hy["fallback_moves"]), "n_turns": int(hy["turns"]),
            "api_silence": int(hy["api_silence"]), "api_silence_rate": hy["api_silence"] / turns,
            "dm_volume": hy["dms"] / max(1, completed * spec.n_bidders),
            "dm_graph": {f"{a}->{b}": c for (a, b), c in state["dm"].graph().items()},
            "dm_dropped": int(state["dm"].dropped),
            "broadcasts": int(hy["broadcasts"]),
            # The channel's CONTENT, chronological across both rungs. The dyad counts above are not enough for
            # design.md §9.3's measure 3: the per-dyad mutual information is between a seat's message TEXT to a
            # given rival and its value bin, so a stored run that kept only counts made the campaign's third
            # collusion measure uncomputable in exactly the DM cells (R2, R3, R4) it exists for. Broadcasts
            # carry ``recipient = None`` and are treated as a dyad to "all", which is what puts the two rungs
            # of the ladder on one scale.
            "messages": ([{"stage": m["stage"], "round": m["round"], "phase": m["phase"],
                           "channel": "broadcast", "sender": m["sender"], "recipient": None,
                           "text": m["text"]}
                          for m in state["broadcasts"]]
                         + [{"stage": r.stage, "round": r.round, "phase": r.phase, "channel": "dm",
                             "sender": r.sender, "recipient": r.recipient, "text": r.text}
                            for r in state["dm"].records]),
            "transfers": state["transfers"].to_json()["declared"],
            "policy_seats": {str(k): v for k, v in state["policy_seats"].items()},
            "channel": spec.channel, "family": spec.mechanism.family, "n_items": spec.n_items,
            "value_structure": spec.value_structure,
            # A first-class outcome column, not a config detail: X1 and O1 differ ONLY in this, so an analysis
            # that pooled them would compare a cell with itself and report G2(b) against its own reference.
            # ``None`` in every unscrambled cell, so the column is defined everywhere.
            "card_scramble": spec.meta.get("card_scramble"),
            "cards": [b.persona_id for b in spec.bidders],
        }

    def classify_outcome(self, state: dict, turns: list, outcome: dict) -> dict:
        """Episode-level tags the run index sorts on, computed purely from the stored outcome."""
        return {"onset_theta_crossings": sum(1 for r in outcome.get("stages", [])
                                             if not math.isnan(r["suppression"])
                                             and r["suppression"] > 0.15)}


# --------------------------------------------------------------------------------------------------------- #
# Small helpers.
# --------------------------------------------------------------------------------------------------------- #
def _replace(obj, **kw):
    """``dataclasses.replace`` without importing it at every call site."""
    from dataclasses import replace
    return replace(obj, **kw)


def _action_json(action) -> dict:
    """The canonical machine-readable rendering of a binding move — what is republished to every seat and what
    ``TurnRecord.parsed_action`` stores, so a stored episode replays exactly."""
    if isinstance(action, A.SAATurn):
        return {"action": "bid" if action.bids else "pass",
                "bids": [{"lot": P.lot_id(b.item), "amount": b.amount} for b in action.bids],
                "lots": [P.lot_id(p.item) for p in action.passes]}
    if hasattr(action, "to_json"):
        return action.to_json()
    return {"action": type(action).__name__.lower()}
