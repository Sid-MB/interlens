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
"""The lobby's browser layer: edit the seat lineup, then start the game.

Every edit is POSTed to ``/api/lobby`` and the server's response is what the page re-renders from — the server
owns the configuration, the page never keeps its own copy. That is what makes a second browser tab on the lobby
show the same lineup instead of a private one, and it means the validation that matters (does this model exist,
does it accept this thinking mode) happens where the provider is.

``/api/start`` returns the session id; the page then navigates to ``/play``, which is rendered server-side from
the session's snapshot.

Owned by lane C.
"""
from __future__ import annotations

# The lobby page's inline script. See ``lobby_page.render_lobby_html`` for the DOM it drives.
JS_LOBBY = r"""
// live-play lane C
"""
