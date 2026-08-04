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

"""``python -m interlens.arena.viz`` — the self-documenting CLI for the episode visualizer."""
from __future__ import annotations

import argparse
import tempfile

from .compare import DEFAULT_PAIR_KEY, SELECTIONS
from .export import export_comparison, export_run
from .serve import serve_directory


def scratch_out_dir() -> str:
    """A fresh throwaway output directory under ``$TMPDIR``, used when ``--out`` is omitted. Not cleaned up on
    exit: the pages must outlive the process for ``--serve`` to hand them to a browser, and a user who renders
    without ``--out`` still gets a printed path they can open or copy later."""
    return tempfile.mkdtemp(prefix="interlens_viz_")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m interlens.arena.viz",
        description="Render arena negotiation episodes as self-contained interactive HTML: every deal placed "
                    "against the exact Pareto frontier and the axiomatic solution points, every turn's action "
                    "beside the post-hoc oracle counterfactual, and every prompt the models saw. No network "
                    "assets, no server — the pages open from a filesystem path.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--run", metavar="RUN_DIR",
        help="Render one page per episode of a single run. RUN_DIR is a run directory holding 'episodes/' "
             "(an EpisodeStore tree) and, ideally, 'instances/' (needed for the frontier, thresholds and "
             "solution points), 'annotations/' (needed for post-hoc oracles such as bestresponse) and "
             "'manifest.json' (records which seats were LLMs and which computable policies). A bare episodes "
             "directory also works, with the game panels omitted.")
    mode.add_argument(
        "--compare", nargs=2, metavar=("LEFT_RUN", "RIGHT_RUN"),
        help="Render seat-swap comparisons: pair each episode of LEFT_RUN with the episode of RIGHT_RUN that "
             "played the same instance, seed, arm and cell, and show the two transcripts side by side with the "
             "divergence point marked and a table of paired deltas. Use it for a rational-policy seat against an "
             "LLM seat (a reverse-mixed run vs its all-LLM baseline) or for any two runs that share an instance "
             "pool. LEFT is the reference; deltas are right minus left.")
    ap.add_argument(
        "--out", default=None, metavar="OUT_DIR",
        help="Output directory for the pages, 'index.html', and 'manifest.json'. Created if absent; existing "
             "pages with the same episode ids are overwritten. OPTIONAL: omit it and the pages go to a fresh "
             "temporary directory under $TMPDIR (printed on startup) — the right choice when you only want to "
             "look, especially with --serve, and do not want to invent a save location for pages you will throw "
             "away. Pass it when the pages are a deliverable you intend to keep or publish.")
    ap.add_argument(
        "--serve", action="store_true",
        help="After rendering, serve the output directory over HTTP and block until Ctrl-C. Use it whenever the "
             "run lives on a machine whose browser you cannot reach — the usual cluster case, where you are "
             "ssh'd into a node and your browser is on your laptop. The startup message prints the URL and the "
             "exact 'ssh -L' port-forward command with this host's name filled in. Omit it to just write the "
             "pages and exit (they are self-contained files, so a copied-back directory opens by double-click).")
    ap.add_argument(
        "--port", type=int, default=0, metavar="N",
        help="With --serve, the TCP port to listen on. Default 0 asks the OS for a free ephemeral port, which is "
             "what you want on a shared node where a fixed port may already be taken. Pass a specific N when you "
             "have a standing 'ssh -L' tunnel on that port and want the same URL every time.")
    ap.add_argument(
        "--limit", type=int, default=None, metavar="N",
        help="Render only the first N episodes (or N matched pairs), in sorted order. Omit to render everything: "
             "a campaign cell can hold hundreds of episodes and each page embeds its whole deal space, so use a "
             "small N (3-10) for a spot check and no limit only when publishing the full set.")
    ap.add_argument(
        "--pair-key", nargs="+", default=list(DEFAULT_PAIR_KEY), metavar="FIELD",
        help="With --compare, the episode fields whose equality defines a matched pair "
             f"(default: {' '.join(DEFAULT_PAIR_KEY)}). Drop 'cell' when comparing two runs that deliberately "
             "differ in sweep cell; drop 'arm' only if you accept mixing protocol arms in one comparison.")
    ap.add_argument(
        "--select", choices=SELECTIONS, default="first",
        help="With --compare and --limit, WHICH matched pairs to render. 'first' takes them in sorted key order "
             "(deterministic but arbitrary — a small sample can easily be all no-deal-on-both and show nothing). "
             "'largest-effect' takes the pairs whose primary score moved most between the two conditions, which is "
             "what you want for a spot check: it shows the cases the aggregate effect is made of. 'deal-flip' "
             "keeps only pairs where a deal closed on exactly one side, ranked by effect — the qualitative "
             "transition. 'most-fabricated' ranks by how many turns the ENGINE fabricated instead of generating "
             "(dropping pairs with none): the right choice for showing what a generation-failure bug did to a run, "
             "e.g. a contaminated cell against its clean re-run. Ranking reads only stored records, so it is free "
             "even over hundreds of pairs.")
    ap.add_argument(
        "--no-reconstruct-views", action="store_true",
        help="Do not re-derive missing prompt views by replaying the episode through the scenario state machine. "
             "Episodes recorded before per-turn view capture then show 'not recorded' instead of a reconstructed "
             "prompt. Use it when you want the pages to contain ONLY bytes that were actually recorded (an audit "
             "of what a model truly saw), or to skip the replay cost on a large export.")
    ap.add_argument(
        "--annotations-dir", default="annotations", metavar="NAME",
        help="Per-run subdirectory to read the post-hoc oracle annotations from — above all the 'bestresponse' "
             "counterfactual (the oracle's best action and its per-turn value gap). In PRIVATE episodes the "
             "standard best-response oracle is omniscient, so this is a hindsight diagnostic. Default "
             "'annotations' is the original scoring pass. Use 'annotations_v1' (written by the oracle "
             "seat-binding fix's re-annotation) to render the CORRECTED counterfactual instead of the "
             "contaminated one; the chosen name is shown on every page so an auditor sees which vintage they are "
             "reading. A name that does not exist yields no counterfactual (reported as missing), not an error.")
    a = ap.parse_args(argv)
    reconstruct = not a.no_reconstruct_views
    out = a.out
    if out is None:
        out = scratch_out_dir()
        print(f"[viz] no --out given; rendering to a temporary directory: {out}")
    if a.run:
        m = export_run(a.run, out, limit=a.limit, reconstruct=reconstruct,
                       annotations_dirname=a.annotations_dir)
        print(f"[viz] {m['n_episodes']} episode page(s) -> {m['out_dir']}\n[viz] index: {m['index']}")
        for failure in m["failures"]:
            print(f"[viz] FAILED {failure['episode']}: {failure['error']}")
    else:
        m = export_comparison(a.compare[0], a.compare[1], out, limit=a.limit,
                              pair_fields=tuple(a.pair_key), reconstruct=reconstruct, select=a.select,
                              annotations_dirname=a.annotations_dir)
        r = m["report"]
        print(f"[viz] {m['n_comparisons']} comparison page(s) -> {m['out_dir']}\n[viz] index: {m['index']}")
        print(f"[viz] paired on {r['pair_fields']}: {r['n_left']} left / {r['n_right']} right episodes, "
              f"{r['n_matched_keys']} shared key(s), {r['n_candidate_pairs']} candidate pair(s), "
              f"rendered by select={r['select']}")
        if r["unmatched_left"] or r["unmatched_right"]:
            print(f"[viz] unmatched keys: {len(r['unmatched_left'])} left-only, "
                  f"{len(r['unmatched_right'])} right-only")
    if a.serve:
        serve_directory(out, port=a.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
