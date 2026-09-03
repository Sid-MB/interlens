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

#: Key the loader stamps on a trace so :func:`episode_advice` can find its shards. Not written to disk — the
#: file records only a RELATIVE ``shard_dir``, so a published trace stays portable between machines.
ROOT_KEY = "_root"


def advice_trace(run_root: str | Path | None) -> dict | None:
    """The optional advice sidecar for a run, or ``None`` when it is absent or unreadable.

    Two shapes are read, because one blob does not serve both arm sizes. A single-advised-seat arm's trace is a
    few megabytes and ships whole, with its episodes inline. An **all-advised** arm's is tens of megabytes — every
    turn is advised, so there are five times the turns and five times the claims — and is written as an index
    plus one file per episode; a reader auditing one episode then fetches that episode rather than the corpus.
    The index says which shape it is (``sharded``), so nothing is inferred from the presence of a key.

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
    if not isinstance(data, dict):
        return None
    # Where the shards live is resolved here and not stored in the file, so moving a published trace between a
    # run directory and a pages entry does not strand it.
    return {**data, ROOT_KEY: str(Path(run_root))} if data.get("sharded") else data


def episode_advice(trace: dict | None, episode_id: str | None) -> dict[str, dict]:
    """One episode's advised turns from the trace, keyed by turn index as a string.

    Reads an inline ``episodes`` map or, on a sharded trace, the one shard for this episode. Returns an empty
    dict for an episode the trace does not cover — an unadvised arm, an episode that errored, a run with no
    sidecar, or a shard that has gone missing — which is what makes every caller a no-op rather than a special
    case, and what keeps one absent shard from costing the whole render.
    """
    if not trace or not episode_id:
        return {}
    if trace.get("sharded"):
        shard = (Path(trace.get(ROOT_KEY) or ".") / str(trace.get("shard_dir") or "advice_trace")
                 / f"{episode_id}.json")
        if not shard.is_file():
            return {}
        try:
            turns = (json.loads(shard.read_text()) or {}).get("turns")
        except (OSError, json.JSONDecodeError):
            return {}
        return turns if isinstance(turns, dict) else {}
    turns = (trace.get("episodes") or {}).get(str(episode_id))
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


def round_ledger(turns: dict[str, dict]) -> list[dict]:
    """Per round, every advised seat's turn side by side — the shape an all-advised arm is read in.

    On a one-advised-seat arm a round holds one advised turn and this is the transcript in a narrower column. On
    an ALL-advised arm a round holds five, each seat deciding against its own planner at the same table state,
    and the question that matters is no longer "did this seat take its advice" but "what did the five of them do
    to each other" — which is a question this view lets a reader put, not one it answers.

    **It reports arithmetic and asserts no mechanism.** The intuitive account — that simultaneous concessions
    cancel where a lone concession transfers — was written down as a prediction with a falsifier and tested on
    an all-advised corpus; both prespecified correlations came back null, so it is a conjecture and this view
    must not be captioned as showing it. What the view is FOR is being the substrate a design that *assigns* the
    number of advised seats would be read against.

    Each round reports its rows plus the arithmetic over them: how many seats overrode, and the total own-surplus
    those overrides moved. ``conceded`` sums only the NEGATIVE deltas and ``claimed`` only the positive ones,
    kept apart rather than netted, because a round where two seats each gave up twenty points is not the same
    round as one where nobody moved, and a single net figure cannot tell them apart.

    ``advice_overridden_toward`` is defined only where a seat proposed a package of its own (an accept names an
    offer, not a deal), so ``n_measured`` reports the denominator beside the sums rather than letting a round
    with one measurable override read like a round with five.
    """
    rounds: dict[int, list[dict]] = {}
    for idx, row in sorted(turns.items(), key=lambda kv: int(kv[0])):
        rounds.setdefault(int(row.get("round") or 0), []).append({**row, "turn_idx": idx})
    ledger = []
    for number, rows in sorted(rounds.items()):
        deltas = [float((r.get("uptake") or {}).get("advice_overridden_toward"))
                  for r in rows if (r.get("uptake") or {}).get("advice_overridden_toward") is not None]
        ledger.append({
            "round": number, "rows": rows, "n_advised": len(rows),
            "n_overrode": sum(1 for r in rows if r.get("followed") is False),
            "n_measured": len(deltas),
            "conceded": -sum(d for d in deltas if d < 0),
            "claimed": sum(d for d in deltas if d > 0),
        })
    return ledger


def round_ledger_card(payload: dict) -> str:
    """The per-round, all-seats view, or ``""`` on an episode that advises fewer than two seats.

    Rendered server-side, one block per round, so the picture reads with scripting off and every number on it is
    in the page rather than computed in the browser. Omitted entirely on a single-advised-seat arm, where five
    columns would be four empty ones.
    """
    turns = {str(row["idx"]): row["advice"] for row in (payload.get("turns") or []) if row.get("advice")}
    if len({row.get("seat") for row in turns.values() if row.get("seat")}) < 2:
        return ""
    blocks = []
    for entry in round_ledger(turns):
        rows = "".join(
            f"<tr class='{'overrode' if row.get('followed') is False else 'took'}'>"
            f"<td><a href='#turn-{_e(row['turn_idx'])}'>{_e(row.get('seat'))}</a></td>"
            f"<td>{'<span class=\"badge advice-override\">overrode</span>' if row.get('followed') is False else '<span class=\"badge advice-followed\">took the advice</span>'}</td>"
            f"<td>{_e((row.get('uptake') or {}).get('emitted_kind'))}</td>"
            f"<td>{_own_delta((row.get('uptake') or {}).get('advice_overridden_toward'))}</td>"
            f"<td>{_package_words(((row.get('candidates') or [{}])[0]).get('package'))}</td></tr>"
            for row in entry["rows"])
        measured = (f"{entry['n_measured']} of them measurable" if entry["n_measured"] != entry["n_overrode"]
                    else "all measurable")
        blocks.append(
            f"<h3>Round {entry['round']}</h3><div class='card'>"
            f"<div class='pills'><span class='pill'>{entry['n_advised']} seats advised</span>"
            f"<span class='pill{' bad' if entry['n_overrode'] else ''}'>{entry['n_overrode']} overrode "
            f"({_e(measured)})</span>"
            f"<span class='pill'>own surplus given up: <b>{_num(entry['conceded'], 1)}</b></span>"
            f"<span class='pill'>taken: <b>{_num(entry['claimed'], 1)}</b></span></div>"
            f"<div class='tablewrap'><table class='advice-round'><thead><tr><th>seat</th><th>verdict</th>"
            f"<th>move</th><th>own surplus vs its own top pick</th><th>the package its planner ranked first</th>"
            f"</tr></thead><tbody>{rows}</tbody></table></div></div>")
    return f"""<section class='card advice' id='advice-rounds'><h2>All five seats, round by round</h2>
 <div class='sub'>Every seat at this table has its own parser, its own planner and its own ranked advice, so a
 round is five simultaneous decisions against one table state rather than one seat's decision against four
 fixed opponents. Each round lists what every seat was told to want and what it did instead, with the own-surplus
 cost of each override beside it. <b>Given up</b> and <b>taken</b> are kept apart rather than netted: a round in
 which two seats each concede twenty points is a different round from one in which nobody moves, and a single net
 figure cannot tell those apart. The surplus column is defined only where a seat proposed a package of its own —
 an accept names an offer id, not a deal — so a blank there is an absent measurement, not a zero.
 <b>This table is evidence to read, not an explanation.</b> The obvious account of an all-advised table — that
 concessions made at once cancel where a lone concession transfers — has been tested against a falsifier set in
 advance and did not survive it, so nothing here should be read as showing it; and the same table on a
 one-advised-seat arm has exactly one measurable seat per round by construction, which is why the spread of
 concessions across seats cannot be compared between the two arms.</div>
 {''.join(blocks)}</section>"""


def _own_delta(value: Any) -> str:
    """One seat's own-surplus change against its planner's top pick, signed and coloured, or an em dash."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "—"
    sign = "+" if value >= 0 else ""
    return f"<b class='{'pos' if value > 0 else 'neg' if value < 0 else 'zero'}'>{sign}{_num(value, 1)}</b>"


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
