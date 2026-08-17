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
# [implement: live-play/laneB] 2026-08-16
"""The live server over a real socket: the route table, and the event stream as a browser reads it.

Nothing is mocked. Each test binds the real ``make_live_server`` on an ephemeral port, runs it on a thread, and
talks to it with ``http.client`` — including the SSE endpoint, whose frames are parsed off the raw response the
way ``EventSource`` parses them (``id:`` / ``event:`` / ``data:``, blank line between frames). A stub provider
supplies one tiny generated negotiation played by computable seats, so a whole game runs in milliseconds and no
test touches the network.

What is worth pinning here rather than at the session level is everything that only exists once there is a
socket: that a reconnect with ``Last-Event-ID`` delivers exactly the tail it missed, that the response carries
the headers which stop a proxy from buffering an event stream into uselessness, and that a refused human move
answers 400 AND tells every watching browser why.
"""
from __future__ import annotations

import contextlib
import http.client
import json
import threading

import pytest

from interlens.arena.live import events
from interlens.arena.live.server import make_live_server
from interlens.arena.live.provider import SeatConfig

from .test_arena_live_session import StubProvider, lane_a_ready, wait_for

# Every socket operation is bounded: a live server test that hangs is far worse than one that fails, because it
# takes the whole suite with it.
TIMEOUT = 20.0

needs_lane_a = pytest.mark.skipif(not lane_a_ready(),
                                  reason="lane A's SeatConfig.occupant_label has not landed yet")

RATIONAL = {"kind": "rational", "policy": "bayes-rational"}


@contextlib.contextmanager
def serving(tmp_path, n_parties: int = 3):
    """A bound, running live server over a fresh stub provider. Shut down on exit."""
    server = make_live_server(StubProvider(n_parties), host="127.0.0.1", port=0, run_dir=tmp_path)
    thread = threading.Thread(target=server.serve_forever, name="live-test-server", daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=TIMEOUT)


def call(server, method: str, path: str, body=None, headers: dict | None = None):
    """One request/response against the server. Returns ``(status, parsed_body)`` — JSON decoded when the
    response says JSON, text otherwise."""
    conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=TIMEOUT)
    try:
        payload = None if body is None else json.dumps(body)
        conn.request(method, path, body=payload,
                     headers={"Content-Type": "application/json", **(headers or {})})
        response = conn.getresponse()
        raw = response.read()
        kind = response.getheader("Content-Type") or ""
        return response.status, (json.loads(raw) if raw and kind.startswith("application/json")
                                 else raw.decode("utf-8", "replace"))
    finally:
        conn.close()


@contextlib.contextmanager
def stream(server, sid: str, last_event_id: int | None = None):
    """An open SSE connection, yielding ``(response, headers)``.

    Read frames off it with :func:`read_frames`. ``last_event_id`` is sent as the header ``EventSource`` sends on
    its own reconnects, which is the path a reloading browser actually takes."""
    conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=TIMEOUT)
    headers = {} if last_event_id is None else {"Last-Event-ID": str(last_event_id)}
    try:
        conn.request("GET", f"/api/session/{sid}/events", headers=headers)
        response = conn.getresponse()
        yield response
    finally:
        conn.close()


def read_frames(response, until: str | None = None, limit: int = 500) -> list[tuple]:
    """Parse SSE frames off an open response, exactly as ``EventSource`` would.

    Reads line by line from the raw response body (an event stream has no Content-Length — it ends when the game
    does), accumulating ``field: value`` lines until the blank line that terminates a frame. Comment lines (the
    ``: ping`` keepalives) carry no fields and are skipped. Stops after a frame of type ``until``, or at ``limit``
    frames, or at EOF."""
    frames: list[tuple] = []
    while len(frames) < limit:
        fields: dict[str, str] = {}
        while True:
            line = response.fp.readline().decode("utf-8")
            if line in ("", "\n", "\r\n"):
                break
            if line.startswith(":"):
                continue
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
        if not fields:
            if line == "":
                break                                    # the server closed the stream
            continue                                     # a keepalive comment
        frames.append((int(fields["id"]), fields["event"], json.loads(fields["data"])))
        if until is not None and fields["event"] == until:
            break
    return frames


def start_game(server, seats: list[dict], budget_usd: float | None = None) -> str:
    """Configure a lineup and start it over HTTP. Returns the session id."""
    status, state = call(server, "POST", "/api/lobby", {"seats": seats, "budget_usd": budget_usd})
    assert status == 200, state
    status, started = call(server, "POST", "/api/start", {})
    assert status == 200, started
    return started["sid"]


def played_out(server, sid: str) -> dict:
    """Wait for the session's episode to finish and return its final snapshot."""
    wait_for(lambda: call(server, "GET", f"/api/session/{sid}/state")[1]["phase"] == "done",
             timeout=TIMEOUT, what="the episode to finish")
    return call(server, "GET", f"/api/session/{sid}/state")[1]


# --------------------------------------------------------------------------------------- the lobby --
def test_the_lobby_api_serves_the_configuration_and_takes_an_edit(tmp_path):
    """GET renders the lobby, POST changes it, and the change is what the next GET returns — the whole contract
    the lobby page's JS is written against."""
    with serving(tmp_path) as server:
        status, state = call(server, "GET", "/api/lobby")
        assert status == 200 and [s["kind"] for s in state["seats"]] == ["rational"] * 3

        status, updated = call(server, "POST", "/api/lobby",
                               {"index": 2, "seat": {"kind": "oracle", "policy": "bayes-rational"}})
        assert status == 200 and updated["seats"][2]["kind"] == "oracle"
        assert call(server, "GET", "/api/lobby")[1]["seats"][2]["kind"] == "oracle"


def test_a_refused_lobby_edit_is_a_400_with_the_reason(tmp_path):
    """The lobby's own validation, over the wire: refused where the person can still see the form."""
    with serving(tmp_path) as server:
        status, body = call(server, "POST", "/api/lobby", {"seats": [{"kind": "llm", "model_id": "nope"}]})
        assert status == 400 and "unknown model" in body["error"]


def test_a_body_that_is_not_a_json_object_is_a_400(tmp_path):
    """A 500 here would look like a server bug when it is a malformed request."""
    with serving(tmp_path) as server:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=TIMEOUT)
        conn.request("POST", "/api/lobby", body="not json", headers={"Content-Type": "application/json"})
        assert conn.getresponse().status == 400
        conn.close()


@pytest.mark.parametrize("method, path", [("GET", "/api/nope"), ("POST", "/api/nope"),
                                          ("GET", "/api/session/ghost/state"),
                                          ("POST", "/api/session/ghost/stop")])
def test_unknown_routes_and_sessions_are_404(tmp_path, method, path):
    with serving(tmp_path) as server:
        status, body = call(server, method, path, {} if method == "POST" else None)
        assert status == 404 and "error" in body


# -------------------------------------------------------------------------------------- the stream --
@needs_lane_a
def test_the_stream_opens_with_hello_and_replays_the_whole_game(tmp_path):
    """A browser that attaches after a fast game still receives all of it: ``hello`` first, then every logged
    event in order. This is the same code path a mid-episode reload takes, which is why replay is not an
    afterthought — it IS the normal path on a localhost server where the page is opened by hand."""
    with serving(tmp_path) as server:
        sid = start_game(server, [RATIONAL] * 3)
        played_out(server, sid)
        with stream(server, sid) as response:
            frames = read_frames(response, until=events.EPISODE_DONE)

    assert frames[0][1] == events.HELLO
    assert frames[0][2]["sid"] == sid and frames[0][2]["phase"] == "done"
    ids = [seq for seq, _, _ in frames]
    assert ids == sorted(ids), "sequence ids must never go backwards"
    kinds = [kind for _, kind, _ in frames]
    assert kinds.index(events.EPISODE_STARTED) < kinds.index(events.TURN_APPENDED)
    assert kinds.count(events.TURN_APPENDED) >= 3
    assert kinds[-1] == events.EPISODE_DONE
    assert frames[-1][2]["status"] == "done"


@needs_lane_a
def test_hello_never_consumes_a_sequence_number(tmp_path):
    """``hello`` is connection metadata, not a logged event, so it is framed with the id the client already has.
    If it took an id of its own, a reconnect echoing it would skip a real event."""
    with serving(tmp_path) as server:
        sid = start_game(server, [RATIONAL] * 3)
        played_out(server, sid)
        with stream(server, sid) as response:
            frames = read_frames(response, until=events.EPISODE_DONE)
        assert frames[0][0] == 0
        assert [seq for seq, _, _ in frames[1:]] == list(range(1, len(frames)))


@needs_lane_a
def test_a_reconnect_delivers_exactly_the_tail_it_missed(tmp_path):
    """The reload guarantee. A browser that reconnects with ``Last-Event-ID`` gets everything after it and
    nothing it already had — which is what makes a reload mid-episode lossless rather than a re-render that
    silently drops the turns played while the page was gone."""
    with serving(tmp_path) as server:
        sid = start_game(server, [RATIONAL] * 3)
        played_out(server, sid)
        with stream(server, sid) as response:
            whole = read_frames(response, until=events.EPISODE_DONE)
        resume = whole[3][0]
        with stream(server, sid, last_event_id=resume) as response:
            tail = read_frames(response, until=events.EPISODE_DONE)

    assert tail[0][1] == events.HELLO and tail[0][0] == resume
    assert tail[1:] == whole[4:], "a reconnect must replay the tail byte for byte"


@needs_lane_a
def test_the_stream_sends_the_headers_that_stop_a_proxy_buffering_it(tmp_path):
    """Without ``X-Accel-Buffering: no`` a proxy holds the stream until it has a bufferful, which for an event
    stream means the page shows nothing for a minute and then the whole game at once."""
    with serving(tmp_path) as server:
        sid = start_game(server, [RATIONAL] * 3)
        played_out(server, sid)
        with stream(server, sid) as response:
            assert response.status == 200
            for key, value in events.SSE_HEADERS:
                assert response.getheader(key) == value
            read_frames(response, until=events.EPISODE_DONE)


@needs_lane_a
def test_two_browsers_watch_the_same_game(tmp_path):
    """Fanout: a second subscriber is a second queue over one log, so both see the same session identically."""
    with serving(tmp_path) as server:
        sid = start_game(server, [RATIONAL] * 3)
        played_out(server, sid)
        with stream(server, sid) as first, stream(server, sid) as second:
            assert read_frames(first, until=events.EPISODE_DONE) == read_frames(second,
                                                                                until=events.EPISODE_DONE)


# ----------------------------------------------------------------------------- snapshot vs the stream --
@needs_lane_a
def test_a_reloaded_page_and_a_streamed_one_show_the_same_game(tmp_path):
    """The zero-drift guarantee at the HTTP boundary: the turn rows a client accumulated from the stream are the
    rows ``/state`` hands a page that just reloaded. One payload code path, asserted as an identity."""
    with serving(tmp_path) as server:
        sid = start_game(server, [RATIONAL] * 3)
        snapshot = played_out(server, sid)
        with stream(server, sid) as response:
            frames = read_frames(response, until=events.EPISODE_DONE)

    streamed = [data["turn"] for _, kind, data in frames if kind == events.TURN_APPENDED]
    assert streamed == snapshot["payload"]["turns"]
    assert snapshot["seq"] >= frames[-1][0]
    assert snapshot["occupants"] and set(snapshot["occupants"]) == {"Avery", "Blake", "Casey"}


# ------------------------------------------------------------------------------ playing a seat by hand --
@needs_lane_a
def test_a_person_plays_a_seat_over_http(tmp_path):
    """The act endpoint end to end: the seat blocks, the browser is told what it may legally do, a POST becomes
    the move, and the turn is recorded as the person's."""
    with serving(tmp_path) as server:
        sid = start_game(server, [{"kind": "human", "display_name": "sid"}, RATIONAL, RATIONAL])
        wait_for(lambda: call(server, "GET", f"/api/session/{sid}/state")[1]["phase"] == "awaiting_human",
                 timeout=TIMEOUT, what="the human seat to be asked")
        awaiting = call(server, "GET", f"/api/session/{sid}/state")[1]["awaiting"]
        assert awaiting["seat"] == "Avery" and awaiting["legal"]["can_offer"] is True

        issues = server.manager.provider.spec.space.issues
        deal = {issue.name: issue.options[0] for issue in issues}
        status, body = call(server, "POST", f"/api/session/{sid}/act",
                            {"seat": "Avery", "action": "propose", "deal": deal, "message": "My package.",
                             "note": "opening high"})
        assert status == 200 and body["ok"] is True
        snapshot = played_out(server, sid)

    first = snapshot["payload"]["turns"][0]
    assert first["occupant"] == "human:sid" and first["human_note"] == "opening high"
    assert first["action"]["atype"] == "propose"


@needs_lane_a
def test_an_illegal_move_is_a_400_and_tells_every_watcher_why(tmp_path):
    """A rejection is not private. The person who typed it is not necessarily the only one watching, the seat is
    still blocked, and the form has to stay open with the reason attached — so it answers 400 AND broadcasts."""
    with serving(tmp_path) as server:
        sid = start_game(server, [{"kind": "human", "display_name": "sid"}, RATIONAL, RATIONAL])
        wait_for(lambda: call(server, "GET", f"/api/session/{sid}/state")[1]["phase"] == "awaiting_human",
                 timeout=TIMEOUT, what="the human seat to be asked")

        status, body = call(server, "POST", f"/api/session/{sid}/act",
                            {"seat": "Avery", "action": "accept", "offer_id": "P9"})
        assert status == 400 and "P9" in body["error"]

        state = call(server, "GET", f"/api/session/{sid}/state")[1]
        assert state["phase"] == "awaiting_human", "the seat must still be waiting"
        assert state["payload"]["turns"] == [], "a refused move must never reach the engine"

        with stream(server, sid) as response:
            frames = read_frames(response, until=events.INPUT_REJECTED)
        assert frames[-1][1] == events.INPUT_REJECTED and "P9" in frames[-1][2]["reason"]

        call(server, "POST", f"/api/session/{sid}/stop", {})
        played_out(server, sid)


@needs_lane_a
@pytest.mark.parametrize("key", ["seat", "seat_config"])
def test_a_seat_can_be_reassigned_mid_game_over_http(tmp_path, key):
    """The swap endpoint, and the occupant map a page badges seats from.

    The config arrives under ``seat`` from the lobby's seat editor and under ``seat_config`` from the play
    page's swap dock. They carry the same dataclass, so both are read rather than making one page rename a
    field to match the other."""
    with serving(tmp_path) as server:
        sid = start_game(server, [RATIONAL] * 3)
        played_out(server, sid)
        status, body = call(server, "POST", f"/api/session/{sid}/swap",
                            {"seat_idx": 1, key: {"kind": "oracle", "policy": "bayes-rational"}})
        assert status == 200
        assert body["occupants"]["Blake"] == SeatConfig(kind="oracle",
                                                        policy="bayes-rational").occupant_label()


@needs_lane_a
def test_the_snapshots_lobby_carries_what_the_swap_dock_offers(tmp_path):
    """The play page's swap dock reuses the lobby's seat editor, so it needs the same choices the lobby has —
    from the snapshot it already fetched, not a second round trip to ``/api/lobby``."""
    with serving(tmp_path) as server:
        sid = start_game(server, [RATIONAL] * 3)
        snapshot = played_out(server, sid)
    lobby = snapshot["lobby"]
    assert snapshot["sid"] == sid == lobby["sid"]
    assert [s["kind"] for s in lobby["seats"]] == ["rational"] * 3
    assert "bayes-rational" in lobby["policies"]
    assert {m["model_id"] for m in lobby["models"]} == {"stub-free", "stub-paid", "stub-gone"}


@needs_lane_a
def test_stop_ends_the_session_and_reset_returns_to_the_lobby(tmp_path):
    """Two clicks that have to work at any moment: a stop mid-game, and a reset that clears the way for the next
    lineup without restarting the server."""
    with serving(tmp_path) as server:
        sid = start_game(server, [{"kind": "human", "display_name": "sid"}, RATIONAL, RATIONAL])
        wait_for(lambda: call(server, "GET", f"/api/session/{sid}/state")[1]["phase"] == "awaiting_human",
                 timeout=TIMEOUT, what="the human seat to be asked")
        status, body = call(server, "POST", f"/api/session/{sid}/stop", {})
        assert status == 200
        played_out(server, sid)

        status, lobby = call(server, "POST", "/api/reset", {})
        assert status == 200 and lobby["running"] is False and lobby["sid"] is None
        # and the server is ready to play again, with the lineup it was left with
        assert call(server, "POST", "/api/start", {})[0] == 200


# ------------------------------------------------------------------------------------------ the pages --
def test_the_lobby_page_is_served_at_the_root(tmp_path):
    """The one page a person opens by hand. Skipped until lane C's renderer lands."""
    with serving(tmp_path) as server:
        status, body = call(server, "GET", "/")
        if status == 500 and "NotImplementedError" in str(body):
            pytest.skip("lane C's render_lobby_html has not landed yet")
        assert status == 200 and body.lstrip().startswith("<!")


@needs_lane_a
def test_the_live_page_needs_a_running_game(tmp_path):
    """``/play`` renders from a snapshot, so with no session there is nothing to render — and saying so is more
    useful than an empty page that silently never updates."""
    with serving(tmp_path) as server:
        assert call(server, "GET", "/play")[0] == 404
        sid = start_game(server, [RATIONAL] * 3)
        played_out(server, sid)
        status, body = call(server, "GET", "/play")
        if status == 500 and "NotImplementedError" in str(body):
            pytest.skip("lane D's render_live_html has not landed yet")
        assert status == 200 and body.lstrip().startswith("<!")
