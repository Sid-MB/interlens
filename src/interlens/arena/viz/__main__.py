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

"""``python -m interlens.arena.viz`` — the self-documenting CLI for the episode visualizer."""
from __future__ import annotations

import argparse

from .compare import DEFAULT_PAIR_KEY, SELECTIONS
from .export import export_comparison, export_run


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m interlens.arena.viz",
        description="Render arena negotiation episodes as self-contained interactive HTML: every deal placed "
                    "against the exact Pareto frontier and the axiomatic solution points, every turn's action "
                    "beside what a rational agent would have done, and every prompt the models saw. No network "
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
        "--out", required=True, metavar="OUT_DIR",
        help="Output directory for the pages, 'index.html', and 'manifest.json'. Created if absent; existing "
             "pages with the same episode ids are overwritten.")
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
             "counterfactual (what a rational agent would have done, and the per-turn regret). Default "
             "'annotations' is the original scoring pass. Use 'annotations_v1' (written by the oracle "
             "seat-binding fix's re-annotation) to render the CORRECTED counterfactual instead of the "
             "contaminated one; the chosen name is shown on every page so an auditor sees which vintage they are "
             "reading. A name that does not exist yields no counterfactual (reported as missing), not an error.")
    a = ap.parse_args(argv)
    reconstruct = not a.no_reconstruct_views
    if a.run:
        m = export_run(a.run, a.out, limit=a.limit, reconstruct=reconstruct,
                       annotations_dirname=a.annotations_dir)
        print(f"[viz] {m['n_episodes']} episode page(s) -> {m['out_dir']}\n[viz] index: {m['index']}")
        for failure in m["failures"]:
            print(f"[viz] FAILED {failure['episode']}: {failure['error']}")
        return 0
    m = export_comparison(a.compare[0], a.compare[1], a.out, limit=a.limit,
                          pair_fields=tuple(a.pair_key), reconstruct=reconstruct, select=a.select,
                          annotations_dirname=a.annotations_dir)
    r = m["report"]
    print(f"[viz] {m['n_comparisons']} comparison page(s) -> {m['out_dir']}\n[viz] index: {m['index']}")
    print(f"[viz] paired on {r['pair_fields']}: {r['n_left']} left / {r['n_right']} right episodes, "
          f"{r['n_matched_keys']} shared key(s), {r['n_candidate_pairs']} candidate pair(s), "
          f"rendered by select={r['select']}")
    if r["unmatched_left"] or r["unmatched_right"]:
        print(f"[viz] unmatched keys: {len(r['unmatched_left'])} left-only, {len(r['unmatched_right'])} right-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
