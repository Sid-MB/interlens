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
# [rational_agents: viz-ux] 2026-08-03
# [rational_agents: viz-sidebar] 2026-08-03

"""HTML assembly: a payload in, one self-contained interactive page out.

Everything that can be rendered without JavaScript is rendered here in Python — the summary strip, the game side
panel, every score sheet, the numeric table view of the chart, the pairing banner, the comparison score table and
its verdict, and the whole run index including its rows. The browser script only draws the two charts and the
transcript cards. That split is deliberate: the numbers are the deliverable, so they must be in the document even
if the script never runs, and it makes the tests able to assert on real structure and real values without a
browser.

Pages are opened over ``file://``, so nothing is fetched: the stylesheet and script are inlined, and the payload
travels in a ``<script type="application/json">`` tag (data in a data position — never interpolated into
executable code, and closing-tag sequences are escaped).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from markdown_it import MarkdownIt

from .assets import CSS, JS, JS_COMPARE, JS_EPISODE, JS_INDEX_PAGE
from .ballots import ballot_table
from .census import census_strip
from .chrome import (_e, _num, distance_to_nbs, help_overlay, nav_group, quick_stats, slim_payload,
                     summary_strip, topbar)
from .hazards import budget_badge, budget_note, vintage_badge, vintage_banner, vintage_pairing

__all__ = ["nav_group", "render_compare_html", "render_episode_html", "render_index_html"]


_MARKDOWN = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})


def _threshold(v) -> str:
    """Format a threshold without decimal noise when its numeric value is integral."""
    if isinstance(v, (int, float)) and not isinstance(v, bool) and float(v).is_integer():
        return str(int(v))
    return _num(v, 1)


def _render_readme(markdown: str) -> str:
    """Render an optional run README without allowing embedded HTML to enter the generated page."""
    return _MARKDOWN.render(markdown) if markdown.strip() else ""


def _payload_script(payload: dict) -> str:
    """The payload as an inert JSON script tag, in its wire form (see :func:`~.chrome.slim_payload`). ``</`` is
    escaped so no string inside the data can end the tag."""
    data = json.dumps(slim_payload(payload), ensure_ascii=False, separators=(",", ":"),
                      default=str).replace("</", "<\\/")
    return f'<script type="application/json" id="viz-payload">{data}</script>'


def _document(title: str, chrome: str, body: str, payload: dict | None, script: str) -> str:
    """The complete HTML document: inline CSS, the top bar, the body, the help overlay, the inert payload, then
    the shared + page-specific JS. ``payload`` is ``None`` on the index, which carries no episode data."""
    data = _payload_script(payload) if payload is not None else ""
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{_e(title)}</title><style>{CSS}</style></head><body>"
            "<a class='skip' href='#content'>Skip to content</a>"
            f"{chrome}<main id='content'>{body}</main>{help_overlay()}"
            f"{data}<script>{script}</script></body></html>")


# ------------------------------------------------------------------------------------ shared parts --
def _meta_pills(payload: dict) -> str:
    ep = payload.get("episode") or {}
    pills = [f"<span class='pill'>model <b>{_e(ep.get('model'))}</b></span>",
             f"<span class='pill'>arm <b>{_e(ep.get('arm'))}</b></span>",
             f"<span class='pill'>cell <b>{_e(ep.get('cell'))}</b></span>",
             f"<span class='pill'>seed <b>{_e(ep.get('seed'))}</b></span>",
             f"<span class='pill'>level <b>{_e(ep.get('level'))}</b></span>",
             f"<span class='pill'>status <b>{_e(ep.get('status'))}</b></span>",
             f"<span class='pill'>instance <b>{_e(ep.get('instance_id'))}</b></span>",
             f"<span class='pill'>{_e(ep.get('tokens_out'))} tok out</span>"]
    return f"<div class='pills'>{''.join(pills)}</div>"


def _preferences_are_public(payload: dict) -> bool:
    """Whether the protocol revealed every party's preferences to every seat.

    Stored negotiation records call this mode ``full``; ``public`` and ``shared`` are accepted as equivalent
    spellings so the visual distinction follows the meaning rather than one generator's serialization detail.
    Unknown or absent values stay quiet, like the default private mode, rather than making an unsupported claim.
    """
    info = str((((payload.get("game") or {}).get("protocol") or {}).get("info") or "")).strip().lower()
    return info in {"full", "public", "shared"}


def preference_visibility(payload: dict) -> str:
    """The compact index label for a negotiation's information condition.

    Private information is the protocol default, including older records that did not serialize ``info``;
    the exceptional public/shared spellings are normalized to the experiment-facing label ``FULL``.
    """
    return "FULL" if _preferences_are_public(payload) else "PRIVATE"


def _preference_visibility_quick(payload: dict) -> str:
    """The sticky quick-read label for the exceptional public-preference condition; private emits nothing."""
    if not _preferences_are_public(payload):
        return ""
    return ("<span class='prefvisquick'><span class='k'>preference visibility</span> "
            "<b>public</b></span>")


def _preference_visibility_banner(payload: dict) -> str:
    """A prominent top-of-page explanation when full preferences were revealed to the table."""
    if not _preferences_are_public(payload):
        return ""
    return ("<div class='prefvis' role='note'><span class='k'>Preference visibility</span>"
            "<strong>PUBLIC</strong><span>Every party's full score sheet and threshold were revealed to all "
            "participants in this episode.</span></div>")


def _source_links(payload: dict) -> str:
    """Links to the exact records this page was built from — the reproduction trail, absolute paths as ``file://``
    URIs so they open from the generated HTML wherever it is copied to."""
    paths = payload.get("paths") or {}
    if not paths:
        return ""
    items = [f"<a href='{_e(Path(v).as_uri())}'>{_e(k)}</a>" for k, v in paths.items() if v]
    return f"<div class='sub'>source records: {' · '.join(items)}</div>"


def _contamination_banner(payload: dict, label: str = "") -> str:
    """A loud banner when any of this episode's turns were FABRICATED by the engine rather than generated.

    This is the one thing on the page that must not be subtle. The substituted placeholder parses into a
    well-formed no-op action, so a fabricated episode otherwise renders as a perfectly clean transcript of a party
    that chose to stay quiet — which is exactly how a campaign cell reached 100% fabricated turns while reporting
    ``status="done"`` and ``parse_ok=True`` throughout."""
    gen = payload.get("generation") or {}
    n = gen.get("fabricated") or 0
    if not n:
        return ""
    who = f"{_e(label)}: " if label else ""
    return (f"<div class='warn danger'><b>{who}{n} of {_e(gen.get('n_turns'))} turns "
            f"({_num(100 * (gen.get('fraction') or 0), 1)}%) were NOT GENERATED.</b> The engine substituted a "
            "placeholder after generation failed, so those turns are not model behaviour — they parse as a "
            "well-formed no-op, which is why this is called out here rather than left to the reader to notice. "
            f"Detected by {_e(', '.join(gen.get('detected_by') or []))}. Exclude these turns from any behavioural "
            "measurement of this episode.</div>")


def _vintage_banners(*sides: dict) -> str:
    """Each DISTINCT vintage hazard among these episodes, once.

    Two episodes of the same spoiled run share one hazard file and must not produce two identical banners; two
    episodes of different spoiled runs must produce two, because on a comparison page WHICH side is spoiled is
    the finding rather than a detail."""
    seen: set = set()
    out = []
    for side in sides:
        vintage = (side or {}).get("vintage")
        if vintage and vintage.get("path") not in seen:
            seen.add(vintage.get("path"))
            out.append(vintage_banner(vintage))
    return "".join(out)


def _reference_table(game: dict) -> str:
    """The chart's TABLE VIEW: every reference point with its coordinates and its numbers. Required relief for the
    solution-point colour, and the answer to "what exactly is that star" without hovering."""
    d = game["deals"]
    rows = []

    def row(label: str, note: str, index: int):
        s = d["s"][index]
        rows.append(f"<tr><td><b>{_e(label)}</b> <span class='muted'>{_e(note)}</span></td>"
                    f"<td>{index}</td><td>{_num(d['wx'][index])}</td><td>{_num(d['wy'][index])}</td>"
                    f"<td>{_num(sum(s), 1)}</td><td>{_num(min(s), 1)}</td>"
                    f"<td>{'yes' if d['pareto'][index] else 'no'}</td>"
                    f"<td>{'yes' if d['feasible'][index] else 'no'}</td></tr>")

    for name, pt in (game.get("solutions") or {}).items():
        note = name.replace("_", " ") + ("" if pt.get("scale_invariant") else " · not scale-invariant")
        row(pt.get("label", name), note, int(pt["index"]))
    for pb in game.get("party_best") or []:
        row(f"best for {pb['agent']}", f"party {pb['party']} · surplus {pb['surplus']}", int(pb["index"]))
    return ("<div class='tablewrap'><table><thead><tr><th>reference point</th><th>deal #</th>"
            "<th>joint welfare</th><th>min surplus</th><th>USW</th><th>ESW</th><th>Pareto</th>"
            "<th>can close</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>")


def _legend(mode: str) -> str:
    """The chart legend. Present whenever more than one identity is on screen, and every entry names its shape as
    well as its colour so identity is never carried by colour alone. It sits above the plot rather than inside it,
    so it cannot occlude a mark at any zoom level."""
    left, right = ("the model's play", "oracle recommendation") if mode == "episode" else ("left episode", "right episode")
    return ("<div class='legend'>"
            f"<span><i class='swatch' style='background:var(--s1)'></i>{_e(left)} (numbered, in order)</span>"
            f"<span><i class='swatch sq' style='background:var(--s1)'></i>the deal that closed</span>"
            f"<span><i class='swatch' style='background:var(--s2)'></i>{_e(right)}</span>"
            "<span><i class='swatch' style='background:var(--s3)'></i>NBS / KS / EGAL solution (star)</span>"
            "<span><i class='swatch tri' style='background:var(--reference-alt)'></i>UTIL / MNW solution (triangle)</span>"
            "<span><i class='swatch di' style='background:var(--s3)'></i>a party's individually-best deal</span>"
            "<span><i class='swatch' style='background:var(--ink-2)'></i>Pareto-frontier deal (acceptable to all)</span>"
            "<span><i class='swatch xmark'></i>efficient but below a party's threshold &mdash; cannot close</span>"
            "<span><i class='swatch' style='background:var(--muted)'></i>dominated deal</span></div>")


def _game_cards(payload: dict) -> str:
    """The game panel's cards: who is at the table, the thresholds, the protocol, the size of the bargaining
    problem, the solution concepts, and every party's private score sheet — the whole normative context of the
    episode. Rendered without its container so both the comparison page's plain ``<aside>`` and the episode
    page's tabbed sidebar can carry the same content."""
    game = payload.get("game")
    seats = payload.get("seats") or []
    if not game:
        return ("<section class='card'><h2>Game</h2><div class='gap'>No instance record was supplied, so "
                "the game setup, thresholds, and frontier are unavailable; the transcript above is complete.</div>"
                "</section>")
    counts, protocol = game.get("counts") or {}, game.get("protocol") or {}
    public_preferences = _preferences_are_public(payload)
    ideal = game.get("ideal_surplus") or []
    seat_rows = "".join(
        f"<tr><td>{_e(s.get('name'))} <span class='badge {_e(s.get('kind'))}'>{_e(s.get('kind'))}</span></td>"
        f"<td class='muted'>{_e((game.get('parties') or [])[i] if i < len(game.get('parties') or []) else '')}</td>"
        f"<td>{_threshold((game.get('thresholds') or [None] * (i + 1))[i])}</td>"
        f"<td>{_num(ideal[i] if i < len(ideal) else None, 1)}</td>"
        f"<td>{_num(((payload.get('outcome') or {}).get('per_party_surplus') or [None] * (i + 1))[i], 1)}</td></tr>"
        for i, s in enumerate(seats))
    issues = "".join(f"<tr><td>{_e(iss['name'])}</td><td class='muted'>{_e(', '.join(iss['options']))}</td></tr>"
                     for iss in game.get("issues") or [])
    veto = ", ".join(str((game.get("parties") or [])[v] if v < len(game.get("parties") or []) else v)
                     for v in protocol.get("veto_seats") or []) or "none"
    sheets = "".join(
        f"<details><summary>{'Score sheet' if public_preferences else 'Private score sheet'} — "
        f"{_e(sh['agent'])} (threshold {_threshold(sh['threshold'])})</summary><div class='body'><table>"
        "<thead><tr><th>issue</th>"
        + "".join(f"<th>{_e(o)}</th>" for o in (game['issues'][0]['options'] if game.get('issues') else []))
        + "</tr></thead><tbody>"
        + "".join(f"<tr><td>{_e(game['issues'][j]['name'])}</td>"
                  + "".join(f"<td>{_num(v, 1)}</td>" for v in row) + "</tr>"
                  for j, row in enumerate(sh["values"]))
        + "</tbody></table></div></details>"
        for sh in game.get("sheets") or [])
    views = payload.get("views") or {}
    kind_src = payload.get("seat_kind_source") or {}
    return f"""<section class='card'><h2>Who is at the table</h2>
 <table><thead><tr><th>seat</th><th>party</th><th>threshold τ</th><th>ideal surplus</th><th>realized</th></tr></thead>
 <tbody>{seat_rows}</tbody></table>
 <div class='sub muted'>Seat occupant kinds: {_e(kind_src.get('detail'))}</div></section>
<section class='card'><h2>Protocol</h2><div class='pills'>
 <span class='pill'>rounds <b>{_e(protocol.get('rounds'))}</b></span>
 <span class='pill'>information <b>{_e(protocol.get('info'))}</b></span>
 <span class='pill'>cheap talk <b>{'on' if protocol.get('chat') else 'off'}</b></span>
 <span class='pill'>veto <b>{_e(veto)}</b></span>
 <span class='pill'>min accept <b>{_e(protocol.get('min_accept') if protocol.get('min_accept') is not None else 'unanimity')}</b></span>
 <span class='pill'>discount δ <b>{_num(protocol.get('discount'))}</b></span>
 <span class='pill'>breakdown risk <b>{_num(protocol.get('breakdown_risk'))}</b></span>
 </div>
 <table><thead><tr><th>issue</th><th>options</th></tr></thead><tbody>{issues}</tbody></table></section>
<section class='card'><h2>Size of the problem</h2>
 <table><tbody>
 <tr><td>deals in the space</td><td>{_e(counts.get('deal_space_size') or game['deals']['n'])}</td></tr>
 <tr><td>on the Pareto frontier</td><td>{_e(counts.get('pareto_count'))}</td></tr>
 <tr><td>acceptable to everyone (IR)</td><td>{_e(counts.get('ir_count'))}</td></tr>
 <tr><td>acceptable AND efficient</td><td>{_e(counts.get('ir_pareto_count'))}</td></tr>
 <tr><td>acceptable but wasteful</td><td>{_num(counts.get('dominated_acceptable_fraction'))}</td></tr>
 <tr><td>score-sheet overlap (IoU)</td><td>{_num(counts.get('pairwise_iou'))}</td></tr>
 </tbody></table>
 <div class='sub muted'>Solution concepts were {_e(game.get('solutions_source'))} for this page.</div></section>
<section class='card'><h2>{'Public score sheets' if public_preferences else 'Private score sheets'}</h2>
 <div class='sub'>{'Full preferences and thresholds were revealed to every seat before play.' if public_preferences else 'What each party is secretly optimizing. Never shown to the other seats.'}</div>{sheets}</section>
<section class='card'><h2>Prompt provenance</h2>
 <div class='sub'>{_e(views.get('stored'))} of {_e(views.get('n_turns'))} turns carry the exact view recorded at
 generation time; {_e(views.get('reconstructed'))} were re-derived by replay through today's prompt code and are
 labelled as reconstructed wherever they appear.
 {(f"Of those, {views.get('reconstructed_pre_retry')} were retry turns, whose reconstruction is the FIRST "
   "attempt's prompt — the repair instruction the model saw on the retry is not recoverable from the record."
   ) if views.get('reconstructed_pre_retry') else ''}</div></section>"""


def _side_panel(payload: dict) -> str:
    """The plain (untabbed) game side panel, as the comparison page carries it."""
    return f"<aside>{_game_cards(payload)}</aside>"


# ------------------------------------------------------------------------------- the tabbed sidebar --
#: The sidebar's tabs, in order. The first is the default. ``game`` is the panel the page always had; ``chat``,
#: ``frontier``, and ``issues`` are scroll-synced views of the turn currently in the reader's viewport; ``info``
#: is the standing reading guide linked from terms and measurements throughout the episode.
SIDEBAR_TABS = [("game", "Game info"), ("chat", "Conversation"), ("frontier", "Frontier"),
                ("issues", "Issues"), ("info", "Info")]


def _deal_summary(named: dict | None) -> str:
    """A named deal as the compact ``Issue=Option, Issue=Option`` line the page uses everywhere."""
    if not isinstance(named, dict) or not named:
        return ""
    return ", ".join(f"{k}={v}" for k, v in named.items())


def _action_chip(turn: dict) -> str:
    """The formal action of one turn as a compact chip — exactly what the other seats saw published beside the
    free text, and nothing else. A talk-only turn published no formal action, so it gets no chip.

    The engine republishes each validated move as canonical JSON in the public log (``ScorableNegotiation._publish``),
    so this is a rendering of public record, not an inference: ``PROPOSE P3`` names the id the proposal was
    registered under and the package it put on the table, ``ACCEPT P2`` / ``REJECT P2`` name the offer voted on."""
    action = turn.get("action") or {}
    atype = (action.get("atype") or "").lower()
    ref = turn.get("offer_id") or action.get("offer")
    if atype == "propose":
        deal = _deal_summary(action.get("deal_named"))
        head = f"PROPOSE {ref}" if ref else "PROPOSE"
        return (f"<span class='actchip a-propose'><b>{_e(head)}</b>"
                f"{(': ' + _e(deal)) if deal else ''}</span>")
    if atype in ("accept", "reject", "vote"):
        return (f"<span class='actchip a-{_e(atype)}'><b>{_e(atype.upper())}"
                f"{(' ' + _e(ref)) if ref else ''}</b></span>")
    if atype == "walk":
        return "<span class='actchip a-walk'><b>WALK</b></span>"
    return ""


def _chat_bubbles(payload: dict) -> str:
    """The public conversation as chat bubbles, one per PUBLISHED turn, in order.

    This is the transcript as a *seat* experienced it, so it carries only what the engine published to the other
    parties: the free-text message and the formal action. The scratchpad, the reasoning trace, the prompt, and the
    oracle verdicts are all private or post-hoc and are deliberately absent — a conversation view that leaked any
    of them would misrepresent what the other seats could possibly have been reacting to. Turns that were first
    attempts at a slot the seat later retried are absent too, because the engine never published them.

    Every bubble carries its speaker's seat, so the browser can re-anchor the whole list to whichever seat is in
    view (that seat's own bubbles move to the right) without re-rendering anything."""
    seats = {s.get("name"): s for s in payload.get("seats") or []}
    rows = [t for t in payload.get("turns") or [] if t.get("published", True)]
    if not rows:
        return "<div class='gap'>This episode published no turns.</div>"
    bubbles = []
    for t in rows:
        seat = t.get("seat")
        party = (seats.get(seat) or {}).get("party")
        message = (t.get("action") or {}).get("message")
        chip = _action_chip(t)
        body = [f"<div class='who'><span class='pidx'>{_e(party)}</span> {_e(seat)}"
                f"<span class='at'>turn {_e(t.get('idx'))} · round {_e(t.get('round'))}</span></div>"]
        if message:
            body.append(f"<div class='body'>{_e(message)}</div>")
        if chip:
            body.append(f"<div class='chipline'>{chip}</div>")
        if t.get("gen_failed"):
            body.append("<div class='fabtag'>NOT GENERATED — engine placeholder</div>")
        elif t.get("silent"):
            # The conversation view is what the other seats saw, and what they saw here was a party that said
            # nothing. Tagging it keeps the bubble honest without inventing content for it.
            body.append("<div class='fabtag'>SAID NOTHING — the seat published no answer this turn</div>")
        bubbles.append(
            f"<div class='bubble{' fab' if t.get('gen_failed') else (' silent' if t.get('silent') else '')}' "
            f"id='bub-{_e(t.get('idx'))}' "
            f"data-turnidx='{_e(t.get('idx'))}' data-seat='{_e(seat)}' data-party='{_e(party)}'>"
            f"{''.join(body)}</div>")
    return f"<div class='chatlog' id='chatlog'>{''.join(bubbles)}</div>"


def _issue_bars_svg(game: dict, party: int) -> str:
    """One agent's private valuation of the issues being decided, as one vertical bar per issue.

    The y axis is that agent's own score scale; each option's score is a tick on its issue's bar (labelled on
    hover only — a tick per option per issue, labelled, is unreadable at sidebar width). The horizontal line is
    ``threshold / n_issues``: the average per-issue score this agent needs to clear its threshold, which is the
    reference that makes a bar's ticks mean something. The marker line showing which option the deal on the table
    picks is added by the browser, because it changes with the turn in view; every tick carries its y coordinate
    so the marker is placed from this scale rather than from a second copy of it."""
    issues = game.get("issues") or []
    sheets = game.get("sheets") or []
    if not issues or party >= len(sheets):
        return "<div class='gap'>This instance carries no per-agent score sheet, so there is nothing to plot.</div>"
    sheet = sheets[party]
    values = sheet.get("values") or []
    n = len(issues)
    tau = float(sheet.get("threshold") or 0.0)
    per_issue = tau / n if n else 0.0
    flat = [float(v) for row in values for v in row] or [0.0]
    lo, hi = min(flat + [per_issue, 0.0]), max(flat + [per_issue])
    pad = max(1e-6, (hi - lo) * 0.08)
    lo, hi = lo - pad, hi + pad
    W, H = 340, 224
    m = {"l": 38, "r": 14, "t": 14, "b": 42}
    span = (W - m["l"] - m["r"]) / n

    def y(v: float) -> float:
        return H - m["b"] - ((v - lo) / (hi - lo)) * (H - m["t"] - m["b"])

    parts = []
    for i in range(5):                                  # a recessive value grid, labelled on the left
        gv = lo + (hi - lo) * i / 4
        parts.append(f"<line class='gridline' x1='{m['l']}' x2='{W - m['r']}' y1='{y(gv):.1f}' y2='{y(gv):.1f}'/>")
        parts.append(f"<text x='{m['l'] - 6}' y='{y(gv) + 4:.1f}' text-anchor='end'>{gv:.0f}</text>")
    parts.append(f"<line class='axisline' x1='{m['l']}' x2='{W - m['r']}' "
                 f"y1='{H - m['b']}' y2='{H - m['b']}'/>")
    for j, issue in enumerate(issues):
        cx = m["l"] + (j + 0.5) * span
        bw = min(26.0, span * 0.42)
        x0, x1 = cx - bw / 2, cx + bw / 2
        row = [float(v) for v in (values[j] if j < len(values) else [])]
        ticks = "".join(
            f"<line class='opt' data-opt='{o}' data-y='{y(v):.2f}' x1='{x0 - 4:.1f}' x2='{x1 + 4:.1f}' "
            f"y1='{y(v):.1f}' y2='{y(v):.1f}'><title>{_e(issue['options'][o] if o < len(issue['options']) else o)}"
            f" — {v:g} for {_e(sheet.get('agent'))}</title></line>"
            for o, v in enumerate(row))
        label = issue["name"] if len(issue["name"]) <= 9 else issue["name"][:8] + "…"
        parts.append(
            f"<g class='issuebar' data-issue='{j}' data-name='{_e(issue['name'])}' "
            f"data-x0='{x0:.1f}' data-x1='{x1:.1f}'>"
            f"<rect class='track' x='{x0:.1f}' y='{m['t']}' width='{bw:.1f}' "
            f"height='{H - m['b'] - m['t']:.1f}' rx='4'/>{ticks}"
            f"<text class='issuelab' x='{cx:.1f}' y='{H - m['b'] + 15}' text-anchor='middle'>{_e(label)}"
            f"<title>{_e(issue['name'])}: {_e(', '.join(issue['options']))}</title></text></g>")
    parts.append(f"<line class='taul' data-threshold='{per_issue:.4f}' x1='{m['l']}' x2='{W - m['r']}' "
                 f"y1='{y(per_issue):.1f}' y2='{y(per_issue):.1f}'/>")
    parts.append(f"<text class='taulab' x='{W - m['r']}' y='{y(per_issue) - 4:.1f}' text-anchor='end'>"
                 f"τ/{n} = {per_issue:.1f}</text>")
    return (f"<div class='chartwrap'><svg viewBox='0 0 {W} {H}' role='img' class='issuesvg' "
            f"aria-label='Per-issue option scores for {_e(sheet.get('agent'))}, on that agent's own score scale. "
            f"Each tick is one option; the dashed line is the average per-issue score needed to clear the "
            f"threshold ({per_issue:.1f}).'>{''.join(parts)}</svg></div>")


def _issue_pane(payload: dict) -> str:
    """The per-agent issue view: one block per seat (the one for the seat in view is shown), each with its bars,
    a value table, and the running numbers the browser fills for the deal on the table."""
    game = payload.get("game")
    if not game:
        return ("<div class='gap'>No instance record was supplied, so the per-agent score sheets and thresholds "
                "are unavailable.</div>")
    seats = payload.get("seats") or []
    sheets = game.get("sheets") or []
    private = str((game.get("protocol") or {}).get("info") or "").lower().startswith("priv")
    note = ("<div class='warn'><b>You are reading this post hoc and omniscient.</b> This episode was played under "
            "private information: no seat could see another seat's sheet or threshold while playing. The bars "
            "below are the analyst's view, never a player's.</div>") if private else ""
    picker = "".join(f"<option value='{i}'>{_e(s.get('name'))}</option>" for i, s in enumerate(seats))
    blocks = []
    for i, s in enumerate(seats):
        sheet = sheets[i] if i < len(sheets) else {}
        tau = sheet.get("threshold")
        blocks.append(
            f"<div class='issueseat' data-party='{i}' data-seat='{_e(s.get('name'))}'{'' if i == 0 else ' hidden'}>"
            f"<div class='hd'>{_e(s.get('name'))} <span class='badge {_e(s.get('kind'))}'>{_e(s.get('kind'))}</span>"
            f"<span class='muted'>party {i} · {_e(sheet.get('agent'))} · threshold τ {_threshold(tau)}</span></div>"
            f"{_issue_bars_svg(game, i)}"
            "<div class='legend'>"
            "<span><i class='swatch tick'></i>an option's score for this agent (hover for its name)</span>"
            "<span><i class='swatch line'></i>the option the deal on the table picks</span>"
            "<span><i class='swatch dash'></i>average per-issue score needed (τ/issues)</span></div>"
            f"<div class='issuenums' id='issuenums-{i}' data-party='{i}'>"
            "<span class='sub muted'>Scroll the transcript, or pick a turn, to place a deal on these bars.</span>"
            "</div></div>")
    return (f"{note}<div class='bar'><label class='sub'>seat "
            f"<select id='issue-seat-pick'><option value='auto'>follow the transcript</option>{picker}"
            "</select></label><span class='sub muted' id='issue-seat-note'></span></div>"
            f"<div id='issue-seats'>{''.join(blocks)}</div>")


def _info_pane(payload: dict) -> str:
    """The visualizer's compact reading guide, including the target linked from every oracle measurement.

    Formulae use semantic HTML rather than a network-loaded maths library so exported pages keep working as
    self-contained files. Each formula is immediately restated in words for readers and assistive technology.
    """
    private = not _preferences_are_public(payload)
    information_note = (
        "<div class='warn'><b>PRIVATE episode: this oracle is omniscient.</b> The standard saved "
        "<code>bestresponse</code> annotation reads every party's hidden score sheet and threshold. It does not "
        "infer them from the public conversation. Its recommendation and improvement gap are hindsight "
        "diagnostics, not actions or regret from a policy the acting seat could implement.</div>"
        if private else
        "<div class='sub'><b>FULL episode:</b> every score sheet and threshold used by the oracle was also "
        "revealed to the participants.</div>"
    )
    return f"""<div class='infointro'>A reading guide for the measurements and counterfactuals on this page.</div>
<section class='infosection' id='info-oracle'>
 <h2>Oracle values and the improvement gap</h2>
 {information_note}
 <p>The oracle is a <b>post-hoc counterfactual evaluator</b>, not another participant. At turn <var>t</var>, it
 enumerates legal deals, reads the full utility and threshold table, computes continuation values by
 <b>backward induction</b> over the remaining turns, and selects the highest-valued action. A proposed deal closes only when
 every responder's surplus clears that responder's computed continuation value.</p>
 <div class='formula' role='math' aria-label='a star at turn t equals arg max over actions a of V sub t of a'>
  <var>a<sup>*</sup><sub>t</sub> = arg max<sub>a</sub> V<sub>t</sub>(a)</var></div>
 <p><b>Oracle's value of the model's move</b>, <var>V<sub>t</sub>(a<sub>t</sub>)</var>, appears with the model's
 action. <b>Oracle's value of its best move</b>, <var>V<sub>t</sub>(a<sup>*</sup><sub>t</sub>)</var>, appears with
 the counterfactual action. Their difference is the oracle's value gap:</p>
 <div class='formula' role='math' aria-label='R sub t equals V sub t of a star sub t minus V sub t of a sub t,
 and is greater than or equal to zero'>
  <var>R<sub>t</sub> = V<sub>t</sub>(a<sup>*</sup><sub>t</sub>) − V<sub>t</sub>(a<sub>t</sub>) ≥ 0</var></div>
 <p>This is often called <i>regret</i>. A value of 4.18 means the oracle estimates that its best legal move was
 worth 4.18 more than the model's move. Values are in that oracle's own units: compare moves within the same
 turn and oracle, not raw values across different seats or oracle types. The result is only as good as the
 oracle's candidate set, evaluator, and information reconstruction; it is not proof of the uniquely correct move.</p>
</section>
<section class='infosection' id='info-utility'>
 <h2>Utility, threshold, surplus, and <var>z</var></h2>
 <p><var>u<sub>i</sub>(d)</var> is party <var>i</var>'s score for deal <var>d</var>; <var>τ<sub>i</sub></var> is
 its walk-away threshold. Raw surplus is <var>u<sub>i</sub>(d) − τ<sub>i</sub></var>. Normalized surplus
 <var>z<sub>i</sub></var> expresses that gain relative to the party's own available range, making differently
 scaled score sheets more comparable. “Below τ” means a deal is not individually rational for that party.</p>
</section>
<section class='infosection' id='info-frontier'>
 <h2>Frontier and reference points</h2>
 <p>Each dot is a legal deal. Up and right is better; the Pareto frontier contains deals where no party can gain
 without another losing. Numbered circles are the model's proposals, orange circles are oracle proposals, and
 the square is the agreement. NBS, KS, UTIL, EGAL, and MNW are normative reference rules, not additional plays.
 Hover or focus any point for its deal, scores, party ranking, and the reference rule's definition.</p>
</section>
<section class='infosection' id='info-sidebar'>
 <h2>Conversation and issue views</h2>
 <p><b>Conversation</b> contains only published messages and formal moves. It excludes private scratchpads,
 prompts, failed attempts that were retried, and post-hoc oracle verdicts. <b>Issues</b> is an analyst's view of
 a seat's score sheet; in a private-information game, other seats could not see it while negotiating. Both views
 follow the turn currently in the transcript.</p>
</section>
<section class='infosection' id='info-provenance'>
 <h2>Provenance and generated failures</h2>
 <p>The annotation label identifies which saved oracle pass supplied the counterfactuals. A “NOT GENERATED” turn
 is an engine placeholder after generation failed, not an intentional model move. Expand a turn's audit panels
 to distinguish the published action, private reasoning, reconstructed prompt view, and raw stored text.</p>
</section>"""


def _sidebar(payload: dict) -> str:
    """The episode page's right-hand sidebar: five tabs over one sticky column, three of them scroll-synced.

    ``Game info`` is the panel the page always carried. ``Conversation`` is the public chat as the seat in view
    experienced it. ``Frontier`` is the deal-space chart restricted to what had been proposed by the turn in view.
    ``Issues`` is that seat's private valuation of each issue with the deal on the table marked on it. Everything
    but the two charts and the moving markers renders here, server-side, so the sidebar still reads with scripting
    off — it simply stops following the scroll."""
    tabs = "".join(
        f"<button class='tab' role='tab' id='tab-{k}' data-tab='{k}' aria-controls='pane-{k}' "
        f"aria-selected='{'true' if i == 0 else 'false'}'>{_e(label)}</button>"
        for i, (k, label) in enumerate(SIDEBAR_TABS))
    game = payload.get("game")
    frontier = ("<div class='sub'>Every deal proposed up to the turn in view, numbered in order, against the same "
                "frontier as the main chart. The deal standing on the table is squared; proposals still to come "
                "are ghosted, so the sidebar never shows a reader the future of the transcript they are reading."
                "</div><div id='mini-chart'></div><div class='sub muted' id='mini-note'></div>"
                if game else "<div class='gap'>No instance record was supplied, so there is no deal space to "
                             "draw.</div>")
    panes = {
        "game": _game_cards(payload),
        "chat": ("<div class='sub'>The public record only: each seat's free text and the formal move it published. "
                 "Scratchpads, prompts, and oracle verdicts are private or post-hoc and are not here. The seat in "
                 "view speaks on the right.</div>" + _chat_bubbles(payload)),
        "frontier": frontier,
        "issues": _issue_pane(payload),
        "info": _info_pane(payload),
    }
    bodies = "".join(
        f"<section class='pane' id='pane-{k}' role='tabpanel' aria-labelledby='tab-{k}'"
        f"{'' if i == 0 else ' hidden'}>{panes[k]}</section>"
        for i, (k, _label) in enumerate(SIDEBAR_TABS))
    return (f"<aside class='sidebar' id='sidebar'><div class='tabs' role='tablist' "
            f"aria-label='episode sidebar'>{tabs}</div>"
            f"<div class='sub muted syncline' id='sync-note'>following the transcript</div>{bodies}</aside>")


def _system_prompt_audit(payload: dict) -> str:
    """One expandable panel per DISTINCT system prompt in the episode, with the seats that received it.

    A run's seats normally share one system prompt template differing only in the private sheet, so de-duplicating
    turns an unreadable 24-copy dump into a handful of panels — which is what makes "audit exactly what the models
    saw" a thing a person can actually do. Only stored/reconstructed views contribute; the provenance of each is
    carried on its panel."""
    groups: dict[tuple, dict] = {}
    for t in payload.get("turns") or []:
        view = t.get("view") or []
        system = next((m.get("content") for m in view if m.get("role") == "system"), None)
        if system is None:
            continue
        g = groups.setdefault((system, t.get("view_source")),
                              {"seats": [], "source": t.get("view_source"), "content": system, "n": 0})
        g["n"] += 1
        if t.get("seat") not in g["seats"]:
            g["seats"].append(t.get("seat"))
    if not groups:
        return ("<section class='card'><h2>System prompts</h2><div class='gap'>This episode stores no per-turn "
                "views and none could be reconstructed by replay, so the literal system prompts are unavailable. "
                "The game setup and each seat's private sheet are in the side panel — they are the CONTENT the "
                "prompt was built from, not the prompt text itself.</div></section>")
    panels = "".join(
        f"<details><summary>System prompt for {_e(', '.join(g['seats']))} — {g['n']} turn(s), "
        f"{_e(g['source'])}</summary><div class='body'><pre>{_e(g['content'])}</pre></div></details>"
        for g in groups.values())
    return (f"<section class='card'><h2>System prompts ({len(groups)} distinct)</h2>"
            "<div class='sub'>Exactly what each seat was conditioned on, de-duplicated. Per-turn user prompts are "
            "on each turn card below.</div>" + panels + "</section>")


# ----------------------------------------------------------------------------------- episode page --
def render_episode_html(payload: dict) -> str:
    """One self-contained interactive page for one episode.

    Sections, in order: the summary strip; the frontier chart with the play trajectory, the oracle's
    recommendations, and every normative reference point (plus its numeric table view); the per-turn regret strip;
    the system-prompt audit; and the transcript, where each turn shows what the model did NEXT TO what the rational
    agent would have done there, with the regret between them. The tabbed sidebar (see :func:`_sidebar`) is sticky
    alongside and follows the transcript as it scrolls.

    The top bar carries the run name, the episode picker, and the quick read; where the picker's contents go is a
    marker the exporter fills once every page of the run is known (see :func:`~.chrome.nav_group`), so a page
    rendered on its own is still complete — it simply has nothing to navigate to."""
    ep = payload.get("episode") or {}
    game = payload.get("game")
    oracles = payload.get("oracle_names") or []
    counterfactual = payload.get("counterfactual_oracles") or []
    # the best-response oracle first, so the page opens on the one that carries a full counterfactual deal
    ordered = counterfactual + [o for o in oracles if o not in counterfactual]
    labels = {"rational_private": "private-information rational agent",
              "oracle_omniscient": "omniscient oracle"}
    options = "".join(f'<option value="{_e(o)}">{_e(labels.get(o, o))}</option>' for o in ordered)
    selector = (f"<label class='sub'>detailed counterfactual <select id='oracle-select'>{options}</select></label>"
                if oracles else "")
    oracle_scope = ("full-information oracle" if _preferences_are_public(payload)
                    else "omniscient hindsight oracle")
    no_cf = ("" if counterfactual else
             "<div class='warn'><b>No best-response oracle on this run; no decision counterfactuals are available.</b> Its episodes were scored with "
             f"{_e(', '.join(oracles) or 'no oracles')}, so the per-turn post-hoc oracle "
             "column shows only the oracles that are present. Re-annotate the run with "
             "<code>rational_private</code> and <code>oracle_omniscient</code> references to fill it in.</div>")
    chart = (f"""<section class='card' id='frontier'><h2>Where every deal sits, and where this episode went</h2>
 <div class='sub'>{_e(game.get('n_parties'))} parties means a deal's utility vector has {_e(game.get('n_parties'))} dimensions, so the chart plots the two summaries
 that carry the normative content, both scale-invariant: joint welfare (mean normalized surplus) across, and the
 worst-off party's normalized surplus up. Up and to the right is better for everyone. Hover any deal for its
 headline numbers and click to pin the full per-party breakdown; click a numbered move to jump to that turn. Drag
 to pan, Ctrl or Shift with the wheel to zoom.</div>
 {_legend('episode')}
 <div id='chart'></div>
 <div class='bar'><button id='table-toggle' aria-pressed='false'>Show the numbers as a table</button>
  <span class='sub muted'>every reference point, exactly</span></div>
 <div id='chart-table' hidden>{_reference_table(game)}</div>
 <div class='detail' id='detail'></div></section>""" if game else "")
    regret = (f"""<section class='card'><h2>Per-turn value gap against the {_e(oracle_scope)}</h2>
 <div class='sub'>Each bar is the oracle's value of its own best move minus its value of the move the seat played,
 in that oracle's units — the centipawn-loss analogue. On PRIVATE episodes this is an omniscient hindsight gap,
 not implementable-policy regret. Click a bar to jump to the turn.</div>
 <div class='bar'>{selector}</div><div id='regret'></div></section>""" if oracles else "")
    body = f"""<h1>{_e(ep.get('scenario'))} — <code>{_e(ep.get('episode_id'))}</code></h1>
{_meta_pills(payload)}{_source_links(payload)}
{vintage_banner(payload.get('vintage'))}
{_preference_visibility_banner(payload)}
{summary_strip(payload)}{census_strip(payload.get('census'))}
{_contamination_banner(payload)}{budget_note(payload.get('budget'))}{no_cf}
{ballot_table(payload.get('ballots'))}
<div class='layout'><div>
{chart}{regret}
{_system_prompt_audit(payload)}
<section class='card'><h2>Transcript — what the model did, and what the {_e(oracle_scope)} scores as best</h2>
 <div class='sub'>Every panel is expandable: the reasoning recorded for the turn, the exact prompt the seat saw,
 the raw turn text, and every action each oracle scored with its value. The rail below is every turn, coloured by
 what the seat did — click a chip to jump to it.</div>
 <div class='bar'><button id='expand-all'>Expand all panels</button>
  <button id='collapse-all'>Collapse all</button>
  <span class='sub muted'>or press <kbd>e</kbd> / <kbd>c</kbd>; <kbd>j</kbd> <kbd>k</kbd> walk the turns</span></div>
 <div id='turns'></div></section>
</div>{_sidebar(payload)}</div>"""
    return _document(f"{ep.get('episode_id')} — episode",
                     topbar(_e(ep.get("cell") or ep.get("scenario") or "run"), "index.html",
                            quick_stats(payload) + _preference_visibility_quick(payload)
                            + vintage_badge(payload.get("vintage")) + budget_badge(payload.get("budget")),
                            brand_title="back to the run index"),
                     body, payload, JS + "\n" + JS_EPISODE)


# -------------------------------------------------------------------------------- comparison page --
def _score_table_html(rows: list[dict]) -> str:
    out = []
    for r in rows:
        better = r.get("higher_is_better", 1)
        cls = ("zero" if not r.get("delta") else
               ("pos" if (r["delta"] > 0) == (better >= 0) and better != 0 else
                ("neg" if better != 0 else "zero")))
        delta = ("—" if r.get("delta") is None else
                 f"{'+' if r['delta'] >= 0 else ''}{r['delta']:g}")
        out.append(f"<tr><td>{_e(r['metric'])} <span class='muted'>{_e(r.get('note'))}</span></td>"
                   f"<td>{_num(r.get('left'), 3) if isinstance(r.get('left'), float) else _e(r.get('left'))}</td>"
                   f"<td>{_num(r.get('right'), 3) if isinstance(r.get('right'), float) else _e(r.get('right'))}</td>"
                   f"<td class='{cls}'><b>{delta}</b></td></tr>")
    return "".join(out)


def _verdict_strip(payload: dict) -> str:
    """Who won, on what — the one line a reader wants before reading a table of deltas.

    Counts the metrics that moved in each side's favour, using each row's own ``higher_is_better`` (so a lower
    Gini counts as a win for the side that lowered it), and names the largest move in each direction. Metrics
    with no directional preference, or that did not move, are counted as ties and stated as such rather than
    being quietly dropped — "3 of 9" would otherwise be read as 6 losses."""
    rows = [r for r in payload.get("scores") or [] if isinstance(r.get("delta"), (int, float))]
    labels = payload["labels"]
    directional = [r for r in rows if r.get("higher_is_better") and r["delta"]]
    right = [r for r in directional if (r["delta"] > 0) == (r["higher_is_better"] > 0)]
    left = [r for r in directional if r not in right]
    ties = len(rows) - len(directional)

    def biggest(group: list[dict]) -> str:
        if not group:
            return ""
        r = max(group, key=lambda r: abs(r["delta"]))
        return f" (largest: {_e(r['metric'])} {'+' if r['delta'] >= 0 else ''}{r['delta']:g})"

    if not directional:
        head = "<span class='hd'>Neither side won on any scored metric.</span>"
    elif not left or not right:
        winner, group = (labels["right"], right) if right else (labels["left"], left)
        side = "r" if right else "l"
        head = (f"<span class='hd'>Verdict:</span> <span class='won {side}'>{_e(winner)}</span> is better on all "
                f"{len(group)} metric(s) that moved{biggest(group)}.")
    else:
        head = (f"<span class='hd'>Verdict: split.</span> <span class='won r'>{_e(labels['right'])}</span> better "
                f"on {len(right)}{biggest(right)}; <span class='won l'>{_e(labels['left'])}</span> better on "
                f"{len(left)}{biggest(left)}.")
    return (f"<div class='verdict'>{head}"
            f"<span class='sub muted'>{ties} scored metric(s) tied or carry no better direction.</span></div>")


def render_compare_html(payload: dict) -> str:
    """One self-contained page for a seat-swap comparison: a verdict strip, the quantified score table with paired
    deltas, one shared frontier carrying both trajectories, and two synchronized transcript columns with the
    divergence point marked."""
    L, R = payload["left"], payload["right"]
    labels, pairing = payload["labels"], payload["pairing"]
    le, re_ = L.get("episode") or {}, R.get("episode") or {}
    focal = payload.get("focal_seats") or []
    game = L.get("game") or R.get("game")
    banner = []
    if not pairing["matched"]:
        banner.append("<div class='warn'><b>These two episodes are not a matched pair.</b> Their pairing key "
                      f"({_e(', '.join(pairing['fields']))}) differs: {_e(pairing['left'])} vs "
                      f"{_e(pairing['right'])}. Any difference below mixes the seat swap with that mismatch.</div>")
    if not focal:
        banner.append("<div class='warn'><b>No seat swap detected.</b> Every seat holds the same kind of occupant "
                      "in both episodes, so there is no substitution effect to attribute; the two runs differ in "
                      "some other way (model, scaffold, or sampling).</div>")
    else:
        who = ", ".join(f"{f['name']} (party {f['party']}): {f['left_kind']} → {f['right_kind']}" for f in focal)
        banner.append(f"<div class='warn'><b>Seat swap:</b> {_e(who)}. Every other seat, the instance, the seed, "
                      "and the protocol arm are held fixed, so the deltas below are the substitution effect.</div>")
    if payload.get("divergence") is None:
        banner.append("<div class='warn'><b>The two episodes never diverged.</b> Every turn slot carries the same "
                      "public behaviour on both sides.</div>")
    chart = (f"""<section class='card' id='frontier'><h2>Both trajectories on one frontier</h2>
 <div class='sub'>Identical game, identical seed — so one chart, one frontier, two paths through it. Numbered
 circles are the deals each side put on the table, in order; squares are the deals that closed. Hover any deal for
 its headline numbers, click to pin the per-party breakdown.</div>
 {_legend('compare')}<div id='chart'></div>
 <details><summary>The reference points as a table</summary><div class='body'>{_reference_table(game)}</div></details>
 <div class='detail' id='detail'></div></section>""" if game else "")
    quick = (f"<span><span class='k'>{_e(labels['left'])}</span> <b>{_num((L.get('outcome') or {}).get('primary'))}</b></span>"
             f"<span><span class='k'>{_e(labels['right'])}</span> <b>{_num((R.get('outcome') or {}).get('primary'))}</b></span>"
             f"<span><span class='k'>divergence</span> <b>"
             f"{payload['divergence'] if payload.get('divergence') is not None else 'none'}</b></span>"
             f"{_preference_visibility_quick(L)}")
    body = f"""<h1>Seat-swap comparison — <code>{_e(le.get('instance_id'))}</code> seed {_e(le.get('seed'))}</h1>
<div class='sub'>{_e(labels['left'])} <code>{_e(le.get('episode_id'))}</code> ({_e(le.get('model'))})
 vs {_e(labels['right'])} <code>{_e(re_.get('episode_id'))}</code> ({_e(re_.get('model'))})</div>
{_verdict_strip(payload)}
{vintage_pairing(L, R, labels)}{_vintage_banners(L, R)}
{_preference_visibility_banner(L)}
{''.join(banner)}
{_contamination_banner(L, labels['left'])}{_contamination_banner(R, labels['right'])}
<section class='card'><h2>What changed, in numbers</h2>
 <div class='sub'>Paired deltas, right minus left. Green is the better direction for that metric; a dash means the
 metric was not recorded on one side.</div>
 <div class='tablewrap'><table><thead><tr><th>metric</th><th>{_e(labels['left'])}</th><th>{_e(labels['right'])}</th>
 <th>delta</th></tr></thead><tbody>{_score_table_html(payload['scores'])}</tbody></table></div></section>
{chart}
<section class='card'><h2>Two transcripts, aligned until they diverge</h2>
 <div class='sub'>Turn slots are aligned on (round, phase, seat). Turns where the public behaviour differs are
 outlined; after the first such turn the two episodes are in different states, so the columns are two separate
 trajectories rather than a line-by-line diff.</div>
 <div class='bar'><button id='jump-divergence'>Jump to the divergence point</button>
 <button id='cf-toggle' aria-pressed='false'>Show each turn's post-hoc oracle counterfactual</button>
 <button id='expand-all'>Expand all panels</button><button id='collapse-all'>Collapse all</button>
 <span class='sub'>{('divergence at aligned slot ' + str(payload['divergence'])) if payload.get('divergence') is not None else 'no divergence'}</span></div>
 <div class='two'>
  <div><div class='colhd a'>{_e(labels['left'])} · {_e(le.get('model'))}</div><div id='col-left'></div></div>
  <div><div class='colhd b'>{_e(labels['right'])} · {_e(re_.get('model'))}</div><div id='col-right'></div></div>
 </div></section>
<div class='layout'><div>{_system_prompt_audit(L)}{_system_prompt_audit(R)}</div>{_side_panel(L)}</div>"""
    return _document(
        f"seat-swap comparison — {le.get('episode_id')} vs {re_.get('episode_id')}",
        topbar(_e(le.get("cell") or "comparison"), "index.html", quick, brand_title="back to the comparison index"),
        body, payload, JS + "\n" + JS_COMPARE)


# --------------------------------------------------------------------------------------- indexes --
#: The index's columns: (header, row key, kind). ``kind`` decides both the cell's rendering and how it sorts —
#: ``num`` for a tabular figure, ``bar`` for a figure with an inline magnitude bar, ``pct`` for a percentage that
#: goes red above zero, ``text`` for everything else.
INDEX_COLUMNS = [("page", "label", "link"), ("model", "model", "text"), ("arm", "arm", "text"),
                 ("visibility", "visibility", "visibility"),
                 ("instance", "instance", "text"), ("difficulty", "difficulty", "num"),
                 ("parameter tags", "difficulty_tags", "tags"), ("seed", "seed", "num"),
                 ("outcome", "deal", "deal"),
                 ("primary", "primary", "bar"), ("dist NBS", "dist_nbs", "num"), ("USW", "usw", "num"),
                 ("worst-off", "esw", "num"), ("fabricated", "fabricated_pct", "pct"),
                 ("hazards", "hazards", "hazards"),
                 ("score Δ", "score_diff", "bar"), ("total regret", "regret", "num")]


def _index_cell(row: dict, key: str, kind: str, scale: float) -> str:
    """One index cell, carrying a ``data-sort`` value so the browser sorts on the NUMBER, not on the string it is
    rendered as (``"10.0"`` sorts before ``"9.0"`` as text, and an em dash must sink rather than count as zero)."""
    v = row.get(key)
    if kind == "link":
        return f"<td data-sort='{_e(v)}'><a href='{_e(row['href'])}'>{_e(v)}</a></td>"
    if kind == "deal":
        return (f"<td data-sort='{1 if row.get('deal') else 0}'>"
                f"{'deal' if row.get('deal') else '<span class=neg>no deal</span>'}</td>")
    if kind == "visibility":
        label = str(v or "PRIVATE").upper()
        return f"<td data-sort='{_e(label)}'><span class='visibility'>{_e(label)}</span></td>"
    if kind == "hazards":
        # Every reason this row's numbers may not pair with another row's, as one badge each. Sorted on the
        # COUNT so a click brings the compromised episodes to the top, which is the only ordering a reader
        # scanning an index for trouble actually wants.
        flags = [f.strip() for f in str(v or "").split("·") if f.strip()]
        rendered = " ".join(f"<span class='badge hazard'>{_e(f)}</span>" for f in flags)
        return (f"<td data-sort='{len(flags)}' title='{_e(row.get('hazard_detail') or '')}'>"
                f"{rendered or '<span class=muted>none</span>'}</td>")
    if kind == "tags":
        values = [tag.strip() for tag in str(v or "").split(",") if tag.strip()]
        rendered = " ".join(f"<span class='badge parameter-tag'>{_e(tag)}</span>" for tag in values)
        detail = row.get("difficulty_components") or ""
        return f"<td data-sort='{_e(v)}' title='{_e(detail)}'>{rendered or '—'}</td>"
    if kind == "pct":
        if not v:
            return "<td data-sort='0' class='muted'>0%</td>"
        return f"<td data-sort='{v}'><span class='flag'>{_num(v, 1)}%</span></td>"
    if kind == "bar":
        if not isinstance(v, (int, float)):
            return "<td data-sort=''>—</td>"
        width = 0.0 if not scale else max(0.0, min(1.0, abs(v) / scale))
        return (f"<td data-sort='{v}'>{_num(v)}"
                f"<span class='inlinebar{'' if v >= 0 else ' warnfill'}'>"
                f"<i style='width:{width * 100:.0f}%'></i></span></td>")
    if kind == "num":
        return f"<td data-sort='{v if isinstance(v, (int, float)) else ''}'>" + (
            _num(v, 1) if isinstance(v, float) and abs(v) >= 10 else _num(v)) + "</td>"
    return f"<td data-sort='{_e(v)}'>{_e(v)}</td>"


def _difficulty_correlation(rows: list[dict]) -> str:
    """Render Pearson's ``r`` when at least three difficulty/effect pairs support it.

    Missing values are excluded. Constant difficulty or score differential has zero variance, so the correlation
    is undefined and omitted rather than reported as zero. The sample count is shown beside every coefficient.
    """
    # Seeds/rollouts of the same instance are repeated measurements, not extra parameter sets. Average them first
    # so a parameter set with more completed rollouts does not silently receive more weight in the correlation.
    grouped: dict[str, list[tuple[float, float]]] = {}
    for index, row in enumerate(rows):
        if not (isinstance(row.get("difficulty"), (int, float))
                and isinstance(row.get("score_diff"), (int, float))):
            continue
        key = str(row.get("instance") or f"__row_{index}")
        grouped.setdefault(key, []).append((float(row["difficulty"]), float(row["score_diff"])))
    pairs = [(sum(x for x, _ in values) / len(values), sum(y for _, y in values) / len(values))
             for values in grouped.values()]
    if len(pairs) < 3:
        return ""
    xs, ys = zip(*pairs)
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return ""
    r = sum((x - mx) * (y - my) for x, y in pairs) / math.sqrt(vx * vy)
    return ("<div class='correlation'><b>Difficulty × score differential:</b> "
            f"Pearson <var>r</var> = {_num(r, 3)} across {len(pairs)} paired parameter sets. "
            "Positive means the compared condition gains more on harder sets.</div>")


def render_index_html(rows: list[dict], title: str, note: str = "", readme_markdown: str = "") -> str:
    """A run index: one row per generated page, sortable on every column and filterable by text, outcome, and
    whether the engine fabricated any turns.

    Sorting and filtering are client-side over the rows already in the document — there is no second copy of the
    data in a JSON blob, so a 200-episode index stays a small file and still reads correctly with scripting off.
    The row count of what survives a filter is always on screen, because a filter that silently hides rows is how
    a reader concludes a run has fewer episodes than it has."""
    scale = max((abs(r["primary"]) for r in rows if isinstance(r.get("primary"), (int, float))), default=0.0)
    head = "".join(f"<th data-sort scope='col'>{_e(h)}</th>" for h, _, _ in INDEX_COLUMNS)
    body = []
    for r in rows:
        hay = " ".join(str(r.get(k) or "") for _, k, _ in INDEX_COLUMNS)
        body.append(f"<tr data-hay=\"{_e(hay)}\" data-deal='{1 if r.get('deal') else 0}' "
                    f"data-fabricated='{r.get('fabricated_pct') or 0}' "
                    f"data-hazards='{len([f for f in str(r.get('hazards') or '').split('·') if f.strip()])}'>"
                    + "".join(_index_cell(r, k, kind, scale) for _, k, kind in INDEX_COLUMNS) + "</tr>")
    table = (f"<section class='card'>{_difficulty_correlation(rows)}<div class='filterbar'>"
             "<input type='search' id='idx-search' placeholder='Filter by episode, model, arm, instance…' "
             "aria-label='filter the table'>"
             "<button data-filter='outcome:1' aria-pressed='false'>deal only</button>"
             "<button data-filter='outcome:0' aria-pressed='false'>no-deal only</button>"
             "<button data-filter='flag:fabricated' aria-pressed='false'>has fabricated turns</button>"
             "<button data-filter='flag:hazards' aria-pressed='false'>has hazards</button>"
             "<span class='count' id='idx-count'></span></div>"
             f"<div class='tablewrap'><table class='sortable'><thead><tr>{head}</tr></thead>"
             f"<tbody>{''.join(body)}</tbody></table></div>"
             "<div class='sub muted'>Click a column header to sort; <kbd>/</kbd> focuses the filter, "
             "<kbd>Enter</kbd> opens the first row that survives it.</div></section>")
    readme = _render_readme(readme_markdown)
    readme_html = f"<section class='card run-readme'>{readme}</section>" if readme else ""
    body_html = (f"<h1>{_e(title)}</h1>" + (f"<div class='sub'>{note}</div>" if note else "")
                 + readme_html + table)
    return _document(title,
                     topbar(title, None, f"<span><span class='k'>pages</span> <b>{len(rows)}</b></span>",
                            brand_title=title, nav=False),
                     body_html, None, JS_INDEX_PAGE)
