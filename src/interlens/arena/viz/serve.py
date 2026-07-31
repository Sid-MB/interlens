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
# [rational_agents: viz] 2026-07-29
# [rational_agents: viz-serve] 2026-07-31

"""Hand the rendered pages to a browser over HTTP, for when the filesystem the pages live on is not the one the
browser runs on.

The pages themselves need no server — they are self-contained and open by double-click. This exists for the
usual research setup: you are ssh'd into a cluster node, the run directory is there, and your browser is on your
laptop. Rather than copying a directory of HTML back, serve it in place and forward one port.

Stdlib only (:mod:`http.server`), so this adds no dependency to a package whose visualizer is otherwise pure
string-building. The server is threading so a page's several asset-free requests do not serialize, and it is
read-only by construction: :class:`~http.server.SimpleHTTPRequestHandler` implements GET/HEAD and nothing else.
"""
from __future__ import annotations

import socket
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Bind address. All interfaces, not localhost: the point is to be reachable, and a login/compute node is normally
# behind the cluster firewall anyway. ``serve_banner`` says so out loud so the choice is never silent.
DEFAULT_HOST = "0.0.0.0"


def make_server(directory: str | Path, port: int = 0, host: str = DEFAULT_HOST) -> ThreadingHTTPServer:
    """Bind (but do not run) an HTTP server rooted at ``directory``.

    ``port`` is the TCP port to listen on; ``0`` — the default — asks the OS for a free ephemeral port, which is
    what you want when several people share a node and fixed ports collide. Read the port that was actually
    chosen back off ``server.server_address[1]``. ``host`` is the bind address (see :data:`DEFAULT_HOST`).

    Returns the bound server so the caller decides how to run it: ``serve_forever()`` on this thread (see
    :func:`serve_directory`) or on another one for a test. Call ``server_close()`` when done.
    """
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    return ThreadingHTTPServer((host, port), handler)


def serve_banner(directory: str | Path, port: int, host: str = DEFAULT_HOST) -> str:
    """The startup message: where the pages are, the URL to open, and — because the reader is usually on a
    cluster node with no browser — the exact ``ssh -L`` command to forward ``port`` to their laptop, with this
    machine's real hostname already filled in. Returned as a string rather than printed so it is testable.
    """
    hostname = socket.getfqdn()
    lines = [
        f"[viz] serving {Path(directory).resolve()}",
        f"[viz] open: http://{hostname}:{port}/index.html",
    ]
    if host == "0.0.0.0":
        lines.append(f"[viz] bound to {host} (all interfaces) — anything that can route to this host can read it")
    lines += [
        "[viz] no browser on this machine? forward the port from your laptop:",
        f"[viz]     ssh -L {port}:localhost:{port} {hostname}",
        f"[viz]     then open http://localhost:{port}/index.html",
        "[viz] Ctrl-C to stop",
    ]
    return "\n".join(lines)


def serve_directory(directory: str | Path, port: int = 0, host: str = DEFAULT_HOST) -> None:
    """Serve ``directory`` over HTTP until interrupted — bind, print :func:`serve_banner`, then block in
    ``serve_forever``. ``Ctrl-C`` (``KeyboardInterrupt``) shuts the server down and returns normally rather than
    raising, so the CLI exits 0. See :func:`make_server` for ``port`` / ``host``.
    """
    server = make_server(directory, port=port, host=host)
    try:
        print(serve_banner(directory, server.server_address[1], host=host), flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[viz] stopped", flush=True)
    finally:
        server.server_close()
