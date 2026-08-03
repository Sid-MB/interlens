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

"""Interactive episode visualization: any arena run directory in, self-contained interactive HTML out.

This is the shared renderer for negotiation episodes — the graphical counterpart of
:mod:`interlens.arena.export`, which produces the flat markdown/HTML transcript. Where the exporter answers "what
was said", this answers "was it any good": every deal placed against the exact Pareto frontier and the axiomatic
solution points, every turn's action next to what a rational agent would have done there with the regret between
them, and every prompt the models actually saw, expandable and marked with its provenance.

Swapping a run in is one call — nothing about a run is hard-coded, and the same renderer serves any scenario whose
instances carry a scorable game (episodes without one still render their transcript, minus the game panels).

Two modes:

**Per episode** — one page each, plus a run index::

    from interlens.arena import viz
    viz.export_run("runs/p2_pilot", "products/viz")                 # every episode + index.html
    viz.export_run("runs/p2_pilot", "products/viz", limit=3)        # just the first three

    html = viz.render_episode("runs/p2_pilot", "runs/p2_pilot/episodes/.../abc.json")

**Seat-swap comparison** — the same instance and seed played with a different occupant in one seat::

    viz.export_comparison("runs/p2_X_all_llm", "runs/p2_X_mixed", "products/viz_compare", limit=4)

CLI (self-documenting, ``--help`` on every argument)::

    python -m interlens.arena.viz --run RUN_DIR --out OUT_DIR [--limit N]
    python -m interlens.arena.viz --compare LEFT_RUN RIGHT_RUN --out OUT_DIR [--pair-key instance_id seed arm]

The pages are self-contained: inline CSS and JS, no network requests, no build step, light and dark aware. They
open by double-click from a filesystem path.

**Looking at them from a cluster node** — when the run is on a machine with no browser, drop ``--out`` (the
pages go to a temporary directory) and add ``--serve`` (a stdlib HTTP server on a free port, which prints the URL
and the ``ssh -L`` command to forward it)::

    python -m interlens.arena.viz --run runs/p2_pilot --limit 5 --serve
    python -m interlens.arena.viz --run runs/p2_pilot --serve --port 8899   # a standing tunnel's port

See :func:`~interlens.arena.viz.serve.serve_directory` to do the same from Python.
"""
from __future__ import annotations

from .chrome import NAV_MARKER, distance_to_nbs, inject_nav, nav_group, slim_payload, summary_strip
from .compare import (DEFAULT_PAIR_KEY, SELECTIONS, align, compare_payload, focal_seats, pair_key,
                      pair_runs, score_table)
from .episode import RETRY_SOURCE, RunDir, episode_payload, reconstruct_views, seat_kinds
from .export import export_comparison, export_episode, export_run, render_compare, render_episode
from .geometry import DealGeometry, GameGeometry
from .page import render_compare_html, render_episode_html, render_index_html
from .serve import DEFAULT_HOST, make_server, serve_banner, serve_directory

__all__ = [
    "DEFAULT_HOST", "DEFAULT_PAIR_KEY", "DealGeometry", "GameGeometry", "NAV_MARKER", "RETRY_SOURCE", "RunDir",
    "SELECTIONS", "align", "compare_payload", "distance_to_nbs", "episode_payload", "export_comparison",
    "export_episode", "export_run", "focal_seats", "inject_nav", "make_server", "nav_group", "pair_key",
    "pair_runs", "reconstruct_views", "render_compare", "render_compare_html", "render_episode",
    "render_episode_html", "render_index_html", "score_table", "seat_kinds", "serve_banner", "serve_directory",
    "slim_payload", "summary_strip",
]
