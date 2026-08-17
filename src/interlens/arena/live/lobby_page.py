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
"""The lobby: choose a game and decide who plays each seat.

Built on ``viz.page._document``, the same shell the episode pages use, so the lobby inherits the visualizer's
CSS, its light/dark handling and its layout without a second stylesheet to keep in step. Pure string-building
like the rest of the visualizer: this module renders, it never fetches or mutates.

The one thing the lobby must get right is not offering a configuration that will fail. Model capabilities differ
in ways that are hard errors rather than degradations — the Claude-5 models reject a temperature outright, Fable
cannot turn thinking off, Haiku refuses adaptive thinking — so the seat cards are generated FROM each model's
declared ``thinking_modes`` and ``supports_temperature`` rather than from a fixed set of controls. A budget cap
is required before any metered seat can start, for the same reason: it is the only thing standing between a
click and an unbounded bill.

Owned by lane C.
"""
from __future__ import annotations


def render_lobby_html(state: dict) -> str:
    """The complete lobby page.

    ``state`` is ``SessionManager.lobby_state()``: the provider's listings (``banks``, ``framings``, ``models``)
    plus the current selection (``bank``, ``framing``, ``instance_id``, ``seats``, ``budget_usd``) and whether a
    session is already running. Self-contained — inline CSS and JS, no network fetches on load — so it opens the
    same way the exported visualizer pages do.
    """
    raise NotImplementedError("live-play lane C")


def _seat_card(idx: int, seat_name: str, config: dict, models: list[dict], policies: list[str]) -> str:
    """One seat's configuration card: kind picker, then the controls that kind needs — model + thinking mode for
    an LLM seat (generated from that model's declared capabilities), policy for a computable one, player name for
    a human — plus the private-instructions box, greyed out for computable seats since a policy reads no prose."""
    raise NotImplementedError("live-play lane C")


def _game_picker(state: dict) -> str:
    """The bank / framing / instance pickers and the budget cap field."""
    raise NotImplementedError("live-play lane C")
