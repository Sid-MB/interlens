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
from pathlib import Path

from .assets import CSS, JS, JS_COMPARE, JS_EPISODE, JS_INDEX_PAGE
from .chrome import (_e, _num, distance_to_nbs, help_overlay, nav_group, quick_stats, slim_payload,
                     summary_strip, topbar)

__all__ = ["nav_group", "render_compare_html", "render_episode_html", "render_index_html"]


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

    Sections, in order: the summary strip; the frontier chart with the play trajectory, the oracle's
    recommendations, and every normative reference point (plus its numeric table view); the per-turn regret strip;
    the system-prompt audit; and the transcript, where each turn shows what the model did NEXT TO what the rational
    agent would have done there, with the regret between them. The game side panel is sticky alongside.

    The top bar carries the run name, the episode picker, and the quick read; where the picker's contents go is a
    marker the exporter fills once every page of the run is known (see :func:`~.chrome.nav_group`), so a page
    rendered on its own is still complete — it simply has nothing to navigate to."""
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
 worst-off party's normalized surplus up. Up and to the right is better for everyone. Hover any deal for its
 headline numbers and click to pin the full per-party breakdown; click a numbered move to jump to that turn. Drag
 to pan, Ctrl or Shift with the wheel to zoom.</div>
 {_legend('episode')}
 <div id='chart'></div>
 <div class='bar'><button id='table-toggle' aria-pressed='false'>Show the numbers as a table</button>
  <span class='sub muted'>every reference point, exactly</span></div>
 <div id='chart-table' hidden>{_reference_table(game)}</div>
 <div class='detail' id='detail'></div></section>""" if game else "")
    regret = (f"""<section class='card'><h2>Per-turn regret against the rational agent</h2>
 <div class='sub'>Each bar is the oracle's value of its own best move minus its value of the move the seat played,
 in that oracle's units — the centipawn-loss analogue. Click a bar to jump to the turn.</div>
 <div class='bar'>{selector}</div><div id='regret'></div></section>""" if oracles else "")
    body = f"""<h1>{_e(ep.get('scenario'))} — <code>{_e(ep.get('episode_id'))}</code></h1>
{_meta_pills(payload)}{_source_links(payload)}
{summary_strip(payload)}{_contamination_banner(payload)}{no_cf}
<div class='layout'><div>
{chart}{regret}
{_system_prompt_audit(payload)}
<section class='card'><h2>Transcript — what the model did, and what a rational agent would have done</h2>
 <div class='sub'>Every panel is expandable: the reasoning recorded for the turn, the exact prompt the seat saw,
 the raw turn text, and every action each oracle scored with its value. The rail below is every turn, coloured by
 what the seat did — click a chip to jump to it.</div>
 <div class='bar'><button id='expand-all'>Expand all panels</button>
  <button id='collapse-all'>Collapse all</button>
  <span class='sub muted'>or press <kbd>e</kbd> / <kbd>c</kbd>; <kbd>j</kbd> <kbd>k</kbd> walk the turns</span></div>
 <div id='turns'></div></section>
</div>{_side_panel(payload)}</div>"""
    return _document(f"{ep.get('episode_id')} — episode",
                     topbar(_e(ep.get("cell") or ep.get("scenario") or "run"), "index.html",
                            quick_stats(payload), brand_title="back to the run index"),
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
             f"{payload['divergence'] if payload.get('divergence') is not None else 'none'}</b></span>")
    body = f"""<h1>Seat-swap comparison — <code>{_e(le.get('instance_id'))}</code> seed {_e(le.get('seed'))}</h1>
<div class='sub'>{_e(labels['left'])} <code>{_e(le.get('episode_id'))}</code> ({_e(le.get('model'))})
 vs {_e(labels['right'])} <code>{_e(re_.get('episode_id'))}</code> ({_e(re_.get('model'))})</div>
{_verdict_strip(payload)}
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
 <button id='cf-toggle' aria-pressed='false'>Show each turn's rational-agent counterfactual</button>
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
                 ("instance", "instance", "text"), ("seed", "seed", "num"), ("outcome", "deal", "deal"),
                 ("primary", "primary", "bar"), ("dist NBS", "dist_nbs", "num"), ("USW", "usw", "num"),
                 ("worst-off", "esw", "num"), ("fabricated", "fabricated_pct", "pct"),
                 ("total regret", "regret", "num")]


def _index_cell(row: dict, key: str, kind: str, scale: float) -> str:
    """One index cell, carrying a ``data-sort`` value so the browser sorts on the NUMBER, not on the string it is
    rendered as (``"10.0"`` sorts before ``"9.0"`` as text, and an em dash must sink rather than count as zero)."""
    v = row.get(key)
    if kind == "link":
        return f"<td data-sort='{_e(v)}'><a href='{_e(row['href'])}'>{_e(v)}</a></td>"
    if kind == "deal":
        return (f"<td data-sort='{1 if row.get('deal') else 0}'>"
                f"{'deal' if row.get('deal') else '<span class=neg>no deal</span>'}</td>")
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


def render_index_html(rows: list[dict], title: str, note: str = "") -> str:
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
                    f"data-fabricated='{r.get('fabricated_pct') or 0}'>"
                    + "".join(_index_cell(r, k, kind, scale) for _, k, kind in INDEX_COLUMNS) + "</tr>")
    table = (f"<section class='card'><div class='filterbar'>"
             "<input type='search' id='idx-search' placeholder='Filter by episode, model, arm, instance…' "
             "aria-label='filter the table'>"
             "<button data-filter='outcome:1' aria-pressed='false'>deal only</button>"
             "<button data-filter='outcome:0' aria-pressed='false'>no-deal only</button>"
             "<button data-filter='flag:fabricated' aria-pressed='false'>has fabricated turns</button>"
             "<span class='count' id='idx-count'></span></div>"
             f"<div class='tablewrap'><table class='sortable'><thead><tr>{head}</tr></thead>"
             f"<tbody>{''.join(body)}</tbody></table></div>"
             "<div class='sub muted'>Click a column header to sort; <kbd>/</kbd> focuses the filter, "
             "<kbd>Enter</kbd> opens the first row that survives it.</div></section>")
    body_html = f"<h1>{_e(title)}</h1>" + (f"<div class='sub'>{note}</div>" if note else "") + table
    return _document(title,
                     topbar(title, None, f"<span><span class='k'>pages</span> <b>{len(rows)}</b></span>",
                            brand_title=title, nav=False),
                     body_html, None, JS_INDEX_PAGE)
