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

# [rational_agents restructure: phase-C] 2026-07-24 — SeatRouter + the table builders moved up from the
# experiment layer; seat dispatch now reads the engine-passed seat identity instead of matching prompt text.
"""Heterogeneous **tables**: present a whole many-seat lineup to the arena engine as one participant.

The engine drives ONE ``Participant`` across every seat of an episode — it asks the same object to speak for
each seat in turn. That is exactly right for a homogeneous table (one model plays everyone) and wrong for the
interesting cases: a different computable policy per seat, some LLM seats and some policy seats, or per-seat
model diversity. :class:`SeatRouter` closes the gap by dispatching each turn to the sub-participant that owns
that seat, using the seat identity the engine passes (``Participant.generate(..., seat=...)``, straight from
``SeatRequest.seat``).

The builders here compose a table from a game and a lineup, so seat assignment lives in one place rather than
being re-derived per experiment:

- :func:`policy_seat` — one computable-rational seat (a :class:`PolicyParticipant` bound to a named policy).
- :func:`rational_table` — every seat a policy, cycled from a list of policy names.
- :func:`mixed_table` — some seats given participants explicitly (LLM or otherwise), the rest filled with
  policy seats, so a partly-specified lineup is always complete.

Example::

    from interlens.arena.table import rational_table, mixed_table
    from interlens.arena.negotiation import games

    game, analysis, protocol_cfg = games.make_preset("divide_dollar", n_parties=3)
    table = rational_table(game, ["boulware", "conceder", "tough"], deadline=game.rounds)
    # or put a model in seat 0 and let policies fill the rest:
    table = mixed_table(game, {0: my_model_participant}, deadline=game.rounds)
    # hand `table` to EpisodePool.run_episode as the participant
"""
from __future__ import annotations

from ..message import Message
from ..participant.participant import Participant
from .negotiation.oracle_context import GameTables
from .negotiation.policy_participant import PolicyParticipant
from .negotiation.sheets import GameSpec
from .negotiation.strategies import (ZOO, BayesianRationalPolicy, FairnessOraclePolicy,
                                     FairnessRationalPolicy)
from .schema import PERSONAS

# The offer-id prefix ``ScorableNegotiation`` mints ("P1", "P2", ...). A PolicyParticipant that falls back to
# reconstructing the ledger from the transcript must mint the same ids, or its offer references won't line up.
OFFER_PREFIX = "P"

# The computable policy zoo, keyed by name: everything in the strategies ZOO plus the composed Bayesian agent
# (not in ZOO because it reads the per-round discount off the NegotiationState the participant builds).
POLICY_FACTORIES = dict(ZOO)
POLICY_FACTORIES["bayes-rational"] = BayesianRationalPolicy
# The same composed agent with the objective swapped from own surplus to table welfare: the omniscient
# fairness mediator and its private-information counterpart.
POLICY_FACTORIES["fairness-oracle"] = FairnessOraclePolicy
POLICY_FACTORIES["fairness-rational"] = FairnessRationalPolicy


class SeatRouter(Participant):
    """One participant that routes each turn to a per-seat sub-participant, so a single object presents a
    heterogeneous table to the arena engine.

    Parameters
    ----------
    seats : dict[str, Participant]
        Seat display name (``"Avery"``, ``"Blake"``, ..., or a scenario's solo seat) to the participant that
        plays it. Interp requests are forwarded to the sub-participant, which accepts or refuses them per its own
        contract (a local-model seat can be captured/steered; a policy seat raises).
    name : str
        Identifier within the conversation.
    """

    self_role = "assistant"
    others_role = "user"

    def __init__(self, seats: dict[str, Participant], name: str = "seat_router"):
        self.name = name
        self.seats = dict(seats)
        self.system_prompt = None
        self.private_context = ()

    def generate(self, view, *, seat: str | None = None, **kwargs) -> Message:
        """Dispatch to the participant owning ``seat`` and return its message unchanged.

        ``seat`` comes from the engine (``SeatRequest.seat``). It is required: without it there is no reliable way
        to know which seat this turn is for, and guessing from the prompt text silently breaks whenever the
        wording changes — so a missing seat raises rather than picking a default."""
        return self.participant_for(seat).generate(view, seat=seat, **kwargs)

    def participant_for(self, seat: str | None):
        """The sub-participant that owns ``seat``.

        Declaring this method is how a table tells the batched engine "I am **pure dispatch** — you may address my
        sub-participants directly". ``BatchedEpisodePool`` uses it to group a co-stepped wave by the participant
        that will actually serve each request rather than by the table object, which is what makes a heterogeneous
        lineup batchable at all: every episode gets its OWN table (policy seats hold per-episode state), so
        grouping by table would put one request in each group and batch nothing, while grouping by owner collects
        the model seats of every live episode — which DO share one cached model participant — into a single batch.

        Only implement it on a table whose ``generate`` adds nothing of its own. A table that rewrites the view
        per seat (a planner/advocate wrapper) must NOT expose this, or the engine would bypass that rewriting;
        such a table supplies ``generate_batch_with_seats`` instead and keeps the whole wave."""
        if seat is None:
            raise ValueError(
                f"SeatRouter {self.name!r} needs the seat identity; the caller passed none. The arena engine "
                "supplies it from SeatRequest.seat — a bare Conversation does not, so drive a table through "
                "EpisodePool/BatchedEpisodePool.")
        if seat not in self.seats:
            raise KeyError(f"no participant assigned to seat {seat!r} (have {sorted(self.seats)})")
        return self.seats[seat]


def policy_seat(policy_name: str, seat_idx: int, game: GameSpec, *, deadline: int,
                full_info: bool = True, tables: GameTables | None = None) -> PolicyParticipant:
    """A computable-rational seat: a :class:`PolicyParticipant` bound to ``policy_name`` for seat ``seat_idx``.

    ``full_info`` (a FULL-information game) attaches the exact :class:`GameTables` so full-info policies (e.g.
    the Bayesian best-responder) compute exactly; a PRIVATE game passes ``tables=None`` so the policy relies on
    its belief model instead. The per-round ``discount`` is read off the game (its single source of truth). Deals
    are emitted and decoded by issue/option NAME straight off ``game.space``, matching the scenario transcript.
    """
    if policy_name not in POLICY_FACTORIES:
        raise ValueError(f"unknown policy {policy_name!r}; choose one of {sorted(POLICY_FACTORIES)}")
    policy = POLICY_FACTORIES[policy_name]()
    if tables is None and full_info:
        tables = GameTables.from_game(game)
    return PolicyParticipant(
        name=f"{policy_name}#{seat_idx}", policy=policy, seat=seat_idx, sheet=game.sheets[seat_idx],
        space=game.space, deadline=deadline, discount=getattr(game, "discount", 1.0), n_seats=game.n_parties,
        registry_prefix=OFFER_PREFIX, tables=tables)


def rational_table(game: GameSpec, policies: list[str], *, deadline: int,
                   full_info: bool = True, name: str = "all_rational") -> SeatRouter:
    """Every seat a computable policy: seat ``i`` plays ``policies[i % len(policies)]`` (cycled). The
    full-information :class:`GameTables` is built once and shared across seats."""
    tables = GameTables.from_game(game) if full_info else None
    seats = {PERSONAS[i]: policy_seat(policies[i % len(policies)], i, game, deadline=deadline,
                                      full_info=full_info, tables=tables)
             for i in range(game.n_parties)}
    return SeatRouter(seats, name=name)


def mixed_table(game: GameSpec, assignment: dict[int, Participant], *, deadline: int,
                full_info: bool = True, fill_policy: str = "bayes-rational",
                name: str = "mixed") -> SeatRouter:
    """A table where ``assignment`` maps a seat index to an already-built participant (e.g. an
    ``AutoModelParticipant`` or ``APIParticipant`` for an LLM seat) and every seat NOT in ``assignment`` is
    filled with a ``fill_policy`` seat — so a partly-specified lineup is always a complete table."""
    tables = GameTables.from_game(game) if full_info else None
    seats: dict[str, Participant] = {}
    for i in range(game.n_parties):
        seats[PERSONAS[i]] = (assignment[i] if i in assignment
                              else policy_seat(fill_policy, i, game, deadline=deadline,
                                               full_info=full_info, tables=tables))
    return SeatRouter(seats, name=name)
