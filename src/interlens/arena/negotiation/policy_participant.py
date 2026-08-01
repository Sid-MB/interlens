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
# [rational_agents restructure: phase-AB] 2026-07-24 — moved here from participant/participants/: it is built
# on this package's NegotiationState/strategies, and a core participant must not import the arena.
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

from ...message import Message
from ...participant.participant import Participant
from ..actions import Propose, action_message, parse_action
from .strategies import NegotiationState, parse_negotiation_state


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
    space : DealSpace
        The shared deal space. Also the seat's issue/option NAME table: proposals are emitted with names
        (``space.named``) and incoming name-based deals decoded (``space.parse``), so the transcript is
        LLM-legible and there is no second copy of the issue names to keep in sync.
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
                 opponents: tuple = (), n_seats: int | None = None, tables=None,
                 state_provider=None, registry_prefix: str = "O",
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
        self.state_provider = state_provider
        self.registry_prefix = registry_prefix
        self.system_prompt = system_prompt
        self.private_context = tuple(private_context)

    # ---------------------------------------------------------------------------------------------------- #
    def generate(self, view: list[dict], *, steering=None, capture=None, patch=None,
                 return_logprobs: bool = False, turn: int | None = None,
                 max_new_tokens: int | None = None, seat: str | None = None) -> Message:
        """Reconstruct the negotiation state from ``view``, ask the bound policy for an action, and return it
        as a fenced-JSON message (the same envelope LLM seats emit). Raises on any interp request — a
        pure-Python seat has no model to steer/capture/patch or read logprobs from."""
        if steering is not None or capture is not None or patch is not None or return_logprobs:
            raise NotImplementedError(
                f"PolicyParticipant {self.name!r} has no model: steering/capture/patch/logprobs are unavailable")
        state = (self.state_provider(view) if self.state_provider is not None
                 else self._state_from_view(view))
        action = self.policy(state)
        message = self._declaration(state, view)
        return Message(author=self.name, content=action_message(action, self.space, message=message),
                       metadata={"action": action.to_json(),
                                 **({"message": message} if message else {})})

    def _declaration(self, state, view: list[dict]) -> str | None:
        """The bound policy's one-time public declaration, or ``None``.

        Emitted on this seat's FIRST turn only, and "first turn" is read off the view — no segment carries
        this seat's own role yet — rather than remembered on the participant. Deriving it from the transcript
        is what keeps the rule correct when one policy object serves several seats or several concurrent
        episodes, and it is also retry-safe: a turn the scenario rejected was never published, so the view on
        the retry still shows no prior turn and the same declaration is re-sent rather than lost."""
        declare = getattr(self.policy, "declaration", None)
        if declare is None or any(seg.get("role") == self.self_role for seg in (view or [])):
            return None
        return declare(state)

    def act(self, state: NegotiationState):
        """Compute this seat's action from a ``NegotiationState`` directly — no view parsing, no engine. The
        pure entry a counterfactual-rollout loop calls (equivalent to ``self.policy(state)``). Note the bound
        ``self.policy`` is itself a public callable ``policy(NegotiationState) -> Action``, so a rollout can
        skip the participant wrapper entirely and call the policy on a reconstructed state."""
        return self.policy(state)

    # ---------------------------------------------------------------------------------------------------- #
    def _decode_deal(self, deal_obj):
        """Decode a ``Propose`` deal payload to an option-index tuple, or ``None`` if malformed — the
        ``deal_decoder`` the canonical parser calls. A list is read as option indices; a
        ``{issue_name: option_label}`` object goes through ``DealSpace.parse`` (the ONE name decoder, tolerant
        of case/whitespace), whose ``ValueError`` on an unknown issue/option becomes the ``None`` that
        ``parse_action`` reports as an economic-legality failure."""
        if isinstance(deal_obj, (list, tuple)):
            try:
                return tuple(int(x) for x in deal_obj)
            except (TypeError, ValueError):
                return None
        if isinstance(deal_obj, dict):
            try:
                return self.space.parse(deal_obj)
            except (ValueError, AttributeError):
                return None
        return None

    def _parse_action(self, content: str):
        """One formal action read from a message body via the canonical ``parse_action``, or ``None`` if the
        turn carried no well-formed legal action."""
        res = parse_action(content, deal_decoder=self._decode_deal)
        return res.action if res.ok else None

    def _state_from_view(self, view: list[dict]) -> NegotiationState:
        """Rebuild a ``NegotiationState`` from the flattened ``view``.

        Preferred path: if the scenario embedded an authoritative ``negotiation_state`` fenced-JSON block in
        any view segment (its canonical offer registry + round), use the latest one. Fallback: walk the view
        in order, assigning monotonic offer ids to every ``Propose`` (role ``assistant`` = this seat, role
        ``user`` = an opponent), track the latest incoming (opponent) offer as ``standing``, and infer the
        round from this seat's completed turns."""
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
