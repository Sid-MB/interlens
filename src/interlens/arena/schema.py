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

"""The arena's record schema: one JSON shape for every episode.

Every episode — regardless of scenario, arm, cell, or model — serializes to one JSON record with the same
top-level fields, so datasets and analyses join cleanly across runs. ``Instance`` is a generated, solver-verified
problem (with its exact ceiling/floor and hidden solution); ``Episode`` is one play-through of an instance;
``EpisodeStore`` is the crash-safe on-disk layout. The schema is shared with the arena experiments that
produced the public transcripts dataset, so stored episodes from those runs re-score under this package
(see ``replay.py``).
"""
from __future__ import annotations

import dataclasses
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "v1.0"

# Neutral seat names, assigned in order (a scenario with n seats uses the first n).
PERSONAS = ["Avery", "Blake", "Casey", "Devon", "Ember", "Flynn", "Greer", "Hollis"]


def new_id(prefix: str) -> str:
	"""A fresh episode/instance id. Random (uuid4-based), deliberately NOT seed-derived: two runs of the same
	seed produce identical payloads but distinct ids."""
	return f"{prefix}-{uuid.uuid4().hex[:10]}"


@dataclass
class Instance:
	"""One generated problem instance, solver-verified at generation time.

	``ceiling`` is the best achievable primary score (computed exactly by the generator's solver), ``floor`` a
	reference floor policy's score, and ``solution`` the exact optimum — never shown to models, used for
	scoring and audits."""

	instance_id: str
	scenario: str
	level: int              # index into the scenario's difficulty ladder (0 = base)
	seed: int
	payload: dict           # scenario-specific: score sheets / shards / dynamics
	ceiling: float
	floor: float
	solution: dict

	def to_json(self) -> dict:
		return dataclasses.asdict(self)

	@staticmethod
	def from_json(d: dict) -> "Instance":
		d = dict(d)
		# the arena experiments' stored instances predate the env->scenario rename
		if "env" in d and "scenario" not in d:
			d["scenario"] = d.pop("env")
		return Instance(**d)


@dataclass
class SeatRequest:
	"""One pending generation: a seat that must speak now, with the exact view its model is conditioned on."""

	episode_id: str
	seat: str               # persona name
	view: list[dict]        # role/content messages (system first), family-agnostic
	phase: str              # e.g. "turn", "final_proposal", "final_answer", "provisional"
	round: int
	max_tokens: int = 2048  # per-turn output cap; a smaller default silently starves thinking models
	meta: dict = field(default_factory=dict)   # scenario-private routing info
	provisional: bool = False                  # forked: the response never enters state or any transcript


@dataclass
class TurnRecord:
	idx: int
	round: int
	phase: str
	seat: str
	content: str            # think-stripped visible content
	parsed_action: Any
	parse_ok: bool
	n_tokens_out: int = 0
	n_tokens_in: int = 0
	stop_reason: str | None = None
	cap: int = 0            # max_tokens this turn was generated under (0 = unrecorded)
	raw: str | None = None  # raw completion incl. reasoning, when different from content


@dataclass
class Episode:
	"""One complete play-through: turns, forked provisional checkpoints, outcome, and usage accounting."""

	episode_id: str
	scenario: str
	arm: str                # "team" | "solo" | variant tags like "team-greedy"
	model: str
	level: int
	instance_id: str
	seed: int
	seats: list[dict]       # [{name, role, ...}]
	cell: str = "base"      # sweep-cell id when the run varies situational config
	cell_cfg: dict = field(default_factory=dict)
	turns: list[TurnRecord] = field(default_factory=list)
	round_checkpoints: list[dict] = field(default_factory=list)  # {round, seat, provisional_action, score, content}
	outcome: dict = field(default_factory=dict)
	rounds_used: int = 0
	tokens_in: int = 0
	tokens_out: int = 0
	cost_usd: float = 0.0
	gen_config: dict = field(default_factory=dict)   # provider/model/sampling/caps provenance
	status: str = "running"     # running | done | error | budget_stopped
	error: str | None = None
	started_at: float = field(default_factory=time.time)
	ended_at: float | None = None
	schema_version: str = SCHEMA_VERSION

	def to_json(self) -> dict:
		return dataclasses.asdict(self)

	def usage(self) -> dict:
		"""This episode's usage summary: tokens in/out (total and per seat) and dollar cost."""
		by_seat: dict[str, dict] = {}
		for t in self.turns:
			s = by_seat.setdefault(t.seat, {"tokens_out": 0, "tokens_in": 0, "turns": 0})
			s["tokens_out"] += t.n_tokens_out
			s["tokens_in"] += t.n_tokens_in
			s["turns"] += 1
		return {"tokens_in": self.tokens_in, "tokens_out": self.tokens_out,
		        "cost_usd": round(self.cost_usd, 6), "by_seat": by_seat}


class EpisodeStore:
	"""Per-episode JSON persistence, written atomically on every update so a crash loses at most one turn.

	Layout: ``{root}/{scenario}/{cell}/{arm}/{model_short}/L{level}/{episode_id}.json``."""

	def __init__(self, root: str | Path):
		self.root = Path(root)

	def path(self, ep: Episode) -> Path:
		model_short = ep.model.split("/")[-1].replace(".", "-")
		cell = ep.cell or "base"
		p = self.root / ep.scenario / cell / ep.arm / model_short / f"L{ep.level}"
		p.mkdir(parents=True, exist_ok=True)
		return p / f"{ep.episode_id}.json"

	def save(self, ep: Episode) -> None:
		p = self.path(ep)
		tmp = p.with_suffix(".tmp")
		tmp.write_text(json.dumps(ep.to_json(), ensure_ascii=False))
		os.replace(tmp, p)

	def load_all(self, scenario: str | None = None) -> list[dict]:
		pattern = f"{scenario}/**/*.json" if scenario else "**/*.json"
		return [json.loads(f.read_text()) for f in sorted(self.root.glob(pattern))]

	def summary(self) -> str:
		"""A printable run-usage summary aggregated over every stored episode: episode counts, token totals,
		and dollar cost, broken down per (model, arm) — plus cost-per-success where outcomes carry ``success``."""
		rows: dict[tuple, dict] = {}
		for e in self.load_all():
			key = (e["model"], e["arm"])
			r = rows.setdefault(key, {"episodes": 0, "done": 0, "success": 0,
			                          "tokens_in": 0, "tokens_out": 0, "usd": 0.0})
			r["episodes"] += 1
			r["done"] += e["status"] == "done"
			r["success"] += bool((e.get("outcome") or {}).get("success"))
			r["tokens_in"] += e.get("tokens_in", 0)
			r["tokens_out"] += e.get("tokens_out", 0)
			r["usd"] += e.get("cost_usd", 0.0)
		lines = []
		for (model, arm), r in sorted(rows.items()):
			cps = f", ${r['usd'] / r['success']:.2f}/success" if r["success"] and r["usd"] else ""
			lines.append(f"  {model} [{arm}]: {r['done']}/{r['episodes']} done, {r['success']} successes, "
			             f"{r['tokens_in']:,} in / {r['tokens_out']:,} out tokens — ${r['usd']:.2f}{cps}")
		return "Episodes:\n" + "\n".join(lines) if lines else "Episodes: (none stored)"


def save_instances(instances: list[Instance], root: str | Path, name: str | None = None) -> Path:
	"""Persist an instance pool as one JSON file (``{scenario}_L{level}.json`` unless ``name`` overrides)."""
	root = Path(root)
	root.mkdir(parents=True, exist_ok=True)
	stem = name or f"{instances[0].scenario}_L{instances[0].level}"
	p = root / f"{stem}.json"
	p.write_text(json.dumps([i.to_json() for i in instances], ensure_ascii=False, indent=1))
	return p


def load_instances(root: str | Path, scenario: str, level: int | None = None,
                   name: str | None = None) -> list[Instance]:
	"""Load an instance pool saved by ``save_instances`` (or by the arena experiments — the pre-rename ``env``
	key is migrated on read)."""
	stem = name or f"{scenario}_L{level}"
	p = Path(root) / f"{stem}.json"
	return [Instance.from_json(d) for d in json.loads(p.read_text())]
