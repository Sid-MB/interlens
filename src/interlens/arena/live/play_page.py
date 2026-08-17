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
"""The live episode page: the visualizer's episode view, plus the controls to play in it.

This is deliberately the EXISTING episode page and not a new one. The body is assembled from the same fragments
the static page uses (``viz.page._chat_bubbles``/``_sidebar``/``_game_cards``/``_issue_pane``, ``viz.chrome``'s
topbar and summary strip) inside the same ``viz.page._document`` shell, and the same chart/transcript/hover JS
runs on the same ``PAYLOAD`` object. What live play adds is a live UPDATE path (``assets/js_live.py``) and two
docks; everything a reader already knows how to read stays exactly where it was.

Rendering server-side from a snapshot, rather than booting an empty page that fetches, is what makes a reload
mid-episode land on the full transcript immediately and then attach to the stream — no flash of an empty game,
no divergence between what was rendered and what is being streamed.

The two docks:

- the HUMAN CONTROL DOCK — an offer builder generated from the deal space (one selector per issue, so an
  unrepresentable deal cannot be expressed), accept/reject/walk/pass buttons enabled from the server's own
  legality verdict, a public message box, a private scratchpad recorded as ``TurnRecord.human_note``, and the
  seat's PRIVATE score sheet with its values and threshold. The player negotiates under exactly the information
  a model seat has, which is the only way a human turn is comparable to a model one.
- the SWAP DOCK — reassign any seat mid-game.

Owned by lane D.
"""
from __future__ import annotations


def render_live_html(snapshot: dict) -> str:
    """The complete live page for a session.

    ``snapshot`` is ``LiveSession.snapshot()``: ``{seq, payload, phase, awaiting, occupants, lobby}``. The
    ``payload`` is a full ``viz.episode_payload`` — the same object the exported page is built from — so the page
    is a correct static rendering of the game so far even before its JS runs, and ``seq`` is the sequence number
    the page then subscribes from so nothing is missed between render and attach.
    """
    raise NotImplementedError("live-play lane D")


def _human_dock(awaiting: dict | None, game: dict, sheet: dict | None) -> str:
    """The player's control dock: offer builder over ``game``'s issues and options, action buttons enabled from
    ``awaiting["legal"]``, message box, private scratchpad, and the private score sheet. Rendered (disabled) even
    when ``awaiting`` is ``None``, so the layout does not jump when it is this seat's turn."""
    raise NotImplementedError("live-play lane D")


def _swap_dock(occupants: dict, lobby: dict) -> str:
    """The mid-game seat-reassignment dock: current occupant per seat and the same seat-configuration controls
    the lobby uses, reusing ``lobby_page._seat_card`` so there is one seat editor rather than two."""
    raise NotImplementedError("live-play lane D")
