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
"""The HTTP surface: a stdlib ``ThreadingHTTPServer`` serving the lobby, the live page, and the event stream.

Stdlib only, matching ``viz/serve.py`` — the visualizer's whole point is that it adds no dependency to a package
that is otherwise pure string-building, and a live server is not a good enough reason to put a web framework in
it. ``ThreadingHTTPServer`` gives a thread per request, which is what an SSE endpoint needs: those handlers are
long-lived, looping on their subscriber queue for the length of the game, and would block every other request on
a single-threaded server.

Routes (all JSON in, JSON out, except the two HTML pages):

===================================== ====== ==========================================================
Route                                 Method Purpose
===================================== ====== ==========================================================
``/``                                 GET    The lobby page (HTML)
``/play``                             GET    The live episode page (HTML), rendered from the snapshot
``/api/lobby``                        GET    Current lobby configuration + provider listings
``/api/lobby``                        POST   Partial lobby edit; returns the updated state
``/api/start``                        POST   Prepare a game and start a session -> ``{sid, episode_id}``
``/api/session/{sid}/state``          GET    Full snapshot: payload, phase, awaiting, occupants, seq
``/api/session/{sid}/events``         GET    The SSE stream (honours ``Last-Event-ID``)
``/api/session/{sid}/act``            POST   A human seat's move
``/api/session/{sid}/swap``           POST   Replace a seat's occupant
``/api/session/{sid}/stop``           POST   End the session
``/api/reset``                        POST   Drop the session and return to the lobby
===================================== ====== ==========================================================

The server binds but does not start, exactly like ``viz.serve.make_server``, so the caller chooses the thread and
the tests can run it on an ephemeral port. Port 0 is the default for the same reason it is there: shared nodes
and fixed ports collide.

Owned by lane B.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .provider import ScenarioProvider

# Bind address. All interfaces rather than localhost, matching ``viz.serve`` — the reader is normally on a
# cluster node behind a firewall and reaching it over ``ssh -L``.
DEFAULT_HOST = "0.0.0.0"


class LiveHandler(BaseHTTPRequestHandler):
    """One request. Dispatches the route table above against the server's ``SessionManager``.

    The manager and the provider hang off the server object (set by :func:`make_live_server`) rather than off the
    handler, since a handler instance lives for exactly one request.
    """

    # HTTP/1.1 so a keep-alive SSE connection is not closed after the first response.
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        """Serve the two pages, the snapshot, and the event stream."""
        raise NotImplementedError("live-play lane B")

    def do_POST(self) -> None:
        """Handle a lobby edit, a start, a human move, a swap, a stop, or a reset."""
        raise NotImplementedError("live-play lane B")

    def log_message(self, fmt: str, *args) -> None:
        """Quiet by default: an SSE stream plus a per-turn poll would otherwise fill the terminal the operator is
        watching the game in. Routed through the module logger at debug level instead."""
        raise NotImplementedError("live-play lane B")


def make_live_server(provider: ScenarioProvider, host: str = DEFAULT_HOST, port: int = 0,
                     run_dir=None) -> ThreadingHTTPServer:
    """Bind (but do not run) the live-play server over ``provider``.

    ``port=0`` asks the OS for a free ephemeral port; read the one chosen back off ``server.server_address[1]``.
    ``run_dir`` is where episodes are written (a temporary directory when omitted — but a session whose episodes
    are worth keeping should be given a real one, since the JSON on disk is the durable artifact and the stream
    is only a view of it).

    Returns the bound server so the caller decides how to run it: ``serve_forever()`` on this thread, or another
    one in a test. Call ``server_close()`` when done.
    """
    raise NotImplementedError("live-play lane B")


def run_live_server(provider: ScenarioProvider, host: str = DEFAULT_HOST, port: int = 0, run_dir=None) -> None:
    """Serve live play until interrupted — bind, print the banner (including the ``ssh -L`` line, reusing
    ``viz.serve.serve_banner``'s form), then block in ``serve_forever``. ``Ctrl-C`` shuts down and returns
    normally so the CLI exits 0, and stops any session still running first."""
    raise NotImplementedError("live-play lane B")
