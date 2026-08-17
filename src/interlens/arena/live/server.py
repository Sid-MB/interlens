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

import json
import logging
import queue
import re
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ..viz.serve import serve_banner
from . import events
from .lobby_page import render_lobby_html
from .play_page import render_live_html
from .provider import ScenarioProvider, SeatConfig
from .session import SessionManager

logger = logging.getLogger(__name__)

# Bind address. All interfaces rather than localhost, matching ``viz.serve`` — the reader is normally on a
# cluster node behind a firewall and reaching it over ``ssh -L``.
DEFAULT_HOST = "0.0.0.0"

# The per-session routes, as one pattern: ``/api/session/{sid}/{action}``.
SESSION_ROUTE = re.compile(r"^/api/session/(?P<sid>[^/]+)/(?P<action>state|events|act|swap|stop)$")

# A cap on a POST body, so a stray upload cannot be read into memory forever. Generous next to the largest thing
# a browser sends here (a lobby with eight seats and per-seat instructions).
MAX_BODY_BYTES = 1 << 20


class LiveHandler(BaseHTTPRequestHandler):
    """One request. Dispatches the route table above against the server's ``SessionManager``.

    The manager and the provider hang off the server object (set by :func:`make_live_server`) rather than off the
    handler, since a handler instance lives for exactly one request.
    """

    # HTTP/1.1 so a keep-alive SSE connection is not closed after the first response.
    protocol_version = "HTTP/1.1"
    server_version = "interlens-live/1.0"

    # --- routing --------------------------------------------------------------------------------------- #
    @property
    def manager(self) -> SessionManager:
        """The server's one session registry."""
        return self.server.manager                                             # type: ignore[attr-defined]

    def do_GET(self) -> None:
        """Serve the two pages, the snapshot, and the event stream."""
        url = urlparse(self.path)
        route = url.path.rstrip("/") or "/"
        try:
            if route == "/":
                return self._send_html(render_lobby_html(self.manager.lobby_state()))
            if route == "/play":
                session = self._active_or_404()
                if session is None:
                    return
                return self._send_html(render_live_html(session.snapshot()))
            if route == "/api/lobby":
                return self._send_json(self.manager.lobby_state())
            match = SESSION_ROUTE.match(route)
            if match and match["action"] == "state":
                session = self._session_or_404(match["sid"])
                return None if session is None else self._send_json(session.snapshot())
            if match and match["action"] == "events":
                session = self._session_or_404(match["sid"])
                return None if session is None else self._stream(session, url.query)
            self._send_json({"error": f"no route {route}"}, status=404)
        except Exception as exc:                         # noqa: BLE001 - one request must not kill the server
            logger.exception("live server: GET %s failed", self.path)
            self._send_json({"error": f"{type(exc).__name__}: {exc}"}, status=500)

    def do_POST(self) -> None:
        """Handle a lobby edit, a start, a human move, a swap, a stop, or a reset."""
        route = urlparse(self.path).path.rstrip("/") or "/"
        try:
            body = self._read_json()
        except ValueError as exc:
            return self._send_json({"error": str(exc)}, status=400)
        try:
            if route == "/api/lobby":
                return self._send_json(self.manager.update_lobby(body))
            if route == "/api/start":
                session = self.manager.start(body or None)
                return self._send_json({"sid": session.sid, "episode_id": session.episode_id,
                                        "phase": session.phase})
            if route == "/api/reset":
                self.manager.reset()
                return self._send_json(self.manager.lobby_state())
            match = SESSION_ROUTE.match(route)
            if match:
                session = self._session_or_404(match["sid"])
                if session is None:
                    return None
                return self._act(session, match["action"], body)
            self._send_json({"error": f"no route {route}"}, status=404)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
        except Exception as exc:                         # noqa: BLE001 - one request must not kill the server
            logger.exception("live server: POST %s failed", self.path)
            self._send_json({"error": f"{type(exc).__name__}: {exc}"}, status=500)

    def _act(self, session, action: str, body: dict) -> None:
        """The three per-session mutations. A refused human move is the interesting one: it answers 400 AND
        broadcasts ``input_rejected``, because the person who typed it is not necessarily the only one watching —
        and the seat is still blocked, so the form has to stay open with the reason attached."""
        if action == "act":
            seat = body.get("seat") or ""
            try:
                session.submit_human(seat, body)
            except ValueError as exc:
                session.broadcast(*events.input_rejected(seat, str(exc)))
                return self._send_json({"error": str(exc)}, status=400)
            return self._send_json({"ok": True})
        if action == "swap":
            # ``seat_config`` is what the play page's swap dock sends and ``seat`` what the lobby's seat editor
            # sends; they carry the same SeatConfig, so both are read rather than making one page rename a field
            # to match the other.
            config = body.get("seat_config") if body.get("seat_config") is not None else body.get("seat")
            session.swap_seat(int(body.get("seat_idx", -1)), SeatConfig.from_json(config or {}))
            return self._send_json({"ok": True, "occupants": session.occupants})
        if action == "stop":
            session.stop()
            return self._send_json({"ok": True, "phase": session.phase})
        return self._send_json({"error": f"no action {action}"}, status=404)

    # --- the event stream ------------------------------------------------------------------------------ #
    def _stream(self, session, query: str) -> None:
        """The SSE endpoint: replay, then live, forever.

        Replay comes first and comes from the session's log (everything after ``Last-Event-ID``), so a browser
        that reloaded mid-episode is caught up before it hears anything new. Then the handler simply blocks on its
        subscriber queue, writing a ``: ping`` comment whenever a whole keepalive interval passes with nothing
        happening — which is normal, since one API turn can take half a minute and an idle connection is exactly
        what a proxy reaps. Every frame is flushed on write; buffering an event stream defeats it.

        ``Last-Event-ID`` is read from the header EventSource sends on its own reconnects, and from a
        ``last_event_id`` query parameter for the first connection, where a page rendered from a snapshot has a
        sequence number to resume from but no way to set a header.

        The opening ``hello`` is connection metadata rather than a logged event, so it is framed with the id the
        client ALREADY has (the resume point, or 0) instead of consuming a sequence number of its own: every id
        the client then sees is strictly increasing, and a reconnect that echoes the hello's id resumes from
        exactly where this one started. Its body carries the session's current tip, which is how a page rendered
        from a snapshot learns whether it is behind.
        """
        header = self.headers.get("Last-Event-ID")
        param = (parse_qs(query or "").get("last_event_id") or [None])[0]
        raw = header if header not in (None, "") else param
        try:
            last = int(raw) if raw not in (None, "") else None
        except (TypeError, ValueError):
            last = None

        q = session.subscribe(last)
        self.send_response(200)
        for key, value in events.SSE_HEADERS:
            self.send_header(key, value)
        self.end_headers()
        # No Content-Length is possible on a stream that ends when the game does, so this response owns its
        # connection to the end of it.
        self.close_connection = True
        try:
            kind, data = events.hello(session.sid, session.seq, session.phase, session.occupants)
            self.wfile.write(events.format_sse(last or 0, kind, data))
            self.wfile.flush()
            while True:
                try:
                    seq, event, data = q.get(timeout=events.KEEPALIVE_SECONDS)
                except queue.Empty:
                    self.wfile.write(events.KEEPALIVE_FRAME)
                    self.wfile.flush()
                    continue
                self.wfile.write(events.format_sse(seq, event, data))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError, ValueError):
            pass                                          # the browser navigated away; nothing to report
        finally:
            session.unsubscribe(q)

    # --- plumbing -------------------------------------------------------------------------------------- #
    def _session_or_404(self, sid: str):
        """The named session, or ``None`` after answering 404 — so a caller returns immediately on ``None``."""
        try:
            return self.manager.get(sid)
        except KeyError:
            self._send_json({"error": f"no session {sid!r}"}, status=404)
            return None

    def _active_or_404(self):
        """The running session, or ``None`` after answering 404 (the live page with no game to show)."""
        session = self.manager.active
        if session is None:
            self._send_json({"error": "no session is running; start one from the lobby"}, status=404)
        return session

    def _read_json(self) -> dict:
        """The request body as a dict. An empty body is ``{}`` (a stop needs no arguments); anything that is not
        a JSON object raises ``ValueError``, which the caller answers 400 with."""
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        if length > MAX_BODY_BYTES:
            raise ValueError(f"request body of {length} bytes exceeds the {MAX_BODY_BYTES}-byte limit")
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"body is not valid JSON: {exc}") from exc
        if not isinstance(body, dict):
            raise ValueError("body must be a JSON object")
        return body

    def _send_json(self, payload: dict, status: int = 200) -> None:
        """One JSON response. ``default=str`` so a stray Path on a provenance field degrades to its string
        instead of taking the response down."""
        self._send_bytes(json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"),
                         "application/json; charset=utf-8", status)

    def _send_html(self, html: str, status: int = 200) -> None:
        """One HTML page."""
        self._send_bytes(html.encode("utf-8"), "text/html; charset=utf-8", status)

    def _send_bytes(self, body: bytes, content_type: str, status: int) -> None:
        """Write one complete response. ``Content-Length`` is always set: under HTTP/1.1 a keep-alive connection
        with no length has no way to tell where the response ended, and the next request on it hangs."""
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass                                          # the client gave up before we answered

    def log_message(self, fmt: str, *args) -> None:
        """Quiet by default: an SSE stream plus a per-turn poll would otherwise fill the terminal the operator is
        watching the game in. Routed through the module logger at debug level instead."""
        logger.debug("%s - %s", self.address_string(), fmt % args)


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
    root = Path(run_dir) if run_dir is not None else Path(tempfile.mkdtemp(prefix="interlens-live-"))
    root.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), LiveHandler)
    server.manager = SessionManager(provider, root)                            # type: ignore[attr-defined]
    server.run_dir = root                                                      # type: ignore[attr-defined]
    return server


def run_live_server(provider: ScenarioProvider, host: str = DEFAULT_HOST, port: int = 0, run_dir=None) -> None:
    """Serve live play until interrupted — bind, print the banner (including the ``ssh -L`` line, reusing
    ``viz.serve.serve_banner``'s form), then block in ``serve_forever``. ``Ctrl-C`` shuts down and returns
    normally so the CLI exits 0, and stops any session still running first."""
    server = make_live_server(provider, host=host, port=port, run_dir=run_dir)
    bound = server.server_address[1]
    # The visualizer's banner, re-tagged: it already works out this host's real name and the exact ``ssh -L``
    # line to forward the port, which is the only part anyone reads. Reusing it and relabelling beats a second
    # copy of the hostname/forwarding logic that would drift the first time either changes.
    banner = serve_banner(server.run_dir, bound, host=host).replace("[viz]", "[live]").replace("/index.html", "/")
    try:
        print(banner, flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[live] stopped", flush=True)
    finally:
        server.manager.reset()
        server.server_close()
