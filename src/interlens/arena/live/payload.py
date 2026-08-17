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
# [implement: live-play/laneB] 2026-08-16
"""Per-turn slices of the visualizer payload, for streaming one turn at a time.

A live page and a static page must show the same thing, and the only way to be sure of that is for both to come
out of the same code. So there is no live payload builder: :func:`turn_delta` calls the visualizer's own
``viz.episode._turn_payload`` and :func:`bubble_html` its own ``viz.page._chat_bubble``, which are exactly the
per-turn units ``episode_payload`` and ``_chat_bubbles`` are built from. A streamed turn is therefore
byte-identical to the row a reload rebuilds, and a drift between the two is not a bug that can happen — it would
require the shared function to disagree with itself.

Everything episode-scoped (the geometry, the seat kinds, the seat->party map) is computed ONCE per session and
passed in, because rebuilding a game's geometry on every turn is the one thing here expensive enough to notice.

Owned by lane B.
"""
from __future__ import annotations

from typing import Any

from ..viz.episode import _oracle_records, _turn_payload, gen_failures, public_ledger, seat_kinds
from ..viz.page import _chat_bubble


def turn_delta(episode: dict, turn: dict, rows: list[dict], *, geometry: Any = None, kinds: dict | None = None,
               oracles: dict | None = None, seat_party: dict | None = None) -> dict:
    """Append one committed turn's payload row to ``rows`` and return it — what a ``turn_appended`` event carries.

    ``episode`` is the live episode's ``to_json()`` (read for the seat list), ``turn`` the stored turn dict to
    render, and ``rows`` the session's ACCUMULATED payload rows, appended to in place. ``geometry`` is the
    session's prebuilt ``GameGeometry``, ``kinds`` the ``viz.episode.seat_kinds`` result, ``oracles`` the
    episode's per-turn oracle records and ``seat_party`` the seat-name -> party-index map: all four are
    episode-scoped and computed once at session start rather than per turn.

    The accumulated list is required, not a convenience. Three fields on a row — ``published``, ``offer_id`` and
    ``standing_deal_index`` — are properties of a turn's POSITION IN THE SEQUENCE rather than of the turn
    (``viz.episode.public_ledger`` derives them), and a retried turn retroactively flips an earlier row's
    ``published`` to False. So the ledger is re-derived over the whole accumulated list after each append: a few
    dozen rows of pure Python, next to an engine turn that just spent seconds in a model call. Skipping it is the
    one way a streamed row can differ from the row a reload rebuilds.

    Views are never reconstructed here (replaying the episode once per turn would be absurd on a live path), so a
    turn the engine did not store a view for is reported ``view_source="absent"`` rather than reconstructed — the
    honest answer, and the same one ``episode_payload(reconstruct=False)`` gives.

    ``kinds``, ``oracles`` and ``seat_party`` are derived from ``episode`` when omitted, so a caller with nothing
    cached still gets a correct row. Pass the episode-scoped ones (``kinds``, ``seat_party``, ``geometry``) for
    the live path; ``oracles`` is the exception that is normally left to default, since a turn's oracle records
    are written by the engine as the turn is committed and so do not exist before it.
    """
    idx = int(turn.get("idx", len(rows)))
    slot = (turn.get("round"), turn.get("phase"), turn.get("seat"))
    # A superseded first attempt at a slot already played: the ONLY thing it changes is how a missing view is
    # labelled, and it is read off the rows already accumulated rather than tracked separately, so a session that
    # was rebuilt from a reload gets the same answer as one that has been streaming since turn zero.
    is_retry = any((r.get("round"), r.get("phase"), r.get("seat")) == slot for r in rows)
    if kinds is None:
        kinds = seat_kinds(episode, None)
    if seat_party is None:
        seat_party = {s.get("name"): i for i, s in enumerate(episode.get("seats") or [])}
    if oracles is None:
        oracles = _oracle_records(episode, None)
    fabricated = {row["idx"]: row for row in gen_failures(episode)}
    row = _turn_payload(turn, idx, is_retry=is_retry, geo=geometry, kinds=kinds, oracles=oracles,
                        seat_party=seat_party, rebuilt={}, fabricated=fabricated)
    rows.append(row)
    # In place over the WHOLE list, not just the new row — see the note above on retroactive ``published``.
    public_ledger(rows)
    return row


def bubble_html(payload: dict, turn: dict) -> str:
    """The chat bubble for one turn, server-rendered by the visualizer's own ``_chat_bubble``.

    Rendered server-side rather than reimplemented in JS for the same reason the static page renders it there:
    there would otherwise be two bubble renderers to keep in step, and the browser copy would be the one that
    quietly went stale.

    ``payload`` must carry BOTH the seat table and the transcript so far (``{"seats": [...], "turns": [...]}``),
    and ``turn`` should already be among those turns. The seats are the obvious half; the turns are the half that
    is easy to skip and silently wrong to omit. ``_chat_bubble`` derives each seat's DEFAULT occupant from the
    transcript and badges a turn only when it DEPARTS from that default — so against an empty ``turns`` no seat
    has a known default, every badge suppresses itself, and a transcript renders as though no seat had ever
    changed hands. That is not a degraded bubble, it is the swap badge silently doing nothing, which is the one
    thing a live transcript shows that a static one cannot. Passing the accumulated rows is also what makes the
    bubble byte-identical to the one a reload rebuilds, since a reload derives the same map from the same rows.
    """
    return _chat_bubble(payload, turn)
