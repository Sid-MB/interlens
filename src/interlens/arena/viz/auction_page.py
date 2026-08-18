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
# [implement: auctions | 2026-08-18 | lane auction-viz | session 68537820-d6a1-44ca-88b5-847d81e4811a]

"""The auction episode page's own panels — the four charts design.md §10 commits to, plus the per-turn
counterfactual table.

Split out of :mod:`~interlens.arena.viz.page` rather than branched inside it, because none of these panels
share a line with the negotiation ones: an auction has no deal space to embed, so there is no frontier chart,
no solution-concept legend, and no regret strip. What IS shared comes back in through ``page.py`` — the shell,
the transcript, the census and vintage badges, the prompt audit, and the chat bubbles — so this module renders
only what is genuinely new.

Everything here is server-rendered SVG and HTML. The browser layer
(:data:`~interlens.arena.viz.assets.js_auction.JS_AUCTION`) adds the stage scrubber, the hover cards, and the
transcript cross-links; with scripting off, every number and every mark is still in the document, which is the
same contract the rest of the visualizer keeps.

The four panels, in the order the page carries them:

1. :func:`bid_ladder` — price against round, stages laid out left to right on one shared price scale, one line
   per seat, exits and standing-high transitions marked, private valuations as per-stage reference ticks, with
   the collusion-onset stage and every detected defection shaded onto the stage axis.
2. :func:`allocation_strip` — one bar per lot per stage, private valuations as ticks, the clearing price as the
   tau-line. A direct adaptation of ``page._issue_bars_svg``'s scale-and-tick construction.
3. :func:`settlement_panel` — winner, payment and surplus per stage, with the episode total.
4. :func:`dm_graph` — the directed message graph with a stage scrubber and the per-dyad counts beside it.
"""
from __future__ import annotations

from .chrome import _e, _num, stat

__all__ = ["allocation_strip", "auction_body", "auction_summary_strip", "bid_ladder", "counterfactual_table",
           "dm_graph", "settlement_panel"]

#: One SVG geometry for the staged ladder, so the stage widths, the axis gutter and the legend all agree.
LADDER = {"h": 300, "left": 46, "right": 12, "top": 16, "bottom": 44, "stage_min": 120, "stage_gap": 10}

#: The allocation strip's per-stage block. Narrow bars: a 20-lot stage has to stay legible at page width.
STRIP = {"h": 190, "left": 42, "right": 12, "top": 14, "bottom": 40, "bar_max": 26}

#: The DM graph's ring layout. Five seats on a circle is the whole design — a force layout would move the same
#: seat between two stages of the same episode and make the scrubber unreadable.
GRAPH = {"w": 360, "h": 300, "r": 108}


# --------------------------------------------------------------------------------------------------------- #
# Helpers.
# --------------------------------------------------------------------------------------------------------- #
def _seat_names(payload: dict) -> list[str]:
    """Seat display names in seat order, from the episode record."""
    return [s.get("name") or f"seat {i}" for i, s in enumerate(payload.get("seats") or [])]


def _seat_kinds(payload: dict) -> list[str]:
    """Per-seat occupant kind (``llm`` / a policy name), which is what makes an arm readable on the chart."""
    return [s.get("kind") or "llm" for s in payload.get("seats") or []]


def _pct(fraction, digits: int = 1) -> str:
    """A recorded rate as a percentage, em dash when there is no measurement."""
    if not isinstance(fraction, (int, float)) or isinstance(fraction, bool):
        return "—"
    return f"{100 * fraction:.{digits}f}%"


def _bid_label(bids: list[dict]) -> str:
    """A move's committed money as one short string: ``L04 140`` or ``140`` on a single-lot format."""
    if not bids:
        return "—"
    return ", ".join(f"{b['lot']} {b['amount']:g}" if b.get("lot") else f"{b['amount']:g}" for b in bids)


def _move_label(entry: dict | None) -> str:
    """A counterfactual rule's move as one cell: its action word plus whatever money it committed."""
    if not entry:
        return "—"
    if entry.get("error"):
        return "<span class='neg'>not scored</span>"
    action = entry.get("action") or "none"
    bids = entry.get("bids") or []
    return f"{_e(action)} {_e(_bid_label(bids))}" if bids else _e(action)


# --------------------------------------------------------------------------------------------------------- #
# 1. The staged bid ladder.
# --------------------------------------------------------------------------------------------------------- #
def bid_ladder(auction: dict, payload: dict) -> str:
    """Price against bidding round, every stage of the episode side by side on one shared price scale.

    One polyline per seat per stage through the highest price that seat committed in each round — on a clock
    format that is the clock price its ``stay``/``claim`` happened at, since a clock move carries no amount of
    its own. Individual lot bids under SAA are drawn as marks rather than folded into the line, because a line
    through ten simultaneous lot bids would trace a number nobody bid. A mark that took the standing high is
    filled; an irrevocable exit is a cross.

    Two overlays make the repeated-play story readable from the one figure: each seat's own top realized
    valuation for the stage as a reference tick (post-hoc — no seat saw another's), and a shaded band on any
    stage where the outcome rule found an agreement in force, with the onset stage and every defection
    labelled on the stage axis.

    ``None``-safe: a stage with no priced action at all renders as an empty stage column rather than being
    dropped, so the stage axis always counts to ``T``.
    """
    ladder = auction.get("ladder") or {}
    stages = ladder.get("stages") or []
    if not stages:
        return ("<section class='card' id='ladder'><h2>Bid ladder</h2><div class='gap'>No stage of this "
                "episode recorded a priced action, so there is no price path to draw.</div></section>")
    onset = auction.get("onset") or {}
    names, kinds = _seat_names(payload), _seat_kinds(payload)
    hi = float(ladder.get("price_ceiling") or 1.0)
    reserve = float(stages[0].get("reserve") or 0)
    lo = 0.0
    pad = max(1.0, (hi - lo) * 0.06)
    top, bottom = hi + pad, lo
    n_rounds = [max(1, int(s.get("n_rounds") or 1)) for s in stages]
    widths = [max(LADDER["stage_min"], 26 * r) for r in n_rounds]
    W = LADDER["left"] + LADDER["right"] + sum(widths) + LADDER["stage_gap"] * (len(stages) - 1)
    H = LADDER["h"]

    def y(v: float) -> float:
        return H - LADDER["bottom"] - ((v - bottom) / (top - bottom)) * (H - LADDER["top"] - LADDER["bottom"])

    parts, x0 = [], float(LADDER["left"])
    for i in range(5):                                   # a recessive price grid, labelled once on the left
        gv = bottom + (top - bottom) * i / 4
        parts.append(f"<line class='gridline' x1='{LADDER['left']}' x2='{W - LADDER['right']}' "
                     f"y1='{y(gv):.1f}' y2='{y(gv):.1f}'/>")
        parts.append(f"<text x='{LADDER['left'] - 6}' y='{y(gv) + 4:.1f}' text-anchor='end'>{gv:.0f}</text>")
    if reserve > 0:
        parts.append(f"<line class='taul' x1='{LADDER['left']}' x2='{W - LADDER['right']}' "
                     f"y1='{y(reserve):.1f}' y2='{y(reserve):.1f}'><title>reserve price "
                     f"{reserve:g}</title></line>")
    for block, width, rounds in zip(stages, widths, n_rounds):
        t = int(block["stage"])
        span = width / max(1, rounds)
        agreement = t in (onset.get("agreement_stages") or [])
        defected = t in (onset.get("defections") or [])
        if agreement or defected:
            parts.append(f"<rect class='stageband{' defect' if defected else ''}' x='{x0:.1f}' "
                         f"y='{LADDER['top']}' width='{width:.1f}' "
                         f"height='{H - LADDER['top'] - LADDER['bottom']:.1f}'><title>stage {t}: "
                         f"{'a defection from the agreement in force' if defected else 'an agreement in force by the outcome rule'}"
                         f"</title></rect>")
        if x0 > LADDER["left"] + 1:
            parts.append(f"<line class='stagerule' x1='{x0 - LADDER['stage_gap'] / 2:.1f}' "
                         f"x2='{x0 - LADDER['stage_gap'] / 2:.1f}' y1='{LADDER['top']}' "
                         f"y2='{H - LADDER['bottom']}'/>")
        label = f"stage {t}"
        if onset.get("stage") == t:
            label += " · ONSET"
        parts.append(f"<text class='stagelab' x='{x0 + width / 2:.1f}' y='{H - LADDER['bottom'] + 15}' "
                     f"text-anchor='middle'>{_e(label)}</text>")
        for tick in block.get("value_ticks") or []:
            seat = int(tick["seat"])
            parts.append(f"<line class='vtick sc{seat % 5}' x1='{x0:.1f}' x2='{x0 + width:.1f}' "
                         f"y1='{y(float(tick['top'])):.1f}' y2='{y(float(tick['top'])):.1f}'>"
                         f"<title>{_e(names[seat] if seat < len(names) else seat)}: top realized value "
                         f"{tick['top']} this stage, budget {tick['budget']} (post-hoc; no rival saw it)"
                         f"</title></line>")
        for series in block.get("seats") or []:
            seat = int(series["seat"])
            pts = [(x0 + (int(p["round"]) - 0.5) * span, y(float(p["price"]))) for p in series["points"]]
            if len(pts) > 1:
                path = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
                parts.append(f"<polyline class='bidline sc{seat % 5}' points='{path}'/>")
            for p, (px, py) in zip(series["points"], pts):
                parts.append(f"<circle class='bidpt sc{seat % 5}' data-turn='{int(p['turn'])}' cx='{px:.1f}' "
                             f"cy='{py:.1f}' r='3.4'><title>{_e(names[seat] if seat < len(names) else seat)}"
                             f" — stage {t}, round {int(p['round'])}: {_e(p['atype'])} at "
                             f"{float(p['price']):g} (turn {int(p['turn'])})</title></circle>")
            for mark in series.get("marks") or []:
                if mark.get("lot") is None:
                    continue                             # already drawn as the line's own point
                mx = x0 + (int(mark["round"]) - 0.5) * span
                cls = "lotmark took" if mark.get("standing_high") else "lotmark"
                parts.append(f"<rect class='{cls} sc{seat % 5}' data-turn='{int(mark['turn'])}' "
                             f"x='{mx - 2.5:.1f}' y='{y(float(mark['price'])) - 2.5:.1f}' width='5' "
                             f"height='5'><title>{_e(names[seat] if seat < len(names) else seat)} bid "
                             f"{float(mark['price']):g} on {_e(mark['lot'])} in round {int(mark['round'])}"
                             f"{' — took the standing high' if mark.get('standing_high') else ''}</title>"
                             f"</rect>")
            for ex in series.get("exits") or []:
                ex_x = x0 + (int(ex["round"]) - 0.5) * span
                ex_y = y(float(ex["price"]))
                parts.append(f"<path class='exitmark sc{seat % 5}' data-turn='{int(ex['turn'])}' "
                             f"d='M{ex_x - 4:.1f},{ex_y - 4:.1f}l8,8M{ex_x + 4:.1f},{ex_y - 4:.1f}l-8,8'>"
                             f"<title>{_e(names[seat] if seat < len(names) else seat)} "
                             f"{_e(ex['atype'])} at clock price {float(ex['price']):g}</title></path>")
        x0 += width + LADDER["stage_gap"]
    legend = "".join(
        f"<span><i class='swatch sc{i % 5}'></i>{_e(n)} <span class='muted'>{_e(kinds[i] if i < len(kinds) else '')}</span></span>"
        for i, n in enumerate(names))
    onset_note = ("no collusion-onset event: suppression never exceeded "
                  f"θ = {_num(onset.get('theta'), 2)} in two consecutive stages, so this episode is "
                  "right-censored"
                  if onset.get("censored") else f"onset at stage {onset.get('stage')}")
    return f"""<section class='card' id='ladder'><h2>The bid ladder, stage by stage</h2>
 <div class='sub'>Price up, bidding round across, every stage of the episode on one shared price scale so the
 path is readable as a single figure. A line follows the highest price a seat committed in each round; under a
 multi-lot format each individual lot bid is a small square beside it, filled where the bid took the standing
 high. A cross is an irrevocable exit. The faint horizontal rule in each seat's colour is that seat's own top
 realized valuation for the stage — an analyst's overlay, never something a rival could see. Shaded stages are
 the ones where the outcome rule found an agreement in force. Click any mark to jump to its turn.</div>
 <div class='legend'>{legend}
  <span><i class='swatch sq'></i>a lot bid that took the standing high</span>
  <span><i class='swatch xmark'></i>exit / wait on the clock</span>
  <span><i class='swatch dash'></i>that seat's own top value this stage (post hoc)</span></div>
 <div class='chartwrap wide'><svg viewBox='0 0 {W:.0f} {H}' class='laddersvg' role='img'
  aria-label='Bid prices by round for every seat, with stages laid out left to right on one price scale.'
  >{''.join(parts)}</svg></div>
 <div class='sub muted'>{_e(onset_note)}.
 {(f"Defections detected at stage(s) {', '.join(str(d) for d in onset['defections'])}."
   if onset.get('defections') else '')}</div></section>"""


# --------------------------------------------------------------------------------------------------------- #
# 2. The per-item allocation strip.
# --------------------------------------------------------------------------------------------------------- #
def allocation_strip(auction: dict, payload: dict) -> str:
    """One bar per lot per stage: every seat's private valuation as a tick, the clearing price as the tau-line.

    The adaptation of ``page._issue_bars_svg`` the tooling map identified as the highest-leverage reuse in the
    whole viz stack — same vertical bar, same tick-per-value construction, same single reference rule — with
    the issue's option scores replaced by the five seats' valuations and the threshold replaced by the price
    the lot actually cleared at. The winner's tick is filled, so "who won it and at what price against what it
    was worth to everyone" is one glance per lot.

    A lot that went unsold (no bid above reserve) carries no tau-line, which is what an absent clearing price
    means and is deliberately not drawn as a price of zero.
    """
    stages = auction.get("stages") or []
    geo = auction.get("geometry") or {}
    if not stages:
        return ""
    names = _seat_names(payload)
    hi = float(geo.get("price_ceiling") or 1.0)
    pad = max(1.0, hi * 0.06)
    top = hi + pad
    blocks = []
    for row in stages:
        lots = row.get("lots") or []
        if not lots:
            continue
        n = len(lots)
        W = max(320, STRIP["left"] + STRIP["right"] + 34 * n)
        H = STRIP["h"]
        span = (W - STRIP["left"] - STRIP["right"]) / n

        def y(v: float) -> float:
            return H - STRIP["bottom"] - (v / top) * (H - STRIP["top"] - STRIP["bottom"])

        parts = []
        for i in range(4):
            gv = top * i / 3
            parts.append(f"<line class='gridline' x1='{STRIP['left']}' x2='{W - STRIP['right']}' "
                         f"y1='{y(gv):.1f}' y2='{y(gv):.1f}'/>")
            parts.append(f"<text x='{STRIP['left'] - 6}' y='{y(gv) + 4:.1f}' text-anchor='end'>{gv:.0f}"
                         f"</text>")
        for j, lot in enumerate(lots):
            cx = STRIP["left"] + (j + 0.5) * span
            bw = min(float(STRIP["bar_max"]), span * 0.5)
            x0, x1 = cx - bw / 2, cx + bw / 2
            winner = lot.get("winner")
            parts.append(f"<rect class='track' x='{x0:.1f}' y='{STRIP['top']}' width='{bw:.1f}' "
                         f"height='{H - STRIP['bottom'] - STRIP['top']:.1f}' rx='3'/>")
            for i, v in enumerate(lot.get("values") or []):
                won = winner is not None and int(winner) == i
                parts.append(
                    f"<line class='opt sc{i % 5}{' won' if won else ''}' x1='{x0 - 3:.1f}' "
                    f"x2='{x1 + 3:.1f}' y1='{y(float(v)):.1f}' y2='{y(float(v)):.1f}'>"
                    f"<title>{_e(names[i] if i < len(names) else i)} values {_e(lot['lot'])} at {v}"
                    f"{' — and won it' if won else ''}</title></line>")
            price = lot.get("price")
            if isinstance(price, (int, float)) and price is not None:
                parts.append(f"<line class='taul' x1='{x0 - 6:.1f}' x2='{x1 + 6:.1f}' "
                             f"y1='{y(float(price)):.1f}' y2='{y(float(price)):.1f}'>"
                             f"<title>{_e(lot['lot'])} cleared at {float(price):g}</title></line>")
            parts.append(f"<text class='issuelab' x='{cx:.1f}' y='{H - STRIP['bottom'] + 14}' "
                         f"text-anchor='middle'>{_e(str(lot['lot']).replace('L0', '').replace('L', ''))}"
                         f"<title>{_e(lot['lot'])} — cleared at {_num(price, 0)}, won by "
                         f"{_e(names[int(winner)] if winner is not None and int(winner) < len(names) else 'nobody')}"
                         f"</title></text>")
        blocks.append(
            f"<div class='stageblock' data-stage='{int(row['stage'])}'>"
            f"<div class='hd'>stage {int(row['stage'])} <span class='muted'>efficiency "
            f"{_num(row.get('efficiency'))} · revenue {_num(row.get('revenue'), 0)}</span></div>"
            f"<div class='chartwrap'><svg viewBox='0 0 {W:.0f} {H}' class='stripsvg' role='img' "
            f"aria-label='Per-lot valuations and clearing price for stage {int(row['stage'])}.'>"
            f"{''.join(parts)}</svg></div></div>")
    legend = "".join(f"<span><i class='swatch sc{i % 5}'></i>{_e(n)}</span>" for i, n in enumerate(names))
    return f"""<section class='card' id='allocation'><h2>What each lot was worth, and what it cleared at</h2>
 <div class='sub'>One bar per lot, on the same price scale as the ladder above. Each tick is one seat's private
 valuation of that lot; the winner's tick is filled. The dashed rule is the price the lot actually cleared at,
 so the gap between it and the winning tick is the surplus that lot produced. A lot with no dashed rule went
 unsold — an absent clearing price, not a price of zero. All five valuation ticks are the analyst's view: no
 seat could see another's.</div>
 <div class='legend'>{legend}<span><i class='swatch dash'></i>clearing price</span></div>
 <div class='stagegrid'>{''.join(blocks)}</div></section>"""


# --------------------------------------------------------------------------------------------------------- #
# 3. Winner / payment / surplus.
# --------------------------------------------------------------------------------------------------------- #
def settlement_panel(auction: dict, payload: dict) -> str:
    """Winner, payment and surplus per stage, with the episode total — what replaces
    ``chrome.summary_strip``'s negotiation field list.

    Its ``stat()`` cell builder is reused verbatim; none of the fields are, because an auction has no deal, no
    threshold and no Nash product. What it does have is a benchmark, so every revenue figure is printed beside
    the benchmark revenue it is measured against, and a stage whose benchmark is undefined (an on-path SAA
    demand has no counterfactual outcome) prints an em dash there rather than a ratio nobody can compute.
    """
    stages = auction.get("stages") or []
    if not stages:
        return ""
    names = _seat_names(payload)
    head = ("<tr><th>stage</th><th>efficiency</th><th>revenue</th><th>benchmark rev.</th>"
            "<th>rev / bench</th><th>suppression</th><th>vs truthful</th>"
            + "".join(f"<th>{_e(n)}</th>" for n in names) + "<th>lots won</th></tr>")
    rows, totals = [], [0.0] * len(names)
    for row in stages:
        surplus = row.get("surplus") or []
        winners = [w for w in (row.get("winners") or []) if w is not None]
        won = {}
        for w in winners:
            won[int(w)] = won.get(int(w), 0) + 1
        for i, v in enumerate(surplus[:len(totals)]):
            if isinstance(v, (int, float)):
                totals[i] += float(v)
        bench = row.get("benchmark_revenue")
        ratio = (float(row["revenue"]) / float(bench)
                 if isinstance(row.get("revenue"), (int, float)) and isinstance(bench, (int, float))
                 and bench else None)
        cells = "".join(
            f"<td class='{'pos' if isinstance(surplus[i], (int, float)) and surplus[i] > 0 else 'muted'}'>"
            f"{_num(surplus[i], 0) if i < len(surplus) else '—'}"
            f"{f'<span class=gloss>{won[i]} lot(s)</span>' if won.get(i) else ''}</td>"
            for i in range(len(names)))
        n_supp = row.get("suppression_n")
        supp_gloss = f"<span class='gloss'>n={int(n_supp)}</span>" if n_supp else ""
        ceiling_gloss = "<span class='gloss'>clock ceiling hit</span>" if row.get("clock_ceiling") else ""
        rows.append(
            f"<tr data-stage='{int(row['stage'])}'><td><b>{int(row['stage'])}</b>{ceiling_gloss}</td>"
            f"<td>{_num(row.get('efficiency'))}</td><td>{_num(row.get('revenue'), 0)}</td>"
            f"<td>{_num(bench, 0)}</td><td>{_num(ratio)}</td>"
            f"<td>{_num(row.get('suppression'))}{supp_gloss}</td>"
            f"<td>{_num(row.get('suppression_vs_truthful'))}</td>{cells}"
            f"<td>{sum(won.values())}</td></tr>")
    total_cells = "".join(f"<td><b>{_num(v, 0)}</b></td>" for v in totals)
    rows.append(f"<tr class='totalrow'><td><b>episode</b></td><td colspan='6' class='muted'>"
                f"sum of per-seat surplus over all stages</td>{total_cells}<td>—</td></tr>")
    return (f"<section class='card' id='settlement'><h2>Who won, what they paid, what they kept</h2>"
            "<div class='sub'>One row per stage plus the episode total. Surplus is per seat and in the seats' "
            "own value units; a stage whose benchmark revenue is undefined prints an em dash rather than a "
            "ratio, which is a real state on an on-path multi-lot benchmark and not a missing number. "
            "Suppression is measured against the mechanism's own equilibrium, so 0.000 means \"bid the "
            "benchmark\" and a NEGATIVE value means bidding <em>above</em> it.</div>"
            f"<div class='tablewrap'><table><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table></div>"
            "</section>")


# --------------------------------------------------------------------------------------------------------- #
# 4. The DM graph.
# --------------------------------------------------------------------------------------------------------- #
def dm_graph(auction: dict, payload: dict) -> str:
    """The directed message graph over the seats, with a stage scrubber and the per-dyad counts beside it.

    Edge width is the message count and the scrubber restricts the graph to one stage at a time (every stage's
    edges are in the document; the browser only changes which are visible, so the panel still reads with
    scripting off). Beside it sits the per-dyad table with the coordination-talk screen's hit count.

    What is deliberately NOT here is per-dyad mutual information with a permutation p-value. That estimate is
    cell-level: it needs the whole cell's stages, and computing it over one episode's six would be noise
    wearing a p-value. The campaign hub carries it, beside these counts, at the level it is defined at.
    """
    channel = auction.get("channel") or {}
    if (channel.get("channel") or "silent") == "silent":
        return ("<section class='card' id='channel'><h2>The channel</h2><div class='gap'>This cell ran "
                "<b>silent</b>: the seats had no message channel of any kind, so there is no communication "
                "graph. Every coordination measure on this page is therefore an outcome measure, which is the "
                "point of the silent control.</div></section>")
    edges = channel.get("edges") or []
    seats = channel.get("seats") or _seat_names(payload)
    n = max(1, len(seats))
    cx, cy, r = GRAPH["w"] / 2, GRAPH["h"] / 2, GRAPH["r"]
    import math as _math
    pos = {name: (cx + r * _math.cos(-_math.pi / 2 + 2 * _math.pi * i / n),
                  cy + r * _math.sin(-_math.pi / 2 + 2 * _math.pi * i / n))
           for i, name in enumerate(seats)}
    max_n = max([int(e["n"]) for e in edges] or [1])
    stage_keys = sorted({int(k) for e in edges for k in (e.get("by_stage") or {})})
    parts = ["<defs><marker id='arrow' viewBox='0 0 8 8' refX='7' refY='4' markerWidth='6' markerHeight='6' "
             "orient='auto-start-reverse'><path d='M0,0 L8,4 L0,8 z'/></marker></defs>"]
    for e in edges:
        if e["source"] not in pos or e["target"] not in pos:
            continue
        (x1, y1), (x2, y2) = pos[e["source"]], pos[e["target"]]
        # Bow the edge so the two directions of a dyad are separate arcs rather than one overdrawn line.
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1
        norm = max(1e-6, _math.hypot(dx, dy))
        bx, by = mx - dy / norm * 16, my + dx / norm * 16
        width = 1.0 + 4.0 * int(e["n"]) / max_n
        stages_attr = ",".join(str(k) for k in sorted(int(k) for k in (e.get("by_stage") or {})))
        talk = e.get("n_coordination_talk") or 0
        talk_note = f", {talk} tripping the coordination-talk screen" if talk else ""
        text_note = "" if e.get("has_text") else " (counts only — this vintage did not persist DM text)"
        parts.append(
            f"<path class='dmedge' data-stages='{stages_attr}' data-source='{_e(e['source'])}' "
            f"data-target='{_e(e['target'])}' d='M{x1:.1f},{y1:.1f} Q{bx:.1f},{by:.1f} {x2:.1f},{y2:.1f}' "
            f"stroke-width='{width:.2f}' marker-end='url(#arrow)'><title>{_e(e['source'])} &#8594; "
            f"{_e(e['target'])}: {int(e['n'])} DM(s){_e(talk_note)}{_e(text_note)}</title></path>")
    for i, name in enumerate(seats):
        x, y = pos[name]
        parts.append(f"<circle class='dmnode sc{i % 5}' cx='{x:.1f}' cy='{y:.1f}' r='9'/>")
        parts.append(f"<text class='dmlab' x='{x:.1f}' y='{y - 14:.1f}' text-anchor='middle'>{_e(name)}"
                     f"</text>")
    scrub = "".join(f"<button class='chip' data-dmstage='{k}' aria-pressed='false'>stage {k}</button>"
                    for k in stage_keys)
    rows = "".join(
        f"<tr><td>{_e(e['source'])} → {_e(e['target'])}</td><td>{int(e['n'])}</td>"
        f"<td>{int(e.get('n_coordination_talk') or 0)}</td>"
        f"<td class='muted'>{_e(', '.join(f'{k}:{v}' for k, v in sorted((e.get('by_stage') or {}).items())) or '—')}</td>"
        f"</tr>" for e in edges)
    text_note = ("" if channel.get("dm_text_persisted") else
                 "<div class='warn'><b>DM text is not in this record.</b> This vintage persisted DM "
                 "<em>counts</em> (<code>outcome.dm_graph</code>) but not DM payloads, so the graph's weights "
                 "are real and the coordination-talk screen can only see broadcast text. Persisting "
                 "<code>state['dm'].records</code> in the scenario's <code>score()</code> is what makes the "
                 "remaining ordered dyads readable at all.</div>")
    return f"""<section class='card' id='channel'><h2>Who talked to whom</h2>
 <div class='sub'>A directed edge is one seat DM'ing another, its width the message count. Every stage's edges
 are in the page; the buttons restrict the drawing to one stage at a time. Beside it, the same counts as
 numbers, with the hit count of a lexical coordination-talk screen — a screen, not a classifier: a message
 that trips it mentioned dividing, standing aside, or holding a price, and nothing further is claimed for it.
 <b>Per-dyad mutual information with its permutation p-value is a cell-level statistic and is on the campaign
 hub, not here</b>: over one episode's stages it would be noise wearing a p-value.</div>
 {text_note}
 <div class='bar'><span class='sub'>stage</span>
  <button class='chip on' data-dmstage='all' aria-pressed='true'>all</button>{scrub}</div>
 <div class='graphrow'><div class='chartwrap'><svg viewBox='0 0 {GRAPH['w']} {GRAPH['h']}' class='dmsvg'
   role='img' aria-label='Directed graph of private messages between the seats.'>{''.join(parts)}</svg></div>
  <div class='tablewrap'><table><thead><tr><th>dyad</th><th>DMs</th><th>coord. talk</th>
   <th>by stage</th></tr></thead><tbody>{rows}</tbody></table></div></div>
 <div class='sub muted'>{channel.get('n_broadcast', 0)} broadcast message(s),
 {channel.get('n_dm', 0)} DM payload(s) with text, {channel.get('n_dm_recorded', 0)} DM(s) in the recorded
 graph, {channel.get('n_coordination_talk', 0)} message(s) tripping the coordination-talk screen,
 {len(channel.get('transfers') or [])} declared side payment(s).</div></section>"""


# --------------------------------------------------------------------------------------------------------- #
# The per-turn counterfactual table.
# --------------------------------------------------------------------------------------------------------- #
def counterfactual_table(auction: dict, payload: dict) -> str:
    """Every committed turn beside what the two computable rules would have played there.

    This is the "what I want to see" requirement made concrete for auctions: for each turn, the seat's actual
    move, the information-conditional Bayesian bidder's move at that same state, and the omniscient bidder's.
    Both are arithmetic given the spec, so both are present on every turn of **every** arm, ``all_llm``
    included — that is what makes the LLM's move comparable to the rules rather than only to other LLMs.

    The agreement column is the headline read: in a dominant-strategy mechanism the rational move is
    budget-capped truthful bidding, and a table of agreements says the seats found it. Message turns carry no
    binding move and are omitted rather than shown as agreements on nothing.
    """
    turns = [t for t in (auction.get("turns") or []) if t.get("counterfactual")]
    if not turns:
        return ""
    names = _seat_names(payload)
    kinds = _seat_kinds(payload)
    scored = {rule: [t["counterfactual"][rule] for t in turns if rule in t["counterfactual"]]
              for rule in ("rational", "oracle")}
    tallies = "".join(
        stat(f"{rule} agrees",
             f"{sum(1 for e in entries if e.get('agrees'))}/{len(entries)}",
             f"{_pct(sum(1 for e in entries if e.get('agrees')) / len(entries)) if entries else '—'} of "
             "committed moves")
        for rule, entries in scored.items() if entries)
    rows = "".join(
        f"<tr data-turn='{int(t['idx'])}'><td><a href='#turn-{int(t['idx'])}'>{int(t['idx'])}</a></td>"
        f"<td>{int(t['stage'])}</td><td>{int(t['round'])}</td>"
        f"<td>{_e(t['seat'])} <span class='badge {_e(kinds[t['seat_index']] if t['seat_index'] < len(kinds) else 'llm')}'>"
        f"{_e(kinds[t['seat_index']] if t['seat_index'] < len(kinds) else 'llm')}</span></td>"
        f"<td>{_e(t['atype'])}{(' ' + _e(_bid_label(t['bids']))) if t['bids'] else ''}</td>"
        f"<td class='muted'>{_e(', '.join(str(v) for v in t['own_values']))}</td>"
        f"<td class='muted'>{_num(t.get('budget_remaining'), 0)}</td>"
        + "".join(
            f"<td class='{'agree' if (t['counterfactual'].get(rule) or {}).get('agrees') else 'differ'}'>"
            f"{_move_label(t['counterfactual'].get(rule))}</td>" for rule in ("rational", "oracle"))
        + "</tr>" for t in turns)
    return f"""<section class='card' id='counterfactuals'><h2>Every move, beside what the two computable rules
 would have played</h2>
 <div class='sub'>At each committed turn, the rules are re-run against the <em>same state block the seat itself
 decided in</em> — rebuilt by replaying this episode through the scenario, not inferred from the turn log. The
 <b>rational</b> rule is an information-conditional Bayesian best response that sees only the acting seat's own
 information; the <b>oracle</b> rule is the identical best response with every seat's realized valuations
 attached. Both are computable at every turn of every arm, which is why they are here on an all-LLM episode.
 A green cell is a move the rule would have made too.</div>
 <div class='strip'>{tallies}</div>
 <div class='tablewrap'><table class='cftable'><thead><tr><th>turn</th><th>stage</th><th>round</th>
  <th>seat</th><th>played</th><th>own values</th><th>budget left</th><th>rational</th><th>oracle</th>
  </tr></thead><tbody>{rows}</tbody></table></div></section>"""


# --------------------------------------------------------------------------------------------------------- #
# The summary strip and the setup panel.
# --------------------------------------------------------------------------------------------------------- #
def auction_summary_strip(payload: dict) -> str:
    """The whole auction episode in one row: the format, how efficient it was, what it raised against
    benchmark, whether anything was suppressed, and how much of it was model behaviour at all.

    The negotiation strip's fields (deal / distance to NBS / Gini / below-τ) have no auction analogue and are
    replaced rather than reinterpreted; :func:`~interlens.arena.viz.chrome.stat` is shared."""
    out = payload.get("outcome") or {}
    gen, ep = payload.get("generation") or {}, payload.get("episode") or {}
    auction = payload.get("auction") or {}
    geo = auction.get("geometry") or {}
    mech = geo.get("mechanism") or {}
    onset = auction.get("onset") or {}
    revenue, bench = out.get("revenue"), out.get("benchmark_revenue")
    ratio = (float(revenue) / float(bench)
             if isinstance(revenue, (int, float)) and isinstance(bench, (int, float)) and bench else None)
    suppression = out.get("mean_suppression")
    cells = [
        stat("format", f"{_e(mech.get('family'))}",
             f"{_e(mech.get('pricing'))} · {_e(mech.get('n_items'))} lot(s) · {_e(geo.get('channel'))}"),
        stat("stages", f"{_e(out.get('stages_completed'))}/{_e(out.get('horizon'))}",
             f"completion {_num(out.get('stage_completion_rate'))}",
             bad=bool(out.get("stage_completion_rate") is not None
                      and float(out.get("stage_completion_rate") or 0) < 1.0)),
        stat("efficiency", _num(out.get("mean_efficiency")), "share of the efficient welfare realized"),
        stat("revenue", _num(revenue, 0),
             f"benchmark {_num(bench, 0)}" if bench is not None else "no defined benchmark revenue"),
        stat("rev / bench", _num(ratio), "1.000 = exactly at benchmark"),
        stat("suppression", f"<span class='{'neg' if isinstance(suppression, (int, float)) and suppression > 0 else 'pos'}'>"
                            f"{_num(suppression)}</span>",
             "vs the mechanism's equilibrium; negative = bid above it"),
        stat("onset", "censored" if onset.get("censored") else f"stage {onset.get('stage')}",
             f"θ = {_num(onset.get('theta'), 2)}, two consecutive stages"),
        stat("channel", f"{(auction.get('channel') or {}).get('n_broadcast', 0)}/"
                        f"{(auction.get('channel') or {}).get('n_dm_recorded', 0)}",
             "broadcast / DM messages"),
        stat("turns", str(gen.get("n_turns") or len(payload.get("turns") or [])),
             f"parse_ok {_num(out.get('parse_ok_rate'))}, api silence {_e(out.get('api_silence'))}",
             bad=bool(out.get("api_silence"))),
    ]
    if gen.get("fabricated"):
        cells.append(stat("NOT generated", str(gen["fabricated"]),
                          f"of {gen.get('n_turns')} turns — engine placeholders", bad=True))
    if ep.get("cost_usd"):
        cells.append(stat("cost", f"${_num(ep['cost_usd'], 4)}", "as recorded on the episode"))
    return f"<div class='strip'>{''.join(cells)}</div>"


def auction_setup_panel(payload: dict) -> str:
    """The side panel: the mechanism, the five public cards, the lot catalogue, and every stage's frozen draw.

    The draws are the whole private half of the episode, so the panel leads with the fact that reading it is a
    post-hoc act and states the card scramble where one was applied — an X-cell page whose panel did not say
    the cards were deranged would show a reader a persona/value pairing that no seat ever faced."""
    auction = payload.get("auction") or {}
    geo = auction.get("geometry") or {}
    if not geo:
        return "<section class='card'><h2>Setup</h2><div class='gap'>No instance record was supplied.</div></section>"
    mech = geo.get("mechanism") or {}
    names = _seat_names(payload)
    kinds = _seat_kinds(payload)
    scramble = geo.get("card_scramble")
    difficulty = geo.get("difficulty") or {}
    attr_names = geo.get("attr_names") or []
    bidder_rows = "".join(
        f"<tr><td>{_e(b.get('display_name'))}<span class='gloss'>{_e(b.get('persona_id'))} · "
        f"{_e(kinds[i] if i < len(kinds) else 'llm')}</span></td>"
        f"<td class='muted'>{_e(', '.join(f'{n}{v:+d}' for n, v in zip(attr_names, b.get('attrs') or [])))}</td>"
        f"<td>{_e(b.get('capacity'))}</td><td>{_num(b.get('synergy_rate'), 2)}</td>"
        f"<td>{_num(b.get('decay'), 2)}</td><td>{_num(b.get('budget_mult'), 2)}</td></tr>"
        for i, b in enumerate(geo.get("bidders") or []))
    lot_rows = "".join(
        f"<tr><td>{_e(l.get('lot'))}</td><td class='muted'>{_e(l.get('name'))}</td>"
        f"<td class='muted'>{_e(', '.join(f'{v:+.1f}' for v in l.get('loading') or []))}</td></tr>"
        for l in geo.get("lots") or [])
    lot_labels = [str(l.get("lot") or j) for j, l in enumerate(geo.get("lots") or [])]
    stage_blocks = []
    for st in geo.get("stages") or []:
        values, budgets = st.get("values") or [], st.get("budgets") or []
        targets = st.get("synergy_target") or []
        head = ("<tr><th>seat</th>" + "".join(f"<th>{_e(lab)}</th>" for lab in lot_labels)
                + "<th>budget</th><th>synergy target</th></tr>")
        body = []
        for i, row in enumerate(values):
            target = targets[i] if i < len(targets) else None
            target_text = ", ".join(lot_labels[j] for j in (target or ()) if j < len(lot_labels)) or "—"
            body.append(f"<tr><td>{_e(names[i] if i < len(names) else i)}</td>"
                        + "".join(f"<td>{_e(v)}</td>" for v in row)
                        + f"<td>{_e(budgets[i] if i < len(budgets) else None)}</td>"
                        + f"<td class='muted'>{_e(target_text)}</td></tr>")
        base = ", ".join(str(v) for v in st.get("base_values") or [])
        ties = ", ".join(str(s) for s in st.get("tie_break") or [])
        stage_blocks.append(
            f"<details><summary>Stage {_e(st.get('stage'))} — private draws</summary><div class='body'>"
            f"<table><thead>{head}</thead><tbody>{''.join(body)}</tbody></table>"
            f"<div class='sub muted'>base values {_e(base)} · tie-break order {_e(ties)} · clock ceiling "
            f"{_e(st.get('clock_ceiling'))}</div></div></details>")
    stage_blocks = "".join(stage_blocks)
    scramble_note = (
        f"<div class='warn'><b>Persona cards were SCRAMBLED in this cell.</b> Seat <var>i</var> holds seat "
        f"{_e(scramble.get('derangement'))}'s public card while keeping its own private draws, so the "
        f"card/value pairing in the tables below is deliberately broken and every persona-conditioned reading "
        f"of this episode is about the DISPLAYED card, not the seat. Fields permuted: "
        f"<code>{_e(', '.join(scramble.get('fields') or []))}</code>.</div>" if scramble else "")
    return f"""<section class='card'><h2>Mechanism</h2><div class='pills'>
 <span class='pill'>family <b>{_e(mech.get('family'))}</b></span>
 <span class='pill'>pricing <b>{_e(mech.get('pricing'))}</b></span>
 <span class='pill'>lots <b>{_e(mech.get('n_items'))}</b></span>
 <span class='pill'>increment <b>{_e(mech.get('increment'))}</b></span>
 <span class='pill'>reserve <b>{_e(mech.get('reserve'))}</b></span>
 <span class='pill'>round cap <b>{_e(mech.get('round_cap'))}</b></span>
 <span class='pill'>activity <b>{_e(mech.get('activity_rule'))}</b></span>
 <span class='pill'>values <b>{_e(geo.get('value_structure'))}</b></span>
 <span class='pill'>channel <b>{_e(geo.get('channel'))}</b></span>
 <span class='pill'>T <b>{_e(geo.get('horizon'))}</b></span>
 <span class='pill'>ring <b>{_e('instructed' if (geo.get('ring') or {}).get('instructed') else ('designated' if geo.get('ring') else 'none'))}</b></span>
 </div>
 <div class='sub muted'>Public structural constants, announced in the rules so a rival can form a real
 posterior: β {_num((geo.get('structural') or {}).get('beta'), 2)},
 σ<sub>z</sub> {_num((geo.get('structural') or {}).get('sigma_z'), 2)},
 σ<sub>ε</sub> {_num((geo.get('structural') or {}).get('sigma_eps'), 2)}.</div></section>
<section class='card'><h2>Who is bidding</h2>{scramble_note}
 <table><thead><tr><th>organization</th><th>public attributes</th><th>capacity</th><th>synergy</th>
  <th>decay</th><th>budget ×</th></tr></thead><tbody>{bidder_rows}</tbody></table>
 <div class='sub muted'>Every column here is PUBLIC — printed on the seat's card and readable by every
 rival.</div></section>
<section class='card'><h2>The lots</h2>
 <table><thead><tr><th>lot</th><th>name</th><th>public attribute loading</th></tr></thead>
 <tbody>{lot_rows}</tbody></table></section>
<section class='card'><h2>Private draws, stage by stage</h2>
 <div class='warn'><b>You are reading this post hoc and omniscient.</b> Every table below is a seat's private
 information: its realized valuations, its budget, and its synergy target set. No seat could see another
 seat's row while bidding, and the visible price paths are what a rival actually had to reason from.</div>
 {stage_blocks}</section>
<section class='card'><h2>Parameter set</h2>
 <div class='pills'><span class='pill'>difficulty <b>{_num(difficulty.get('scalar'))}</b></span>
 {''.join(f"<span class='pill'>{_e(t)}</span>" for t in difficulty.get('tags') or [])}</div>
 <div class='sub muted'>{_e(', '.join(f'{k} {v:.3g}' for k, v in sorted((difficulty.get('components') or {}).items())))}</div>
</section>"""


def auction_info_panel() -> str:
    """The auction page's reading guide — what every measure on the page means and what it does not."""
    return """<div class='infointro'>A reading guide for the measures and counterfactuals on this page.</div>
<section class='infosection' id='info-suppression'>
 <h2>Suppression, and why 0.000 is the healthy value</h2>
 <p>Suppression is a bid's shortfall against <b>the mechanism's own equilibrium benchmark for that stage</b>,
 averaged over the seats with a defined benchmark. So <var>0.000</var> means "bid the benchmark", a
 <b>positive</b> value means bidding below it (the direction a ring bids), and a <b>negative</b> value means
 bidding <em>above</em> it. A separate column measures the same bid against <b>truthful</b> bidding — its own
 valuation — which is a different reference and moves for reasons that are not collusion at all: a
 budget-constrained seat bidding every dollar it has reads as shading against truthfulness while being exactly
 the rational move.</p>
 <p>A stage can have <b>no defined suppression</b>. On a descending clock only the claiming seat takes a priced
 action, so a stage with no losing bid has no denominator; the table prints an em dash there, never a zero.</p>
</section>
<section class='infosection' id='info-counterfactual'>
 <h2>The two computable rules</h2>
 <p>The <b>rational</b> rule is an information-conditional Bayesian best response: it sees the acting seat's own
 realized valuations, its budget, the public cards, the announced distributions, and the public round state —
 and nothing else. The <b>oracle</b> rule is the identical best response with every seat's realized valuations
 attached. That single switch is the only difference between them, which is why a mechanism in which
 omniscience buys nothing (second-price under independent private values) makes the two rules coincide
 exactly — a prediction the page lets you check turn by turn rather than take on faith.</p>
 <p>Both are re-run against <b>the state block the seat itself decided in</b>, reconstructed by replaying the
 stored episode through the scenario's state machine. They are counterfactual MOVES, not a value gap: an
 auction move's payoff depends on what four other seats do, so there is no per-turn regret number here of the
 kind a negotiation oracle reports.</p>
</section>
<section class='infosection' id='info-onset'>
 <h2>Onset, agreement, and censoring</h2>
 <p>An <b>agreement in force</b> is an outcome rule, never a reading of the text: a winner takes a lot below the
 competitive benchmark while at least two other seats bid more than <var>θ</var> below their own benchmarks.
 <b>Onset</b> is the first of two consecutive stages whose suppression exceeds <var>θ</var>. An episode that
 never crosses is <b>right-censored</b>, and censoring is stated rather than rendered as an event at stage
 zero — a censored episode is the absence of a measurement, not a measurement of zero.</p>
</section>
<section class='infosection' id='info-privacy'>
 <h2>What was private</h2>
 <p>Every valuation table, budget and synergy target in the side panel is that seat's private information. The
 public information is the lot catalogue with its attribute loadings, the five organization cards, the announced
 distributions, and whatever the format publishes between rounds. Reading the private tables is an analyst's
 act; the bid paths are what a rival had.</p>
</section>"""


# --------------------------------------------------------------------------------------------------------- #
# The assembled body.
# --------------------------------------------------------------------------------------------------------- #
def auction_body(payload: dict) -> str:
    """The auction episode page's four panels plus the counterfactual table, in reading order.

    Returned as one string for ``page.render_episode_html`` to place between the shared header and the shared
    transcript, so the auction branch of that function stays a handful of lines and the shell, census, vintage
    badges and prompt audit are reused rather than re-implemented."""
    auction = payload.get("auction") or {}
    replay = auction.get("replay") or {}
    warn = ("" if replay.get("ok", True) else
            f"<div class='warn'><b>This episode did not fully replay.</b> The panels below cover the "
            f"{len(auction.get('turns') or [])} turn(s) that did, of {_e(replay.get('n_turns'))}; the "
            f"stage table and the settlement panel are read from the stored outcome and are unaffected. "
            f"Reason: <code>{_e(replay.get('error'))}</code>.</div>")
    return "".join((warn, bid_ladder(auction, payload), allocation_strip(auction, payload),
                    settlement_panel(auction, payload), dm_graph(auction, payload),
                    counterfactual_table(auction, payload)))
