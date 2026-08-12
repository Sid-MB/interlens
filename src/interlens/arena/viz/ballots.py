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

"""The final vote, as a tally a reader can check at a glance — including the ballots that were never recorded.

The forced final is the one turn where every seat must answer the same question about the same package, so it is
the one place in an episode where a missing answer is unambiguous. It is also where a defect hid for weeks: a
computable seat cast its up/down vote on whichever live offer it valued most rather than on the offer actually
under the vote, the protocol rejected that as illegal, the seat repeated itself on its single retry, and the turn
was recorded as a **pass**. A pass parses cleanly, so the episode closed, the status said ``done``, and 99% of
one arm's final ballots were silent abstentions that nothing on the page mentioned.

So the tally is deliberately built around absence. Every seat that should have voted gets a row whether or not it
produced a ballot, and a seat with no recorded ballot is called an abstention in the loudest style the page has.

**And "abstention" is where the page stops describing and starts quoting**, because the word undersells what
happened. The seat did not decline to vote: it voted, on the wrong offer id, and the record kept nothing. Both
halves of that signature are in the record — the protocol's rejection (``"The final vote is only on P9; reference
that offer id."``) and the seat's own response (``{"action": "accept", "offer_id": "P6"}``) — so the row prints
both verbatim rather than paraphrasing either. Everything downstream that called this a silent abstention was
describing the record's shape instead of the agent's behaviour.

**Derived ballots.** Where a computable policy occupied the seat, its vote has an offline answer, and gate G3
(``experiments/rational_agents/gate_seeded_offer_votes.py``) already re-derives exactly that by replaying the
policy against the view the seat really saw. Re-implementing it in the renderer would be a second opinion with
no authority, so this reads the gate's own output instead, from an optional ``vote_derivation.json`` at the run
root with the shape::

    {"episodes": {"<episode_id>": {"<turn_idx>": {"expected": {...}, "recorded": {...}, "match": false}}}}

Absent sidecar, absent run, or an episode the gate did not cover: the derived column is omitted and the recorded
tally stands on its own, which is already the part that makes the defect visible.
"""
from __future__ import annotations

import json
from pathlib import Path

from .chrome import _e

#: The turn phase carrying the forced up/down vote, and the phase that tabled the package it is a vote on.
FINAL_VOTE_PHASE = "final_vote"
FINAL_PROPOSAL_PHASE = "final_proposal"

#: The file a gate writes into a run directory to give the tally its derived column (see the module docstring).
DERIVATION_SIDECAR = "vote_derivation.json"

#: Action kinds that constitute a ballot. Anything else on a final-vote turn — a pass, an unparsed response, an
#: attempted proposal — is an abstention, whatever the seat intended.
BALLOT_ACTIONS = ("accept", "reject", "vote")

#: How much of a rejected response the tally quotes. The spoiled ballots are one JSON object of about fifty
#: characters, and a seat that wrote a scratchpad before its illegal move should still show its move — so this is
#: generous enough for the latter and the row links to the turn for anything longer.
ATTEMPT_EXCERPT_CHARS = 600


def vote_derivation(run_root: str | Path | None) -> dict | None:
    """The optional per-turn re-derivation sidecar for a run, or ``None`` when it is absent or unreadable.

    Unreadable is treated as absent on purpose: a malformed sidecar must cost the page one optional column, not
    the whole render."""
    if run_root is None:
        return None
    path = Path(run_root) / DERIVATION_SIDECAR
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _ballot_label(action: dict) -> str:
    """A recorded final-vote action as a ballot word: ``ACCEPT P9``, ``REJECT P9``, or ``no ballot``."""
    atype = str((action or {}).get("atype") or "").lower()
    if atype not in BALLOT_ACTIONS:
        return "no ballot"
    ref = (action or {}).get("offer")
    return f"{atype.upper()} {ref}".strip() if ref else atype.upper()


def _derived_for(derivation: dict | None, episode_id: str | None, idx: int) -> dict | None:
    """One turn's re-derivation row from the sidecar, tolerating both int-ish and string turn keys."""
    episodes = (derivation or {}).get("episodes") or {}
    turns = episodes.get(str(episode_id)) or {}
    row = turns.get(str(idx))
    return row if isinstance(row, dict) else None


def final_ballots(payload: dict, derivation: dict | None = None) -> dict:
    """The episode's final vote as ``{offer, rows, n_ballots, n_abstentions, n_retries, n_mismatch, derived}``.

    ``rows`` is one entry per PUBLISHED final-vote turn in order, carrying the seat, the kind of occupant, the
    recorded ballot, the parser's complaint when there was one, and — when the sidecar covers the turn — what the
    seat's own policy re-derives and whether the record matches it. ``offer`` is the package under the vote,
    taken from the offer id the forced final proposal was registered under and falling back to whichever id the
    ballots themselves reference, so a protocol whose final proposal is not in the ledger still names its own
    question.

    Returns ``{"rows": []}`` for an episode with no final-vote phase, which is most protocols; the page renders
    nothing rather than an empty table.
    """
    turns = payload.get("turns") or []
    votes = [t for t in turns if t.get("phase") == FINAL_VOTE_PHASE]
    if not votes:
        return {"offer": None, "rows": [], "n_ballots": 0, "n_abstentions": 0, "n_retries": 0,
                "n_mismatch": 0, "derived": False}
    proposal = [t for t in turns if t.get("phase") == FINAL_PROPOSAL_PHASE and t.get("published")]
    offer = next((t.get("offer_id") for t in reversed(proposal) if t.get("offer_id")), None)
    if offer is None:
        referenced = [(t.get("action") or {}).get("offer") for t in votes]
        offer = next((r for r in referenced if r), None)
    published = [t for t in votes if t.get("published", True)]
    episode_id = (payload.get("episode") or {}).get("episode_id")
    rows, derived_any = [], False
    for t in published:
        action = t.get("action") or {}
        atype = str(action.get("atype") or "").lower()
        derived = _derived_for(derivation, episode_id, int(t.get("idx")))
        derived_any = derived_any or derived is not None
        # What the seat actually said, quoted, when the record holds no ballot. This is the half of the signature
        # that names the mechanism: a rejected response reading `{"action": "accept", "offer_id": "P6"}` when only
        # P9 was up for the vote is not an abstention, it is a ballot on the wrong offer. Only for non-ballots —
        # a seat that voted legally has its vote in the ballot column and needs no transcript quoted at it.
        attempted = None
        if atype not in BALLOT_ACTIONS and (t.get("content") or "").strip():
            text = " ".join(str(t["content"]).split())
            attempted = (text[:ATTEMPT_EXCERPT_CHARS] + "…"
                         if len(text) > ATTEMPT_EXCERPT_CHARS else text)
        rows.append({
            "turn_idx": t.get("idx"),
            "seat": t.get("seat"),
            "party": t.get("party"),
            "kind": t.get("kind"),
            "ballot": _ballot_label(action),
            "is_ballot": atype in BALLOT_ACTIONS,
            "on_offer": action.get("offer"),
            # A ballot on the wrong package is a different failure from no ballot at all, and only this
            # comparison separates them.
            "off_ballot": bool(action.get("offer")) and offer is not None and action.get("offer") != offer,
            "syntax_error": action.get("syntax_error"),
            "attempted": attempted,
            "derived": (derived or {}).get("expected"),
            "derived_matches": (None if derived is None else bool(derived.get("match",
                               derived.get("expected") == derived.get("recorded")))),
        })
    return {
        "offer": offer,
        "rows": rows,
        "n_ballots": sum(1 for r in rows if r["is_ballot"]),
        "n_abstentions": sum(1 for r in rows if not r["is_ballot"]),
        # Turns in the final-vote phase that were superseded by a retry. A seat that had to be asked twice is
        # worth counting even when the second attempt succeeded.
        "n_retries": len(votes) - len(published),
        "n_mismatch": sum(1 for r in rows if r["derived_matches"] is False),
        "derived": derived_any,
    }


def ballot_table(tally: dict | None) -> str:
    """The final-vote tally as a card, or nothing when the episode has no final-vote phase.

    An abstention is styled as a hazard and stated in words, because the count is the thing that was missing: a
    reader who can see "1 of 5 seats cast no ballot" on the page does not need a forensic audit to find the
    defect that produced it. The derived column appears only when a sidecar covered at least one turn, and a
    recorded-vs-derived disagreement is called a harness bug in the row itself."""
    if not tally or not tally.get("rows"):
        return ""
    show_derived = bool(tally.get("derived"))
    head = ("<tr><th>seat</th><th>occupant</th><th>recorded ballot</th>"
            + ("<th>the seat's own policy re-derives</th><th>agrees</th>" if show_derived else "")
            + "<th>notes</th></tr>")
    body = []
    for r in tally["rows"]:
        ballot = (f"<b>{_e(r['ballot'])}</b>" if r["is_ballot"]
                  else f"<b class='neg'>NO BALLOT — abstained</b>")
        notes = []
        if r["attempted"]:
            notes.append("the seat did not stay silent — it answered "
                         f"<code>{_e(r['attempted'])}</code>")
        if r["syntax_error"]:
            notes.append((("and the protocol rejected that: " if r["attempted"]
                           else "the protocol rejected this seat's response: ")
                          + f"<i>{_e(r['syntax_error'])}</i>"))
        if r["off_ballot"]:
            notes.append(f"voted on <b>{_e(r['on_offer'])}</b>, but the vote is on "
                         f"<b>{_e(tally.get('offer'))}</b>")
        if r["derived_matches"] is False:
            notes.append("<b class='neg'>the record does not match this seat's own policy — harness bug</b>")
        derived_cells = ""
        if show_derived:
            expected = r.get("derived")
            agrees = ("—" if r["derived_matches"] is None
                      else ("yes" if r["derived_matches"] else "<b class='neg'>no</b>"))
            derived_cells = (f"<td>{_e(json.dumps(expected, sort_keys=True)) if expected else '—'}</td>"
                             f"<td>{agrees}</td>")
        body.append(f"<tr class='{'' if r['is_ballot'] else 'abstained'}'>"
                    f"<td><a href='#turn-{_e(r['turn_idx'])}'>{_e(r['seat'])}</a></td>"
                    f"<td><span class='badge {_e(r['kind'])}'>{_e(r['kind'])}</span></td>"
                    f"<td>{ballot}</td>{derived_cells}"
                    f"<td class='sub'>{' · '.join(notes) or '—'}</td></tr>")
    counts = [f"<span class='pill'>{tally['n_ballots']} ballot(s) cast</span>"]
    if tally["n_abstentions"]:
        counts.append(f"<span class='pill bad'><b class='neg'>{tally['n_abstentions']} seat(s) cast no "
                      "ballot</b></span>")
    if tally["n_retries"]:
        counts.append(f"<span class='pill'>{tally['n_retries']} retried attempt(s)</span>")
    if tally["n_mismatch"]:
        counts.append(f"<span class='pill bad'><b class='neg'>{tally['n_mismatch']} recorded-vs-derived "
                      "mismatch(es)</b></span>")
    lead = ("A missing ballot on a forced final vote is always worth seeing: the seat was asked a yes/no question "
            "about one named package and the record holds no answer. Where the seat DID answer and the protocol "
            "rejected it, both its own words and the rejection are quoted below — a response voting on some other "
            "offer id is not an abstention, and calling it one describes the record's shape rather than the "
            "agent's behaviour. Where a computable policy held the seat, its ballot has an offline answer"
            + (" and it is shown beside the record."
               if show_derived else "; run gate G3 with its sidecar flag to show it beside the record."))
    return (f"<section class='card ballots{' hazard' if (tally['n_abstentions'] or tally['n_mismatch']) else ''}'"
            f" id='ballots'><h2>The final vote on <code>{_e(tally.get('offer'))}</code></h2>"
            f"<div class='sub'>{lead}</div><div class='pills'>{''.join(counts)}</div>"
            f"<div class='tablewrap'><table><thead>{head}</thead><tbody>{''.join(body)}</tbody></table></div>"
            "</section>")
