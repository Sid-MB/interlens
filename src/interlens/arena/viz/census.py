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
# [rational_agents: viz-upgrades] 2026-08-12

"""How much of an episode is actually play: the per-turn census, and the strip that puts it in the page header.

The existing contamination banner counts turns the ENGINE fabricated, and it is right to be loud about them. But
it is a screen for one cause, and a turn can carry nothing for reasons the engine never sees:

- a thinking model spends its entire per-turn budget inside an unterminated ``<think>`` block, so the harness
  substitutes the same placeholder text — with ``gen_failed`` false, because generation succeeded, it just never
  produced a visible answer;
- a move is rejected as illegal, the seat repeats itself on its one retry, and the turn is recorded as a pass;
- a seat talks and takes no formal action at all, which is legal play but is not a move.

All three render as an ordinary, well-formed, quiet turn. A campaign cell reached **24% silent turns while
passing every gate**, including the fabrication gate, because 0.000 fabricated was the honest answer to the only
question anyone was asking. This module asks the other questions, on one episode, and puts the answers where a
reader cannot walk past them: non-action rate, placeholder count, at-cap count, and the same three by round.
"""
from __future__ import annotations

from .chrome import _e, _num

#: A turn is treated as pressed against its generation cap when its output is within this many tokens of it.
#: Two rather than zero because a sampler can stop a token or two early; the same slack the campaign's own
#: reporting uses (``report_local_cell.rollout_gates``), so a page and a cell report cannot disagree about
#: which turns ran out of room.
AT_CAP_SLACK = 2


def at_cap(row: dict) -> bool:
    """Whether one payload turn spent essentially its whole generation budget.

    There is no ``stop_reason`` on the local generation path, so "ran out of room" has to be inferred from
    output length against the per-turn cap the scenario stamped on the request. A turn with no recorded cap
    cannot be judged and is not counted."""
    cap = row.get("cap")
    if not cap:
        return False
    return int(row.get("n_tokens_out") or 0) >= int(cap) - AT_CAP_SLACK


def turn_census(rows: list[dict]) -> dict:
    """Count the ways this episode's turns carried nothing, from the payload's own turn rows.

    ``rows`` are the payload turns (see :func:`~interlens.arena.viz.episode.episode_payload`), which already
    carry the three facts this needs — ``silent`` and ``gen_failed`` from the placeholder screen, ``action.atype``
    from the parse, and ``cap`` / ``n_tokens_out`` from generation accounting. Deriving the census from the same
    rows the page renders is deliberate: a header that disagreed with the transcript below it would be worse
    than no header.

    Returns ``{n_turns, placeholder, placeholder_budget_burned, placeholder_engine_failure, non_action,
    non_action_rate, at_cap, at_cap_rate, placeholder_rate, by_round: [...], clean}``. ``by_round`` is one row
    per round in play order with the same counts, which is what turns "a quarter of this episode is silent" into
    "and all of it is in the last two rounds". ``clean`` is true only when every count is zero.
    """
    placeholder = [r for r in rows if r.get("silent")]
    # An engine failure is already screened for and stamped upstream (``arena.engine.gen_failures``); the
    # remainder is the model burning its whole budget without emitting an answer. Splitting them here rather
    # than re-deriving keeps one detector for the engine's half.
    engine = [r for r in placeholder if r.get("gen_failed")]
    non_action = [r for r in rows if str((r.get("action") or {}).get("atype") or "") in ("none", "unparsed", "")]
    capped = [r for r in rows if at_cap(r)]
    n = len(rows)

    def rate(k: int) -> float | None:
        return round(k / n, 4) if n else None

    # Membership by identity, not by value: two turns of one episode can hold equal dicts (two seats passing in
    # the same round), and a value-based ``in`` would credit both to whichever came first.
    silent_ids = {id(r) for r in placeholder}
    non_action_ids = {id(r) for r in non_action}
    capped_ids = {id(r) for r in capped}
    by_round: dict = {}
    for r in rows:
        bucket = by_round.setdefault(r.get("round"), {"round": r.get("round"), "n_turns": 0, "placeholder": 0,
                                                     "non_action": 0, "at_cap": 0})
        bucket["n_turns"] += 1
        bucket["placeholder"] += 1 if id(r) in silent_ids else 0
        bucket["non_action"] += 1 if id(r) in non_action_ids else 0
        bucket["at_cap"] += 1 if id(r) in capped_ids else 0
    ordered = [by_round[k] for k in sorted(by_round, key=lambda x: (x is None, x))]
    return {
        "n_turns": n,
        "placeholder": len(placeholder),
        "placeholder_rate": rate(len(placeholder)),
        "placeholder_budget_burned": len(placeholder) - len(engine),
        "placeholder_engine_failure": len(engine),
        "non_action": len(non_action),
        "non_action_rate": rate(len(non_action)),
        "at_cap": len(capped),
        "at_cap_rate": rate(len(capped)),
        "by_round": ordered,
        "clean": not (placeholder or non_action or capped),
    }


def _cell(key: str, value: str, note: str, *, bad: bool, tooltip: str) -> str:
    return (f"<div class='censuscell{' bad' if bad else ''}' title='{_e(tooltip)}'>"
            f"<span class='k'>{_e(key)}</span><span class='v'>{value}</span>"
            f"<span class='n'>{_e(note)}</span></div>")


def _by_round_tooltip(census: dict, key: str) -> str:
    """The per-round breakdown of one count, as the cell's hover text."""
    rows = census.get("by_round") or []
    if not rows:
        return "no turns recorded"
    return "by round — " + ", ".join(f"r{r['round']}: {r[key]}/{r['n_turns']}" for r in rows)


def census_strip(census: dict | None) -> str:
    """The per-episode census as a compact header strip, always rendered when there are turns to count.

    Present even when everything is zero, because "this episode has no silent turns" is the claim a reader needs
    and an absent strip cannot make it. Non-zero counts are styled as hazards and every cell carries its
    by-round breakdown on hover."""
    if not census or not census.get("n_turns"):
        return ""
    n = census["n_turns"]
    burned, engine = census["placeholder_budget_burned"], census["placeholder_engine_failure"]
    split = (f"{burned} burned the budget, {engine} engine failure" if census["placeholder"]
             else "no placeholder turns")
    cells = [
        _cell("non-action turns", f"{census['non_action']}<span class='of'>/{n}</span>",
              f"{_num(100 * (census['non_action_rate'] or 0), 1)}% of turns",
              bad=bool(census["non_action"]),
              tooltip="Turns that published no formal move — a pass, an unparsed response, or talk only. "
                      + _by_round_tooltip(census, "non_action")),
        _cell("placeholder turns", f"{census['placeholder']}<span class='of'>/{n}</span>", split,
              bad=bool(census["placeholder"]),
              tooltip="Turns whose visible text is the engine's placeholder. "
                      + _by_round_tooltip(census, "placeholder")),
        _cell("at the token cap", f"{census['at_cap']}<span class='of'>/{n}</span>",
              f"{_num(100 * (census['at_cap_rate'] or 0), 1)}% spent the whole budget",
              bad=bool(census["at_cap"]),
              tooltip=f"Output within {AT_CAP_SLACK} tokens of the per-turn cap stamped on the request. "
                      + _by_round_tooltip(census, "at_cap")),
    ]
    lead = ("<span class='censushd ok'>every turn of this episode carried a move</span>" if census["clean"]
            else "<span class='censushd'>how much of this episode is play</span>")
    return f"<div class='census' role='note'>{lead}{''.join(cells)}</div>"
