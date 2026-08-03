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

"""Tests for the interactive episode visualizer (``arena/viz/``).

No browser is involved: the pages render every number in Python (the browser script only draws the charts and the
transcript cards), so the assertions are on real structure and real values in the emitted document — the frontier
panel, the reference-point table with each solution concept, the per-turn rational-agent counterfactual, the
expandable prompt panels with their provenance, the comparison score table and divergence point.
"""
from __future__ import annotations

import asyncio
import json
import re
import socket
from pathlib import Path

import numpy as np
import pytest

from interlens.arena import viz
from interlens.arena.engine import EpisodePool
from interlens.arena.negotiation.acceptance import ThresholdOracle
from interlens.arena.negotiation.bestresponse import BestResponseOracle
from interlens.arena.negotiation.games import build_preset_instance
from interlens.arena.negotiation.solutions import pareto_mask
from interlens.arena.schema import EpisodeStore
from interlens.arena.scenarios.scorable import ScorableNegotiation
from interlens.message import Message
from interlens.participant.participant import Participant


class _Scripted(Participant):
    """A deterministic table: every seat proposes ``deal`` on its first turn, then accepts the first live offer.

    Deterministic so two of them with DIFFERENT target deals produce two episodes that diverge at a known point —
    which is exactly the shape the comparison renderer consumes."""

    self_role, others_role = "assistant", "user"

    def __init__(self, deal: dict):
        self.name, self.system_prompt, self.private_context = "scripted", None, ()
        self.deal, self.proposed = deal, set()

    def generate(self, view, *, seat=None, **kw):
        text = view[-1]["content"]
        offers = re.findall(r'"(P\d+)":\s*\{', text)
        if seat in self.proposed and offers:
            return Message(self.name, '```json\n' + json.dumps({"action": "accept", "offer_id": offers[0]}) + '\n```')
        self.proposed.add(seat)
        return Message(self.name, '```json\n' + json.dumps({"action": "propose", "deal": self.deal}) + '\n```')


def _missing(html: str, *needles: str) -> list[str]:
    """The needles NOT present in ``html``.

    Assertions go through this rather than ``needle in html`` so a failure reports the handful of missing strings
    instead of pytest rendering a diff of a 300 KB document (which is slow enough to look like a hang)."""
    return [n for n in needles if n not in html]


def _instance(n_parties: int = 4):
    inst, cfg = build_preset_instance("scorable", n_parties=n_parties, n_issues=3, n_options=3, seed=3)
    return inst, cfg


def _run(inst, cfg, deal_index: int | None = None):
    """Play one episode with both a threshold and a best-response oracle, with the table proposing one fixed deal.

    ``deal_index`` defaults to the Nash bargaining solution's deal; pass a different index to get an episode that
    provably diverges from the default one (two solution concepts can coincide on a given instance, so choosing
    the counterpart by CONCEPT would not guarantee a divergence to test against)."""
    geo = viz.GameGeometry.from_instance(inst.to_json())
    index = geo.solution_index("nash") if deal_index is None else deal_index
    scen = ScorableNegotiation(oracles=[ThresholdOracle(), BestResponseOracle(0)])
    ep = asyncio.run(EpisodePool(None).run_episode(scen, inst, "moves_chat", _Scripted(geo.at(index).named),
                                                  seed=0, cfg=cfg))
    return ep.to_json(), inst.to_json()


def _differing_deal_index(inst) -> int:
    """A deal index whose named deal differs from the Nash solution's — the target for the "other" episode."""
    geo = viz.GameGeometry.from_instance(inst.to_json())
    nash = geo.solution_index("nash")
    return next(i for i in range(geo.n_deals) if i != nash)


def _write_run(tmp_path: Path, name: str, episodes, instance, invocation=None) -> Path:
    """Lay out a run directory the way the campaigns do, so the loader is tested against the real layout."""
    root = tmp_path / name
    store = EpisodeStore(root / "episodes")
    for ep in episodes:
        path = store.path(type("E", (), {"scenario": ep["scenario"], "cell": ep["cell"], "arm": ep["arm"],
                                         "model": ep["model"], "level": ep["level"],
                                         "episode_id": ep["episode_id"]})())
        path.write_text(json.dumps(ep))
    (root / "instances").mkdir(parents=True, exist_ok=True)
    (root / "instances" / f"{instance['instance_id']}.json").write_text(json.dumps(instance))
    if invocation:
        (root / "manifest.json").write_text(json.dumps({"run_name": name, "invocation": invocation}))
    return root


@pytest.fixture(scope="module")
def episode():
    inst, cfg = _instance()
    return _run(inst, cfg)


@pytest.fixture(scope="module")
def payload(episode):
    ep, inst = episode
    return viz.episode_payload(ep, inst)


# ------------------------------------------------------------------------------------- geometry --
def test_geometry_is_exact_and_scale_invariant(episode):
    _, inst = episode
    geo = viz.GameGeometry.from_instance(inst)
    assert geo.n_deals == 27 and geo.n_parties == 4
    # the embedding is built from clipped normalized surplus, so both axes live in [0, 1]
    assert 0.0 <= geo.wx.min() and geo.wx.max() <= 1.0
    assert 0.0 <= geo.wy.min() and geo.wy.max() <= 1.0
    # every axiomatic solution point is Pareto-optimal (that is what makes it a solution)
    for concept in ("nash", "kalai_smorodinsky", "utilitarian", "egalitarian"):
        assert geo.pareto[geo.solution_index(concept)], f"{concept} must sit on the frontier"
    # a party's marked best deal really is its argmax over the efficient deals that can close
    for i, idx in enumerate(geo.party_best):
        mask = geo.feasible & geo.pareto
        if mask.any():
            assert geo.X[idx, i] == pytest.approx(geo.X[mask, i].max())
    # the stored analysis and a fresh recomputation agree on the frontier size
    assert geo.pareto.sum() == pareto_mask(geo.U).sum() == inst["solution"]["pareto_count"]
    assert geo.solutions_source == "stored"


def test_geometry_deal_index_round_trips_and_rejects_garbage(episode):
    _, inst = episode
    geo = viz.GameGeometry.from_instance(inst)
    for idx in (0, 5, geo.n_deals - 1):
        assert geo.deal_index(geo.at(idx).named) == idx
    assert geo.deal_index({"nope": "nope"}) is None      # a model's malformed proposal must not raise
    assert geo.deal_index(None) is None and geo.deal_index("propose") is None


def test_envelope_is_a_monotone_staircase_of_frontier_deals(episode):
    _, inst = episode
    geo = viz.GameGeometry.from_instance(inst)
    env = geo.envelope()
    assert env, "a non-empty frontier must yield an envelope"
    xs, ys = [p[0] for p in env], [p[1] for p in env]
    assert xs == sorted(xs) and ys == sorted(ys, reverse=True)      # left to right: welfare up, min surplus down
    for x, y in env:            # every envelope vertex is a real frontier deal (coordinates are rounded for the wire)
        assert any(geo.pareto[i] and abs(geo.wx[i] - x) < 1e-3 and abs(geo.wy[i] - y) < 1e-3
                   for i in range(geo.n_deals))


def test_geometry_returns_none_for_a_non_game_payload():
    assert viz.GameGeometry.from_instance({"payload": {"not": "a game"}}) is None
    assert viz.GameGeometry.from_instance({}) is None


# -------------------------------------------------------------------------------------- payload --
def test_payload_quantifies_every_turn(payload):
    assert payload["turns"], "the fixture episode must have turns"
    proposals = [t for t in payload["turns"] if t["action"]["atype"] == "propose"]
    assert proposals, "the scripted table proposes"
    for t in proposals:
        assert t["action"]["deal_index"] is not None
        assert len(t["deal"]["s"]) == payload["game"]["n_parties"]        # per-party surplus on every proposal
        assert t["deal_welfare"]["usw"] == pytest.approx(sum(t["deal"]["s"]), abs=1e-6)
        assert t["deal"]["ir"] in (0, 1) and t["deal"]["feasible"] in (0, 1)
    assert len(payload["trajectory"]) == len(proposals)
    assert [p["ordinal"] for p in payload["trajectory"]] == list(range(1, len(proposals) + 1))


def test_payload_carries_the_rational_agent_counterfactual(payload):
    assert "bestresponse" in payload["counterfactual_oracles"]
    scored = [t for t in payload["turns"] if "bestresponse" in t["oracles"]]
    assert scored, "the best-response oracle must annotate turns"
    for t in scored:
        o = t["oracles"]["bestresponse"]
        assert o["best_label"], "the counterfactual action must be named"
        assert o["action_values"], "the actions the oracle scored must be listed with their values"
        if o["chosen_value"] is not None and o["best_value"] is not None:
            assert o["divergence"] == pytest.approx(o["best_value"] - o["chosen_value"], abs=1e-6)
            assert o["divergence"] >= -1e-9, "regret is never negative"


def test_payload_records_welfare_of_the_agreed_deal(payload):
    out = payload["outcome"]
    if out.get("deal"):
        assert out["deal_index"] is not None
        assert out["deal_geometry"]["s"] == pytest.approx(out["per_party_surplus"], abs=1e-6)
        assert out["nsw_geomean"] >= 0
    else:
        # No deal means no realized surplus, so Nash welfare is a recorded ZERO, not a missing measurement —
        # otherwise a comparison against an episode that did close would show a dash where it should show 0.
        assert out["nsw_geomean"] == 0.0


def test_seat_kinds_read_the_manifest_then_fall_back_to_token_accounting(episode):
    ep, _ = episode
    assert viz.seat_kinds(ep, {"invocation": ["run.py", "--table", "all_llm"]})["kinds"]["Avery"] == "llm"
    rational = viz.seat_kinds(ep, {"invocation": ["run.py", "--table", "reverse_mixed", "--rational-seat", "2"]})
    assert rational["kinds"]["Casey"] == "policy" and rational["kinds"]["Avery"] == "llm"
    assert rational["source"] == "manifest"
    mixed = viz.seat_kinds(ep, {"invocation": ["run.py", "--table", "mixed", "--models", "Qwen/Qwen3-4B"]})
    assert mixed["kinds"]["Avery"] == "llm" and mixed["kinds"]["Blake"] == "policy"
    # inference: a seat that generated no tokens was a computable policy
    silent = json.loads(json.dumps(ep))
    for t in silent["turns"]:
        if t["seat"] == "Blake":
            t["n_tokens_out"] = 0
    inferred = viz.seat_kinds(silent, None)
    assert inferred["source"] == "inferred" and inferred["kinds"]["Blake"] == "policy"


# ------------------------------------------------------------------------ prompt-view provenance --
def test_stored_views_are_marked_stored(payload):
    assert payload["views"]["stored"] == payload["views"]["n_turns"] > 0
    assert all(t["view_source"] == "stored" and t["view"] for t in payload["turns"])


def test_views_are_reconstructed_by_replay_when_absent(episode):
    ep, inst = episode
    stripped = json.loads(json.dumps(ep))
    for t in stripped["turns"]:
        t["view"] = None
    rebuilt = viz.episode_payload(stripped, inst, reconstruct=True)
    assert rebuilt["views"]["stored"] == 0
    assert rebuilt["views"]["reconstructed"] == rebuilt["views"]["n_turns"]
    # Replay reproduces the recorded prompt EXACTLY on every turn except a retry, where the live view carried the
    # failed attempt plus a repair instruction that the record does not preserve. Retries are marked as such, and
    # every other turn must round-trip byte for byte — that is what makes the panel trustworthy.
    retries = 0
    for original, redone in zip(ep["turns"], rebuilt["turns"]):
        if redone["view_source"] == viz.RETRY_SOURCE:
            retries += 1
            continue
        assert redone["view_source"] == "reconstructed"
        assert redone["view"] == original["view"], "a non-retry view must reconstruct byte for byte"
    assert rebuilt["views"]["reconstructed_pre_retry"] == retries
    html = viz.render_episode_html(rebuilt)
    assert "re-derived by replay" in html.lower()


def test_absent_views_are_reported_not_invented(episode):
    ep, inst = episode
    stripped = json.loads(json.dumps(ep))
    for t in stripped["turns"]:
        t["view"] = None
    bare = viz.episode_payload(stripped, inst, reconstruct=False)
    assert (bare["views"]["stored"], bare["views"]["reconstructed"]) == (0, 0)
    assert bare["views"]["n_turns"] == len(ep["turns"])
    assert all(t["view"] is None and t["view_source"] == "absent" for t in bare["turns"])
    assert _missing(viz.render_episode_html(bare), "stores no per-turn", "not the prompt text itself") == []


# ----------------------------------------------------------------------------------- episode page --
def test_episode_page_has_every_panel(payload):
    h = viz.render_episode_html(payload)
    assert h.startswith("<!doctype html>")
    assert _missing(
        h,
        # the frontier panel, its legend, and its numeric table view
        "id='frontier'", "id='chart'", "id='chart-table'", "joint welfare", "individually-best deal",
        "best for P0", "Pareto",
        # the per-turn regret strip and the counterfactual oracle selector
        "id='regret'", "id='oracle-select'", ">bestresponse<",
        # the game side panel: seats, thresholds, protocol, problem size, private sheets
        "Who is at the table", "threshold τ", "ideal surplus",
        "Protocol", "cheap talk", "discount δ",
        "Size of the problem", "on the Pareto frontier",
        "Private score sheets", "Private score sheet — P0",
        # the expandable system-prompt audit and the headline numbers
        "System prompts", "<details>", "worst-off", "Gini",
        # every solution concept must be named in the table view
        *(f"<b>{label}</b>" for label in ("NBS", "KS", "UTIL", "EGAL", "MNW")),
    ) == []


def test_episode_page_is_self_contained_and_theme_aware():
    inst, cfg = _instance(3)
    h = viz.render_episode_html(viz.episode_payload(*_run(inst, cfg)))
    assert [s for s in ("http://", "https://", "<link", " src=", "@import") if s in h] == []
    # dark mode is selected twice over: the OS preference AND the explicit theme stamp, which must win either way
    assert _missing(h, "prefers-color-scheme:dark", '[data-theme="dark"]', '[data-theme="light"]') == []


def test_payload_travels_as_inert_json_that_cannot_break_out(payload):
    h = viz.render_episode_html(payload)
    head, _, rest = h.partition('<script type="application/json" id="viz-payload">')
    data, _, tail = rest.partition("</script>")
    assert data, "the payload must travel in a JSON script tag"
    assert data.count("</") == 0, "a closing-tag sequence in the data would end the script tag early"
    assert json.loads(data.replace("<\\/", "</"))["kind"] == "episode"
    assert len(re.findall(r"<script>", tail)) == 1, "exactly one executable script, after the data"
    assert "<script" not in head


def test_page_renders_without_an_instance(episode):
    ep, _ = episode
    h = viz.render_episode_html(viz.episode_payload(ep, None))
    assert _missing(h, "Transcript", "No instance record was supplied") == []
    assert "id='chart'" not in h, "no frontier panel without a game"


def test_page_reports_a_missing_best_response_oracle(episode):
    ep, inst = episode
    stripped = json.loads(json.dumps(ep))
    stripped["round_checkpoints"] = [r for r in stripped["round_checkpoints"] if r.get("oracle") != "bestresponse"]
    h = viz.render_episode_html(viz.episode_payload(stripped, inst))
    assert "No best-response oracle on this run" in h


def test_post_hoc_annotation_supplies_oracles_the_episode_lacks(episode):
    ep, inst = episode
    stripped = json.loads(json.dumps(ep))
    stripped["round_checkpoints"] = []
    annotation = {"episode_id": ep["episode_id"], "summary": {"total_regret": 12.5, "mean_regret": 0.5},
                  "turns": [{"turn_idx": r.get("turn_idx", 0), "oracle": {r["oracle"]: r}}
                            for r in ep["round_checkpoints"] if r.get("oracle")]}
    merged = viz.episode_payload(stripped, inst, annotation)
    assert "bestresponse" in merged["oracle_names"]
    assert merged["annotation_summary"]["total_regret"] == 12.5
    assert "12.5" in viz.render_episode_html(merged)


# ---------------------------------------------------------------------------------- comparison --
@pytest.fixture(scope="module")
def two_runs(tmp_path_factory):
    """Two runs over one shared instance whose tables target different deals — a synthetic seat swap."""
    tmp = tmp_path_factory.mktemp("viz")
    inst, cfg = _instance()
    left, inst_json = _run(inst, cfg)
    right, _ = _run(inst, cfg, _differing_deal_index(inst))
    lrun = _write_run(tmp, "left_all_llm", [left], inst_json, ["run.py", "--table", "all_llm"])
    rrun = _write_run(tmp, "right_reverse", [right], inst_json,
                      ["run.py", "--table", "reverse_mixed", "--rational-seat", "1"])
    return lrun, rrun


def test_comparison_pairs_on_the_key_and_finds_the_focal_seat(two_runs):
    lrun, rrun = two_runs
    comparisons, report = viz.pair_runs(lrun, rrun)
    assert report["n_matched_keys"] == 1 and len(comparisons) == 1
    assert not report["unmatched_left"] and not report["unmatched_right"]
    c = comparisons[0]
    assert c["pairing"]["matched"] and c["pairing"]["shared_game"]
    assert c["focal_seats"] == [{"party": 1, "name": "Blake", "left_kind": "llm", "right_kind": "policy"}]
    assert c["focal_parties"] == [1]
    # both sides were placed in ONE geometry, so the frontier they are compared against is identical
    assert c["left"]["game"]["deals"]["wx"] == c["right"]["game"]["deals"]["wx"]


def test_comparison_marks_the_divergence_point(two_runs):
    lrun, rrun = two_runs
    c = viz.pair_runs(*two_runs)[0][0]
    assert c["divergence"] == 0, "the two tables propose different deals from the first turn"
    assert c["aligned"][0]["different"] and c["aligned"][0]["seat"] == "Avery"
    assert all(row["round"] is not None for row in c["aligned"])


def test_comparison_score_table_has_paired_deltas(two_runs):
    c = viz.pair_runs(*two_runs)[0][0]
    rows = {r["metric"]: r for r in c["scores"]}
    assert "primary score" in rows and "joint welfare USW" in rows and "deal reached" in rows
    assert "focal seat surplus" in rows and "focal seat capture" in rows
    for r in c["scores"]:
        if isinstance(r["left"], (int, float)) and isinstance(r["right"], (int, float)):
            assert r["delta"] == pytest.approx(r["right"] - r["left"], abs=1e-6)
        assert r["higher_is_better"] in (-1, 0, 1)
    assert rows["Gini of surplus"]["higher_is_better"] == -1


def test_swapped_seats_metric_averages_over_the_whole_swapped_set(two_runs):
    """A mixed-vs-all-LLM pair swaps every seat but one; attributing that to a single seat would be wrong."""
    c = viz.pair_runs(*two_runs)[0][0]
    many = viz.score_table(c["left"], c["right"], [1, 2, 3])
    labels = [r["metric"] for r in many]
    assert "swapped seats (mean of 3) surplus" in labels and "focal seat surplus" not in labels
    lps = (c["left"]["outcome"].get("per_party_surplus") or [])
    if len(lps) > 3:
        row = next(r for r in many if r["metric"].endswith("surplus"))
        assert row["left"] == pytest.approx(sum(lps[1:4]) / 3, abs=1e-4)


def test_pair_selection_ranks_by_effect_and_is_recorded(two_runs):
    lrun, rrun = two_runs
    for select in viz.SELECTIONS:
        comparisons, report = viz.pair_runs(lrun, rrun, limit=1, select=select)
        assert report["select"] == select, "how pairs were chosen must be recorded alongside the count"
        assert report["n_candidate_pairs"] >= len(comparisons)
    with pytest.raises(ValueError, match="unknown pair selection"):
        viz.pair_runs(lrun, rrun, select="whatever")
    # 'deal-flip' keeps only pairs where exactly one side closed, so it never returns a both-or-neither pair
    flips, _ = viz.pair_runs(lrun, rrun, select="deal-flip")
    for c in flips:
        assert bool((c["left"]["outcome"] or {}).get("deal")) != bool((c["right"]["outcome"] or {}).get("deal"))


def test_comparison_page_has_scores_frontier_and_two_columns(two_runs):
    c = viz.pair_runs(*two_runs)[0][0]
    h = viz.render_compare_html(c)
    assert "What changed, in numbers" in h and "Paired deltas, right minus left" in h
    assert "Seat swap:" in h and "Blake (party 1): llm &rarr; policy" in h or "llm → policy" in h
    assert "id='col-left'" in h and "id='col-right'" in h and "id='chart'" in h
    assert "jump-divergence" in h
    assert "http://" not in h and "https://" not in h and " src=" not in h


def test_comparison_page_warns_when_there_is_no_seat_swap(two_runs):
    lrun, _ = two_runs
    c = viz.pair_runs(lrun, lrun)[0][0]
    h = viz.render_compare_html(c)
    assert "No seat swap detected" in h
    assert "never diverged" in h and c["divergence"] is None


def test_comparison_page_warns_on_an_unmatched_pair(two_runs, episode):
    lrun, rrun = two_runs
    left = viz.RunDir(lrun).payload(viz.RunDir(lrun).episode_files()[0])
    other, other_inst = _run(*_instance(3))
    c = viz.compare_payload(left, viz.episode_payload(other, other_inst))
    assert not c["pairing"]["matched"]
    assert "not a matched pair" in viz.render_compare_html(c)


# --------------------------------------------------------------------------------------- export --
def test_export_run_writes_pages_index_and_manifest(two_runs, tmp_path):
    lrun, _ = two_runs
    out = tmp_path / "pages"
    manifest = viz.export_run(lrun, out)
    assert manifest["n_episodes"] == 1 and not manifest["failures"]
    assert (out / "index.html").exists() and (out / "manifest.json").exists()
    page = Path(manifest["pages"][0])
    assert page.exists() and page.read_text().startswith("<!doctype html>")
    index = (out / "index.html").read_text()
    assert "total regret" in index and page.name in index


def test_export_run_survives_one_unreadable_episode(two_runs, tmp_path):
    lrun, _ = two_runs
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "episodes").mkdir()
    (broken / "episodes" / "bad.json").write_text('{"episode_id": "bad", "turns": "not a list"}')
    for src in (viz.RunDir(lrun).episode_files()):
        (broken / "episodes" / src.name).write_text(src.read_text())
    manifest = viz.export_run(broken, tmp_path / "out")
    assert manifest["n_episodes"] == 1 and len(manifest["failures"]) == 1
    assert "bad.json" in manifest["failures"][0]["episode"]


def test_export_comparison_writes_the_pairing_report(two_runs, tmp_path):
    lrun, rrun = two_runs
    out = tmp_path / "cmp"
    manifest = viz.export_comparison(lrun, rrun, out)
    assert manifest["n_comparisons"] == 1
    assert manifest["report"]["n_matched_keys"] == 1
    assert (out / "index.html").exists()
    index = (out / "index.html").read_text()
    assert "DELTAS" in index and "shared key" in index
    assert json.loads((out / "manifest.json").read_text())["report"]["pair_fields"] == list(viz.DEFAULT_PAIR_KEY)


def test_cli_renders_a_run_and_a_comparison(two_runs, tmp_path, capsys):
    from interlens.arena.viz.__main__ import main
    lrun, rrun = two_runs
    assert main(["--run", str(lrun), "--out", str(tmp_path / "a"), "--limit", "1"]) == 0
    assert "episode page(s)" in capsys.readouterr().out
    assert main(["--compare", str(lrun), str(rrun), "--out", str(tmp_path / "b")]) == 0
    assert "comparison page(s)" in capsys.readouterr().out
    assert (tmp_path / "a" / "index.html").exists() and (tmp_path / "b" / "index.html").exists()


# [rational_agents: viz-serve] 2026-07-31 --- serving the rendered pages over HTTP ---

def test_cli_renders_to_a_temp_dir_when_out_is_omitted(two_runs, capsys):
    """``--out`` is optional: without it the pages go to a fresh $TMPDIR directory whose path is printed, so a
    user who only wants to look never has to invent a save location. No --serve required for this."""
    from interlens.arena.viz.__main__ import main
    lrun, _ = two_runs
    assert main(["--run", str(lrun), "--limit", "1"]) == 0
    out = capsys.readouterr().out
    assert "temporary directory" in out
    scratch = Path(re.search(r"temporary directory: (\S+)", out).group(1))
    assert scratch.name.startswith("interlens_viz_")
    assert (scratch / "index.html").exists(), "the temp dir must actually hold the rendered pages"


def test_scratch_out_dirs_are_fresh_each_time():
    from interlens.arena.viz.__main__ import scratch_out_dir
    a, b = scratch_out_dir(), scratch_out_dir()
    assert a != b and Path(a).is_dir() and Path(b).is_dir()


def test_server_hands_the_rendered_bytes_to_an_http_client(two_runs, tmp_path):
    """The --serve payload check, without a browser: bind on port 0 (a free ephemeral port), fetch
    /index.html over real HTTP from a client thread, and confirm the bytes are the rendered file."""
    import threading
    from urllib.request import urlopen
    lrun, _ = two_runs
    out = tmp_path / "served"
    viz.export_run(lrun, out, limit=1)

    server = viz.make_server(out, port=0)
    port = server.server_address[1]
    assert port != 0, "port 0 must be resolved to a real ephemeral port at bind time"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://127.0.0.1:{port}/index.html", timeout=10) as response:
            assert response.status == 200
            assert response.read() == (out / "index.html").read_bytes()
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()
    assert not thread.is_alive(), "shutdown() must stop the serving thread"


def test_serve_banner_gives_the_url_and_a_usable_port_forward():
    """The banner is the whole point of --serve on a cluster: it must name a real host, the URL to open, and an
    'ssh -L' line that forwards the SAME port the server actually bound."""
    banner = viz.serve_banner("/tmp/pages", 8899)
    hostname = socket.getfqdn()
    assert f"http://{hostname}:8899/index.html" in banner
    assert f"ssh -L 8899:localhost:8899 {hostname}" in banner
    assert "http://localhost:8899/index.html" in banner
    assert "all interfaces" in banner, "binding 0.0.0.0 must be stated, never silent"


def test_serve_directory_exits_cleanly_on_keyboard_interrupt(tmp_path, capsys, monkeypatch):
    """Ctrl-C is the documented way to stop serving, so it must return normally (CLI exit 0) rather than
    propagate, and must close the socket on the way out."""
    closed = []
    real_make_server = viz.make_server

    def interrupting_server(directory, port=0, host=viz.DEFAULT_HOST):
        server = real_make_server(directory, port=port, host=host)
        monkeypatch.setattr(server, "serve_forever", lambda: (_ for _ in ()).throw(KeyboardInterrupt))
        monkeypatch.setattr(server, "server_close", lambda: closed.append(True))
        return server

    monkeypatch.setattr("interlens.arena.viz.serve.make_server", interrupting_server)
    viz.serve_directory(tmp_path)                       # must NOT raise
    assert closed == [True]
    assert "stopped" in capsys.readouterr().out


def test_hostile_model_text_cannot_become_markup_or_script(episode):
    """Model output is untrusted. A turn that emits a script tag must stay data: the JSON payload escapes every
    closing-tag sequence so it cannot end the tag early, and the transcript it feeds is built through the page's
    own escaping helper rather than by concatenating raw model text."""
    ep, inst = episode
    poisoned = json.loads(json.dumps(ep))
    poisoned["turns"][0]["parsed_action"]["message"] = "<img src=x onerror=alert(1)>"
    poisoned["turns"][0]["content"] = "</script><script>alert(2)</script>"
    poisoned["turns"][0]["view"] = [{"role": "system", "content": "</script><script>alert(3)</script>"}]
    h = viz.render_episode_html(viz.episode_payload(poisoned, inst))
    head, _, rest = h.partition('<script type="application/json" id="viz-payload">')
    data, _, tail = rest.partition("</script>")
    assert data.count("</") == 0, "the hostile closing tag must be escaped inside the data"
    assert len(re.findall(r"<script>", tail)) == 1, "the hostile script tag must not become a second script"
    # the system-prompt audit renders server-side, so its escaping is visible in the document itself
    assert "&lt;script&gt;alert(3)" in head and "<script>alert(3)" not in head
    assert "<img src=x" not in head and "onerror=alert(1)" not in head


# ------------------------------- annotation vintage / full-cloud hover / compare counterfactual toggle --
def test_run_dir_selects_the_annotation_vintage_and_surfaces_it(episode, tmp_path):
    """The visualizer must read whichever annotation subdirectory it is pointed at — default ``annotations``
    unchanged, ``annotations_v1`` (the oracle seat-binding re-annotation) when asked — and the page must state
    WHICH vintage it is showing so an auditor is never misled about which counterfactual they are reading.

    Hermetic, mirroring ``tests/test_campaign_annotations_v1.py``: two annotation sets that DISAGREE on the
    best-response values, with the episode's own inline oracle stripped so the annotation store is the sole
    source. Asserts the knob selects the set, the default is unchanged, the provenance is carried into the page,
    and a nonexistent set degrades gracefully rather than crashing or claiming a false provenance."""
    ep, inst = episode
    by_round_seat = {(t["round"], t["seat"]): t["idx"] for t in ep["turns"]}

    def annotation(best_value):
        turns = []
        for r in ep["round_checkpoints"]:
            if r.get("oracle") != "bestresponse":
                continue
            idx = r.get("turn_idx")
            if idx is None or idx < 0:
                idx = by_round_seat.get((r.get("round"), r.get("seat")))
            rec = json.loads(json.dumps(r))
            rec["best_value"] = best_value
            rec["divergence"] = best_value - (rec.get("chosen_value") or 0.0)
            turns.append({"turn_idx": idx, "oracle": {"bestresponse": rec}})
        return {"episode_id": ep["episode_id"], "summary": {"total_regret": best_value}, "turns": turns}

    stripped = json.loads(json.dumps(ep))
    stripped["round_checkpoints"] = []          # the annotation store is now the SOLE source of the counterfactual
    root = _write_run(tmp_path, "reann", [stripped], inst)
    for name, value in (("annotations", 10.0), ("annotations_v1", 99.0)):
        d = root / name
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{ep['episode_id']}.json").write_text(json.dumps(annotation(value)))
    ep_path = viz.RunDir(root).episode_files()[0]

    default = viz.RunDir(root).payload(ep_path)
    v1 = viz.RunDir(root, annotations_dirname="annotations_v1").payload(ep_path)

    assert default["annotations_source"] == "annotations"        # the default preserves the original reads
    assert v1["annotations_source"] == "annotations_v1"
    assert default["annotation_summary"]["total_regret"] == 10.0
    assert v1["annotation_summary"]["total_regret"] == 99.0
    dbest = [t["oracles"]["bestresponse"]["best_value"] for t in default["turns"] if "bestresponse" in t["oracles"]]
    vbest = [t["oracles"]["bestresponse"]["best_value"] for t in v1["turns"] if "bestresponse" in t["oracles"]]
    assert dbest and vbest, "both vintages must annotate at least one turn"
    assert all(b == 10.0 for b in dbest) and all(b == 99.0 for b in vbest)
    # the chosen vintage is carried into the document, so the provenance line can name it for an auditor
    assert "annotations_v1" in viz.render_episode_html(v1)
    # a nonexistent set is graceful: no counterfactual, no crash, and no false provenance claim
    missing = viz.RunDir(root, annotations_dirname="annotations_v9").payload(ep_path)
    assert missing["annotations_source"] is None and "bestresponse" not in missing["oracle_names"]


def test_cli_accepts_the_annotations_dir_flag(two_runs, tmp_path):
    """``--annotations-dir`` is accepted end to end and, pointed at an absent set, still produces pages (the
    counterfactual is simply reported as missing) rather than failing the export."""
    from interlens.arena.viz.__main__ import main
    lrun, _ = two_runs
    assert main(["--run", str(lrun), "--out", str(tmp_path / "ad"),
                 "--annotations-dir", "annotations_v1"]) == 0
    assert (tmp_path / "ad" / "index.html").exists()


def test_frontier_chart_advertises_full_cloud_hover(payload):
    """Every deal in the cloud is inspectable, not only the marked ones: the chart's accessible label says so and
    the nearest-deal pointer handler is wired into the inlined browser layer (which draws the chart)."""
    h = viz.render_episode_html(payload)
    assert "Hover anywhere" in h                 # the chart aria-label advertises full-cloud inspection
    assert "mousemove" in h                       # the nearest-deal handler ships in the page's script


def test_comparison_page_ships_the_counterfactual_toggle(two_runs):
    """The seat-swap page carries the opt-in per-turn rational-agent counterfactual toggle (off by default)."""
    c = viz.pair_runs(*two_runs)[0][0]
    h = viz.render_compare_html(c)
    assert "cf-toggle" in h and "rational-agent counterfactual" in h.lower()


# ------------------------------------------------------------------- fabricated-turn visibility --
def test_fabricated_turns_are_surfaced_and_impossible_to_miss(episode):
    """A turn the ENGINE fabricated must be visible as such. Without this the page renders engine filler as a
    party that chose to stay quiet, because the placeholder parses into a well-formed no-op — which is exactly how
    a fully contaminated campaign cell read as clean."""
    from interlens.arena.engine import EMPTY_TURN_PLACEHOLDER
    ep, inst = episode
    poisoned = json.loads(json.dumps(ep))
    for t in poisoned["turns"][:2]:
        # A genuine pre-v1.2 record: the value signature AND no stamp field at all. Dropping the key matters —
        # an explicit `gen_failed: False` is authoritative and must NOT be re-screened by the legacy signature.
        t["content"], t["n_tokens_out"], t["raw"] = EMPTY_TURN_PLACEHOLDER, 0, None
        t.pop("gen_failed", None)
    poisoned["turns"][2]["gen_failed"] = True           # and the explicit v1.2 stamp
    poisoned["turns"][2]["gen_failure"] = "RuntimeError: CUDA error: out of memory"

    payload = viz.episode_payload(poisoned, inst)
    assert payload["generation"]["fabricated"] == 3
    assert payload["generation"]["fraction"] > 0
    assert sorted(payload["generation"]["detected_by"]) == ["legacy_signature", "stamp"]
    flagged = [t for t in payload["turns"] if t["gen_failed"]]
    assert [t["idx"] for t in flagged] == [0, 1, 2]
    assert "out of memory" in flagged[2]["gen_failure"]

    h = viz.render_episode_html(payload)
    assert _missing(h, "were NOT GENERATED", "not model behaviour", "NOT generated") == []
    assert "3" in h.split("NOT generated")[1][:120]      # the tile carries the count
    # a clean episode says nothing about fabrication at all
    assert "were NOT GENERATED" not in viz.render_episode_html(viz.episode_payload(ep, inst))


def test_compare_page_labels_which_side_was_contaminated(two_runs, episode):
    """The de-contamination view: a contaminated episode beside its clean counterpart must name which side is
    which, per side, rather than showing one undifferentiated warning."""
    from interlens.arena.engine import EMPTY_TURN_PLACEHOLDER
    lrun, _ = two_runs
    clean = viz.RunDir(lrun).payload(viz.RunDir(lrun).episode_files()[0])
    ep, inst = episode
    poisoned = json.loads(json.dumps(ep))
    for t in poisoned["turns"][:2]:
        t["content"], t["n_tokens_out"], t["raw"] = EMPTY_TURN_PLACEHOLDER, 0, None
        t.pop("gen_failed", None)
    dirty = viz.episode_payload(poisoned, inst)
    h = viz.render_compare_html(viz.compare_payload(dirty, clean, left_label="contaminated", right_label="clean"))
    assert "contaminated: 2 of" in h, "the banner must name the affected side"
    assert h.count("were NOT GENERATED") == 1, "only the contaminated side gets a banner"


def test_most_fabricated_selection_ranks_and_drops_clean_pairs(two_runs):
    """`most-fabricated` exists to make a generation-failure bug visible; it must rank by fabricated count and
    return nothing at all when no pair has any."""
    lrun, rrun = two_runs
    assert "most-fabricated" in viz.SELECTIONS
    comparisons, report = viz.pair_runs(lrun, rrun, select="most-fabricated")
    assert report["select"] == "most-fabricated"
    # the fixture runs are clean, so there is deliberately nothing to show
    assert comparisons == [] and report["n_comparisons"] == 0


def test_alignment_keeps_retry_turns_instead_of_overwriting_them(episode):
    """A seat can occupy the same (round, phase, seat) slot twice under the engine's one-retry rule. Keying the
    alignment on the slot alone dropped the FIRST attempt — which on the contaminated campaign cells is precisely
    the engine-fabricated turn, so the comparison hid the contamination it was built to show."""
    ep, inst = episode
    payload = viz.episode_payload(ep, inst)
    slots = [(t["round"], t["phase"], t["seat"]) for t in payload["turns"]]
    repeated = [s for s in set(slots) if slots.count(s) > 1]
    assert repeated, "the fixture must contain a retry for this test to have teeth"

    rows, _ = viz.align(payload, payload)
    # every turn on each side reaches a row — nothing is silently swallowed
    assert len([r for r in rows if r["left_idx"] is not None]) == len(payload["turns"])
    assert len([r for r in rows if r["right_idx"] is not None]) == len(payload["turns"])
    assert sorted(r["left_idx"] for r in rows) == sorted(t["idx"] for t in payload["turns"])
    # retries are labelled as such, and first attempts pair with first attempts
    assert any(r["attempt"] > 0 for r in rows)
    assert all(r["left_idx"] == r["right_idx"] for r in rows), "an episode aligned to itself must pair exactly"


def test_fabricated_turns_survive_into_the_comparison_view(episode):
    """The de-contamination demo's core requirement: a contaminated episode's fabricated turns must be present in
    the aligned rows, so they actually render in the transcript column."""
    from interlens.arena.engine import EMPTY_TURN_PLACEHOLDER
    ep, inst = episode
    poisoned = json.loads(json.dumps(ep))
    for t in poisoned["turns"]:
        t["content"], t["n_tokens_out"], t["raw"] = EMPTY_TURN_PLACEHOLDER, 0, None
        t.pop("gen_failed", None)
    dirty = viz.episode_payload(poisoned, inst)
    clean = viz.episode_payload(ep, inst)
    fabricated = {t["idx"] for t in dirty["turns"] if t["gen_failed"]}
    assert fabricated, "the poisoned episode must have fabricated turns"
    rows, _ = viz.align(dirty, clean)
    reached = {r["left_idx"] for r in rows if r["left_idx"] is not None}
    assert fabricated <= reached, f"{len(fabricated - reached)} fabricated turn(s) missing from the comparison"


# ------------------------------------------------- [rational_agents: viz-ux] 2026-08-03 — the UX layer --
# Navigation, the sortable index, the summary strip, the message pool, and the action grammar. The pages'
# behaviour still renders server-side wherever it can, so these assert on the emitted document; what genuinely
# only exists in the browser (handlers) is asserted as "the binding ships", and the demo sets are separately
# executed in a DOM harness.

def test_page_wears_the_shell_with_navigation_theme_and_help(payload):
    """Every page carries the same shell: a sticky top bar with the quick read, a theme toggle that can beat the
    OS setting, a help overlay, and a skip link. Without the shell the keyboard bindings have nothing to drive."""
    h = viz.render_episode_html(payload)
    assert _missing(h, "class='topbar'", "id='theme-toggle'", "id='help-toggle'", "id='help'",
                    "class='skip'", "id='content'", "class='quick'") == []
    # the nav slot is reserved but not filled: one payload cannot know its siblings
    assert viz.NAV_MARKER in h


def test_export_run_links_every_page_to_its_siblings(two_runs, tmp_path):
    """The exporter fills each page's reserved nav slot once the whole run is known: prev/next links that really
    point at the neighbouring files, a picker listing every page, and a disabled link at each end rather than a
    missing one (so the control row never changes width)."""
    lrun, _ = two_runs
    # three copies of the one fixture episode, so there is a genuine middle page to test
    run = tmp_path / "many"
    (run / "episodes").mkdir(parents=True)
    src = viz.RunDir(lrun).episode_files()[0]
    ep = json.loads(src.read_text())
    for i in range(3):
        ep["episode_id"] = f"ep{i}"
        (run / "episodes" / f"ep{i}.json").write_text(json.dumps(ep))
    for name in ("instances",):
        for f in (viz.RunDir(lrun).root / name).glob("*.json"):
            (run / name).mkdir(exist_ok=True)
            (run / name / f.name).write_text(f.read_text())
    manifest = viz.export_run(run, tmp_path / "nav")
    assert manifest["n_episodes"] == 3
    pages = [Path(p).read_text() for p in manifest["pages"]]
    assert all(viz.NAV_MARKER not in p for p in pages), "every exported page must have its nav slot filled"
    assert "data-nav='prev'" not in pages[0] and "ep1.html" in pages[0]      # first page: no prev, next is ep1
    assert "data-nav='prev'" in pages[1] and "data-nav='next'" in pages[1]   # the middle page walks both ways
    assert "data-nav='next'" not in pages[2]
    for p in pages:                                     # the picker lists every sibling, on every page
        assert p.count("id='ep-picker'") == 1
        assert all(f"value='ep{i}.html'" in p for i in range(3))
    assert pages[1].count(" selected>") == 1, "the picker marks exactly the page you are on"
    assert "<option value='ep1.html' selected>" in pages[1]


def test_nav_group_marks_position_and_disables_the_ends():
    rows = [{"href": "a.html", "label": "a"}, {"href": "b.html", "label": "b"}]
    first, last = viz.nav_group(rows, 0), viz.nav_group(rows, 1)
    assert "1/2" in first and "2/2" in last
    assert "aria-disabled='true'" in first and "aria-disabled='true'" in last
    assert "<option value='a.html' selected>" in first and "<option value='b.html' selected>" in last


def test_index_is_a_sortable_filterable_table_with_the_columns_that_decide_what_to_open():
    """The index has to answer "which episode is worth opening" without opening any. That means the deciding
    numbers as COLUMNS (outcome, primary, distance to the Nash solution, fabricated share, arm/seed/instance), a
    machine-sortable value on every numeric cell, and filters — all client-side over the rows already present, so
    the file stays one static table rather than a table plus a JSON copy of itself."""
    rows = [{"href": "a.html", "label": "a", "model": "m", "arm": "moves_chat", "instance": "inst1", "seed": 0,
             "deal": True, "primary": 0.7, "dist_nbs": 0.12, "usw": 3.0, "esw": 0.5, "fabricated_pct": 0.0,
             "regret": 2.0},
            {"href": "b.html", "label": "b", "model": "m", "arm": "moves_only", "instance": "inst2", "seed": 1,
             "deal": False, "primary": 0.0, "dist_nbs": None, "usw": 0.0, "esw": -1.0, "fabricated_pct": 40.0,
             "regret": None}]
    h = viz.render_index_html(rows, "Episodes — run")
    assert _missing(h, "class='sortable'", "id='idx-search'", "data-filter='outcome:1'",
                    "data-filter='outcome:0'", "data-filter='flag:fabricated'", "id='idx-count'",
                    "dist NBS", "fabricated", "instance", "total regret") == []
    assert "data-sort='0.7'" in h and "data-sort='0.12'" in h, "numeric cells sort on the number"
    assert "data-fabricated='40.0'" in h, "the fabricated filter reads a row attribute, not the rendered text"
    assert h.count("<tr data-hay=") == 2
    assert "inst1" in h and "moves_only" in h
    assert "40.0%" in h and "class='flag'" in h, "a fabricated share is flagged, not just printed"
    assert "http://" not in h and " src=" not in h                       # still self-contained


def test_summary_strip_carries_the_whole_episode_in_one_row(payload):
    """The strip replaced a grid of tiles because it sits above the chart and the chart is what a reader came
    for. It must still carry every number the tiles did, plus the ones the brief added."""
    h = viz.render_episode_html(payload)
    assert "class='strip'" in h
    for key in ("outcome", "primary", "dist to NBS", "joint welfare", "worst-off", "Gini", "turns"):
        assert f">{key}</div>" in h, f"the summary strip must carry {key!r}"


def test_distance_to_nbs_is_zero_when_the_deal_that_closed_is_the_nash_solution(episode):
    """The fixture table proposes the Nash bargaining solution, so if it closed, the distance is exactly zero —
    which is the only value that pins the metric down rather than merely looking plausible."""
    ep, inst = episode
    p = viz.episode_payload(ep, inst)
    d = viz.distance_to_nbs(p)
    if (p["outcome"] or {}).get("deal_index") is not None:
        nash = p["game"]["solutions"]["nash"]["index"]
        expected = 0.0 if p["outcome"]["deal_index"] == nash else None
        if expected is not None:
            assert d == pytest.approx(0.0, abs=1e-9)
    # and it is absent, not zero, when nothing closed
    no_deal = json.loads(json.dumps(p))
    no_deal["outcome"].pop("deal_index", None)
    assert viz.distance_to_nbs(no_deal) is None


def test_prompt_views_travel_as_a_shared_message_pool_and_rehydrate_exactly(payload):
    """The biggest thing on a page was the same prompt text repeated per turn: a six-seat episode re-states its
    system prompt every turn and each view carries the whole history. Pooling identical messages is a pure
    transport change, so it must (a) shrink the wire form and (b) rebuild every view byte for byte."""
    wire = viz.slim_payload(payload)
    pool = wire["msgpool"]
    assert pool and all(isinstance(t["view"][0], int) for t in wire["turns"] if t["view"])
    for original, slim in zip(payload["turns"], wire["turns"]):
        if not original["view"]:
            assert slim["view"] == original["view"]
            continue
        rebuilt = [{"role": pool[i][0], "content": pool[i][1]} for i in slim["view"]]
        assert rebuilt == original["view"], "a pooled view must rebuild exactly"
    assert len(json.dumps(wire)) < len(json.dumps(payload)), "the whole point is that the wire form is smaller"
    # the caller's payload is a public API and must not be mutated by rendering
    assert all(isinstance(t["view"][0], dict) for t in payload["turns"] if t["view"])


def test_page_embeds_the_pooled_payload_and_ships_its_rehydrator(payload):
    h = viz.render_episode_html(payload)
    data = h.partition('<script type="application/json" id="viz-payload">')[2].partition("</script>")[0]
    assert '"msgpool"' in data
    assert "function viewOf" in h, "the page must carry the code that turns pool indices back into messages"
    # the server-rendered system-prompt audit reads the UNSLIMMED payload, so the text is still in the document
    assert "System prompts" in h


def test_transcript_wears_the_action_grammar_and_defers_prompt_bodies(payload):
    """Action types are states, so they wear the reserved status palette with a glyph and a word beside the
    colour; and a prompt panel ships its summary with an EMPTY body, filled on first open — the difference
    between a page that appears instantly and one that hitches on a few hundred kilobytes of prompt text."""
    h = viz.render_episode_html(payload)
    for cls in ("a-propose", "a-accept", "a-reject", "a-walk"):
        assert f".turn.{cls}" in h and f".chip.{cls}" in h, f"{cls} needs both a card and a scrubber style"
    assert "ACT_KINDS" in h and 'word: "propose"' in h
    assert 'data-lazy="view"' in h and "function fillLazy" in h
    assert "function scrubberHtml" in h, "the turn rail is what makes a 30-turn transcript navigable"


def test_keyboard_bindings_ship_and_are_self_documenting(payload):
    """A shortcut that is not in the help overlay does not exist as far as a reader is concerned, so the overlay
    is generated from the SAME list the handler reads."""
    h = viz.render_episode_html(payload)
    assert "function registerKeys" in h
    for key in ('keys: ["j", "ArrowDown"]', 'keys: ["k", "ArrowUp"]', 'keys: ["n"]', 'keys: ["p"]',
                'keys: ["f"]', 'keys: ["?"]', 'keys: ["e"]', 'keys: ["c"]'):
        assert key in h, f"missing binding {key}"
    assert "next turn" in h and "previous episode" in h          # the help text for them
    assert "ev.ctrlKey || ev.metaKey || ev.altKey" in h, "modified keystrokes must stay with the browser"
    assert '["INPUT", "TEXTAREA", "SELECT", "OPTION"]' in h, "shortcuts must not fire while typing"


def test_comparison_page_opens_with_a_verdict_and_gives_each_column_its_own_ids(two_runs):
    """Two things the compare page was missing: a one-line answer to "who won" above the delta table, and
    per-column element-id prefixes. Both columns numbered their turns from zero, so a single prefix put two
    elements with the same id on one page and every lookup silently resolved to whichever came first."""
    c = viz.pair_runs(*two_runs)[0][0]
    h = viz.render_compare_html(c)
    assert "class='verdict'" in h
    assert "Verdict" in h or "Neither side won" in h
    assert 'PREFIX = { left: "lturn-", right: "rturn-" }' in h
    assert "id='expand-all'" in h and "id='collapse-all'" in h and "id='cf-toggle'" in h
    assert 'keys: ["d"]' in h, "jump-to-divergence must have a key, it is the page's whole point"


def test_verdict_names_the_side_that_won_and_counts_the_ties():
    """The verdict must use each metric's OWN better-direction (a lower Gini is a win for whoever lowered it) and
    state the ties, because "better on 3" with nine metrics on screen reads as six losses otherwise."""
    from interlens.arena.viz.page import _verdict_strip
    payload = {"labels": {"left": "baseline", "right": "swapped"},
               "scores": [{"metric": "primary score", "delta": 0.4, "higher_is_better": 1},
                          {"metric": "Gini of surplus", "delta": -0.2, "higher_is_better": -1},
                          {"metric": "deal reached", "delta": 0, "higher_is_better": 1},
                          {"metric": "turns", "delta": 3, "higher_is_better": 0}]}
    h = _verdict_strip(payload)
    assert "swapped" in h and "all 2 metric(s)" in h            # both movers favour the right side
    assert "primary score +0.4" in h                            # the largest is named
    assert "2 scored metric(s) tied" in h
    flipped = {**payload, "scores": [{"metric": "primary score", "delta": -0.4, "higher_is_better": 1},
                                     {"metric": "Gini of surplus", "delta": -0.2, "higher_is_better": -1}]}
    assert "split" in _verdict_strip(flipped)


def test_every_page_kind_emits_syntactically_valid_javascript(payload, two_runs, tmp_path):
    """The pages are executed in a DOM harness before release, but that needs node and a DOM library. This is the
    always-available floor: the emitted script must at least PARSE, on all three page kinds, so a stray backtick
    in a template literal cannot ship silently. Skipped where node is unavailable."""
    import shutil
    import subprocess
    node = shutil.which("node") or str(Path.home() / ".nvm/versions/node/v25.9.0/bin/node")
    if not Path(node).exists():
        pytest.skip("node is not available on this machine")
    c = viz.pair_runs(*two_runs)[0][0]
    pages = {"episode": viz.render_episode_html(payload), "compare": viz.render_compare_html(c),
             "index": viz.render_index_html([{"href": "a.html", "label": "a", "deal": True, "primary": 0.5}],
                                            "Episodes")}
    for kind, html in pages.items():
        script = html.rpartition("<script>")[2].partition("</script>")[0]
        assert script.strip(), f"the {kind} page must carry an executable script"
        f = tmp_path / f"{kind}.js"
        f.write_text(script)
        done = subprocess.run([node, "--check", str(f)], capture_output=True, text=True)
        assert done.returncode == 0, f"{kind} page script does not parse:\n{done.stderr[:600]}"
