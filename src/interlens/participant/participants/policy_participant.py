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

# [rational_agents scaffold: oracles-strategies] 2026-07-23
"""``PolicyParticipant``: a state-dependent pure-Python seat that computes its move from a bound policy.

Where ``ScriptedParticipant`` cycles fixed strings ignoring the conversation, a ``PolicyParticipant`` *reads*
the view, reconstructs the structured negotiation state (the offer registry, standing offer, its own and
opponents' past proposals, the round), asks a bound ``policy(state) -> action`` for a typed action
(``Propose`` / ``Accept`` / ``Reject`` / ``Walk``), and emits it in the **same fenced-JSON envelope an LLM
seat produces** — so a computable rational agent and an LLM are interchangeable seats in one scenario.

It holds no model/activations, so (like ``ScriptedParticipant``) it raises on any interp request
(steering / capture / patch / logprobs) rather than silently ignoring it.

Two ways to supply the state each turn:

- **default view reconstruction** — parse the fenced-JSON actions already in the view (role ``assistant`` =
  this seat's past turns, role ``user`` = others'), rebuild the offer ledger with monotonic ids, and infer
  the round from this seat's completed turns. This keeps the participant symmetric with LLM seats (it reads
  exactly what an LLM reads) without any English NLP.
- **``state_provider``** — an injected ``callable(view) -> NegotiationState`` for scenarios that already track
  structured state (e.g. the arena scenario handing over its authoritative registry).
"""
from __future__ import annotations

from ..participant import Participant
from ...message import Message
from ...arena.negotiation._oracle_common import (NegotiationState, action_to_message_content, deal_from_json,
                                                 parse_negotiation_state)


class PolicyParticipant(Participant):
    """A pure-Python negotiation seat driven by a bound ``policy``.

    Parameters
    ----------
    name : str
        Identifier within the conversation.
    policy : callable
        ``policy(state: NegotiationState) -> Action`` — e.g. any policy from
        ``interlens.arena.negotiation.strategies`` or an oracle wrapped as a policy.
    seat : int
        This seat's index into the game's seat-indexed sheets/tables.
    sheet : object
        This seat's private score sheet (exposes ``.utility``/``.surplus``/``.threshold``).
    space : object
        The shared deal space (``.enumerate()`` / ``.size``).
    deadline : int
        Total number of rounds ``T`` (for the policy's time-dependent concession).
    discount : float
        Per-round discount ``delta`` carried into the state.
    opponents : tuple[int, ...]
        Opponent seat indices (default: inferred as all seats != ``seat`` up to ``n_seats``).
    n_seats : int | None
        Total seat count (used to default ``opponents`` when not given).
    tables : object | None
        Optional full-information ``GameTables`` to attach to the state (enables exact full-info policies).
    issue_names, option_names : list | None
        Optional issue/option names. When ``issue_names`` is given, ``Propose`` is emitted with names (for
        LLM-legible transcripts) and incoming name-based deals are decoded; otherwise deals are index lists.
    state_provider : callable | None
        Optional ``callable(view) -> NegotiationState`` overriding the default view reconstruction.
    registry_prefix : str
        Offer-id prefix for the reconstructed registry (default ``"O"``, matching ``OfferRegistry``).
    system_prompt : str | None
        Optional system framing (recorded for view/transcript symmetry; unused by the policy).
    """

    self_role = "assistant"
    others_role = "user"

    def __init__(self, name: str, policy, *, seat: int, sheet, space, deadline: int, discount: float = 1.0,
                 opponents: tuple = (), n_seats: int | None = None, tables=None, issue_names=None,
                 option_names=None, state_provider=None, registry_prefix: str = "O",
                 system_prompt: str | None = None, private_context: tuple = ()):
        self.name = name
        self.policy = policy
        self.seat = int(seat)
        self.sheet = sheet
        self.space = space
        self.deadline = int(deadline)
        self.discount = float(discount)
        if opponents:
            self.opponents = tuple(int(x) for x in opponents)
        elif n_seats is not None:
            self.opponents = tuple(i for i in range(int(n_seats)) if i != self.seat)
        else:
            self.opponents = ()
        self.tables = tables
        self.issue_names = issue_names
        self.option_names = option_names
        self.state_provider = state_provider
        self.registry_prefix = registry_prefix
        self.system_prompt = system_prompt
        self.private_context = tuple(private_context)

    # ---------------------------------------------------------------------------------------------------- #
    def generate(self, view: list[dict], *, steering=None, capture=None, patch=None,
                 return_logprobs: bool = False, turn: int | None = None,
                 max_new_tokens: int | None = None) -> Message:
        """Reconstruct the negotiation state from ``view``, ask the bound policy for an action, and return it
        as a fenced-JSON message (the same envelope LLM seats emit). Raises on any interp request — a
        pure-Python seat has no model to steer/capture/patch or read logprobs from."""
        if steering is not None or capture is not None or patch is not None or return_logprobs:
            raise NotImplementedError(
                f"PolicyParticipant {self.name!r} has no model: steering/capture/patch/logprobs are unavailable")
        state = (self.state_provider(view) if self.state_provider is not None
                 else self._state_from_view(view))
        action = self.policy(state)
        content = action_to_message_content(action, issue_names=self.issue_names,
                                            option_names=self.option_names)
        return Message(author=self.name, content=content,
                       metadata={"action": _to_json(action)})

    def act(self, state: NegotiationState):
        """Compute this seat's action from a ``NegotiationState`` directly — no view parsing, no engine. The
        pure entry a counterfactual-rollout loop calls (equivalent to ``self.policy(state)``). Note the bound
        ``self.policy`` is itself a public callable ``policy(NegotiationState) -> Action``, so a rollout can
        skip the participant wrapper entirely and call the policy on a reconstructed state."""
        return self.policy(state)

    # ---------------------------------------------------------------------------------------------------- #
    def _decode_deal(self, deal_obj):
        """Decode a ``Propose`` deal payload to an option-index tuple (index list, or name dict when
        ``issue_names`` is set)."""
        return deal_from_json(deal_obj, self.issue_names, self.option_names)

    def _parse_action(self, content: str):
        """Parse one formal action from a message body (the last fenced-JSON action), returning a typed
        ``Action`` or ``None``. Uses the canonical ``parse_action`` when available."""
        try:
            from ...arena.actions import parse_action
            res = parse_action(content, deal_decoder=self._decode_deal)
            return res.action if getattr(res, "ok", False) else None
        except Exception:
            from ...arena.negotiation._oracle_common import parse_action_json, Propose, Accept, Reject, Walk
            obj = parse_action_json(content)
            if not isinstance(obj, dict):
                return None
            kind = obj.get("action")
            if kind == "propose" or "deal" in obj:
                deal = self._decode_deal(obj.get("deal"))
                return Propose(deal) if deal is not None else None
            if kind == "accept":
                return Accept(str(obj.get("offer_id")))
            if kind == "reject":
                return Reject(str(obj.get("offer_id")))
            if kind == "walk":
                return Walk()
            return None

    def _state_from_view(self, view: list[dict]) -> NegotiationState:
        """Rebuild a ``NegotiationState`` from the flattened ``view``.

        Preferred path: if the scenario embedded an authoritative ``negotiation_state`` fenced-JSON block in
        any view segment (its canonical offer registry + round), use the latest one. Fallback: walk the view
        in order, assigning monotonic offer ids to every ``Propose`` (role ``assistant`` = this seat, role
        ``user`` = an opponent), track the latest incoming (opponent) offer as ``standing``, and infer the
        round from this seat's completed turns."""
        from ...arena.negotiation._oracle_common import Propose
        for seg in reversed(view or []):
            block = parse_negotiation_state(seg.get("content", ""))
            if block is not None:
                block.setdefault("seat", self.seat)
                block.setdefault("deadline", self.deadline)
                return NegotiationState.from_block(block, sheet=self.sheet, space=self.space,
                                                   tables=self.tables, discount=self.discount,
                                                   opponents=self.opponents, seat=self.seat)
        offers: dict = {}
        received: list = []
        my_offers: list = []
        standing = None
        my_turns = 0
        next_id = 1
        for seg in (view or []):
            role = seg.get("role")
            content = seg.get("content", "")
            if role == "system":
                continue
            mine = (role == self.self_role)
            if mine:
                my_turns += 1
            action = self._parse_action(content)
            if isinstance(action, Propose) and action.deal is not None:
                oid = f"{self.registry_prefix}{next_id}"
                next_id += 1
                offers[oid] = tuple(int(x) for x in action.deal)
                (my_offers if mine else received).append(offers[oid])
                if not mine:
                    standing = oid          # respond to the latest opponent offer
        return NegotiationState(
            seat=self.seat, sheet=self.sheet, space=self.space,
            round=my_turns + 1, deadline=self.deadline, offers=offers, standing=standing,
            received=received, my_offers=my_offers, discount=self.discount, tables=self.tables,
            opponents=self.opponents)


def _to_json(action):
    to_json = getattr(action, "to_json", None)
    return to_json() if callable(to_json) else {"action": getattr(action, "kind", "?")}
