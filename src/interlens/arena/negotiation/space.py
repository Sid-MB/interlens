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

"""The deal space: issues, their discrete options, and the fully-enumerable Cartesian product of options.

A negotiation is over ``J`` issues, each with a fixed list of discrete options. A **deal** picks one option per
issue and is represented as a ``Deal`` -- a ``tuple[int, ...]`` of option indices, one per issue (the frozen
cross-team contract, DESIGN.md §8). The whole deal space ``D = prod_j |options_j|`` is small enough
(|D| ~ 243-3125 in the target regime) to enumerate exactly, which is what makes every normative benchmark in
``solutions.py`` exact rather than sampled.

Enumeration order is ``itertools.product`` order: issue 0 is most significant and the last issue varies
fastest. ``deal_at``/``index_of`` are the mixed-radix encode/decode for that same order, so a deal's position in
``enumerate()`` equals its row in the ``|D| x n`` utility matrix that ``sheets.utility_matrix`` builds -- the
NumPy workhorse the solution concepts consume.

Example::

    space = DealSpace((Issue("Site", ("North", "South")), Issue("Fund", ("None", "1M", "5M"))))
    space.size                       # 6
    list(space.enumerate())          # [(0,0),(0,1),(0,2),(1,0),(1,1),(1,2)]
    space.index_of((1, 2))           # 5
    space.deal_at(5)                 # (1, 2)
    space.named((1, 2))              # {'Site': 'South', 'Fund': '5M'}
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from math import prod
from typing import Iterator

# One option index per issue; the cross-team wire type for a chosen deal. Defined canonically in the arena's
# action layer and re-exported here so the whole stack (actions, oracles, negotiation) shares one type
# (per interlens-core). No import cycle: arena.actions does not import the negotiation package.
from ..actions import Deal


@dataclass(frozen=True)
class Issue:
    """One negotiable issue: a name and its discrete options (order defines the option indices).

    ``options`` are human-readable labels (e.g. site names, funding tiers); a deal never stores these, only the
    integer index into this tuple, so option semantics stay out of the numeric game."""

    name: str
    options: tuple[str, ...]

    def __post_init__(self):
        if len(self.options) < 1:
            raise ValueError(f"issue {self.name!r} has no options")

    @property
    def n_options(self) -> int:
        """Number of options for this issue."""
        return len(self.options)

    def to_json(self) -> dict:
        """JSON-ready dict (``options`` as a list)."""
        return {"name": self.name, "options": list(self.options)}

    @staticmethod
    def from_json(d: dict) -> "Issue":
        """Rebuild an ``Issue`` from :meth:`to_json` output."""
        return Issue(d["name"], tuple(d["options"]))


@dataclass(frozen=True)
class DealSpace:
    """The Cartesian product of all issues' options -- the full, enumerable set of possible deals.

    Frozen and hashable so it can back a cached utility matrix. All indexing (``enumerate``, ``deal_at``,
    ``index_of``) uses one consistent mixed-radix order (issue 0 most significant, last issue fastest), matching
    ``itertools.product`` and the row order of the utility matrix."""

    issues: tuple[Issue, ...]

    def __post_init__(self):
        if len(self.issues) < 1:
            raise ValueError("a deal space needs at least one issue")

    @property
    def n_issues(self) -> int:
        """Number of issues ``J``."""
        return len(self.issues)

    @property
    def shape(self) -> tuple[int, ...]:
        """Per-issue option counts ``(|options_0|, ..., |options_{J-1}|)`` -- the mixed-radix base."""
        return tuple(i.n_options for i in self.issues)

    @property
    def size(self) -> int:
        """Total number of deals ``|D| = prod_j |options_j|``."""
        return prod(self.shape)

    def strides(self) -> tuple[int, ...]:
        """Mixed-radix strides: ``strides[j] = prod(shape[j+1:])`` = the number of consecutive deals for which
        issue ``j``'s option is held fixed under :meth:`enumerate`. Used to map deal <-> flat index and to build
        the utility matrix without materializing every deal."""
        sh = self.shape
        out = [1] * len(sh)
        acc = 1
        for j in range(len(sh) - 1, -1, -1):
            out[j] = acc
            acc *= sh[j]
        return tuple(out)

    def enumerate(self) -> Iterator[Deal]:
        """Iterate all ``|D|`` deals in mixed-radix order (issue 0 most significant, last issue fastest)."""
        return itertools.product(*(range(i.n_options) for i in self.issues))

    def deals(self) -> list[Deal]:
        """All deals as a list (convenience wrapper over :meth:`enumerate`)."""
        return list(self.enumerate())

    def deal_at(self, index: int) -> Deal:
        """The deal at flat position ``index`` in :meth:`enumerate` order (mixed-radix decode)."""
        if not 0 <= index < self.size:
            raise IndexError(f"deal index {index} out of range [0, {self.size})")
        sh = self.shape
        st = self.strides()
        return tuple((index // st[j]) % sh[j] for j in range(len(sh)))

    def index_of(self, deal: Deal) -> int:
        """The flat position of ``deal`` in :meth:`enumerate` order (mixed-radix encode); inverse of
        :meth:`deal_at`."""
        sh = self.shape
        st = self.strides()
        if len(deal) != len(sh):
            raise ValueError(f"deal has {len(deal)} issues, space has {len(sh)}")
        idx = 0
        for j, o in enumerate(deal):
            if not 0 <= o < sh[j]:
                raise ValueError(f"option {o} out of range for issue {j} (|options|={sh[j]})")
            idx += o * st[j]
        return idx

    def named(self, deal: Deal) -> dict[str, str]:
        """Human-readable ``{issue_name: option_label}`` view of a deal -- for solutions, transcripts, and audits
        (never fed back into numeric scoring)."""
        return {self.issues[j].name: self.issues[j].options[o] for j, o in enumerate(deal)}

    def _issue_index(self, name: str) -> int:
        """Issue position for a name, tolerant of surrounding whitespace and case."""
        norm = name.strip().casefold()
        for j, iss in enumerate(self.issues):
            if iss.name.strip().casefold() == norm:
                return j
        raise ValueError(f"unknown issue {name!r}; issues: {[i.name for i in self.issues]}")

    def option_index(self, issue: int | str, label: str) -> int:
        """Index of an option ``label`` within an issue (given by position or name), tolerant of surrounding
        whitespace and case on both. Raises ``ValueError`` if the label matches no option."""
        j = issue if isinstance(issue, int) else self._issue_index(issue)
        norm = label.strip().casefold()
        for o, opt in enumerate(self.issues[j].options):
            if opt.strip().casefold() == norm:
                return o
        raise ValueError(f"unknown option {label!r} for issue {self.issues[j].name!r}; "
                         f"options: {list(self.issues[j].options)}")

    def parse(self, named: dict[str, str]) -> Deal:
        """Map a ``{issue_name: option_label}`` proposal dict to a :data:`Deal` (option index per issue, in issue
        order), tolerant of case/whitespace on both issue names and option labels -- the inverse of :meth:`named`.
        The dict must name every issue exactly once. Raises ``ValueError`` on a missing/unknown/duplicate issue or
        an unknown option, so a scenario can turn a malformed model proposal into a clean parse error to log."""
        idx = {self._issue_index(k): v for k, v in named.items()}
        if len(idx) != self.n_issues:
            raise ValueError(f"proposal names {len(idx)} distinct issues, need all {self.n_issues}")
        return tuple(self.option_index(j, idx[j]) for j in range(self.n_issues))

    def to_json(self) -> dict:
        """JSON-ready dict of the whole space."""
        return {"issues": [i.to_json() for i in self.issues]}

    @staticmethod
    def from_json(d: dict) -> "DealSpace":
        """Rebuild a ``DealSpace`` from :meth:`to_json` output."""
        return DealSpace(tuple(Issue.from_json(i) for i in d["issues"]))
