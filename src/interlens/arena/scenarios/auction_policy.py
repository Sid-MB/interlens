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

"""Computable seats inside the ordinary engine loop.

A policy seat is a :class:`~interlens.arena.participant.Participant` like any other: it receives a view,
returns a :class:`~interlens.arena.message.Message`, and produces a real ``TurnRecord`` that the transcript
export and the analysis read on exactly the same footing as an LLM seat's. That matters more here than
convenience — the whole point of the five-arm design is that the arms differ in the DECISION RULE and nothing
else, so a computable seat that bypassed the turn loop would differ in its instrumentation too.

**Policy seats read a structured state block, not prose.** The scenario renders a fenced ``auction_state``
JSON object into a policy seat's view in place of the natural-language turn prompt (the same precedent as
``ScorableNegotiation``'s ``negotiation_state`` block). The block carries this seat's own private draws and
the public round state, and NOTHING about any other seat's draws — an oracle seat's extra information rides
in a separate, explicitly-named field so that reading it is a deliberate act the policy's own
``_rival_values`` gate controls.

**And they speak.** The mute-channel lesson is binding, so the participant fills the envelope's ``message``
and ``dm`` fields from :mod:`~interlens.arena.auction.policy_text`, driven by the policy's own decision
functions. The oracle's templates are identical to the rational seat's.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..auction import policy_text
from ..auction.bidders import AuctionState, Proposal, policy_for, public_posteriors
from ..auction.spec import AuctionSpec, card_scramble_seed
from ...message import Message
from ...participant.participant import Participant
from ..auction import actions as A
from . import auction_prompts as P

#: The fence label the scenario writes and this participant reads.
STATE_FENCE = "auction_state"


def state_block(payload: dict) -> str:
    """The fenced, machine-readable turn state handed to a policy seat."""
    return f"```{STATE_FENCE}\n{json.dumps(payload)}\n```"


def read_state_block(view) -> dict:
    """The latest ``auction_state`` block in a view. Latest wins, so a retry prompt cannot resurrect a stale
    round."""
    for seg in reversed(view or ()):
        text = seg.get("content") or ""
        marker = f"```{STATE_FENCE}"
        if marker in text:
            body = text.split(marker, 1)[1].split("```", 1)[0]
            return json.loads(body)
    raise ValueError("no auction_state block in the view; a policy seat cannot read a prose turn prompt")


class AuctionPolicyParticipant(Participant):
    """One computable auction seat: an information-conditional best response, plus its templated channel
    behavior.

    Parameters
    ----------
    name : str
        Participant name recorded on the episode.
    spec : AuctionSpec
        The episode spec. Public structure only is read from it; the seat's realized draws arrive through the
        state block, so the same object can back every seat without an information leak by construction.
    seat : int
        Seat index.
    information : str
        ``"private"`` (the rational seat: own information only) or ``"oracle"`` (the same best response with
        everyone's realized private information). This is the ONLY difference between the two arms.
    instance_id : str
        Frozen instance id, used to seed the surface variant of every templated line so the variant is
        reproducible and arm-invariant.
    """

    self_role = "assistant"
    others_role = "user"

    def __init__(self, name: str, *, spec: AuctionSpec, seat: int, information: str = "private",
                 instance_id: str = ""):
        self.name = name
        self.spec = spec
        self.seat = int(seat)
        self.information = information
        self.instance_id = instance_id
        self.policy = policy_for(spec, information=information)
        self.system_prompt = None
        self.private_context = ()

    # -- the participant contract ------------------------------------------------------------------------
    def generate(self, view, *, seat: str | None = None, max_new_tokens: int | None = None, **kwargs
                 ) -> Message:
        """Read the state block, compute the move, and emit the envelope an LLM seat would have written."""
        for unsupported in ("steering", "capture", "patch"):
            if kwargs.get(unsupported) is not None:
                raise NotImplementedError(f"a computable auction seat has no activations to {unsupported}")
        block = read_state_block(view)
        state = self._auction_state(block)
        envelope = self._envelope(block, state)
        return Message(author=self.name, content="```json\n" + json.dumps(envelope) + "\n```",
                       metadata={"policy": self.policy.name, "information": self.information,
                                 "cost_usd": 0.0, "tokens_in": 0, "tokens_out": 0})

    # -- state ---------------------------------------------------------------------------------------------
    def _auction_state(self, block: dict) -> AuctionState:
        """Rebuild the policy's structured state from the block. The realized draws come from the block, never
        from the spec, so a private-information seat cannot read a rival's row even by accident."""
        spec = self.spec
        t = int(block["stage"])
        return AuctionState(
            seat=self.seat, spec=spec, stage=t, round=int(block["round"]),
            values=np.array(block["values"], dtype=np.int64), budget=int(block["budget"]),
            synergy_target=tuple(block["synergy_target"]) if block.get("synergy_target") else None,
            signals=np.array(block["signals"]) if block.get("signals") else None,
            posteriors=public_posteriors(spec, t),
            standing=block.get("standing"), standing_winner=block.get("standing_winner"),
            clock_price=block.get("clock_price"),
            active=tuple(block.get("active", range(spec.n_bidders))),
            exits={int(k): int(v) for k, v in (block.get("exits") or {}).items()},
            oracle_values=(np.array(block["oracle_values"], dtype=np.int64)
                           if block.get("oracle_values") is not None else None),
            reserve=spec.mechanism.reserve, increment=spec.mechanism.increment)

    # -- the envelope --------------------------------------------------------------------------------------
    def _envelope(self, block: dict, state: AuctionState) -> dict:
        """The four-channel turn: the binding move, plus the templated broadcast and DM."""
        channel = block.get("channel", "silent")
        talk = block.get("phase") == "talk"
        env: dict = {"scratchpad": f"{self.policy.name} ({self.information})"}
        if channel != "silent":
            env["message"] = self._broadcast(block, state, talk=talk)
        if channel in ("dm", "dm_transfers"):
            dms = self._dms(block, state)
            if dms:
                env["dm"] = dms
        env.update(self._move(block, state) if not talk else {"action": "none"})
        return env

    def _move(self, block: dict, state: AuctionState) -> dict:
        """The binding move, in the seat's own action grammar."""
        family = self.spec.mechanism.family
        if family == "saa":
            return self._saa_move(block, state)
        action = self.policy.act(state)
        if isinstance(action, A.Bid):
            return {"action": "bid", "amount": int(action.amount)}
        return {"action": {"stay": "stay", "exit": "exit", "claim": "claim", "wait": "wait"}
                .get(getattr(action, "kind", ""), "pass")}

    def _saa_move(self, block: dict, state: AuctionState) -> dict:
        """The SAA turn: render the policy's own :class:`~interlens.arena.auction.actions.SAATurn` into the
        reviewed multi-lot grammar.

        The policy decides the whole round's demand in ONE call, because straightforward bidding's demand
        correspondence is a bundle argmax (see :meth:`AuctionPolicy._saa_move`). This method previously
        rebuilt the turn here instead, asking the policy for one lot at a time against a locally-advanced
        standing table — a greedy path that does not reproduce the bundle argmax once synergies are live, and
        so put both computable arms off the benchmark that G3 pins them to. Rendering rather than re-deriving
        is what keeps the played rule and the benchmarked rule the same rule."""
        action = self.policy.act(state)
        if not isinstance(action, A.SAATurn) or not action.bids:
            return {"action": "pass"}
        return {"action": "bid",
                "bids": [{"lot": P.lot_id(b.item), "amount": int(b.amount)} for b in action.bids]}

    # -- channels ------------------------------------------------------------------------------------------
    def _broadcast(self, block: dict, state: AuctionState, *, talk: bool) -> str:
        """The public position: presence and public-profile fit at stage start, holdings mid-stage."""
        spec = self.spec
        affinity = spec.attribute_score()[self.seat]
        ranked = [P.lot_id(j) for j in np.argsort(-affinity)]
        held = [P.lot_id(j) for j, w in enumerate(block.get("standing_winner") or []) if w == self.seat]
        fit = float(affinity[0]) if spec.n_items == 1 else 0.0
        return policy_text.public_position(
            instance_id=self.instance_id, seat=self.seat, stage=state.stage,
            display_name=spec.bidders[self.seat].display_name, fit_lots=ranked[:3], held_lots=held,
            single_item=spec.n_items == 1, opening=talk,
            fit_word="strong" if fit > 0 else ("weak" if fit < 0 else "neutral"))

    def _dms(self, block: dict, state: AuctionState) -> list[dict]:
        """Replies to any proposal DM'd to this seat, and — when its posterior says a division dominates
        competing — one proposal of its own to the rival its PUBLIC prior identifies as the strongest threat.

        A stage-myopic seat only ever proposes the division it would play anyway, so its proposals are honest
        and it never asks a rival for a suppression it would not itself honor. That is the design's point:
        this seat's non-participation in a ring is structural."""
        spec = self.spec
        out: list[dict] = []
        seats = [b.persona_id for b in spec.bidders]
        for msg in block.get("inbox", ()):
            proposal = _read_proposal(msg, seats, spec.n_items)
            if proposal is None:
                continue
            decision = self.policy.evaluate_proposal(state, proposal)
            mine = tuple((proposal.assignment or {}).get(self.seat, ()))
            theirs = tuple((proposal.assignment or {}).get(proposal.proposer, ()))
            counter = tuple(j for j in mine if state.values[j] >= np.median(state.values))
            out.append({"to": msg["sender"],
                        "text": policy_text.dm_reply(
                            decision, instance_id=self.instance_id, seat=self.seat, stage=state.stage,
                            proposer=msg["sender"], proposed_lots=[P.lot_id(j) for j in mine],
                            proposer_lots=[P.lot_id(j) for j in theirs],
                            counter_lots=[P.lot_id(j) for j in counter] if not decision.accept else None)})
            if len(out) >= int(block.get("dm_cap", 2)):
                return out
        if block.get("phase") == "talk" and spec.n_items > 1:
            proposal = self.policy.initiate_proposal(state)
            if proposal is not None and len(out) < int(block.get("dm_cap", 2)):
                threat = max(state.rivals,
                             key=lambda i: state.posteriors[i].expected_value(int(proposal.item or 0)))
                mine = tuple((proposal.assignment or {}).get(self.seat, ()))
                theirs = tuple((proposal.assignment or {}).get(threat, ()))
                out.append({"to": seats[threat],
                            "text": policy_text.dm_initiate(
                                instance_id=self.instance_id, seat=self.seat, stage=state.stage,
                                threat_seat=seats[threat], fit_lot=P.lot_id(int(proposal.item or 0)),
                                counter_lots=[P.lot_id(j) for j in theirs] or [P.lot_id(j) for j in mine])})
        return out


def _read_proposal(msg: dict, seats, n_items: int) -> Proposal | None:
    """Read a DM as a machine-evaluable proposal: which lots it asks this seat to take, which it claims, and
    any price it asks the seat to hold to.

    Deliberately shallow — lot ids and a price, nothing that requires understanding the sentence. A policy
    seat that could parse arbitrary persuasion would be a different agent than the one design.md §4.1
    preregisters, and the failure mode of a shallow reader (it declines to engage with a proposal it cannot
    parse) is the conservative one for Q5."""
    text = msg.get("text", "")
    mentioned = [j for j in range(n_items) if P.lot_id(j) in text]
    if not mentioned:
        return None
    sender = msg.get("sender")
    proposer = seats.index(sender) if sender in seats else 0
    me = msg.get("recipient_seat")
    half = len(mentioned) // 2 or 1
    return Proposal(proposer=proposer,
                    assignment={int(me): tuple(mentioned[:half]), proposer: tuple(mentioned[half:])},
                    item=mentioned[0], text=text)


# --------------------------------------------------------------------------------------------------------- #
# Replay integrity: is the played seat its own rule?
# --------------------------------------------------------------------------------------------------------- #
#: Arm names whose seats are all computable, mapped to the information their policy runs at. Used only as a
#: fallback: an episode normally records `cell_cfg.policy_seats`, which is per SEAT and therefore also covers
#: the mixed arms (`one_rational`, `one_oracle`) where only some seats are computable.
FREE_ARM_INFORMATION: dict[str, str] = {"all_rational": "private", "all_oracle": "oracle"}


def _played_spec(episode: dict, bank_dir) -> AuctionSpec:
    """The spec the episode was ACTUALLY played on: the frozen bank draws under the cell's own mechanism.

    A bank stores draws under one nominal mechanism, and a cell freely overrides the family, increment,
    horizon and reserve on top of them — the single-lot bank backs the sealed cells AND the Dutch ones. So the
    spec must be rebuilt from what the episode RECORDS it played (`cell_cfg.mechanism`, `cell_cfg.horizon`),
    not from the bank's nominal mechanism. Re-deriving it instead was a real defect in the first version of
    this checker: it replayed Dutch episodes against the bank's sealed mechanism, so every turn was scored
    against a sealed-bid rule and all 1400 of them "failed"."""
    from dataclasses import replace
    from ..auction.spec import Mechanism, scramble_public_cards

    cfg = episode.get("cell_cfg") or {}
    payload = json.loads((Path(bank_dir) / f"{episode['instance_id']}.json").read_text())["payload"]["specs"]
    spec = AuctionSpec.from_json(payload[cfg.get("value_structure", "apv")])
    spec = replace(spec, mechanism=Mechanism.from_json(cfg["mechanism"]),
                   channel=cfg.get("channel", spec.channel))
    # `prefix` is the sanctioned way to shorten a bank's stage draws to the cell's horizon; assigning the
    # horizon directly trips the spec's own invariant that it match the number of stage draws supplied.
    horizon = int(cfg.get("horizon", spec.horizon))
    if horizon != spec.horizon:
        spec = spec.prefix(horizon)
    if cfg.get("scramble_cards"):
        spec = scramble_public_cards(spec, seed=card_scramble_seed(episode["instance_id"]))
    return spec


def replay_integrity(episode: dict, bank_dir) -> dict:
    """Re-derive every computable turn of ``episode`` from its own recorded state block and check it matches
    what the seat actually played.

    **The mechanism-independent form of "the played seat is its rule."** For each turn the participant
    recorded, this rebuilds the :class:`~interlens.arena.auction.bidders.AuctionState` from the very
    ``auction_state`` block that turn was rendered with, re-runs the policy over it, and asserts the freshly
    computed move equals the recorded ``parsed_action``. It needs no equilibrium concept and no benchmark, so
    it applies to **every** mechanism family — including the clock families, where asserting equality against
    an equilibrium bid is meaningless because the policy is a stage-myopic best responder while the benchmark
    is a symmetric equilibrium (design.md §6).

    This is the check that generalizes the SAA on-path gate, and it is exactly the class that catches a policy
    silently forfeiting a lot it merely did not demand, a state block fed with the wrong round, a renderer
    dropping a field, or an oracle seat handed information it should not have — all for $0, from episodes
    already on disk, before a paid arm runs.

    Determinism note: the recorded block is the seat's own input, so seeded tie-breaks and the realized
    standing table are reproduced rather than re-drawn, and the comparison is exact rather than
    tolerance-based. Only turns whose seat is computable in this arm are checked; an LLM seat has no rule to
    replay, which is the entire point of the contrast.

    Parameters
    ----------
    episode : dict
        A stored episode record, carrying ``instance_id``, ``cell_cfg``, ``seats`` and ``turns`` with each
        turn's ``view`` and ``parsed_action``.
    bank_dir : str | Path
        The frozen bank directory the episode's instance was drawn from.

    Returns
    -------
    dict
        ``{"arm", "turns", "checked", "mismatches", "pass"}``. ``checked`` is 0 and ``pass`` True for an
        all-LLM episode, which has no computable seat to replay.
    """
    cfg = episode.get("cell_cfg") or {}
    # `policy_seats` maps seat index -> information and is authoritative, because it also covers the mixed
    # arms where only one seat is computable. The arm-name map is the fallback for older episode vintages.
    # The runner labels a computable seat by ARM role ("rational"/"oracle"); the policy takes the
    # INFORMATION setting ("private"/"oracle"). They are the same distinction under two names.
    information_of = {"rational": "private", "private": "private", "oracle": "oracle"}
    policy_seats = {int(k): information_of[v] for k, v in (cfg.get("policy_seats") or {}).items()
                    if v in information_of}
    if not policy_seats and episode.get("arm") in FREE_ARM_INFORMATION:
        policy_seats = {int(s["seat"]): FREE_ARM_INFORMATION[episode["arm"]]
                        for s in episode.get("seats") or []}
    out = {"arm": episode.get("arm"), "turns": len(episode.get("turns") or []),
           "checked": 0, "mismatches": []}
    if not policy_seats:
        out["pass"] = True
        return out
    spec = _played_spec(episode, bank_dir)
    seat_of = {s["name"]: int(s["seat"]) for s in episode.get("seats") or []}
    for turn in episode.get("turns") or []:
        seat = seat_of.get(turn.get("seat"))
        recorded = turn.get("parsed_action")
        if seat is None or recorded is None or seat not in policy_seats:
            continue
        try:
            block = read_state_block(turn.get("view"))
        except (ValueError, KeyError, json.JSONDecodeError):
            out["mismatches"].append({"turn": turn.get("idx"), "seat": turn.get("seat"),
                                      "why": "no readable auction_state block in the recorded view"})
            continue
        participant = AuctionPolicyParticipant(turn["seat"], spec=spec, seat=seat,
                                               information=policy_seats[seat],
                                               instance_id=episode.get("instance_id", ""))
        state = participant._auction_state(block)
        expected = ({"action": "none"} if block.get("phase") == "talk"
                    else participant._move(block, state))
        if not _same_move(expected, recorded):
            out["mismatches"].append({"turn": turn.get("idx"), "seat": turn.get("seat"),
                                      "round": turn.get("round"), "expected": expected, "played": recorded})
        out["checked"] += 1
    out["pass"] = not out["mismatches"]
    return out


def _same_move(expected: dict, played: dict) -> bool:
    """Whether a freshly computed move and a recorded one are the same binding action.

    Compares the action kind, and for the multi-lot grammar the SET of (lot, amount) pairs — order is a
    rendering detail, membership is the decision. Fields the parser adds (``lots`` on a normalized SAA turn)
    are ignored, since they are the mechanism's reading rather than the policy's output."""
    # `none`, `pass` and an absent tag are ONE move in the action grammar — `auction_action_from_json`
    # accepts all three for "take no binding move" — so they must compare equal here. The participant writes
    # `pass` while the parser records `none`, and reading that synonym as a mismatch is exactly the kind of
    # false positive that would gate a cell on a vocabulary difference rather than on behavior.
    kind = lambda d: "none" if (d.get("action") or "none") in ("none", "pass", "") else d["action"]
    if kind(expected) != kind(played):
        return False
    if "bids" in expected or "bids" in played:
        norm = lambda d: sorted((b.get("lot"), int(b.get("amount", 0))) for b in (d.get("bids") or ()))
        return norm(expected) == norm(played)
    if "amount" in expected or "amount" in played:
        return int(expected.get("amount", -1)) == int(played.get("amount", -1))
    return True
