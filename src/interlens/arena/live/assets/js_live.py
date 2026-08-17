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
"""The live page's browser layer: subscribe, merge, redraw, and take the player's move.

The merge rule is one line and worth stating exactly, because everything else follows from it: a
``turn_appended`` event's ``turn`` is PUSHED onto ``PAYLOAD.turns`` — the array is mutated in place, never
replaced — and then the existing draw functions are called again. The episode page already re-renders entirely
from the in-memory ``PAYLOAD`` (that is how its seat and oracle selectors work), so a live page is that same page
with a growing array. Nothing about the chart, the regret bars, the hover cards or the transcript cards is
reimplemented here.

Per turn: push the row, insert the server-rendered ``bubble_html`` into the chat pane, ``drawChart()`` and
``drawRegret()``, wire the ONE new turn card, and re-mount the sidebar (it snapshots turns at mount, and a
re-mount is cheap enough to be the honest fix).

Reconnects are handled by ``EventSource``, which resends ``Last-Event-ID`` by itself; the session replays its log
from there, so a dropped connection costs nothing. A page that has been away long enough to be unsure re-fetches
``/state`` instead of trusting an incremental merge.

Owned by lane D.
"""
from __future__ import annotations

# The live page's inline script: SSE client, PAYLOAD merge, human control dock, swap dock.
JS_LIVE = r"""
// live-play lane D
"""
