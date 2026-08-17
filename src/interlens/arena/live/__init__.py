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
"""Live play: watch an arena episode as it happens, reconfigure its seats, and play one yourself.

The rest of the arena is run-then-inspect — episodes roll out headlessly and the visualizer renders the JSON
afterwards. This package adds the interactive half: a localhost server that streams a negotiation turn by turn
into the visualizer's own episode page, lets every seat be configured (and re-configured mid-game) between a
model, a computable policy, an omniscient oracle and a person, and blocks a human seat on a browser form that
produces a move byte-identical in form to a model's.

Three design commitments hold the whole thing together:

1. **One payload code path.** A streamed turn and a reloaded page come out of the same visualizer functions
   (``viz.episode._turn_payload``, ``viz.page._chat_bubble``), so live and static views cannot drift.
2. **The stream follows the disk.** Turns are broadcast from an engine observer that runs after the episode is
   persisted, so nothing is ever shown that a reload would not find.
3. **The library stays generic.** Instance banks, framings, scaffolds and model credentials enter through a
   :class:`ScenarioProvider` the experiment implements; interlens never learns what a framing is.

Usage::

    from interlens.arena.live import run_live_server
    run_live_server(MyProvider(), port=8080, run_dir="results/live")

Stdlib only (``http.server`` + server-sent events), like the rest of the visualizer.
"""
from __future__ import annotations

from . import events
from .human import HumanParticipant, PendingRequest
from .provider import BankInfo, ModelInfo, PreparedGame, ScenarioProvider, SeatConfig, SEAT_KINDS
from .router import LiveSeatRouter
from .server import make_live_server, run_live_server
from .session import LiveSession, SessionManager

__all__ = [
    "run_live_server", "make_live_server",
    "ScenarioProvider", "SeatConfig", "PreparedGame", "BankInfo", "ModelInfo", "SEAT_KINDS",
    "HumanParticipant", "PendingRequest", "LiveSeatRouter",
    "LiveSession", "SessionManager", "events",
]
