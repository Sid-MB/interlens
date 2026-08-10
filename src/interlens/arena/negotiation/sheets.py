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
# [rational_agents scaffold: game-theory] 2026-07-23

"""Private score sheets, the additive utility model, the game specification, and the NumPy utility matrix.

Each party holds a secret **score sheet**: an integer/real value for every option of every issue, plus a
private acceptance **threshold** ``tau_i`` (its BATNA / reservation value). Utility is the Keeney-Raiffa additive
form ``u_i(d) = sum_j s_ij(d_j)`` [keeney_raiffa1976]; the analysis object is always the **surplus**
``x_i(d) = u_i(d) - tau_i`` -- raw points sit on arbitrary private scales, so only scale-invariant solution
concepts (Nash product, Kalai-Smorodinsky) are defensible across parties (see ``solutions.py``).

``GameSpec`` bundles the deal space, the sheets, and the protocol knobs (rounds, full/private info, chat on/off,
proposer/veto seats, agreement rule) into one object that round-trips through a plain JSON dict, so a whole game
drops straight into an arena ``Instance.payload`` and back.

The **workhorse** every solution concept consumes is :func:`utility_matrix` -- the dense ``|D| x n`` array
``U[k, i] = u_i(deal_at(k))`` built once via a vectorized mixed-radix accumulation (no Python loop over deals).

Example::

    space = DealSpace((Issue("A", ("a0", "a1")), Issue("B", ("b0", "b1", "b2"))))
    alice = ScoreSheet("Alice", ((10, 0), (0, 3, 6)), threshold=5.0)
    alice.utility((1, 2))            # 0 + 6 = 6.0
    alice.surplus((1, 2))            # 6 - 5 = 1.0
    U = utility_matrix(space, (alice, bob))     # shape (6, 2)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Callable

import numpy as np

from .space import Deal, DealSpace

# --------------------------------------------------------------------------------------------------------- #
# Structural deal constraints, by name.
# --------------------------------------------------------------------------------------------------------- #
# A ``GameSpec`` is a FLAT deal space: any option per issue is combinable with any other, and legality is a
# threshold question. Some games add a STRUCTURAL rule the flat model cannot express -- the trust/investment
# game's "the trustee may return at most 3x what was sent" (``r <= 3s``) is the canonical case, where the legal
# range of one issue's option depends on another's.
#
# Such a rule is registered here by NAME and referenced by ``GameSpec.constraint``. It is a name rather than a
# callable field so a spec survives ``to_json`` -> ``Instance.payload`` -> ``from_json`` unchanged: a lambda
# would be silently dropped on save, and a reloaded instance would then describe a DIFFERENT (unconstrained)
# game than the one that was played -- which the replay gate could not catch, because both sides would drop it.
# A predicate takes a ``Deal`` (option indices, one per issue) and returns whether it is structurally legal;
# ``GameSpec.feasible_mask`` ANDs it into the agreement rule, so it flows into the exact solution concepts, the
# oracles, and the scenario's surplus ceiling with no further wiring.
CONSTRAINTS: dict[str, "Callable[[Deal], bool]"] = {}


def register_constraint(name: str, predicate: "Callable[[Deal], bool]") -> None:
    """Register a structural deal predicate under ``name`` for ``GameSpec(constraint=name)``. Re-registering the
    same name is an error -- two games silently sharing a name would make a stored instance ambiguous."""
    if name in CONSTRAINTS:
        raise ValueError(f"deal constraint {name!r} is already registered")
    CONSTRAINTS[name] = predicate


@dataclass(frozen=True)
class ScoreSheet:
    """One party's private additive score sheet.

    ``values[j]`` is the tuple of per-option values for issue ``j`` (same length as that issue's options);
    ``threshold`` is the party's private acceptance minimum ``tau_i`` (its BATNA). Utility is the sum of the
    chosen options' values; surplus is utility minus threshold. Frozen/hashable so a tuple of sheets can key a
    cached utility matrix."""

    agent: str
    values: tuple[tuple[float, ...], ...]
    threshold: float

    def utility(self, deal: Deal) -> float:
        """Additive utility ``u(d) = sum_j values[j][d_j]`` of a deal."""
        return float(sum(self.values[j][o] for j, o in enumerate(deal)))

    def surplus(self, deal: Deal) -> float:
        """Surplus ``x(d) = u(d) - threshold`` -- positive iff the deal clears this party's BATNA."""
        return self.utility(deal) - self.threshold

    @property
    def n_issues(self) -> int:
        """Number of issues this sheet scores."""
        return len(self.values)

    @property
    def max_utility(self) -> float:
        """Best attainable utility (pick each issue's highest-valued option)."""
        return float(sum(max(v) for v in self.values))

    @property
    def min_utility(self) -> float:
        """Worst attainable utility (pick each issue's lowest-valued option)."""
        return float(sum(min(v) for v in self.values))

    def rescaled(self, a: float, c: float = 0.0) -> "ScoreSheet":
        """This sheet under the positive affine transform of the *utility function* ``u -> a*u + c`` with the
        threshold moved the same way (``tau -> a*tau + c``). Requires ``a > 0``. Because the disagreement point
        moves with the scale, every surplus obeys ``x -> a*x`` exactly; scale-invariant concepts (NBS, KS) are
        unchanged, non-invariant ones (utilitarian, egalitarian) generally are not -- the property the tests
        exercise. The additive constant ``c`` is realized on the additive sheet by adding it to a single issue's
        options (issue 0), so that the *total* utility shifts by ``c`` exactly once (not once per issue)."""
        if a <= 0:
            raise ValueError(f"affine rescale needs a > 0, got {a}")
        vals = [tuple(a * x for x in row) for row in self.values]
        vals[0] = tuple(a * x + c for x in self.values[0])
        return ScoreSheet(self.agent, tuple(vals), a * self.threshold + c)

    def to_json(self) -> dict:
        """JSON-ready dict (values as nested lists)."""
        return {"agent": self.agent, "values": [list(v) for v in self.values], "threshold": self.threshold}

    @staticmethod
    def from_json(d: dict) -> "ScoreSheet":
        """Rebuild a ``ScoreSheet`` from :meth:`to_json` output (lists -> tuples)."""
        return ScoreSheet(d["agent"], tuple(tuple(v) for v in d["values"]), float(d["threshold"]))


@dataclass
class GameSpec:
    """A complete negotiation game: the deal space, every party's private sheet, and the protocol knobs.

    Beyond ``space``/``sheets`` the fields carry the protocol arms: ``rounds`` (round-robin
    rounds before a forced final), ``info`` (``"full"`` = sheets common knowledge, ``"private"`` = only a prior
    over types), ``chat`` (whether a public cheap-talk channel exists alongside formal moves), and the agreement
    structure -- ``proposer`` seat (a rotating-proposer scenario may ignore this default), ``veto`` (one seat, a
    list of seats, or ``None`` -- see :attr:`veto_seats`), and ``min_accept`` (how many parties must clear their
    threshold; ``None`` = unanimity). Impatience knobs the equilibrium/acceptance oracles read as their single
    source of truth: ``discount`` (per-round delta in (0, 1], 1.0 = none) and ``breakdown_risk`` (per-round
    exogenous-breakdown probability in [0, 1), 0.0 = none). ``meta`` holds anything scenario-private (e.g.
    generator provenance, issue-type labels). Serializes to/from a plain JSON dict for ``Instance.payload``."""

    space: DealSpace
    sheets: tuple[ScoreSheet, ...]
    rounds: int = 4
    info: str = "full"                 # "full" | "private"
    chat: bool = True
    proposer: int = 0                  # DEFAULT/designated proposer seat; a rotating-proposer scenario may ignore it
    veto: int | list[int] | None = None    # one seat, several seats, or none; see .veto_seats
    min_accept: int | None = None      # None => unanimity (all n parties must clear threshold)
    discount: float = 1.0              # per-round discount delta in (0, 1]; 1.0 = no impatience. The single
                                       # source of truth the equilibrium/acceptance oracles read (Banks-Duggan
                                       # continuation values, McCall stopping) -- do not re-default it per oracle.
    breakdown_risk: float = 0.0        # per-round probability the negotiation exogenously breaks down in [0, 1);
                                       # 0.0 = none. Makes interior concession rational under a hard deadline
                                       # (the Sandholm-Vulkan 1999 warning).
    constraint: str | None = None      # NAME of a structural deal predicate in CONSTRAINTS, or None. A NAME and
                                       # not a callable so the game round-trips through to_json/Instance.payload
                                       # -- a stored instance must rebuild the SAME game or replay is a lie.
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.info not in ("full", "private"):
            raise ValueError(f"info must be 'full' or 'private', got {self.info!r}")
        for s in self.sheets:
            if s.n_issues != self.space.n_issues:
                raise ValueError(f"sheet {s.agent!r} scores {s.n_issues} issues, space has {self.space.n_issues}")
            for j, row in enumerate(s.values):
                if len(row) != self.space.shape[j]:
                    raise ValueError(
                        f"sheet {s.agent!r} issue {j} has {len(row)} option values, space issue has "
                        f"{self.space.shape[j]} options")
        if not 0 <= self.proposer < self.n_parties:
            raise ValueError(f"proposer seat {self.proposer} out of range")
        if self.min_accept is not None and not 1 <= int(self.min_accept) <= self.n_parties:
            raise ValueError(f"min_accept must be in 1..{self.n_parties} or None, got {self.min_accept!r}")
        for v in self.veto_seats:
            if not 0 <= v < self.n_parties:
                raise ValueError(f"veto seat {v} out of range")
        if not 0.0 < self.discount <= 1.0:
            raise ValueError(f"discount must be in (0, 1], got {self.discount}")
        if not 0.0 <= self.breakdown_risk < 1.0:
            raise ValueError(f"breakdown_risk must be in [0, 1), got {self.breakdown_risk}")
        self.constraint_fn()               # fail fast on an unregistered constraint name, not at analysis time

    @property
    def veto_seats(self) -> list[int]:
        """The veto seats as a list (``[]`` if none): normalizes the ``veto`` field, which may be a single seat
        index, a list of seat indices, or ``None``. Every veto seat must clear its threshold for a deal to pass."""
        if self.veto is None:
            return []
        return [self.veto] if isinstance(self.veto, int) else list(self.veto)

    @property
    def n_parties(self) -> int:
        """Number of parties ``n``."""
        return len(self.sheets)

    @property
    def agents(self) -> list[str]:
        """Party names in seat order."""
        return [s.agent for s in self.sheets]

    @property
    def thresholds(self) -> np.ndarray:
        """The reservation vector ``tau`` of shape ``(n,)``."""
        return np.array([s.threshold for s in self.sheets], dtype=float)

    def utility_matrix(self) -> np.ndarray:
        """The ``|D| x n`` utility matrix for this game (see module-level :func:`utility_matrix`)."""
        return utility_matrix(self.space, self.sheets)

    def surplus_matrix(self) -> np.ndarray:
        """The ``|D| x n`` surplus matrix ``U - tau`` for this game."""
        return self.utility_matrix() - self.thresholds

    def feasible_mask(self, U: np.ndarray | None = None) -> np.ndarray:
        """Boolean ``(|D|,)`` mask of deals that pass this game's agreement rule: the ``proposer`` clears its
        threshold, the ``veto`` seat (if any) clears its threshold, at least ``min_accept`` parties clear theirs
        (``min_accept=None`` => all ``n`` => plain unanimity / the IR set), AND the deal satisfies this game's
        ``constraint`` (if it declares one). Pass a precomputed ``U`` to avoid rebuilding it.

        Because every exact solution concept, the oracles, and the scenario's surplus ceiling all read this
        mask, a constraint declared here flows into all of them for free — it is the single definition of "may
        this deal close?". :meth:`feasible` is the single-deal form of the same rule."""
        if U is None:
            U = self.utility_matrix()
        clears = U >= self.thresholds                       # (|D|, n) bool
        need = self.n_parties if self.min_accept is None else self.min_accept
        ok = clears.sum(axis=1) >= need
        ok &= clears[:, self.proposer]
        for v in self.veto_seats:
            ok &= clears[:, v]
        predicate = self.constraint_fn()
        if predicate is not None:
            ok &= np.fromiter((predicate(d) for d in self.space.enumerate()), dtype=bool, count=self.space.size)
        return ok

    def normalized_geometry(self) -> dict:
        """The game's scale-invariant surplus geometry, and the deal that attains its ceiling.

        Each party is normalized by its own **capacity** ``c_i = max_d x_i(d)`` (its best surplus over the whole
        deal space), giving ``z_i = x_i / c_i``. The **ceiling** is ``max`` over the FEASIBLE set (whatever
        :meth:`feasible_mask` admits) of ``sum_i z_i``, and the **ceiling deal** is the argmax — ties broken by
        the smallest enumeration index, so it is deterministic.

        Returns ``{"feasible", "capacities", "normalized_ceiling", "raw_ceiling", "ceiling_index",
        "ceiling_deal"}``; ``ceiling_index``/``ceiling_deal`` are ``None`` when the game admits no feasible deal
        or some party has zero capacity (a degenerate sheet), which is also when ``normalized_ceiling`` is 0.

        This is the single definition of "the best deal on the table": ``normalized_ceiling`` is the denominator
        of the scenario's ``primary`` score (so score 1.0 *is* the ceiling deal), and ``ceiling_deal`` is what an
        experiment seeds when it wants the optimum already tabled.
        """
        x = self.surplus_matrix()
        mask = self.feasible_mask()
        capacities = x.max(axis=0)
        valid = bool(mask.any()) and bool(np.all(capacities > 1e-9))
        out = {"feasible": bool(mask.any()), "capacities": capacities,
               "normalized_ceiling": 0.0, "ceiling_index": None, "ceiling_deal": None,
               "raw_ceiling": float(x[mask].sum(axis=1).max()) if mask.any() else 0.0}
        if not valid:
            return out
        z_sum = np.where(mask, (x / capacities[None, :]).sum(axis=1), -np.inf)
        index = int(np.argmax(z_sum))
        out["normalized_ceiling"] = float(z_sum[index])
        out["ceiling_index"] = index
        out["ceiling_deal"] = tuple(int(o) for o in self.space.deal_at(index))
        return out

    def constraint_fn(self) -> "Callable[[Deal], bool] | None":
        """This game's structural deal predicate, resolved from the ``constraint`` NAME via
        :data:`CONSTRAINTS`, or ``None`` when it declares none. Raises ``KeyError`` for an unregistered name."""
        if self.constraint is None:
            return None
        try:
            return CONSTRAINTS[self.constraint]
        except KeyError:
            raise KeyError(f"unknown deal constraint {self.constraint!r}; registered: {sorted(CONSTRAINTS)}"
                           ) from None

    def feasible(self, deal: Deal) -> bool:
        """Whether ONE deal may close under this game's agreement rule — the single-deal counterpart of
        :meth:`feasible_mask` (it indexes that mask, so the two can never disagree)."""
        return bool(self.feasible_mask()[self.space.index_of(tuple(deal))])

    def to_json(self) -> dict:
        """JSON-ready dict of the whole game (drops straight into ``Instance.payload``)."""
        return {
            "space": self.space.to_json(),
            "sheets": [s.to_json() for s in self.sheets],
            "rounds": self.rounds,
            "info": self.info,
            "chat": self.chat,
            "proposer": self.proposer,
            "veto": self.veto,
            "min_accept": self.min_accept,
            "discount": self.discount,
            "breakdown_risk": self.breakdown_risk,
            "constraint": self.constraint,
            "meta": self.meta,
        }

    @staticmethod
    def from_json(d: dict) -> "GameSpec":
        """Rebuild a ``GameSpec`` from :meth:`to_json` output."""
        return GameSpec(
            space=DealSpace.from_json(d["space"]),
            sheets=tuple(ScoreSheet.from_json(s) for s in d["sheets"]),
            rounds=d.get("rounds", 4),
            info=d.get("info", "full"),
            chat=d.get("chat", True),
            proposer=d.get("proposer", 0),
            veto=d.get("veto"),
            min_accept=d.get("min_accept"),
            discount=d.get("discount", 1.0),
            breakdown_risk=d.get("breakdown_risk", 0.0),
            constraint=d.get("constraint"),
            meta=d.get("meta", {}),
        )


def utility_matrix(space: DealSpace, sheets: tuple[ScoreSheet, ...] | list[ScoreSheet]) -> np.ndarray:
    """Build the dense ``|D| x n`` utility matrix ``U[k, i] = u_i(space.deal_at(k))``.

    This is the array every solution concept in ``solutions.py`` consumes. It is built without a Python loop over
    the ``|D|`` deals: for each issue ``j`` the per-option, per-party value block (shape ``(|options_j|, n)``) is
    gathered by the mixed-radix option-index pattern ``(arange(|D|) // stride_j) % |options_j|`` and added in, so
    the cost is ``O(J * |D| * n)`` vectorized. Row order matches :meth:`DealSpace.deal_at` /
    :meth:`DealSpace.enumerate`."""
    n = len(sheets)
    size = space.size
    shape = space.shape
    strides = space.strides()
    U = np.zeros((size, n), dtype=float)
    ar = np.arange(size)
    for j in range(space.n_issues):
        block = np.array([[s.values[j][o] for s in sheets] for o in range(shape[j])], dtype=float)  # (opts_j, n)
        opt_idx = (ar // strides[j]) % shape[j]                                                       # (|D|,)
        U += block[opt_idx]
    return U


def surplus_matrix(space: DealSpace, sheets: tuple[ScoreSheet, ...] | list[ScoreSheet]) -> np.ndarray:
    """The ``|D| x n`` surplus matrix ``U - tau``."""
    tau = np.array([s.threshold for s in sheets], dtype=float)
    return utility_matrix(space, sheets) - tau


def sparsity(sheets: tuple[ScoreSheet, ...] | list[ScoreSheet]) -> float:
    """Fraction of option cells (over all sheets, issues, options) whose value is exactly zero -- the
    score-sheet sparsity descriptor of the TMLR reproduction [reproB_tmlr] (their games run 23.7-43.0%). Zero
    options are the ``don't care`` slots that create logrolling room and Pareto-dominated-but-acceptable deals."""
    total = 0
    zeros = 0
    for s in sheets:
        for row in s.values:
            for v in row:
                total += 1
                zeros += (v == 0)
    return zeros / total if total else 0.0


def pairwise_iou(sheets: tuple[ScoreSheet, ...] | list[ScoreSheet]) -> float:
    """Mean pairwise Intersection-over-Union of the parties' *value supports* -- the score-function-overlap
    descriptor of the TMLR reproduction [reproB_tmlr] (their games run 18.8-29.8%).

    Each party's support is the set of ``(issue, option)`` cells it scores with a nonzero value; for every pair
    of parties IoU = ``|support_a & support_b| / |support_a | support_b|``, averaged over all pairs. Low IoU =
    parties care about disjoint parts of the deal (integrative, logrolling-friendly); high IoU = they fight over
    the same cells (distributive)."""
    supports = []
    for s in sheets:
        supp = {(j, o) for j, row in enumerate(s.values) for o, v in enumerate(row) if v != 0}
        supports.append(supp)
    pairs = list(combinations(range(len(supports)), 2))
    if not pairs:
        return 0.0
    vals = []
    for a, b in pairs:
        union = supports[a] | supports[b]
        inter = supports[a] & supports[b]
        vals.append(len(inter) / len(union) if union else 0.0)
    return float(np.mean(vals))
