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

"""HTML assembly: a payload in, one self-contained interactive page out.

Everything that can be rendered without JavaScript is rendered here in Python — the stat tiles, the game side
panel, every score sheet, the numeric table view of the chart, the pairing banner and the comparison score table.
The browser script only draws the two charts and the transcript cards. That split is deliberate: the numbers are
the deliverable, so they must be in the document even if the script never runs, and it makes the tests able to
assert on real structure and real values without a browser.

Pages are opened over ``file://``, so nothing is fetched: the stylesheet and script are inlined, and the payload
travels in a ``<script type="application/json">`` tag (data in a data position — never interpolated into
executable code, and closing-tag sequences are escaped).
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .assets import CSS, JS, JS_COMPARE, JS_EPISODE


def _e(x: Any) -> str:
    """HTML-escape a value; ``None`` renders as an em dash so an empty cell is visibly empty."""
    return html.escape("—" if x is None else str(x))


def _num(v: Any, digits: int = 3) -> str:
    """Format a number for a cell, em-dash for a non-number, so a missing metric never reads as zero."""
    return f"{v:.{digits}f}" if isinstance(v, (int, float)) and not isinstance(v, bool) else "—"


def _payload_script(payload: dict) -> str:
    """The payload as an inert JSON script tag. ``</`` is escaped so no string inside the data can end the tag."""
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str).replace("</", "<\\/")
    return f'<script type="application/json" id="viz-payload">{data}</script>'


def _document(title: str, body: str, payload: dict, script: str) -> str:
    """The complete HTML document: inline CSS, the body, the inert payload, then the shared + page-specific JS."""
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{_e(title)}</title><style>{CSS}</style></head><body><main>{body}</main>"
            f"{_payload_script(payload)}<script>{JS}\n{script}</script></body></html>")


# ------------------------------------------------------------------------------------ shared parts --
def _tile(key: str, value: str, note: str = "") -> str:
    return (f"<div class='tile'><div class='k'>{_e(key)}</div><div class='v'>{value}</div>"
            f"<div class='n'>{note}</div></div>")


def _tiles(payload: dict) -> str:
    """The headline numbers of one episode: outcome, the four welfare scalars, inequality, and total regret."""
    out, game = payload.get("outcome") or {}, payload.get("game") or {}
    summary = payload.get("annotation_summary") or {}
    ceiling = game.get("ceiling")
    tiles = [
        _tile("outcome", "deal" if out.get("deal") else "<span class='neg'>no deal</span>",
              _e(out.get("finalized_by"))),
        _tile("primary", _num(out.get("primary")),
              f"ceiling {_num(ceiling)}" if ceiling is not None else "normalized headline score"),
        _tile("joint welfare", _num(out.get("usw"), 1), "sum of surpluses"),
        _tile("worst-off", f"<span class='{'pos' if (out.get('esw') or 0) >= 0 else 'neg'}'>"
                           f"{_num(out.get('esw'), 1)}</span>", "min surplus (ESW)"),
        _tile("Nash welfare", _num(out.get("nsw_geomean"), 1), "geometric mean; 0 if any party below τ"),
        _tile("Gini", _num(out.get("gini")), "0 = equal surplus split"),
    ]
    if out.get("n_ir_violations") is not None:
        tiles.append(_tile("below threshold", f"<span class='{'neg' if out.get('n_ir_violations') else 'zero'}'>"
                                             f"{out.get('n_ir_violations')}</span>",
                           _e(", ".join(out.get("ir_violations") or []) or "none")))
    gen = payload.get("generation") or {}
    if gen.get("fabricated"):
        tiles.append(_tile("NOT generated", f"<span class='neg'>{gen['fabricated']}</span>",
                           f"of {gen.get('n_turns')} turns — engine placeholders"))
    if summary.get("total_regret") is not None:
        tiles.append(_tile("total regret", _num(summary.get("total_regret"), 1),
                           f"mean {_num(summary.get('mean_regret'), 2)} / turn"))
    return f"<div class='tiles'>{''.join(tiles)}</div>"


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


def _source_links(payload: dict) -> str:
    """Links to the exact records this page was built from — the reproduction trail, absolute paths as ``file://``
    URIs so they open from the generated HTML wherever it is copied to."""
    paths = payload.get("paths") or {}
    if not paths:
        return ""
    items = [f"<a href='{_e(Path(v).as_uri())}'>{_e(k)}</a>" for k, v in paths.items() if v]
    return f"<div class='sub'>source records: {' · '.join(items)}</div>"


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
    return ("<table><thead><tr><th>reference point</th><th>deal #</th><th>joint welfare</th><th>min surplus</th>"
            "<th>USW</th><th>ESW</th><th>Pareto</th><th>can close</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>")


def _legend(mode: str) -> str:
    """The chart legend. Present whenever more than one identity is on screen, and every entry names its shape as
    well as its colour so identity is never carried by colour alone."""
    left, right = ("the model's play", "oracle recommendation") if mode == "episode" else ("left episode", "right episode")
    return ("<div class='legend'>"
            f"<span><i class='swatch' style='background:var(--s1)'></i>{_e(left)} (numbered, in order)</span>"
            f"<span><i class='swatch sq' style='background:var(--s1)'></i>the deal that closed</span>"
            f"<span><i class='swatch' style='background:var(--s2)'></i>{_e(right)}</span>"
            "<span><i class='swatch' style='background:var(--s3)'></i>solution concept (starred, labelled)</span>"
            "<span><i class='swatch di' style='background:var(--s3)'></i>a party's individually-best deal</span>"
            "<span><i class='swatch' style='background:var(--ink-2)'></i>Pareto-frontier deal</span>"
            "<span><i class='swatch' style='background:var(--muted)'></i>dominated deal</span></div>")


def _side_panel(payload: dict) -> str:
    """The game side panel: who is at the table, the thresholds, the protocol, the size of the bargaining problem,
    the solution concepts, and every party's private score sheet — the whole normative context of the episode."""
    game = payload.get("game")
    seats = payload.get("seats") or []
    if not game:
        return ("<aside><section class='card'><h2>Game</h2><div class='gap'>No instance record was supplied, so "
                "the game setup, thresholds, and frontier are unavailable; the transcript above is complete.</div>"
                "</section></aside>")
    counts, protocol = game.get("counts") or {}, game.get("protocol") or {}
    ideal = game.get("ideal_surplus") or []
    seat_rows = "".join(
        f"<tr><td>{_e(s.get('name'))} <span class='badge {_e(s.get('kind'))}'>{_e(s.get('kind'))}</span></td>"
        f"<td class='muted'>{_e((game.get('parties') or [])[i] if i < len(game.get('parties') or []) else '')}</td>"
        f"<td>{_num((game.get('thresholds') or [None] * (i + 1))[i], 1)}</td>"
        f"<td>{_num(ideal[i] if i < len(ideal) else None, 1)}</td>"
        f"<td>{_num(((payload.get('outcome') or {}).get('per_party_surplus') or [None] * (i + 1))[i], 1)}</td></tr>"
        for i, s in enumerate(seats))
    issues = "".join(f"<tr><td>{_e(iss['name'])}</td><td class='muted'>{_e(', '.join(iss['options']))}</td></tr>"
                     for iss in game.get("issues") or [])
    veto = ", ".join(str((game.get("parties") or [])[v] if v < len(game.get("parties") or []) else v)
                     for v in protocol.get("veto_seats") or []) or "none"
    sheets = "".join(
        "<details><summary>Private score sheet — "
        f"{_e(sh['agent'])} (threshold {_num(sh['threshold'], 1)})</summary><div class='body'><table>"
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
    return f"""<aside>
<section class='card'><h2>Who is at the table</h2>
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
<section class='card'><h2>Private score sheets</h2>
 <div class='sub'>What each party is secretly optimizing. Never shown to the other seats.</div>{sheets}</section>
<section class='card'><h2>Prompt provenance</h2>
 <div class='sub'>{_e(views.get('stored'))} of {_e(views.get('n_turns'))} turns carry the exact view recorded at
 generation time; {_e(views.get('reconstructed'))} were re-derived by replay through today's prompt code and are
 labelled as reconstructed wherever they appear.
 {(f"Of those, {views.get('reconstructed_pre_retry')} were retry turns, whose reconstruction is the FIRST "
   "attempt's prompt — the repair instruction the model saw on the retry is not recoverable from the record."
   ) if views.get('reconstructed_pre_retry') else ''}</div></section>
</aside>"""


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

    Sections, in order: the headline numbers; the frontier chart with the play trajectory, the oracle's
    recommendations, and every normative reference point (plus its numeric table view); the per-turn regret strip;
    the system-prompt audit; and the transcript, where each turn shows what the model did NEXT TO what the rational
    agent would have done there, with the regret between them. The game side panel is sticky alongside."""
    ep = payload.get("episode") or {}
    game = payload.get("game")
    oracles = payload.get("oracle_names") or []
    counterfactual = payload.get("counterfactual_oracles") or []
    # the best-response oracle first, so the page opens on the one that carries a full counterfactual deal
    ordered = counterfactual + [o for o in oracles if o not in counterfactual]
    options = "".join(f'<option value="{_e(o)}">{_e(o)}</option>' for o in ordered)
    selector = (f"<label class='sub'>counterfactual oracle <select id='oracle-select'>{options}</select></label>"
                if oracles else "")
    no_cf = ("" if counterfactual else
             "<div class='warn'><b>No best-response oracle on this run.</b> Its episodes were scored with "
             f"{_e(', '.join(oracles) or 'no oracles')}, so the per-turn 'what a rational agent would have done' "
             "column shows only the oracles that are present. Re-annotate the run with the "
             "<code>bestresponse</code> oracle to fill it in.</div>")
    chart = (f"""<section class='card' id='frontier'><h2>Where every deal sits, and where this episode went</h2>
 <div class='sub'>Six parties means a deal's utility vector has six dimensions, so the chart plots the two summaries
 that carry the normative content, both scale-invariant: joint welfare (mean normalized surplus) across, and the
 worst-off party's normalized surplus up. Up and to the right is better for everyone. Hover or click any deal for
 the full per-party breakdown; click a numbered move to jump to that turn.</div>
 {_legend('episode')}
 <div id='chart'></div>
 <div class='bar'><button id='table-toggle' aria-pressed='false'>Show the numbers as a table</button></div>
 <div id='chart-table' hidden>{_reference_table(game)}</div>
 <div class='detail' id='detail'></div></section>""" if game else "")
    regret = (f"""<section class='card'><h2>Per-turn regret against the rational agent</h2>
 <div class='sub'>Each bar is the oracle's value of its own best move minus its value of the move the seat played,
 in that oracle's units — the centipawn-loss analogue. Click a bar to jump to the turn.</div>
 <div class='bar'>{selector}</div><div id='regret'></div></section>""" if oracles else "")
    body = f"""<h1>{_e(ep.get('scenario'))} — <code>{_e(ep.get('episode_id'))}</code></h1>
{_meta_pills(payload)}{_source_links(payload)}
{_tiles(payload)}{_contamination_banner(payload)}{no_cf}
<div class='layout'><div>
{chart}{regret}
{_system_prompt_audit(payload)}
<section class='card'><h2>Transcript — what the model did, and what a rational agent would have done</h2>
 <div class='sub'>Every panel is expandable: the reasoning recorded for the turn, the exact prompt the seat saw,
 the raw turn text, and every action each oracle scored with its value.</div>
 <div id='turns'></div></section>
</div>{_side_panel(payload)}</div>"""
    return _document(f"{ep.get('episode_id')} — episode", body, payload, JS_EPISODE)


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


def render_compare_html(payload: dict) -> str:
    """One self-contained page for a seat-swap comparison: the quantified score table with paired deltas, one
    shared frontier carrying both trajectories, and two synchronized transcript columns with the divergence point
    marked."""
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
 circles are the deals each side put on the table, in order; squares are the deals that closed.</div>
 {_legend('compare')}<div id='chart'></div>
 <details><summary>The reference points as a table</summary><div class='body'>{_reference_table(game)}</div></details>
 <div class='detail' id='detail'></div></section>""" if game else "")
    return _document(
        f"seat-swap comparison — {le.get('episode_id')} vs {re_.get('episode_id')}",
        f"""<h1>Seat-swap comparison — <code>{_e(le.get('instance_id'))}</code> seed {_e(le.get('seed'))}</h1>
<div class='sub'>{_e(labels['left'])} <code>{_e(le.get('episode_id'))}</code> ({_e(le.get('model'))})
 vs {_e(labels['right'])} <code>{_e(re_.get('episode_id'))}</code> ({_e(re_.get('model'))})</div>
{''.join(banner)}
{_contamination_banner(L, labels['left'])}{_contamination_banner(R, labels['right'])}
<section class='card'><h2>What changed, in numbers</h2>
 <div class='sub'>Paired deltas, right minus left. Green is the better direction for that metric; a dash means the
 metric was not recorded on one side.</div>
 <table><thead><tr><th>metric</th><th>{_e(labels['left'])}</th><th>{_e(labels['right'])}</th>
 <th>delta</th></tr></thead><tbody>{_score_table_html(payload['scores'])}</tbody></table></section>
{chart}
<section class='card'><h2>Two transcripts, aligned until they diverge</h2>
 <div class='sub'>Turn slots are aligned on (round, phase, seat). Turns where the public behaviour differs are
 outlined; after the first such turn the two episodes are in different states, so the columns are two separate
 trajectories rather than a line-by-line diff.</div>
 <div class='bar'><button id='jump-divergence'>Jump to the divergence point</button>
 <span class='sub'>{('divergence at aligned slot ' + str(payload['divergence'])) if payload.get('divergence') is not None else 'no divergence'}</span></div>
 <div class='two'>
  <div><div class='colhd a'>{_e(labels['left'])} · {_e(le.get('model'))}</div><div id='col-left'></div></div>
  <div><div class='colhd b'>{_e(labels['right'])} · {_e(re_.get('model'))}</div><div id='col-right'></div></div>
 </div></section>
<div class='layout'><div>{_system_prompt_audit(L)}{_system_prompt_audit(R)}</div>{_side_panel(L)}</div>""",
        payload, JS_COMPARE)


# --------------------------------------------------------------------------------------- indexes --
def render_index_html(rows: list[dict], title: str, note: str = "") -> str:
    """A run index: one sortable-by-eye row per generated page with the numbers that make an episode worth
    opening (outcome, primary, welfare, regret), so a reader picks the interesting episode instead of the first."""
    body = ["<h1>", _e(title), "</h1>"]
    if note:
        body.append(f"<div class='sub'>{note}</div>")
    body.append("<section class='card'><table><thead><tr><th>page</th><th>model</th><th>arm</th><th>seed</th>"
                "<th>outcome</th><th>primary</th><th>USW</th><th>worst-off</th><th>total regret</th>"
                "</tr></thead><tbody>")
    for r in rows:
        body.append(
            f"<tr><td><a href='{_e(r['href'])}'>{_e(r['label'])}</a></td><td>{_e(r.get('model'))}</td>"
            f"<td>{_e(r.get('arm'))}</td><td>{_e(r.get('seed'))}</td>"
            f"<td>{'deal' if r.get('deal') else '<span class=neg>no deal</span>'}</td>"
            f"<td>{_num(r.get('primary'))}</td><td>{_num(r.get('usw'), 1)}</td>"
            f"<td>{_num(r.get('esw'), 1)}</td><td>{_num(r.get('regret'), 1)}</td></tr>")
    body.append("</tbody></table></section>")
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{_e(title)}</title><style>{CSS}</style></head><body><main>{''.join(body)}</main></body></html>")
