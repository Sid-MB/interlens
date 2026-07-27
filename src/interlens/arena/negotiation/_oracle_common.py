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

# [rational_agents scaffold: oracles-strategies] 2026-07-23
"""Shared plumbing for the negotiation oracle stack (beliefs / acceptance / bestresponse / equilibrium /
strategies), written once: the ``|D|×n`` utility/surplus tables (:class:`GameTables`), the structured
:class:`NegotiationState` a policy reads, turn-context readers over the (loose) history/offer-registry shapes,
and the ``make_verdict`` constructor. The typed actions and the ``Oracle`` ABC / ``OracleVerdict`` are imported
from interlens-core (``arena/actions.py``, ``arena/oracles.py``).

A *game* is duck-typed: any object exposing ``.space`` and seat-indexed ``.sheets`` works, plus optionally
``.rounds`` / ``.info`` / ``.discount`` / ``.proposer`` / ``.veto`` (the real one is
:class:`~interlens.arena.negotiation.sheets.GameSpec`). ``Deal = tuple[int, ...]`` is one option index per issue.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable

import numpy as np

# The typed actions and the Oracle ABC / OracleVerdict are owned by interlens-core; import them directly (no
# import cycle — the arena action/oracle layer does not import the negotiation package). ``_jsonify`` is the ONE
# JSON-coercion for oracle diagnostics, owned by ``arena.oracles`` and reused here by ``make_verdict``.
from ..actions import Accept, Propose, Reject, Walk
# Name-based action (de)serialization lives next to the action types in ``arena.actions``; re-exported here so
# the negotiation stack's consumers (e.g. PolicyParticipant) keep one import site.
from ..actions import action_to_json, action_to_message_content, deal_from_json  # noqa: F401
from ..oracles import Oracle, OracleVerdict, _jsonify

if TYPE_CHECKING:  # concrete game classes, used only in type hints (the real space.py / sheets.py types)
    from .sheets import ScoreSheet
    from .space import DealSpace

Deal = tuple[int, ...]


def make_verdict(action_values, best=None, *, beliefs=None, flags=None, extra=None) -> OracleVerdict:
    """Build an ``OracleVerdict`` with its free-form ``extra`` diagnostics coerced JSON-safe up front (the
    ``|D|×n`` numpy tables / typed actions the oracles stash) via the shared ``_jsonify``, so ``to_json`` and the
    episode save never crash. ``beliefs`` is coerced later by ``OracleVerdict.to_json``."""
    return OracleVerdict(action_values=action_values, best=best, beliefs=beliefs,
                         flags=list(flags or []), extra=_jsonify(dict(extra or {})))


# --------------------------------------------------------------------------------------------------------- #
# Utility bookkeeping: enumerate once, vectorize the |D| x n surplus/utility tables.
# --------------------------------------------------------------------------------------------------------- #
def deal_list(space: DealSpace) -> list[Deal]:
    """Materialize the deal space in a *stable* order (matrix rows below use this exact order)."""
    return [tuple(int(x) for x in d) for d in space.enumerate()]


def issue_sizes(space: DealSpace | None = None, sheets: Iterable[ScoreSheet] | None = None,
                deals: list[Deal] | None = None) -> tuple[int, ...]:
    """Per-issue option counts ``(O_1, ..., O_J)``, discovered from (in order): an ``.issue_sizes`` /
    ``.n_options`` attribute on the space; a sheet's ``.values`` rows; or the max option index seen in
    ``deals``. Needed by the belief oracle to build per-issue evaluator hypotheses."""
    if space is not None:
        for attr in ("shape", "issue_sizes", "n_options", "sizes"):
            v = getattr(space, attr, None)
            if v:
                return tuple(int(x) for x in v)
    if sheets is not None:
        for s in sheets:
            vals = getattr(s, "values", None)
            if vals is not None:
                return tuple(len(row) for row in vals)
            break
    if deals:
        arr = np.asarray(deals, dtype=int)
        return tuple(int(x) for x in (arr.max(axis=0) + 1))
    raise ValueError("cannot infer issue_sizes: pass a space with sizes, sheets with .values, or deals")


@dataclass
class GameTables:
    """Precomputed dense tables for a game — built once, shared by every oracle so the ``O(n*J*|D|)``
    utility pass is never duplicated.

    Attributes
    ----------
    deals : list[Deal]
        The deal space in stable order.
    index : dict[Deal, int]
        Inverse map ``deal -> row``.
    deals_arr : np.ndarray
        ``(|D|, J)`` int array of option indices.
    utility : np.ndarray
        ``(|D|, n)`` per-deal per-agent utility.
    surplus : np.ndarray
        ``(|D|, n)`` per-deal per-agent surplus ``utility - threshold``.
    thresholds : np.ndarray
        ``(n,)`` per-agent reservation thresholds.
    """

    deals: list[Deal]
    index: dict[Deal, int]
    deals_arr: np.ndarray
    utility: np.ndarray
    surplus: np.ndarray
    thresholds: np.ndarray

    @property
    def n_deals(self) -> int:
        return len(self.deals)

    @property
    def n_agents(self) -> int:
        return self.utility.shape[1]

    @classmethod
    def build(cls, space: DealSpace, sheets: list[ScoreSheet]) -> "GameTables":
        """Enumerate ``space`` and vectorize utilities over ``sheets``. Uses each sheet's ``.values`` rows
        when present (a single fancy-index per issue); otherwise falls back to calling ``sheet.utility``."""
        deals = deal_list(space)
        deals_arr = np.asarray(deals, dtype=int)
        n = len(sheets)
        D, J = deals_arr.shape
        util = np.zeros((D, n), dtype=float)
        for si, s in enumerate(sheets):
            vals = getattr(s, "values", None)
            if vals is not None:
                for j in range(J):
                    col = np.asarray(vals[j], dtype=float)
                    util[:, si] += col[deals_arr[:, j]]
            else:
                for di in range(D):
                    util[di, si] = float(s.utility(deals[di]))
        thr = np.asarray([float(getattr(s, "threshold", 0.0)) for s in sheets], dtype=float)
        surplus = util - thr[None, :]
        index = {d: i for i, d in enumerate(deals)}
        return cls(deals, index, deals_arr, util, surplus, thr)

    @classmethod
    def from_game(cls, game) -> "GameTables":
        """Build from a ``GameSpec``-like object exposing ``.space`` and ``.sheets``. Reuses the game's own
        ``utility_matrix()`` when available (identical mixed-radix row order) to avoid recomputation."""
        space = game.space
        sheets = list(game.sheets)
        um = getattr(game, "utility_matrix", None)
        if callable(um):
            deals = deal_list(space)
            deals_arr = np.asarray(deals, dtype=int)
            util = np.asarray(um(), dtype=float)
            thr = (np.asarray(game.thresholds, dtype=float) if hasattr(game, "thresholds")
                   else np.asarray([float(getattr(s, "threshold", 0.0)) for s in sheets]))
            index = {d: i for i, d in enumerate(deals)}
            return cls(deals, index, deals_arr, util, util - thr[None, :], thr)
        return cls.build(space, sheets)


# --------------------------------------------------------------------------------------------------------- #
# Small numeric helpers (kept local so the oracle modules share one implementation).
# --------------------------------------------------------------------------------------------------------- #
def logsumexp(a: np.ndarray, axis=None) -> np.ndarray:
    """Numerically stable ``log(sum(exp(a)))``."""
    a = np.asarray(a, dtype=float)
    m = np.max(a, axis=axis, keepdims=True)
    m = np.where(np.isneginf(m), 0.0, m)
    out = np.log(np.sum(np.exp(a - m), axis=axis, keepdims=True)) + m
    return np.squeeze(out, axis=axis) if axis is not None else float(out)


def softmax(a: np.ndarray, temperature: float = 1.0, axis=-1) -> np.ndarray:
    """Tempered softmax; ``temperature -> 0`` approaches a hard argmax (used to break equilibrium cycles)."""
    a = np.asarray(a, dtype=float) / max(temperature, 1e-12)
    a = a - np.max(a, axis=axis, keepdims=True)
    e = np.exp(a)
    return e / np.sum(e, axis=axis, keepdims=True)


def normalize(w: np.ndarray, floor: float = 0.0) -> np.ndarray:
    """Return a probability vector from nonnegative weights, optionally mixed with ``floor`` uniform mass."""
    w = np.asarray(w, dtype=float)
    w = np.clip(w, 0.0, None)
    s = w.sum()
    p = np.full_like(w, 1.0 / len(w)) if s <= 0 else w / s
    if floor > 0:
        p = (1.0 - floor) * p + floor / len(p)
    return p


# --------------------------------------------------------------------------------------------------------- #
# Negotiation view/state that policies consume, and the action <-> message serialization.
# --------------------------------------------------------------------------------------------------------- #
@dataclass
class NegotiationState:
    """The structured state a ``Policy`` reads to compute its next action — the machine-readable counterpart
    of the text ``view`` an LLM seat reads, so a ``PolicyParticipant`` and an LLM participant are
    interchangeable seats.

    Attributes
    ----------
    seat : int
        This policy's seat index.
    sheet : ScoreSheet
        This seat's private score sheet.
    space : DealSpace
        The shared deal space.
    round : int
        Current round (1-indexed).
    deadline : int
        Total number of rounds ``T`` (turn-count deadline, restated every turn).
    offers : dict[str, Deal]
        Live offer registry: ``offer_id -> deal``.
    standing : str | None
        The offer id this seat is being asked to respond to (most recent live offer), if any.
    received : list[Deal]
        Opponent-proposed deals in order (feeds MiCRO / tit-for-tat / belief updates).
    my_offers : list[Deal]
        This seat's own past proposals in order.
    discount : float
        Per-round discount / breakdown-risk ``delta`` (1.0 = none).
    tables : GameTables | None
        Optional cached tables for the full game (only available under full information).
    opponents : tuple[int, ...]
        Seat indices of the other parties.
    must_vote : bool
        True on a vote-only turn (the scenario's forced-final phase): the seat may ONLY accept/reject/walk the
        standing offer, not propose. Policies read this and cast a terminal individually-rational vote
        (accept any offer that clears their threshold, since the only alternative is no-deal = 0). Proposing
        here is an economic-legality violation, so a proposing policy would otherwise blow the deal.
    """

    seat: int
    sheet: ScoreSheet
    space: DealSpace
    round: int = 1
    deadline: int = 1
    offers: dict = field(default_factory=dict)
    standing: str | None = None
    received: list = field(default_factory=list)
    my_offers: list = field(default_factory=list)
    discount: float = 1.0
    tables: GameTables | None = None
    opponents: tuple = ()
    must_vote: bool = False

    @property
    def standing_deal(self) -> Deal | None:
        """The deal referenced by ``standing`` (or None)."""
        return self.offers.get(self.standing) if self.standing else None

    @property
    def time_fraction(self) -> float:
        """``(round-1)/deadline`` in ``[0, 1)`` — the ``t`` used by time-dependent concession curves."""
        return (self.round - 1) / max(self.deadline, 1)

    @classmethod
    def from_block(cls, block: dict, *, sheet, space, tables=None, discount: float = 1.0,
                   opponents: tuple = (), seat: int | None = None) -> "NegotiationState":
        """Build a state from a scenario-emitted ``negotiation_state`` block (see ``parse_negotiation_state``)
        plus the seat-bound context (``sheet``/``space``/``tables``/``discount``/``opponents``). The block
        carries only the dynamic fields — ``seat``, ``round``, ``deadline``, ``offers`` (``{id: [opt,...]}``),
        ``standing`` (id or null), ``received``/``my_offers`` (lists of deals) — so a ``PolicyParticipant``
        can read the scenario's authoritative offer registry straight from its view."""
        offers = {k: tuple(int(x) for x in v) for k, v in (block.get("offers") or {}).items()}
        return cls(seat=int(block.get("seat", seat if seat is not None else 0)), sheet=sheet, space=space,
                   round=int(block.get("round", 1)), deadline=int(block.get("deadline", 1)),
                   offers=offers, standing=block.get("standing"),
                   received=[tuple(int(x) for x in d) for d in block.get("received", [])],
                   my_offers=[tuple(int(x) for x in d) for d in block.get("my_offers", [])],
                   discount=discount, tables=tables, opponents=tuple(opponents),
                   must_vote=bool(block.get("must_vote", False)))


def seat_index(game, agent) -> int:
    """Resolve ``agent`` to a seat index. Accepts an int (returned as-is) or a seat *name* (str), which is
    matched against ``sheet.agent`` on each score sheet, then against a ``game.seats``/``seat_names``/
    ``agents`` name list, then an int-like string. The real ``Oracle`` ABC types ``agent`` as ``str`` (the
    seat name), so oracles call this first before indexing the seat-indexed utility tables."""
    if isinstance(agent, (int, np.integer)):
        return int(agent)
    sheets = list(getattr(game, "sheets", []) or [])
    for i, s in enumerate(sheets):
        if getattr(s, "agent", None) == agent:
            return i
    for attr in ("seats", "seat_names", "agents", "names"):
        names = getattr(game, attr, None)
        if names is not None and agent in list(names):
            return list(names).index(agent)
    try:
        return int(agent)
    except Exception as e:
        raise KeyError(f"cannot resolve seat index for agent {agent!r}") from e


_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def parse_action_json(text: str) -> dict | None:
    """Extract the last fenced-JSON action object from ``text`` (the last block wins, mirroring the arena's
    'trailing action' convention). Returns the parsed dict or None."""
    matches = _FENCE.findall(text or "")
    for raw in reversed(matches):
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if isinstance(obj, dict) and ("action" in obj or "proposal" in obj or "deal" in obj):
            return obj
    return None


# --------------------------------------------------------------------------------------------------------- #
# Turn-context readers, tolerant of the (not-yet-frozen) history / offer-registry shapes. Shared by the
# acceptance and best-response oracles so there is one implementation.
# --------------------------------------------------------------------------------------------------------- #
def game_tables(game) -> GameTables:
    """``GameTables`` for ``game``, cached on the game object when possible."""
    t = getattr(game, "_tables_cache", None)
    if t is None:
        t = GameTables.from_game(game)
        try:
            game._tables_cache = t
        except Exception:
            pass
    return t


def offer_registry(game, history) -> dict:
    """Recover ``{offer_id: Deal}`` from the game/history. Prefers an explicit registry, read as either an
    ``offers`` ATTRIBUTE (``history.offers`` / ``game.offers``) or, when ``history`` is a mapping, an ``offers``
    KEY -- the shape the scenario's per-turn history snapshot carries (``ScorableNegotiation._history_snapshot``
    stores ``offers`` as a LIST of serialized ``Offer`` dicts, each with ``offer_id`` + ``deal``). The registry
    may thus be a ``{id: offer}`` mapping OR a list of ``Offer.to_json()`` dicts / ``Offer`` objects. Falls back
    to scanning turns for ``Propose`` actions, assigning sequential ids ``O1, O2, ...`` in order of appearance.

    Getting this right is load-bearing: if the standing offers are lost, the acceptance / threshold /
    best-response oracles value every ``Accept`` at the no-deal continuation instead of the offer's realized
    surplus (the single-shot mis-scoring bug), so a rational accept reads as 0 regret AND 0 value."""
    for src in (history, game):
        reg = getattr(src, "offers", None)
        if reg is None and isinstance(src, dict):
            reg = src.get("offers")                          # scenario history snapshot: an `offers` key
        if isinstance(reg, dict) and reg:
            return {k: tuple(int(x) for x in getattr(v, "deal", v)) for k, v in reg.items()}
        if isinstance(reg, list) and reg:                    # a list of Offer.to_json() dicts (or Offer objects)
            out: dict = {}
            for o in reg:
                oid = o.get("offer_id") if isinstance(o, dict) else getattr(o, "offer_id", None)
                deal = o.get("deal") if isinstance(o, dict) else getattr(o, "deal", None)
                if oid is not None and deal is not None:
                    out[str(oid)] = tuple(int(x) for x in deal)
            if out:
                return out
    out = {}
    n = 0
    for turn in (history or []):
        act = getattr(turn, "action", None)
        if act is None and isinstance(turn, dict):
            act = turn.get("action")
        deal = getattr(act, "deal", None)
        if deal is None and isinstance(act, dict) and act.get("action") == "propose":
            deal = act.get("deal")
        if deal is not None:
            n += 1
            out[f"O{n}"] = tuple(int(x) for x in deal)
    return out


def n_agents(game) -> int:
    return len(list(getattr(game, "sheets", []) or [])) or 1


def rounds_left(game, history) -> int:
    """Rounds remaining (this turn inclusive). Uses ``game.rounds`` and completed rounds when discoverable;
    defaults to ``game.rounds`` (or 1)."""
    T = int(getattr(game, "rounds", 0) or 0)
    if T <= 0:
        return 1
    r = getattr(history, "round", None)
    if r is None and history:
        r = len(history) // max(n_agents(game), 1)
    return max(T - int(r or 0), 1)


def current_round(game, history) -> int:
    """1-indexed current round."""
    T = int(getattr(game, "rounds", 0) or 1)
    return max(T - rounds_left(game, history) + 1, 1)


def effective_discount(game, override=None) -> float:
    """The per-round continuation factor the acceptance/best-response/equilibrium oracles should use, read
    from the game as the single source of truth: ``discount * (1 - breakdown_risk)`` (time preference times
    the per-round no-breakdown survival probability — the BRW 1986 breakdown model). An explicit ``override``
    (a non-None oracle-level ``discount``) wins, so a caller can still force a value; otherwise the game's own
    impatience is honored. ``GameSpec`` defaults ``discount=1.0`` (neutral) / ``breakdown_risk=0.0``, which
    yields the Sandholm-Vulkan brinkmanship baseline — set ``discount < 1`` on the game for interior
    concession to be rational."""
    if override is not None:
        return float(override)
    d = float(getattr(game, "discount", 1.0))
    b = float(getattr(game, "breakdown_risk", 0.0))
    return d * (1.0 - b)


def proposer_sequence(game) -> list:
    """Per-round proposer seat indices. Uses ``game.proposer_sequence`` if present; else a rotation starting
    at ``game.proposer`` (default 0) over ``range(n)`` — DESIGN §3 'rotating proposer'."""
    seq = getattr(game, "proposer_sequence", None)
    if seq:
        return [int(x) for x in seq]
    n = n_agents(game)
    start = int(getattr(game, "proposer", 0) or 0)
    return [(start + k) % n for k in range(n)]


def parse_negotiation_state(text: str) -> dict | None:
    """Extract the last fenced JSON object carrying a top-level ``"negotiation_state"`` key and return that
    inner dict — the authoritative structured-state channel a scenario embeds in a seat's view so a
    ``PolicyParticipant`` reads canonical offer ids / round instead of reconstructing them from the transcript.
    """
    for raw in reversed(_FENCE.findall(text or "")):
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("negotiation_state"), dict):
            return obj["negotiation_state"]
    return None
