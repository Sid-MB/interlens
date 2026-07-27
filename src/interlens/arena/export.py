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
# [rational_agents scaffold: games-presets] 2026-07-23

"""Human-readable transcripts from stored episodes: an ``EpisodeStore`` tree -> one markdown + one self-contained
HTML page per episode, plus a per-run index.

Each transcript shows the game setup (issues/options, every seat's private sheet + threshold, the arm / protocol /
scaffold config), then every turn (seat, private scratchpad/reasoning, public cheap-talk message, the validated
action + offer id, and any per-oracle regret), then the outcome + welfare. It reads a stored ``Episode`` JSON
(``schema.Episode.to_json`` shape) plus the ``Instance`` it was played on; it degrades gracefully on episodes
recorded before the per-turn ``view`` field existed (renders what is there) and surfaces the rendered ``view``
when present.

Usage (library)::

    from interlens.arena import export
    md = export.render_markdown(episode_dict, instance_dict)
    export.export_run("runs/episodes", "runs/instances", "runs/transcripts")   # -> writes md+html+index

CLI::

    python -m interlens.arena.export --episodes runs/episodes --instances runs/instances --out runs/transcripts
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

from .negotiation.sheets import GameSpec


# ------------------------------------------------------------------------------------ game setup --
def _game_spec(instance: dict | None) -> GameSpec | None:
    """The negotiation ``GameSpec`` from an ``Instance`` dict, or ``None`` if the payload is not a scorable game
    (the exporter then renders whatever the episode carries, so it stays useful for any scenario)."""
    if not instance:
        return None
    payload = instance.get("payload")
    if not isinstance(payload, dict):
        return None
    spec = payload.get("game") or payload.get("spec") or payload
    try:
        return GameSpec.from_json(spec)
    except Exception:
        return None


def _setup_rows(game: GameSpec | None) -> tuple[list[tuple[str, str]], list[tuple[str, str, str]]]:
    """``(issue_rows, sheet_rows)`` for the setup header. ``issue_rows`` = ``(issue_name, "opt0, opt1, ...")``;
    ``sheet_rows`` = ``(party, threshold, "issue: opt=val, ...")`` — each party's private additive sheet."""
    if game is None:
        return [], []
    issues = [(iss.name, ", ".join(iss.options)) for iss in game.space.issues]
    sheets = []
    for s in game.sheets:
        cells = "; ".join(
            f"{iss.name}: " + ", ".join(f"{opt}={s.values[j][k]:g}" for k, opt in enumerate(iss.options))
            for j, iss in enumerate(game.space.issues))
        sheets.append((s.agent, f"{s.threshold:g}", cells))
    return issues, sheets


# ---------------------------------------------------------------------------------- oracle regret --
def _oracle_by_turn(episode: dict) -> dict[int, list[dict]]:
    """Inline oracle records grouped by the turn index they annotate. Falls back to ``(round, seat)`` matching
    when a record predates the ``turn_idx`` field (older episodes), keyed to the matching turn's ``idx``."""
    turns = episode.get("turns") or []
    by_rs = {(t.get("round"), t.get("seat")): t.get("idx") for t in turns}
    out: dict[int, list[dict]] = {}
    for rec in episode.get("round_checkpoints") or []:
        if rec.get("oracle") is None:              # a forked provisional probe, not an inline oracle annotation
            continue
        idx = rec.get("turn_idx")
        if idx is None or idx < 0:
            idx = by_rs.get((rec.get("round"), rec.get("seat")))
        if idx is not None:
            out.setdefault(idx, []).append(rec)
    return out


def _regret_str(recs: list[dict]) -> str:
    """One-line per-oracle regret summary for a turn (``oracle=divergence``), skipping unscored entries."""
    parts = [f"{r['oracle']}={r['divergence']:+.3g}" for r in recs
             if r.get("oracle") and r.get("divergence") is not None]
    return ", ".join(parts)


def _action_str(pa: dict | None) -> str:
    """A compact rendering of a turn's validated action from its ``parsed_action`` record."""
    if not isinstance(pa, dict):
        return "(unparsed)"
    atype = pa.get("atype")
    if atype == "propose":
        deal = pa.get("deal_named")
        return f"PROPOSE {json.dumps(deal, ensure_ascii=False)}" if deal else "PROPOSE"
    if atype in ("accept", "reject"):
        return f"{atype.upper()} {pa.get('offer') or ''}".strip()
    if atype == "walk":
        return "WALK"
    if pa.get("syntax_error"):
        return f"(invalid: {pa['syntax_error']})"
    return atype or "(none)"


# --------------------------------------------------------------------------------------- markdown --
def render_markdown(episode: dict, instance: dict | None = None) -> str:
    """A full markdown transcript for one episode (setup header + per-turn + outcome/welfare)."""
    game = _game_spec(instance)
    issues, sheets = _setup_rows(game)
    oracle = _oracle_by_turn(episode)
    out = episode.get("outcome") or {}
    L: list[str] = []
    L.append(f"# {episode.get('scenario', 'episode')} — `{episode.get('episode_id', '?')}`\n")
    L.append(f"**model** {episode.get('model', '?')} · **arm** {episode.get('arm', '?')} · "
             f"**instance** {episode.get('instance_id', '?')} · **seed** {episode.get('seed', '?')} · "
             f"**status** {episode.get('status', '?')}")
    cfg = episode.get("cell_cfg") or {}
    if cfg:
        L.append(f"**protocol/scaffold** `{json.dumps({k: v for k, v in cfg.items() if k != 'personas_resolved'}, ensure_ascii=False)}`")
    L.append("")

    # setup
    if issues:
        L.append("## Game setup\n")
        L.append("**Issues:** " + "; ".join(f"{n} ({o})" for n, o in issues) + "\n")
        L.append("**Private score sheets (threshold):**\n")
        for party, thr, cells in sheets:
            L.append(f"- **{party}** (τ={thr}): {cells}")
        L.append("")

    # turns
    L.append("## Turns\n")
    for t in episode.get("turns") or []:
        pa = t.get("parsed_action") or {}
        head = f"### [{t.get('idx')}] {t.get('seat')} — {t.get('phase')} (round {t.get('round')})"
        L.append(head)
        L.append(f"- **action:** {_action_str(pa)}")
        msg = pa.get("message") if isinstance(pa, dict) else None
        if msg:
            L.append(f"- **message:** {msg}")
        think = (pa.get("thinking") if isinstance(pa, dict) else None) or t.get("reasoning")
        if think:
            L.append(f"- **scratchpad/reasoning:** {think}")
        reg = _regret_str(oracle.get(t.get("idx"), []))
        if reg:
            L.append(f"- **oracle regret:** {reg}")
        L.append("")

    # outcome
    L.append("## Outcome\n")
    if out.get("deal"):
        L.append(f"- **deal:** {json.dumps(out.get('deal_named'), ensure_ascii=False)} "
                 f"(closed by {out.get('finalized_by')})")
    else:
        L.append(f"- **no deal** ({out.get('finalized_by')})")
    L.append(f"- **primary** {out.get('primary')} · **USW** {out.get('usw')} · **ESW** {out.get('esw')} · "
             f"**NSW** {out.get('nsw')} · **Gini** {out.get('gini')}")
    if out.get("per_party_surplus") is not None:
        L.append(f"- **per-party surplus:** {out.get('per_party_surplus')}")
    if out.get("ir_violations"):
        L.append(f"- **IR violations:** {out.get('ir_violations')}")
    L.append(f"- **parse errors:** syntax {out.get('syntax_errors', 0)}, legality {out.get('legality_errors', 0)}, "
             f"economic {out.get('economic_errors', 0)}")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------------------------------- html --
_CSS = """
body{font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#1a1a1a}
h1{font-size:1.5rem}h2{border-bottom:1px solid #ddd;padding-bottom:.2rem;margin-top:1.6rem}
.meta{color:#555;font-size:.9rem}code,pre{background:#f4f4f5;border-radius:4px}code{padding:.1em .3em}
.turn{border:1px solid #e4e4e7;border-radius:8px;padding:.6rem .9rem;margin:.6rem 0}
.turn h3{margin:.1rem 0;font-size:1rem}.act{font-weight:600}.msg{color:#0b6}.think{color:#666;font-style:italic;white-space:pre-wrap}
.reg{color:#a30}.setup li{margin:.2rem 0}.nodeal{color:#a30;font-weight:600}
@media(prefers-color-scheme:dark){body{background:#18181b;color:#e4e4e7}code,pre{background:#27272a}.turn{border-color:#3f3f46}.meta{color:#a1a1aa}}
"""


def _esc(x: Any) -> str:
    return html.escape("" if x is None else str(x))


def render_html(episode: dict, instance: dict | None = None) -> str:
    """A self-contained (inline-CSS, no external assets) HTML transcript for one episode."""
    game = _game_spec(instance)
    issues, sheets = _setup_rows(game)
    oracle = _oracle_by_turn(episode)
    out = episode.get("outcome") or {}
    cfg = {k: v for k, v in (episode.get("cell_cfg") or {}).items() if k != "personas_resolved"}
    P: list[str] = [f"<!doctype html><html><head><meta charset='utf-8'><title>"
                    f"{_esc(episode.get('episode_id'))}</title><style>{_CSS}</style></head><body>"]
    P.append(f"<h1>{_esc(episode.get('scenario'))} <code>{_esc(episode.get('episode_id'))}</code></h1>")
    P.append(f"<p class='meta'>model {_esc(episode.get('model'))} · arm {_esc(episode.get('arm'))} · "
             f"instance {_esc(episode.get('instance_id'))} · seed {_esc(episode.get('seed'))} · "
             f"status {_esc(episode.get('status'))}"
             + (f" · <code>{_esc(json.dumps(cfg, ensure_ascii=False))}</code>" if cfg else "") + "</p>")
    if issues:
        P.append("<h2>Game setup</h2><ul class='setup'>")
        P.append("<li><b>Issues:</b> " + "; ".join(f"{_esc(n)} ({_esc(o)})" for n, o in issues) + "</li>")
        for party, thr, cells in sheets:
            P.append(f"<li><b>{_esc(party)}</b> (τ={_esc(thr)}): {_esc(cells)}</li>")
        P.append("</ul>")
    P.append("<h2>Turns</h2>")
    for t in episode.get("turns") or []:
        pa = t.get("parsed_action") or {}
        P.append("<div class='turn'>")
        P.append(f"<h3>[{_esc(t.get('idx'))}] {_esc(t.get('seat'))} — {_esc(t.get('phase'))} "
                 f"(round {_esc(t.get('round'))})</h3>")
        P.append(f"<div class='act'>{_esc(_action_str(pa))}</div>")
        msg = pa.get("message") if isinstance(pa, dict) else None
        if msg:
            P.append(f"<div class='msg'>💬 {_esc(msg)}</div>")
        think = (pa.get("thinking") if isinstance(pa, dict) else None) or t.get("reasoning")
        if think:
            P.append(f"<div class='think'>{_esc(think)}</div>")
        reg = _regret_str(oracle.get(t.get("idx"), []))
        if reg:
            P.append(f"<div class='reg'>oracle regret: {_esc(reg)}</div>")
        P.append("</div>")
    P.append("<h2>Outcome</h2>")
    if out.get("deal"):
        P.append(f"<p><b>deal:</b> <code>{_esc(json.dumps(out.get('deal_named'), ensure_ascii=False))}</code> "
                 f"(closed by {_esc(out.get('finalized_by'))})</p>")
    else:
        P.append(f"<p class='nodeal'>no deal ({_esc(out.get('finalized_by'))})</p>")
    P.append(f"<p>primary {_esc(out.get('primary'))} · USW {_esc(out.get('usw'))} · ESW {_esc(out.get('esw'))} · "
             f"NSW {_esc(out.get('nsw'))} · Gini {_esc(out.get('gini'))} · "
             f"per-party surplus {_esc(out.get('per_party_surplus'))}</p>")
    P.append("</body></html>")
    return "".join(P)


# ------------------------------------------------------------------------------- run-level export --
def export_episode(episode: dict, instance: dict | None, out_dir: str | Path) -> dict:
    """Write ``<id>.md`` and ``<id>.html`` for one episode into ``out_dir``; returns their paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    eid = episode.get("episode_id", "episode")
    md_p, html_p = out_dir / f"{eid}.md", out_dir / f"{eid}.html"
    md_p.write_text(render_markdown(episode, instance))
    html_p.write_text(render_html(episode, instance))
    return {"md": str(md_p), "html": str(html_p)}


def _load_instances(instances_path: str | Path) -> dict[str, dict]:
    """Index instance dicts by ``instance_id`` from a JSON file or a directory of them."""
    p = Path(instances_path)
    files = [p] if p.is_file() else sorted(p.glob("*.json"))
    out: dict[str, dict] = {}
    for f in files:
        data = json.loads(f.read_text())
        for d in (data if isinstance(data, list) else [data]):
            if isinstance(d, dict) and "instance_id" in d and "payload" in d:
                out[d["instance_id"]] = d
    return out


def _load_episodes(episodes_path: str | Path) -> list[dict]:
    """Load episode dicts from a single JSON or an ``EpisodeStore`` tree (``**/*.json``)."""
    p = Path(episodes_path)
    if p.is_file():
        return [json.loads(p.read_text())]
    return [json.loads(f.read_text()) for f in sorted(p.glob("**/*.json"))
            if "episode_id" in json.loads(f.read_text() or "{}")]


def export_run(episodes_path: str | Path, instances_path: str | Path | None, out_dir: str | Path) -> dict:
    """Render every episode under ``episodes_path`` to ``out_dir`` (md + html each) plus an ``index.html`` /
    ``index.md`` linking them with one-line summaries. Returns a small manifest."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    instances = _load_instances(instances_path) if instances_path else {}
    episodes = _load_episodes(episodes_path)
    rows = []
    for ep in episodes:
        inst = instances.get(ep.get("instance_id"))
        export_episode(ep, inst, out_dir)
        o = ep.get("outcome") or {}
        rows.append((ep.get("episode_id"), ep.get("model"), ep.get("arm"),
                     ("deal" if o.get("deal") else "no-deal"), o.get("primary")))
    # index
    idx_md = ["# Transcripts index\n", f"{len(rows)} episode(s).\n", "| episode | model | arm | outcome | primary |",
              "|---|---|---|---|---|"]
    idx_html = [f"<!doctype html><html><head><meta charset='utf-8'><title>transcripts</title><style>{_CSS}"
                "table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:.3rem .6rem}</style></head>"
                "<body><h1>Transcripts</h1><table><tr><th>episode</th><th>model</th><th>arm</th>"
                "<th>outcome</th><th>primary</th></tr>"]
    for eid, model, arm, outcome, primary in rows:
        idx_md.append(f"| [{eid}]({eid}.html) | {model} | {arm} | {outcome} | {primary} |")
        idx_html.append(f"<tr><td><a href='{_esc(eid)}.html'>{_esc(eid)}</a></td><td>{_esc(model)}</td>"
                        f"<td>{_esc(arm)}</td><td>{_esc(outcome)}</td><td>{_esc(primary)}</td></tr>")
    idx_html.append("</table></body></html>")
    (out_dir / "index.md").write_text("\n".join(idx_md) + "\n")
    (out_dir / "index.html").write_text("".join(idx_html))
    return {"n_episodes": len(rows), "out_dir": str(out_dir), "index": str(out_dir / "index.html")}


def export_transcripts(episodes_dir: str | Path, out_dir: str | Path, *,
                       instances_dir: str | Path | None = None, annotations_dir: str | Path | None = None) -> dict:
    """Alias of :func:`export_run` with a caller-friendly signature (``episodes_dir, out_dir, instances_dir=``).
    ``annotations_dir`` is accepted for interface stability but IGNORED — per-oracle regret is read from each
    episode's own inline ``round_checkpoints``, so no separate annotation store is needed."""
    return export_run(episodes_dir, instances_dir, out_dir)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Export stored negotiation episodes to markdown + HTML transcripts.")
    ap.add_argument("--episodes", required=True, help="An episode JSON or an EpisodeStore root directory.")
    ap.add_argument("--instances", default=None, help="Instances JSON/dir (for the game-setup header). Optional.")
    ap.add_argument("--out", required=True, help="Output directory for the transcripts + index.")
    a = ap.parse_args(argv)
    manifest = export_run(a.episodes, a.instances, a.out)
    print(f"[export] {manifest['n_episodes']} transcript(s) -> {manifest['out_dir']} (index: {manifest['index']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
