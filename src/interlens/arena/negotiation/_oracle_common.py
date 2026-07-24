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
strategies) so the |D|xn utility bookkeeping and the typed-action layer are written once, not four times.

This module deliberately depends on the DESIGN.md §8 *frozen shapes* by duck-typing, not by importing the
concrete classes eagerly:

- ``Deal = tuple[int, ...]`` — one option index per issue.
- a *sheet* exposes ``.threshold: float``, ``.utility(deal) -> float``, ``.surplus(deal) -> float`` (and,
  when available, ``.values`` = per-issue option-value rows, which we use to vectorize).
- a *space* exposes ``.enumerate() -> Iterator[Deal]`` and ``.size: int``.
- a *game* exposes ``.space`` and ``.sheets`` (seat-indexed), plus optionally ``.rounds``, ``.info``,
  ``.discount``, ``.proposer``, ``.veto``.

The typed actions (``Propose``/``Accept``/``Reject``/``Walk``) and the ``Oracle`` ABC / ``OracleVerdict`` are
owned by interlens-core (``arena/actions.py``, ``arena/oracles.py``). We *try to import them* and fall back to
faithful local mirrors of the frozen shapes, so this scaffold runs and tests green before those land and then
adopts the real types automatically once the names resolve. The mirrors are the single swap point.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Iterable, Iterator, Protocol, runtime_checkable

import numpy as np


def jsonify(obj):
    """Recursively coerce an oracle-diagnostics payload to a JSON-serializable form so ``OracleVerdict.extra``
    always survives ``to_json()`` / the engine's episode save. Handles: numpy arrays/scalars -> lists/py
    scalars; objects with ``.to_json()`` (the typed actions) -> their json; other dataclasses (e.g.
    ``OpponentType``) -> their fields; dicts with non-string keys (e.g. an ``{Action: value}`` map) -> a list
    of ``{"key", "value"}`` entries; tuples/lists element-wise."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.generic):
        return obj.item()
    to_json = getattr(obj, "to_json", None)
    if callable(to_json):
        try:
            return to_json()
        except Exception:
            pass
    if is_dataclass(obj) and not isinstance(obj, type):
        return jsonify(asdict(obj))
    if isinstance(obj, dict):
        if all(isinstance(k, str) for k in obj):
            return {k: jsonify(v) for k, v in obj.items()}
        return [{"key": jsonify(k), "value": jsonify(v)} for k, v in obj.items()]
    if isinstance(obj, (list, tuple, set)):
        return [jsonify(x) for x in obj]
    return obj

Deal = tuple[int, ...]


# --------------------------------------------------------------------------------------------------------- #
# Frozen-shape protocols (structural typing; the real space.py / sheets.py classes satisfy these).
# --------------------------------------------------------------------------------------------------------- #
@runtime_checkable
class SheetLike(Protocol):
    """A private additive score sheet: ``utility(deal) = sum_j values[j][deal[j]]`` with a reservation
    ``threshold`` (the BATNA); ``surplus = utility - threshold``."""

    threshold: float

    def utility(self, deal: Deal) -> float: ...

    def surplus(self, deal: Deal) -> float: ...


@runtime_checkable
class SpaceLike(Protocol):
    """The enumerable discrete deal space ``D = prod_j O_j``."""

    size: int

    def enumerate(self) -> Iterator[Deal]: ...


# --------------------------------------------------------------------------------------------------------- #
# Typed actions + Oracle ABC: import the real ones, else mirror the DESIGN §8 shapes (single swap point).
# --------------------------------------------------------------------------------------------------------- #
try:  # interlens-core (T1) owns these; adopt automatically once the module exists.
    from ..actions import Propose, Accept, Reject, Walk  # type: ignore
    _ACTIONS_ARE_LOCAL = False
except Exception:  # pragma: no cover - exercised only before actions.py lands
    @dataclass(frozen=True)
    class Propose:
        """Register a complete deal as a binding offer. ``deal`` is one option index per issue."""

        deal: Deal

    @dataclass(frozen=True)
    class Accept:
        """Accept a specific live offer by id (unambiguous with >=2 standing offers)."""

        offer_id: str

    @dataclass(frozen=True)
    class Reject:
        """Reject a specific live offer by id."""

        offer_id: str

    @dataclass(frozen=True)
    class Walk:
        """Explicit no-deal exit — no-deal is a decision, not a timeout."""

    _ACTIONS_ARE_LOCAL = True


try:  # interlens-core (T1) owns these too.
    from ..oracles import Oracle, OracleVerdict  # type: ignore
    _ORACLE_IS_LOCAL = False
except Exception:  # pragma: no cover - exercised only before oracles.py lands
    @dataclass
    class OracleVerdict:
        """A per-turn oracle reading (mirror of the DESIGN §8 shape).

        Parameters
        ----------
        action_values : dict
            Maps each legal action (a hashable ``Propose``/``Accept``/``Reject``/``Walk``) to its value in
            surplus units — the centipawn-loss analog (Regan & Haworth 2011).
        best : object
            The value-maximizing legal action (the oracle-preferred move).
        beliefs : object | None
            Optional belief payload (posterior over opponent types / induced distributions).
        flags : list[str]
            Hard-violation / diagnostic tags (e.g. ``"premature_accept"``, ``"ir_violation"``).
        extra : dict
            Free-form diagnostics (surplus-loss of a reference action, reservation value, timings). Present
            on the local mirror only; when the real ``OracleVerdict`` lacks it these are folded into
            ``beliefs``/``flags`` by ``make_verdict``.
        """

        action_values: dict
        best: object = None
        beliefs: object = None
        flags: list = field(default_factory=list)
        extra: dict = field(default_factory=dict)

    class Oracle(ABC):
        """Per-turn evaluation oracle. ``evaluate`` scores every legal action for one agent at one turn."""

        @abstractmethod
        def evaluate(self, game, history, agent, legal) -> "OracleVerdict":
            ...

    _ORACLE_IS_LOCAL = True


def make_verdict(action_values, best=None, *, beliefs=None, flags=None, extra=None) -> "OracleVerdict":
    """Build an ``OracleVerdict`` that works whether ``OracleVerdict`` is the real one or the local mirror.

    If the target dataclass has no ``extra`` field, the ``extra`` diagnostics are attached as a dynamic
    attribute (best-effort) so nothing is lost; ``beliefs``/``flags`` always map to the frozen fields."""
    flags = list(flags or [])
    extra = jsonify(dict(extra or {}))   # keep extra JSON-serializable so to_json()/episode-save never crash
    try:
        v = OracleVerdict(action_values=action_values, best=best, beliefs=beliefs, flags=flags, extra=extra)
    except TypeError:
        v = OracleVerdict(action_values=action_values, best=best, beliefs=beliefs, flags=flags)
        try:
            v.extra = extra  # type: ignore[attr-defined]
        except Exception:
            pass
    return v


# --------------------------------------------------------------------------------------------------------- #
# Utility bookkeeping: enumerate once, vectorize the |D| x n surplus/utility tables.
# --------------------------------------------------------------------------------------------------------- #
def deal_list(space: SpaceLike) -> list[Deal]:
    """Materialize the deal space in a *stable* order (matrix rows below use this exact order)."""
    return [tuple(int(x) for x in d) for d in space.enumerate()]


def issue_sizes(space: SpaceLike | None = None, sheets: Iterable[SheetLike] | None = None,
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
    def build(cls, space: SpaceLike, sheets: list[SheetLike]) -> "GameTables":
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
    sheet : SheetLike
        This seat's private score sheet.
    space : SpaceLike
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
    sheet: SheetLike
    space: SpaceLike
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


def action_to_json(action, issue_names: list[str] | None = None,
                   option_names: list[list[str]] | None = None) -> dict:
    """Serialize a typed action to the canonical fenced-JSON envelope. Delegates to the action's own
    ``.to_json()`` (index-based ``deal``) unless ``issue_names`` is supplied, in which case ``Propose`` is
    rendered with issue/option names for LLM-legibility. This is the format both ``PolicyParticipant`` and
    LLM seats emit."""
    if isinstance(action, Propose) and issue_names is not None:
        if option_names is not None:
            deal = {issue_names[j]: option_names[j][action.deal[j]] for j in range(len(action.deal))}
        else:
            deal = {issue_names[j]: int(action.deal[j]) for j in range(len(action.deal))}
        return {"action": "propose", "deal": deal}
    to_json = getattr(action, "to_json", None)
    if callable(to_json):
        return to_json()
    if isinstance(action, Propose):
        return {"action": "propose", "deal": list(int(x) for x in action.deal)}
    if isinstance(action, Accept):
        return {"action": "accept", "offer_id": action.offer_id}
    if isinstance(action, Reject):
        return {"action": "reject", "offer_id": action.offer_id}
    if isinstance(action, Walk):
        return {"action": "walk"}
    raise TypeError(f"not a negotiation action: {action!r}")


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


def action_to_message_content(action, *, preface: str = "", issue_names=None, option_names=None) -> str:
    """Render an action as a message body: optional free-text ``preface`` then a fenced ``json`` action
    block — the exact envelope an LLM seat produces, so the transcript is symmetric across seat types."""
    body = "```json\n" + json.dumps(action_to_json(action, issue_names, option_names)) + "\n```"
    return f"{preface}\n{body}" if preface else body


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


def deal_from_json(deal_field, issue_names: list[str] | None = None,
                   option_names: list[list[str]] | None = None) -> Deal | None:
    """Parse a ``deal`` payload (index list, or a ``{issue: option}`` dict by name/index) back to a ``Deal``.
    Tolerates name or index option values. Returns None if malformed."""
    if isinstance(deal_field, (list, tuple)):
        try:
            return tuple(int(x) for x in deal_field)
        except Exception:
            return None
    if isinstance(deal_field, dict) and issue_names is not None:
        out = []
        for j, name in enumerate(issue_names):
            v = deal_field.get(name)
            if v is None:
                for k in deal_field:
                    if str(k).lower().replace(" ", "") == name.lower().replace(" ", ""):
                        v = deal_field[k]
                        break
            if v is None:
                return None
            if isinstance(v, int) or (isinstance(v, str) and v.isdigit()):
                out.append(int(v))
            elif option_names is not None:
                opts = [o.lower() for o in option_names[j]]
                if str(v).strip().lower() not in opts:
                    return None
                out.append(opts.index(str(v).strip().lower()))
            else:
                return None
        return tuple(out)
    return None
