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
