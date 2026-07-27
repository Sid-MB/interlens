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

# [rational_agents scaffold: games-presets] 2026-07-23

"""Tests for the transcript exporter (``arena/export.py``): markdown + self-contained HTML per episode, a run
index, per-oracle regret rendering, and backward-compatibility on episodes recorded before the ``view`` field."""
from __future__ import annotations

import asyncio
import json

from interlens.arena import export
from interlens.arena.engine import EpisodePool
from interlens.arena.negotiation.acceptance import ThresholdOracle
from interlens.arena.negotiation.bestresponse import BestResponseOracle
from interlens.arena.negotiation.games import build_preset_instance
from interlens.arena.schema import EpisodeStore
from interlens.arena.scenarios.scorable import ScorableNegotiation
from interlens.message import Message
from interlens.participant.participant import Participant


class _GiveAll(Participant):
    """A scripted seat for a single-shot ultimatum: the proposer keeps everything (P10); the responder accepts."""

    self_role, others_role = "assistant", "user"

    def __init__(self):
        self.name, self.system_prompt, self.private_context = "s", None, ()

    def generate(self, view, **kw):
        if "none yet" in view[-1]["content"]:
            return Message(self.name, '```json\n{"action": "propose", "deal": {"Split": "P10"}}\n```')
        return Message(self.name, '```json\n{"action": "accept", "offer_id": "P1"}\n```')


def _episode():
    inst, pcfg = build_preset_instance("ultimatum", pie=10, n_options=11)
    scen = ScorableNegotiation(oracles=[ThresholdOracle(), BestResponseOracle(0)])
    ep = asyncio.run(EpisodePool(None).run_episode(scen, inst, "moves_only", _GiveAll(), seed=0, cfg=pcfg))
    return ep, inst


def test_markdown_has_setup_turns_outcome():
    ep, inst = _episode()
    md = export.render_markdown(ep.to_json(), inst.to_json())
    assert "## Game setup" in md and "Split (P0" in md            # issues + options
    assert "Proposer" in md and "Responder" in md                 # per-seat private sheets + thresholds
    assert "## Turns" in md and "PROPOSE" in md and "ACCEPT" in md
    assert "oracle regret:" in md                                 # per-oracle per-turn regret line
    assert "## Outcome" in md and "deal:" in md


def test_html_is_self_contained():
    ep, inst = _episode()
    h = export.render_html(ep.to_json(), inst.to_json())
    assert h.startswith("<!doctype html>") and "<style>" in h
    # no external assets — a strict-CSP / offline viewer must render it standalone
    assert "http://" not in h and "https://" not in h and "src=" not in h


def test_export_run_writes_index_and_pages(tmp_path):
    ep, inst = _episode()
    store = EpisodeStore(tmp_path / "episodes")
    store.save(ep)
    inst_dir = tmp_path / "instances"
    inst_dir.mkdir()
    (inst_dir / f"{inst.instance_id}.json").write_text(json.dumps(inst.to_json()))
    manifest = export.export_run(store.root, inst_dir, tmp_path / "transcripts")
    out = tmp_path / "transcripts"
    assert manifest["n_episodes"] == 1
    assert (out / "index.html").exists() and (out / "index.md").exists()
    assert (out / f"{ep.episode_id}.html").exists() and (out / f"{ep.episode_id}.md").exists()
    assert ep.episode_id in (out / "index.md").read_text()


def test_renders_episode_without_view_field():
    # backward-compat: episodes recorded before the per-turn `view` field must still render fully.
    ep, inst = _episode()
    epd = ep.to_json()
    for t in epd["turns"]:
        t.pop("view", None)
    md = export.render_markdown(epd, inst.to_json())
    assert "## Turns" in md and "PROPOSE" in md and "## Outcome" in md


def test_export_without_instance_degrades_gracefully():
    # no instance (no game setup) -> still renders turns + outcome, no crash.
    ep, _ = _episode()
    md = export.render_markdown(ep.to_json(), None)
    assert "## Turns" in md and "## Outcome" in md
    assert "## Game setup" not in md
