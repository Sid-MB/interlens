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

import numpy as np

from ..auction import policy_text
from ..auction.bidders import AuctionState, Proposal, policy_for, public_posteriors
from ..auction.spec import AuctionSpec
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
        """The SAA turn. The policy emits one lot at a time, so the turn is built by asking it repeatedly
        against a locally-advanced standing table until it stops wanting to raise or the budget runs out —
        which is the same straightforward-bidding rule, expressed in the reviewed multi-lot grammar."""
        standing = list(block.get("standing") or [])
        winners = list(block.get("standing_winner") or [])
        headroom = int(state.budget)
        bids: list[dict] = []
        for _ in range(int(self.spec.capacities[self.seat])):
            action = self.policy.act(state)
            if not isinstance(action, A.Bid) or action.amount > headroom:
                break
            if any(b["lot"] == P.lot_id(action.item) for b in bids):
                break
            bids.append({"lot": P.lot_id(action.item), "amount": int(action.amount)})
            headroom -= int(action.amount)
            standing[action.item] = int(action.amount)
            winners[action.item] = self.seat
            state = _with(state, standing=standing, standing_winner=winners, budget=headroom)
        return {"action": "bid", "bids": bids} if bids else {"action": "pass"}

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


def _with(state: AuctionState, **kw) -> AuctionState:
    """A shallow copy of a policy's state with fields replaced — used to advance the standing table locally
    while a multi-lot turn is assembled."""
    from dataclasses import replace
    return replace(state, **kw)


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
