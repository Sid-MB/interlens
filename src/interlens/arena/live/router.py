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
# [implement: live-play/lane0] 2026-08-16
"""``LiveSeatRouter``: a seat table whose occupants can change while the episode is running.

``SeatRouter`` already presents a heterogeneous lineup to the engine as one participant. This subclass adds the
two things live play needs on top:

- **hot-swap.** :meth:`swap` replaces a seat's participant between turns. The engine holds a reference to the
  TABLE, not to the seat participants, so replacing an entry in the table is all it takes for the next turn to be
  played by somebody else — no episode restart, no engine involvement.
- **attribution.** Every message the table returns is stamped with the occupant label that produced it
  (``msg.metadata["occupant"]`` -> ``TurnRecord.occupant``), so the transcript records who played each turn
  rather than who holds the seat when you happen to read it.

The lock matters and is easy to get wrong. ``generate`` runs on an engine worker thread and ``swap`` on an HTTP
thread, so a swap can land at any instant. The rule: the participant AND its label are read together, once, under
the lock, and generation then runs OUTSIDE it against that snapshot. Reading them separately could stamp one
occupant's label on another's turn, which is the one failure that would make the occupant record a lie; holding
the lock across generation would instead block every swap for the length of an API call.

A swap therefore takes effect on the NEXT turn, never mid-turn. That is also why a swap is refused while the
seat's human prompt is open: the person is already answering, and the turn is theirs.

Owned by lane A.
"""
from __future__ import annotations

from typing import Any, Callable

from ...message import Message
from ..table import SeatRouter


class LiveSeatRouter(SeatRouter):
    """A :class:`~interlens.arena.table.SeatRouter` that supports mid-episode occupant changes.

    Parameters
    ----------
    seats : dict[str, Participant]
        Seat display name to the participant that starts the episode in it.
    labels : dict[str, str] | None
        Seat display name to its occupant label (``"api:claude-fable-5"``, ``"human:sid"``, ...). Seats missing
        from the map are stamped with nothing, which is how a turn records "unlabelled occupant" rather than
        guessing one.
    on_turn_start : callable | None
        ``on_turn_start(seat, occupant) -> None``, called just BEFORE dispatching a turn. This is the hook the
        live page's "who is thinking" indicator is driven from: it fires while the model call is in flight, which
        is the only moment the information exists and the only moment it is useful. Exceptions from it must not
        reach the engine — a broken indicator cannot be allowed to kill a game.
    name : str
        Identifier within the conversation.
    """

    def __init__(self, seats: dict[str, Any], labels: dict[str, str] | None = None,
                 on_turn_start: Callable[[str, str | None], None] | None = None,
                 name: str = "live_table"):
        raise NotImplementedError("live-play lane A")

    def generate(self, view, *, seat: str | None = None, **kwargs) -> Message:
        """Snapshot (participant, label) for ``seat`` under the lock, fire ``on_turn_start``, generate outside the
        lock, and return the message with ``metadata["occupant"]`` set to the snapshotted label.

        The label is stamped only when the participant did not set one itself, so a participant that knows better
        than the table who it is (a human seat naming the player) keeps its own attribution."""
        raise NotImplementedError("live-play lane A")

    def swap(self, seat: str, participant: Any, label: str) -> str | None:
        """Install ``participant`` as ``seat``'s occupant from the next turn on. Returns the label of the
        occupant that was replaced (``None`` if it had none), which the caller reports as the ``from`` side of a
        ``seat_swapped`` event.

        Raises ``KeyError`` for an unknown seat. Does NOT check whether a human prompt is open on that seat — the
        session enforces that, because it is the half that knows the session's phase.
        """
        raise NotImplementedError("live-play lane A")

    def occupants(self) -> dict[str, str | None]:
        """The current seat -> occupant-label map, read under the lock. What ``hello`` reports so a page that
        just connected badges seats correctly without replaying the whole swap history."""
        raise NotImplementedError("live-play lane A")
