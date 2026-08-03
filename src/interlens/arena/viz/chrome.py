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
# [rational_agents: viz-ux] 2026-08-03

"""The shell every page wears, and the wire form of the payload it carries.

Two things live here because both are shared by all three page kinds and neither belongs to any one of them.

**The chrome** — the sticky top bar (run identity, episode navigation, the quick read, theme and help buttons)
and the keyboard-help overlay. Navigation is rendered as plain links and a ``<select>``, so it works with
scripting off; the browser layer only adds the shortcuts.

Where the navigation goes is marked with :data:`NAV_MARKER` rather than filled in at render time. A page cannot
know its own siblings — ``render_episode_html`` is handed one payload — while the exporter, which writes the whole
run, knows all of them but only after the last page is rendered. So the exporter writes the pages and then
replaces one comment in each. A page rendered on its own keeps the comment, which is invisible.

**The wire payload** — :func:`slim_payload` replaces every turn's inlined prompt view with indices into one
de-duplicated message pool. A six-seat thirty-turn episode repeats its system prompt on every turn and re-states
the whole history in each view, so the same bytes were being shipped dozens of times: on a representative
30-turn page the pool takes the embedded data from 566 KB to 332 KB with nothing removed. The returned dict is a
render-time copy — :meth:`RunDir.payload`'s own return value is untouched, because it is a public API whose
consumers expect real message dicts.
"""
from __future__ import annotations

import html
import math
from typing import Any

#: Replaced by the exporter with this page's prev/next links and episode picker; invisible if never replaced.
NAV_MARKER = "<!--interlens-viz-nav-->"


def _e(x: Any) -> str:
    """HTML-escape a value; ``None`` renders as an em dash so an empty cell is visibly empty."""
    return html.escape("—" if x is None else str(x))


def _num(v: Any, digits: int = 3) -> str:
    """Format a number for a cell, em-dash for a non-number, so a missing metric never reads as zero."""
    return f"{v:.{digits}f}" if isinstance(v, (int, float)) and not isinstance(v, bool) else "—"


# ------------------------------------------------------------------------------------ wire payload --
def slim_payload(payload: dict) -> dict:
    """A copy of ``payload`` whose per-turn prompt views are indices into a shared ``msgpool``.

    Identical ``(role, content)`` messages are pooled once and every view becomes a list of integers, which the
    browser turns back into messages on demand (``viewOf``). Purely a transport change: the rendered page shows
    exactly the same text, and any turn that carries no view keeps its ``None``. Comparison payloads carry two
    sides, so both are slimmed into ONE pool — the two episodes of a seat swap share a system prompt and most of
    their history, which is precisely where the duplication is worst."""
    pool: list[list[str]] = []
    seen: dict[tuple, int] = {}

    def intern(msg: dict) -> int:
        key = (msg.get("role"), msg.get("content"))
        if key not in seen:
            seen[key] = len(pool)
            pool.append([key[0], key[1]])
        return seen[key]

    def slim_side(side: dict) -> dict:
        turns = []
        for t in side.get("turns") or []:
            view = t.get("view")
            turns.append({**t, "view": [intern(m) for m in view]} if view else t)
        return {**side, "turns": turns}

    if payload.get("kind") == "compare":
        out = {**payload, "left": slim_side(payload["left"]), "right": slim_side(payload["right"])}
    else:
        out = slim_side(payload)
    out["msgpool"] = pool
    return out


# ------------------------------------------------------------------------------------------ chrome --
def topbar(brand: str, brand_href: str | None, quick: str = "", *, brand_title: str = "",
           nav: bool = True) -> str:
    """The sticky top bar: run identity on the left, the navigation slot, the quick read, theme and help.

    ``brand`` names the run; ``brand_href`` links it to the run index, or is ``None`` on the index itself, where
    there is nothing above to go up to. ``quick`` is the pre-rendered stat run — the two or three numbers a reader
    wants without scrolling. The navigation slot is :data:`NAV_MARKER`, omitted entirely when ``nav`` is false
    (the run index has no siblings to walk)."""
    brand_html = (f"<a class='brand' href='{_e(brand_href)}' data-nav='index' title='{_e(brand_title or brand)}'>"
                  f"&#8592; {_e(brand)}</a>" if brand_href else
                  f"<span class='brand' title='{_e(brand_title or brand)}'>{_e(brand)}</span>")
    return (f"<header class='topbar'>"
            f"{brand_html}"
            f"{NAV_MARKER if nav else ''}"
            f"<span class='spacer'></span>"
            f"<span class='quick'>{quick}</span>"
            "<button id='theme-toggle' class='iconbtn' title='Switch theme' aria-label='Switch theme'>&#9790;</button>"
            "<button id='help-toggle' class='iconbtn' title='Keyboard shortcuts (?)' aria-label='Keyboard shortcuts'>?</button>"
            "</header>")


def help_overlay(extra: str = "") -> str:
    """The keyboard-help overlay. Its table body is filled by the browser layer from the SAME binding list the
    handler uses, so a shortcut cannot exist without being documented here."""
    return ("<div id='help' hidden role='dialog' aria-modal='true' aria-label='Keyboard shortcuts'>"
            "<div class='panel'><h2>Keyboard shortcuts</h2>"
            "<table><tbody></tbody></table>"
            f"{extra}"
            "<div class='bar'><button data-close>Close</button>"
            "<span class='sub muted'>Shortcuts are ignored while you are typing in a box.</span></div>"
            "</div></div>")


def nav_group(rows: list[dict], position: int, *, label_key: str = "label") -> str:
    """The prev/next links and episode picker for the page at ``position`` in ``rows``.

    Written by the exporter into :data:`NAV_MARKER` once every page of the run is known. Prev/next are real
    ``<a href>`` elements (so they work without scripting, and the keyboard bindings just follow them); the picker
    is a ``<select>`` of every sibling page. A page at either end gets a disabled link rather than a missing one,
    so the control row never changes width as a reader walks the run."""
    def link(rel: str, target: int, glyph: str, what: str) -> str:
        if 0 <= target < len(rows):
            r = rows[target]
            return (f"<a class='iconbtn' data-nav='{rel}' href='{_e(r['href'])}' "
                    f"title='{what}: {_e(r.get(label_key))}'>{glyph}</a>")
        return f"<a class='iconbtn disabled' aria-disabled='true' title='no {what.lower()}'>{glyph}</a>"

    options = "".join(
        f"<option value='{_e(r['href'])}'{' selected' if i == position else ''}>{_e(r.get(label_key))}</option>"
        for i, r in enumerate(rows))
    return (f"<span class='navgrp'>{link('prev', position - 1, '&#8249;', 'Previous')}"
            f"<select id='ep-picker' aria-label='jump to another page of this run'>{options}</select>"
            f"{link('next', position + 1, '&#8250;', 'Next')}"
            f"<span class='pos'>{position + 1}/{len(rows)}</span></span>")


def inject_nav(page_html: str, nav: str) -> str:
    """Put a page's navigation into its top bar. A no-op on a page that carries no marker."""
    return page_html.replace(NAV_MARKER, nav, 1)


# ------------------------------------------------------------------------------ the summary strip --
def distance_to_nbs(payload: dict) -> float | None:
    """How far the deal that closed sits from the Nash bargaining solution, in the chart's own plane.

    Euclidean distance in the two scale-invariant coordinates the frontier chart plots — joint welfare (mean
    normalized surplus) and the worst-off party's normalized surplus — between the agreed deal and the NBS deal.
    ``None`` when no deal closed or the instance carries no solution set. It is a *projected* distance by
    construction, like the chart: two deals that differ only along dimensions the projection drops read as
    identical here, which is why the number sits beside the exact per-party table rather than replacing it."""
    game, outcome = payload.get("game") or {}, payload.get("outcome") or {}
    agreed, solutions = outcome.get("deal_index"), (game.get("solutions") or {})
    nbs = solutions.get("nash") or (next(iter(solutions.values()), None))
    if agreed is None or not nbs or not game.get("deals"):
        return None
    d = game["deals"]
    try:
        return math.dist((d["wx"][int(agreed)], d["wy"][int(agreed)]),
                         (d["wx"][int(nbs["index"])], d["wy"][int(nbs["index"])]))
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def stat(key: str, value: str, note: str = "", *, bad: bool = False) -> str:
    """One cell of the summary strip: a small caption, the number, and a line of context under it."""
    return (f"<div class='stat{' bad' if bad else ''}'><div class='k'>{_e(key)}</div>"
            f"<div class='v'>{value}</div><div class='n'>{note}</div></div>")


def summary_strip(payload: dict) -> str:
    """The whole episode in one row: did it close, how good was it, how far from the normative anchor, who was
    left below their threshold, how much of it the engine fabricated, how long it ran, what it cost.

    Replaces the old grid of tiles. Same numbers, a fifth of the vertical space — which matters because it sits
    above the chart, and the chart is what a reader came for."""
    out, game = payload.get("outcome") or {}, payload.get("game") or {}
    gen, ep = payload.get("generation") or {}, payload.get("episode") or {}
    summary = payload.get("annotation_summary") or {}
    ceiling, dist = game.get("ceiling"), distance_to_nbs(payload)
    ir = out.get("n_ir_violations")
    cells = [
        stat("outcome", "deal" if out.get("deal") else "<span class='neg'>no deal</span>",
             _e(out.get("finalized_by")) if out.get("deal") else "nobody agreed"),
        stat("primary", _num(out.get("primary")),
             f"ceiling {_num(ceiling)}" if ceiling is not None else "normalized headline score"),
        stat("dist to NBS", _num(dist) if dist is not None else "—",
             "in the chart's two coordinates" if dist is not None else "no deal closed"),
        stat("joint welfare", _num(out.get("usw"), 1), "sum of surpluses"),
        stat("worst-off", f"<span class='{'pos' if (out.get('esw') or 0) >= 0 else 'neg'}'>"
                          f"{_num(out.get('esw'), 1)}</span>", "min surplus (ESW)"),
        stat("Nash welfare", _num(out.get("nsw_geomean"), 1), "geometric mean"),
        stat("Gini", _num(out.get("gini")), "0 = equal split"),
    ]
    if ir is not None:
        cells.append(stat("below τ", str(ir), _e(", ".join(out.get("ir_violations") or []) or "none"),
                          bad=bool(ir)))
    cells.append(stat("turns", str(gen.get("n_turns") or len(payload.get("turns") or [])),
                      f"{_e(ep.get('rounds_used'))} round(s), {_e(ep.get('tokens_out'))} tok out"))
    if gen.get("fabricated"):
        cells.append(stat("NOT generated", str(gen["fabricated"]),
                          f"of {gen.get('n_turns')} turns — engine placeholders", bad=True))
    if summary.get("total_regret") is not None:
        cells.append(stat("total regret", _num(summary.get("total_regret"), 1),
                          f"mean {_num(summary.get('mean_regret'), 2)} / turn"))
    if ep.get("cost_usd"):
        cells.append(stat("cost", f"${_num(ep['cost_usd'], 4)}", "as recorded on the episode"))
    return f"<div class='strip'>{''.join(cells)}</div>"


def quick_stats(payload: dict) -> str:
    """The two-or-three-number read that rides in the top bar and stays visible while scrolling."""
    out = payload.get("outcome") or {}
    gen = payload.get("generation") or {}
    bits = [f"<span><span class='k'>outcome</span> <b>{'deal' if out.get('deal') else 'no deal'}</b></span>",
            f"<span><span class='k'>primary</span> <b>{_num(out.get('primary'))}</b></span>",
            f"<span><span class='k'>turns</span> <b>{gen.get('n_turns') or len(payload.get('turns') or [])}</b></span>"]
    if gen.get("fabricated"):
        bits.append(f"<span class='neg'><span class='k'>not generated</span> <b>{gen['fabricated']}</b></span>")
    return "".join(bits)
