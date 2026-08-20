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
# [implement f: rational-informed LLM, reading inputs] 2026-08-20

"""The advised seat, audited: what its planner knew, what it recommended, and whether the seat did it.

Some arms give one seat a private advisor and let the model keep the decision. Two questions then decide whether
any number the arm produces means anything, and neither is answerable from the transcript:

1. **What did the advisor actually know?** In an interpreter arm the advice is computed from two very different
   evidence channels — the FORMAL move ledger (packages tabled, offers accepted, all machine-readable) and a
   model's parse of the public chat into structured preference claims, each carrying the verbatim quote it was
   read off. A recommendation that looks bizarre usually looks reasonable next to the claims that produced it,
   and a claim that moved a plan is a claim a reader should be able to check against the sentence it came from.
2. **Did the seat take the advice?** An arm whose advice the model discarded measured a prompt, not an
   intervention. On the wave-2 cell 46% of advised turns did something other than what the planner ranked, so a
   reader scrolling the transcript is looking at two quite different kinds of turn and nothing distinguished
   them.

This module renders both, from one run-level sidecar.

The verdict is READ, never computed
-----------------------------------
``advice_trace.json`` is written into the run directory by the experiment's own
``build_advice_trace.py``, which takes every compliance column from ``advice_uptake`` — the module the arm's
uptake gate is evaluated on. Whether a turn followed its advice is therefore decided once, by the code that owns
the comparison rules (deal identity for a propose, offer id for an accept, which rung of a ranked list was
played), and this file only marks what that decision was. Re-deriving it in the renderer would be a second
opinion with no authority, and the two would disagree the first time either changed. It is the same division of
labour as the final-vote tally's derived column (:mod:`~interlens.arena.viz.ballots`).

No model call and no classifier is involved anywhere in the chain. In particular the page does **not** claim to
know how the seat verbalized its advice: it puts the ranked packages, the move actually played, and the public
message the seat published in one place, and leaves the reading to the reader. "Described the advice
faithfully" is not in the record, so it is not asserted.

What ships to the page
----------------------
Each advised turn's trace row is attached to that turn's payload as ``advice`` and rendered inside its card by
the browser layer (``assets/js_transcript.py``), which also puts an override class on the card and on the
turn's scrubber chip. Above the transcript, :func:`advice_card` renders the same audit as a server-side table,
so the compliance record is readable with scripting off and every row links to its turn.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from .chrome import _e, _num

#: The file an experiment writes into a run root to give the pages their advice audit.
ADVICE_SIDECAR = "advice_trace.json"


def advice_trace(run_root: str | Path | None) -> dict | None:
    """The optional advice sidecar for a run, or ``None`` when it is absent or unreadable.

    Unreadable is treated as absent for the same reason the ballot sidecar is: a malformed audit file must cost
    the page one optional panel, not the whole render.
    """
    if run_root is None:
        return None
    path = Path(run_root) / ADVICE_SIDECAR
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def episode_advice(trace: dict | None, episode_id: str | None) -> dict[str, dict]:
    """One episode's advised turns from the trace, keyed by turn index as a string.

    Returns an empty dict for an episode the trace does not cover — an unadvised arm, an episode that errored, or
    a run with no sidecar at all — which is what makes every caller a no-op rather than a special case.
    """
    episodes = (trace or {}).get("episodes") or {}
    turns = episodes.get(str(episode_id))
    return turns if isinstance(turns, dict) else {}


def attach_advice(rows: Sequence[dict], turns: dict[str, dict]) -> list[dict]:
    """Turn payload rows with each advised turn's trace row attached under ``advice``.

    Keyed on the turn's own ``idx``, which is the index the sidecar recorded and the id the transcript, the
    scrubber and every jump link already agree on.
    """
    return [({**row, "advice": turns[str(row.get("idx"))]} if str(row.get("idx")) in turns else row)
            for row in rows]


def advice_summary(turns: dict[str, dict]) -> dict:
    """This episode's compliance record: how many turns were advised, how many followed, on which rung.

    ``n_followed`` counts turns whose stored verdict is a match; ``n_overridden`` counts the explicit non-matches
    only. A turn whose verdict is missing (a trace that failed to join its sidecar) is in neither, and
    ``n_unverdicted`` says so rather than letting an unknown fall into the compliant column.
    """
    rows = list(turns.values())
    followed = [r for r in rows if r.get("followed") is True]
    overridden = [r for r in rows if r.get("followed") is False]
    ranks: dict[str, int] = {}
    for row in followed:
        rank = (row.get("uptake") or {}).get("advice_rank_taken")
        key = "unranked" if rank is None else f"rank {int(rank) + 1}"
        ranks[key] = ranks.get(key, 0) + 1
    claims = [r for r in rows if r.get("parse")]
    return {
        "n_advised": len(rows), "n_followed": len(followed), "n_overridden": len(overridden),
        "n_unverdicted": len(rows) - len(followed) - len(overridden),
        "follow_rate": (len(followed) / len(rows)) if rows else None,
        "rank_taken": dict(sorted(ranks.items())),
        "n_claims_kept": sum(int(r.get("parse", {}).get("n_kept") or 0) for r in claims),
        "n_claims_parsed": sum(int(r.get("parse", {}).get("n_rows") or 0) for r in claims),
        "n_parse_calls": len(claims),
        "n_turns_unjoined": sum(1 for r in rows if r.get("joined") is False),
    }


def _package_words(package: Any) -> str:
    """A ``{issue: option}`` package as one line of prose, or an em dash when there is none.

    Both the planner's candidates and the scenario's stored ``deal_named`` use this shape, so one formatter
    serves the advised package and the played one and the two cannot be rendered in different notations — which
    is the whole point of putting them next to each other.
    """
    if not isinstance(package, dict) or not package:
        return "—"
    return " · ".join(f"{_e(k)}: <b>{_e(v)}</b>" for k, v in package.items())


def _action_words(action: Any) -> str:
    """A stored or recommended action as a short phrase: the move, and the package or offer id it names."""
    if not isinstance(action, dict):
        return "—"
    kind = str(action.get("atype") or action.get("action") or "—").upper()
    package = action.get("deal_named") or action.get("deal")
    offer = action.get("offer_id") or action.get("offer")
    if isinstance(package, dict) and package:
        return f"<b>{_e(kind)}</b> {_package_words(package)}"
    return f"<b>{_e(kind)}</b>{f' {_e(offer)}' if offer else ''}"


def _turn_row(idx: str, row: dict) -> str:
    """One line of the overview table: what was advised, what was played, and the verdict on the pair."""
    top = (row.get("candidates") or [{}])[0]
    advised = (_action_words(row.get("recommended_action")) if row.get("recommended_action")
               else _package_words(top.get("package")))
    uptake = row.get("uptake") or {}
    rank = uptake.get("advice_rank_taken")
    if row.get("followed") is True:
        verdict = (f"<span class='badge advice-followed'>took rank {int(rank) + 1}</span>"
                   if rank is not None else "<span class='badge advice-followed'>followed</span>")
    elif row.get("followed") is False:
        toward = uptake.get("advice_overridden_toward")
        note = ("" if toward is None else
                f" <span class='sub'>own surplus {'+' if toward >= 0 else ''}{_num(toward, 1)} "
                f"vs the top pick</span>")
        verdict = f"<span class='badge advice-override'>overrode</span>{note}"
    else:
        verdict = "<span class='badge'>no verdict</span>"
    parse = row.get("parse") or {}
    evidence = (f"{parse.get('n_kept', 0)} of {parse.get('n_rows', 0)} claims kept" if parse
                else "no parse call (forced final)")
    return (f"<tr><td><a href='#turn-{_e(idx)}'>turn {_e(idx)}</a>"
            f"<div class='sub'>round {_e(row.get('round'))} · {_e(row.get('seat'))}</div></td>"
            f"<td>{advised}<div class='sub'>{_e(len(row.get('candidates') or []))} candidate(s) ranked · "
            f"{evidence}</div></td>"
            f"<td>{_action_words(row.get('emitted_action'))}</td><td>{verdict}</td></tr>")


def advice_card(payload: dict) -> str:
    """The episode's advice audit as one server-rendered section, or ``""`` when no turn was advised.

    One row per advised turn — the planner's top pick, the move the seat played, and the stored verdict on the
    pair — with the per-turn evidence (the parsed claims and their quotes, the ranked candidates, the ledger
    counts) in each turn's own card below. The section is a hazard style when any turn overrode its advice,
    because that is the fact a reader must not scroll past: those turns measure the model's own choice, not the
    advisor's.
    """
    turns = {str(row["idx"]): row["advice"] for row in (payload.get("turns") or []) if row.get("advice")}
    if not turns:
        return ""
    summary = advice_summary(turns)
    ranks = ", ".join(f"{v}x {k}" for k, v in summary["rank_taken"].items()) or "none taken"
    pills = [
        f"<span class='pill'>{summary['n_advised']} advised turn(s)</span>",
        f"<span class='pill'>{summary['n_followed']} followed</span>",
        (f"<span class='pill bad'>{summary['n_overridden']} overrode the advice</span>"
         if summary["n_overridden"] else "<span class='pill'>0 overrode the advice</span>"),
        f"<span class='pill'>{summary['n_claims_kept']} of {summary['n_claims_parsed']} parsed claims "
        f"entered the ledger</span>",
        f"<span class='pill'>rung taken: {_e(ranks)}</span>",
    ]
    if summary["n_turns_unjoined"]:
        pills.append(f"<span class='pill bad'>{summary['n_turns_unjoined']} turn(s) could not be joined to the "
                     "parse sidecar; their evidence is not shown</span>")
    rows = "".join(_turn_row(idx, turns[idx]) for idx in sorted(turns, key=lambda k: int(k)))
    hazard = " hazard" if summary["n_overridden"] else ""
    return f"""<section class='card advice{hazard}' id='advice'><h2>The advised seat: what the planner
 recommended, and what the seat did</h2>
 <div class='sub'>This seat was given private, fallible advice each turn — a ranked list of candidate packages
 computed from public evidence only — and kept the decision itself. A turn marked <b>overrode</b> played
 something the planner did not rank, so it measures the model's own choice rather than the advisor's. The
 verdict is read from the run's stored advice audit, which is computed by the same code the arm's uptake gate
 uses; nothing on this page re-decides it. What the seat SAID about its advice is not classified anywhere —
 the public message is in each turn's card, next to the advice, for you to read.</div>
 <div class='pills'>{''.join(pills)}</div>
 <div class='tablewrap'><table><thead><tr><th>turn</th><th>the planner's top pick</th>
  <th>what the seat played</th><th>verdict</th></tr></thead><tbody>{rows}</tbody></table></div></section>"""
