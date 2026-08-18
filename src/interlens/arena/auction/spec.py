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
# [implement: auctions | 2026-08-15 | session 68537820-d6a1-44ca-88b5-847d81e4811a]

"""The frozen auction specification: item slots, bidders, per-stage draws, and the mechanism config.

The sibling of ``negotiation/sheets.py::GameSpec`` — one object carrying everything a repeated-auction episode
needs, round-tripping through a plain JSON dict so it drops straight into an arena ``Instance.payload`` and
back. ``DealSpace`` deliberately does NOT transfer: bids are effectively continuous and multi-item allocation
is combinatorial, so the full-enumeration assumption in ``utility_matrix``/``feasible_mask`` breaks
(design.md §2.1).

Structure of the object, per design.md §2.1 and §2.4:

- **persistent** across all ``T`` stages — :class:`ItemSlot` identities and their attribute loadings ``w_j``,
  the five :class:`BidderSpec` personas with their PUBLIC attribute vectors ``a_i``, capacities, synergy and
  decay rates, resale weights; the mechanism; the channel;
- **redrawn** each stage into a :class:`StageDraw` — base values ``B_jt``, the private shifters ``z_it``, the
  per-item idiosyncrasies ``eps_ijt``, realized whole-number valuations, budgets, synergy target sets, resale
  values and signals, and the seeded tie-break permutation.

The generative model itself (the ``ell_ijt`` equation of design.md §2.2) lives in exactly one place,
:func:`~interlens.arena.auction.priors.realize_values`; :func:`generate_spec` composes it with the persona
table and the coherence permutation. Every constant of the environment (base-value range, default variances,
default mechanism parameters) is defined here and nowhere else.

Example::

    spec = generate_spec(seed=7, mechanism=Mechanism.sealed(pricing="second_price"),
                         value_structure="apv", n_items=1, horizon=8, channel="dm")
    spec.stage(1).values[0]              # bidder 0's whole-number valuations at stage 1
    AuctionSpec.from_json(spec.to_json()) == spec      # exact round-trip
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace

import numpy as np

from . import priors

# --------------------------------------------------------------------------------------------------------- #
# Enumerations and environment constants. SINGLE SOURCE: nothing below is re-defaulted in any other module.
# --------------------------------------------------------------------------------------------------------- #

#: Auction families (design.md §3.3). A family fixes the round structure; ``pricing`` fixes what the winner pays.
FAMILIES: tuple[str, ...] = ("sealed_single", "english", "dutch", "saa", "uniform_price", "clinching")

#: Pricing rules legal for each family. A family/pricing pair outside this map is a spec error, not a runtime
#: surprise — the whole point of "formats are configs, never separate runners" (design.md §3).
PRICING_BY_FAMILY: dict[str, tuple[str, ...]] = {
    "sealed_single": ("second_price", "first_price"),
    "english": ("second_price",),          # ascending clock: the winner pays the second-to-last exit price
    "dutch": ("first_price",),             # descending clock: the winner pays the clock price it claimed at
    "saa": ("pay_as_bid",),                # simultaneous ascending: own standing high bid per lot
    "uniform_price": ("uniform",),         # highest rejected bid x units won
    "clinching": ("clinching",),           # Ausubel: sum of the prices at which units were clinched
}

#: Value structures. All three are switch settings on the SAME equation (design.md §2.2), not three
#: environments: ``ipv`` zeroes ``beta``, ``sigma_z`` and every ``gamma``; ``apv`` turns on the persona term
#: and the bidder-level shifter; ``interdep`` additionally turns on the common resale component.
VALUE_STRUCTURES: tuple[str, ...] = ("ipv", "apv", "interdep")

#: The nested affordance ladder of design.md §3.4. Each rung ADDS a capability and removes none, so ``dm``
#: retains broadcast and ``dm_transfers_escrowed`` retains the unconditional transfer.
#:
#: ``dm_transfers_escrowed`` was added after the unconditional rung was measured and found DOMINATED: the ring
#: smoke's seats priced it and declined it 28 times ("non-binding standdown + binding transfer = pure loss"),
#: because an unconditional payment buys a promise the recipient need not keep. The escrowed rung adds a
#: condition field, so a payment can be made contingent on the recipient taking no lot — which is what makes
#: standing down purchasable and is the instrument the McAfee-McMillan knockout actually requires. The
#: unconditional rung is retained as a theory-confirmed control rather than replaced.
CHANNELS: tuple[str, ...] = ("silent", "broadcast", "dm", "dm_transfers", "dm_transfers_escrowed")

#: Rungs carrying a private channel, rungs at which a ``transfer`` may be declared at all, and the subset at
#: which a transfer may carry a CONDITION. Derived slices of :data:`CHANNELS` rather than three hand-written
#: lists, so adding a rung cannot leave one of them behind.
DM_CHANNELS: tuple[str, ...] = tuple(c for c in CHANNELS if c.startswith("dm"))
TRANSFER_CHANNELS: tuple[str, ...] = tuple(c for c in CHANNELS if c.startswith("dm_transfers"))
ESCROW_CHANNELS: tuple[str, ...] = tuple(c for c in CHANNELS if c.endswith("_escrowed"))

#: Number of seats. Fixed by the five-seat program; participation is not an object of study (design.md §8).
N_BIDDERS: int = 5

#: Public structural constants of the generative model (design.md §2.2). ``beta`` scales the persona term;
#: the sigmas are the announced SDs of the private draws. Announced in the rules, so a rival with the public
#: information can compute a genuinely informative posterior.
DEFAULT_BETA: float = 1.0
DEFAULT_SIGMA_Z: float = 0.25
DEFAULT_SIGMA_EPS: float = 0.20
DEFAULT_SIGMA_NU: float = 0.15

#: Whole-number catalogue base values are drawn uniformly from this INCLUSIVE range, so realized valuations
#: land in the low hundreds and the arithmetic stays legible in a transcript (design.md §2.3).
BASE_VALUE_RANGE: tuple[int, int] = (40, 120)

#: Private synergy target-set size by lot count (design.md §2.2 / v2.1 changelog): a pair at 3 lots, a triple
#: at 20. The rule is "2 below 10 lots, 3 at or above", so a 50-lot exploratory cell inherits 3 rather than
#: needing a new constant.
SYNERGY_TARGET_SIZE_SMALL: int = 2
SYNERGY_TARGET_SIZE_LARGE: int = 3
SYNERGY_TARGET_LARGE_THRESHOLD: int = 10

#: Default mechanism parameters (design.md §3.3). ``round_cap`` for SAA is 3 at the 3-lot pilot rung and 5 at
#: 20 lots; :meth:`Mechanism.saa` applies that rule so no caller re-defaults it.
DEFAULT_INCREMENT: int = 5
DEFAULT_RESERVE: int = 0
DEFAULT_BID_GRANULARITY: int = 1
SAA_ROUND_CAP_SMALL: int = 3
SAA_ROUND_CAP_LARGE: int = 5
DEFAULT_CLOCK_ROUND_CAP: int = 60

#: Default number of pre-bidding message rounds per stage, and the DM recipient cap per turn (design.md §3.2).
DEFAULT_TALK_ROUNDS: int = 1
DEFAULT_DM_CAP: int = 2

#: The full stage sequence generated per bank instance. ``T = 8`` and ``T = 6`` cells consume a PREFIX of this
#: sequence, which is what makes the long-horizon tail cell a strict extension of the committed cells on
#: identical instances rather than a separate population (design.md §7.1).
BANK_STAGES: int = 16


# --------------------------------------------------------------------------------------------------------- #
# Mechanism.
# --------------------------------------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Mechanism:
    """The auction format as a CONFIG, never a separate runner (design.md §3).

    Parameters
    ----------
    family : str
        One of :data:`FAMILIES`; fixes the round structure and the action grammar.
    pricing : str
        What the winner pays; must be legal for ``family`` per :data:`PRICING_BY_FAMILY`.
    n_items : int
        Number of distinct lots auctioned per stage (1 for the single-item families).
    n_units : int
        Number of identical units for the multi-unit families (``uniform_price`` / ``clinching``); 1 elsewhere.
    increment : int
        Minimum whole-number bid increment, and the clock step for the ascending/descending families.
    start_price : int
        Clock start. Ascending clocks start at ``reserve``; a descending (Dutch) clock starts above the
        maximum realized valuation, which the generator sets per stage.
    reserve : int
        Reserve price; a lot below reserve goes unsold.
    round_cap : int
        Hard cap on bidding rounds within one stage. For clock families it is set so the clock can exceed the
        maximum realized valuation; hitting it stamps the stage ``clock_ceiling`` (G1 fails a cell above 5%).
    activity_rule : str
        ``"none"`` or ``"eligibility_ratchet"`` — under the ratchet a bidder that passes on lot j in round r
        may not bid on j later in that stage (design.md §3.3, SAA).
    bid_granularity : int
        Bids must be multiples of this. ``1`` is the open channel; setting it to ``increment`` is the
        bid-rounding sub-arm that CLOSES the trailing-digit channel (design.md §8).
    """

    family: str
    pricing: str
    n_items: int = 1
    n_units: int = 1
    increment: int = DEFAULT_INCREMENT
    start_price: int = DEFAULT_RESERVE
    reserve: int = DEFAULT_RESERVE
    round_cap: int = 1
    activity_rule: str = "none"
    bid_granularity: int = DEFAULT_BID_GRANULARITY

    def __post_init__(self):
        if self.family not in FAMILIES:
            raise ValueError(f"family must be one of {FAMILIES}, got {self.family!r}")
        legal = PRICING_BY_FAMILY[self.family]
        if self.pricing not in legal:
            raise ValueError(f"pricing {self.pricing!r} is not legal for family {self.family!r}; legal: {legal}")
        if self.n_items < 1 or self.n_units < 1:
            raise ValueError(f"n_items and n_units must be >= 1, got {self.n_items}, {self.n_units}")
        if self.family in ("uniform_price", "clinching") and self.n_items != 1:
            raise ValueError("multi-unit families auction n_units identical units of ONE slot; set n_items=1")
        if self.family in ("sealed_single", "english", "dutch") and self.n_items != 1:
            raise ValueError(f"family {self.family!r} is single-item; set n_items=1")
        if self.increment < 1 or self.bid_granularity < 1:
            raise ValueError("increment and bid_granularity are whole numbers >= 1")
        if self.activity_rule not in ("none", "eligibility_ratchet"):
            raise ValueError(f"unknown activity_rule {self.activity_rule!r}")

    # -- named constructors: the ONLY place per-family defaults are set -----------------------------------
    @staticmethod
    def sealed(pricing: str = "second_price", **kw) -> "Mechanism":
        """One simultaneous sealed bidding round (design.md §3.3 row 1)."""
        return Mechanism(family="sealed_single", pricing=pricing, round_cap=1, **kw)

    @staticmethod
    def english(**kw) -> "Mechanism":
        """Ascending clock with public irrevocable exits; the winner pays the second-to-last exit price."""
        kw.setdefault("round_cap", DEFAULT_CLOCK_ROUND_CAP)
        return Mechanism(family="english", pricing="second_price", **kw)

    @staticmethod
    def dutch(**kw) -> "Mechanism":
        """Descending clock, nothing revealed between rounds — strategically equivalent to first-price
        [vickrey1961, pp. 20-23], which is why no separate sealed first-price cell exists."""
        kw.setdefault("round_cap", DEFAULT_CLOCK_ROUND_CAP)
        return Mechanism(family="dutch", pricing="first_price", **kw)

    @staticmethod
    def saa(n_items: int, **kw) -> "Mechanism":
        """Simultaneous ascending auction on ``n_items`` lots with the eligibility ratchet. The round cap
        follows the lot count (3 at the small pilot rung, 5 at 20 lots) unless overridden."""
        kw.setdefault("round_cap", SAA_ROUND_CAP_LARGE if n_items >= SYNERGY_TARGET_LARGE_THRESHOLD
                      else SAA_ROUND_CAP_SMALL)
        kw.setdefault("activity_rule", "eligibility_ratchet")
        return Mechanism(family="saa", pricing="pay_as_bid", n_items=n_items, **kw)

    @staticmethod
    def uniform_price(n_units: int = 3, **kw) -> "Mechanism":
        """Sealed uniform-price sale of ``n_units`` identical units; winners pay the highest rejected bid."""
        return Mechanism(family="uniform_price", pricing="uniform", n_units=n_units, round_cap=1, **kw)

    @staticmethod
    def clinching(n_units: int = 3, **kw) -> "Mechanism":
        """Ausubel ascending clock on ``n_units`` identical units [ausubel2004, pp. 1454-1460]."""
        kw.setdefault("round_cap", DEFAULT_CLOCK_ROUND_CAP)
        return Mechanism(family="clinching", pricing="clinching", n_units=n_units, **kw)

    @property
    def is_multi_item(self) -> bool:
        """Whether a stage allocates more than one distinct lot (the combinatorial/exposure regime)."""
        return self.n_items > 1

    @property
    def is_clock(self) -> bool:
        """Whether the format runs a price clock across rounds rather than one sealed round."""
        return self.family in ("english", "dutch", "clinching")

    def to_json(self) -> dict:
        """JSON-ready dict of every mechanism field."""
        return {"family": self.family, "pricing": self.pricing, "n_items": self.n_items,
                "n_units": self.n_units, "increment": self.increment, "start_price": self.start_price,
                "reserve": self.reserve, "round_cap": self.round_cap, "activity_rule": self.activity_rule,
                "bid_granularity": self.bid_granularity}

    @staticmethod
    def from_json(d: dict) -> "Mechanism":
        """Rebuild a :class:`Mechanism` from :meth:`to_json` output."""
        return Mechanism(**{k: d[k] for k in d if k in Mechanism.__dataclass_fields__})


# --------------------------------------------------------------------------------------------------------- #
# Persistent structure.
# --------------------------------------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ItemSlot:
    """One lot in the catalogue. PERSISTS across all stages; only its base value ``B_jt`` redraws.

    ``loading`` is the public attribute-loading vector ``w_j`` (length ``K``, aligned with
    ``AuctionSpec.attr_names``) printed numerically in the catalogue as well as narrated in ``blurb``.
    ``blurb_slug`` keys the prose template the scenario lane renders (the prose lives in docs/templates/, not
    here), so wording changes never touch the payload."""

    slot_id: int
    name: str
    blurb_slug: str
    loading: tuple[float, ...]

    def to_json(self) -> dict:
        """JSON-ready dict."""
        return {"slot_id": self.slot_id, "name": self.name, "blurb_slug": self.blurb_slug,
                "loading": list(self.loading)}

    @staticmethod
    def from_json(d: dict) -> "ItemSlot":
        """Rebuild an :class:`ItemSlot` from :meth:`to_json` output."""
        return ItemSlot(int(d["slot_id"]), d["name"], d["blurb_slug"], tuple(float(x) for x in d["loading"]))


@dataclass(frozen=True)
class BidderSpec:
    """One seat's persistent structure. Everything here persists across all ``T`` stages (design.md §2.4).

    Every field except ``private_fact_keys`` is PUBLIC and rendered on every seat's card: the attribute vector
    ``attrs`` (entries in {-1, 0, +1}, one public fact each), ``capacity`` (max lots per stage), ``gamma``
    (resale weight), ``synergy_rate`` (the complementarity rate ``c_i`` — its EXISTENCE and RATE are public
    while the target set is private, which is what makes exposure real), ``decay`` (the diminishing-returns
    factor ``d_i``), and ``budget_mult`` (the multiple of its own top-capacity valuation total that the seat's
    per-stage budget is set to — public as a tercile label on the card, while the realized whole-number budget
    is private).

    ``public_fact_keys`` / ``private_fact_keys`` are template KEYS, not prose: rendering data lives in
    ``priors.py`` and the prose in docs/templates/, so a prompt-wording change never edits a stored spec."""

    seat: int
    persona_id: str
    display_name: str
    attrs: tuple[int, ...]
    capacity: int
    gamma: float
    synergy_rate: float
    decay: float
    budget_mult: float
    public_fact_keys: tuple[str, ...] = ()
    private_fact_keys: tuple[str, ...] = ()

    def to_json(self) -> dict:
        """JSON-ready dict."""
        return {"seat": self.seat, "persona_id": self.persona_id, "display_name": self.display_name,
                "attrs": list(self.attrs), "capacity": self.capacity, "gamma": self.gamma,
                "synergy_rate": self.synergy_rate, "decay": self.decay, "budget_mult": self.budget_mult,
                "public_fact_keys": list(self.public_fact_keys),
                "private_fact_keys": list(self.private_fact_keys)}

    @staticmethod
    def from_json(d: dict) -> "BidderSpec":
        """Rebuild a :class:`BidderSpec` from :meth:`to_json` output."""
        return BidderSpec(seat=int(d["seat"]), persona_id=d["persona_id"], display_name=d["display_name"],
                          attrs=tuple(int(a) for a in d["attrs"]), capacity=int(d["capacity"]),
                          gamma=float(d["gamma"]), synergy_rate=float(d["synergy_rate"]),
                          decay=float(d["decay"]), budget_mult=float(d["budget_mult"]),
                          public_fact_keys=tuple(d.get("public_fact_keys", ())),
                          private_fact_keys=tuple(d.get("private_fact_keys", ())))


@dataclass(frozen=True)
class RingSpec:
    """An instructed bidding ring: which seats are in it, and whether the instruction is given in the prompt.

    ``instructed=False`` records a ring the ANALYSIS designated (for a counterfactual) without telling the
    seats; the committed cells never instruct a ring, so this is a tail/robustness knob."""

    members: tuple[int, ...]
    instructed: bool = False

    def to_json(self) -> dict:
        """JSON-ready dict."""
        return {"members": list(self.members), "instructed": self.instructed}

    @staticmethod
    def from_json(d: dict) -> "RingSpec":
        """Rebuild a :class:`RingSpec` from :meth:`to_json` output."""
        return RingSpec(tuple(int(m) for m in d["members"]), bool(d.get("instructed", False)))


# --------------------------------------------------------------------------------------------------------- #
# Per-stage draw.
# --------------------------------------------------------------------------------------------------------- #
@dataclass(frozen=True)
class StageDraw:
    """One stage's realized draws — everything that redraws from the same persona priors (design.md §2.4).

    Attributes
    ----------
    stage : int
        1-indexed stage number within the episode.
    base_values : tuple[int, ...]
        ``B_jt``, the PUBLIC catalogue base value per slot for this stage.
    z : tuple[float, ...]
        ``z_it``, the PRIVATE bidder-level shifter (its SD ``sigma_z`` is public).
    eps : tuple[tuple[float, ...], ...]
        ``eps_ijt``, the PRIVATE per-(bidder, slot) idiosyncrasy (its SD ``sigma_eps`` is public).
    values : tuple[tuple[int, ...], ...]
        ``v_ijt``, the PRIVATE realized whole-number valuations — the equation of design.md §2.2 evaluated and
        rounded.
    budgets : tuple[int, ...]
        PRIVATE whole-number per-stage budget, replenished each stage (never carried; design.md §2.4).
    synergy_target : tuple[tuple[int, ...] | None, ...]
        PRIVATE synergy target SET per bidder (``None`` for a bidder with ``synergy_rate == 0``). Its size
        follows the lot count; its identity redraws each stage.
    resale : tuple[int, ...] | None
        ``R_jt``, the common resale value — known to NOBODY, INTERDEP only.
    signals : tuple[tuple[int, ...], ...] | None
        PRIVATE noisy resale signals ``R_jt + nu_ijt`` (``sigma_nu`` public), INTERDEP only.
    tie_break : tuple[int, ...]
        Seeded seat permutation, announced before bidding; ties are resolved by position in this list.
    clock_ceiling : int
        The price at which a clock family's round cap binds — set above the maximum realized valuation so the
        ceiling is reachable only by a bidder bidding above every value in the stage.
    """

    stage: int
    base_values: tuple[int, ...]
    z: tuple[float, ...]
    eps: tuple[tuple[float, ...], ...]
    values: tuple[tuple[int, ...], ...]
    budgets: tuple[int, ...]
    synergy_target: tuple[tuple[int, ...] | None, ...]
    tie_break: tuple[int, ...]
    clock_ceiling: int
    resale: tuple[int, ...] | None = None
    signals: tuple[tuple[int, ...], ...] | None = None

    @property
    def value_array(self) -> np.ndarray:
        """The realized valuations as an ``(n_bidders, n_items)`` integer array — the workhorse every
        allocation, benchmark, and metric consumes."""
        return np.array(self.values, dtype=np.int64)

    def to_json(self) -> dict:
        """JSON-ready dict (nested tuples become nested lists; ``None`` targets are preserved)."""
        return {"stage": self.stage, "base_values": list(self.base_values), "z": list(self.z),
                "eps": [list(r) for r in self.eps], "values": [list(r) for r in self.values],
                "budgets": list(self.budgets),
                "synergy_target": [list(t) if t is not None else None for t in self.synergy_target],
                "tie_break": list(self.tie_break), "clock_ceiling": self.clock_ceiling,
                "resale": list(self.resale) if self.resale is not None else None,
                "signals": [list(r) for r in self.signals] if self.signals is not None else None}

    @staticmethod
    def from_json(d: dict) -> "StageDraw":
        """Rebuild a :class:`StageDraw` from :meth:`to_json` output."""
        return StageDraw(
            stage=int(d["stage"]),
            base_values=tuple(int(x) for x in d["base_values"]),
            z=tuple(float(x) for x in d["z"]),
            eps=tuple(tuple(float(x) for x in r) for r in d["eps"]),
            values=tuple(tuple(int(x) for x in r) for r in d["values"]),
            budgets=tuple(int(x) for x in d["budgets"]),
            synergy_target=tuple(tuple(int(x) for x in t) if t is not None else None
                                 for t in d["synergy_target"]),
            tie_break=tuple(int(x) for x in d["tie_break"]),
            clock_ceiling=int(d["clock_ceiling"]),
            resale=tuple(int(x) for x in d["resale"]) if d.get("resale") is not None else None,
            signals=tuple(tuple(int(x) for x in r) for r in d["signals"])
            if d.get("signals") is not None else None,
        )


# --------------------------------------------------------------------------------------------------------- #
# The spec.
# --------------------------------------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AuctionSpec:
    """A complete repeated-auction episode specification (design.md §2.1).

    Parameters
    ----------
    item_slots : tuple[ItemSlot, ...]
        The persistent catalogue; ``len`` must equal ``mechanism.n_items``.
    attr_names : tuple[str, ...]
        Names of the ``K`` public attribute dimensions, aligned with every ``a_i`` and ``w_j``.
    beta, sigma_z, sigma_eps, sigma_nu : float
        The PUBLIC structural constants of the generative model, announced in the rules so a rival can
        compute a genuinely informative posterior (design.md §2.2).
    bidders : tuple[BidderSpec, ...]
        Exactly :data:`N_BIDDERS` seats; personas persist across stages.
    horizon : int
        ``T``, the number of auction stages in the episode. ``len(stages)`` must equal it.
    stages : tuple[StageDraw, ...]
        The frozen per-stage realizations, in stage order.
    mechanism : Mechanism
        The format config. Formats never fork a runner.
    value_structure : str
        One of :data:`VALUE_STRUCTURES`; consistency with ``beta``/``sigma_z``/``gamma`` is validated here so
        an ``"ipv"`` spec cannot silently carry a live persona term.
    channel, dm_cap, talk_rounds : str, int, int
        The communication affordances (design.md §3.2, §3.4).
    disclose_public_facts : bool
        The linkage-principle switch [milgrom_weber1982]: whether the stage publishes extra public information.
    ring : RingSpec | None
        An instructed/designated ring, or ``None`` (the committed cells).
    framing : str
        ``"datacenter"`` (default) or ``"neutral"`` — a prompt-surface flag carried on the spec so the
        analysis can never pool the two by accident.
    meta : dict
        Anything scenario- or generator-private (provenance, bank position, difficulty tags).
    """

    item_slots: tuple[ItemSlot, ...]
    attr_names: tuple[str, ...]
    bidders: tuple[BidderSpec, ...]
    horizon: int
    stages: tuple[StageDraw, ...]
    mechanism: Mechanism
    beta: float = DEFAULT_BETA
    sigma_z: float = DEFAULT_SIGMA_Z
    sigma_eps: float = DEFAULT_SIGMA_EPS
    sigma_nu: float = DEFAULT_SIGMA_NU
    value_structure: str = "apv"
    channel: str = "silent"
    dm_cap: int = DEFAULT_DM_CAP
    talk_rounds: int = DEFAULT_TALK_ROUNDS
    disclose_public_facts: bool = False
    ring: RingSpec | None = None
    framing: str = "datacenter"
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.value_structure not in VALUE_STRUCTURES:
            raise ValueError(f"value_structure must be one of {VALUE_STRUCTURES}, got {self.value_structure!r}")
        if self.channel not in CHANNELS:
            raise ValueError(f"channel must be one of {CHANNELS}, got {self.channel!r}")
        if len(self.bidders) != N_BIDDERS:
            raise ValueError(f"an auction spec carries exactly {N_BIDDERS} seats, got {len(self.bidders)}")
        if len(self.item_slots) != self.mechanism.n_items:
            raise ValueError(f"{len(self.item_slots)} item slots but mechanism.n_items="
                             f"{self.mechanism.n_items}")
        if len(self.stages) != self.horizon:
            raise ValueError(f"horizon={self.horizon} but {len(self.stages)} stage draws supplied")
        K = len(self.attr_names)
        for slot in self.item_slots:
            if len(slot.loading) != K:
                raise ValueError(f"slot {slot.slot_id} has {len(slot.loading)} loadings, expected K={K}")
        for b in self.bidders:
            if len(b.attrs) != K:
                raise ValueError(f"seat {b.seat} has {len(b.attrs)} attributes, expected K={K}")
            if b.capacity < 1:
                raise ValueError(f"seat {b.seat} capacity must be >= 1")
            if not 0.0 < b.decay <= 1.0:
                raise ValueError(f"seat {b.seat} decay must be in (0, 1], got {b.decay}")
        if [b.seat for b in self.bidders] != list(range(N_BIDDERS)):
            raise ValueError("bidders must be in seat order 0..4")
        # The value-structure switch is a PROPERTY of the stored spec, not a convention the generator kept in
        # its head: an "ipv" spec whose beta is live would print a persona term in the rules that the values
        # do not obey, and no downstream check would catch it.
        if self.value_structure == "ipv" and (self.beta != 0.0 or self.sigma_z != 0.0
                                              or any(b.gamma != 0.0 for b in self.bidders)):
            raise ValueError("ipv requires beta = sigma_z = 0 and every gamma = 0 (design.md §2.2)")
        if self.value_structure == "apv" and any(b.gamma != 0.0 for b in self.bidders):
            raise ValueError("apv requires every gamma = 0; a live resale weight makes values interdependent")
        if self.value_structure != "interdep" and any(s.resale is not None for s in self.stages):
            raise ValueError("only an interdep spec carries realized resale values")
        for t, st in enumerate(self.stages, start=1):
            if st.stage != t:
                raise ValueError(f"stage draws must be in order 1..T; position {t} carries stage {st.stage}")
            if len(st.values) != N_BIDDERS or any(len(r) != self.n_items for r in st.values):
                raise ValueError(f"stage {t} value table must be {N_BIDDERS} x {self.n_items}")
            if any(int(v) != v for r in st.values for v in r) or any(int(b) != b for b in st.budgets):
                raise ValueError(f"stage {t} carries non-whole-number values or budgets")

    # -- shape ---------------------------------------------------------------------------------------------
    @property
    def n_bidders(self) -> int:
        """Number of seats (always :data:`N_BIDDERS`)."""
        return len(self.bidders)

    @property
    def n_items(self) -> int:
        """Number of distinct lots per stage."""
        return len(self.item_slots)

    @property
    def K(self) -> int:
        """Number of public attribute dimensions."""
        return len(self.attr_names)

    @property
    def loadings(self) -> np.ndarray:
        """The ``(n_items, K)`` public loading matrix ``w``."""
        return np.array([s.loading for s in self.item_slots], dtype=float)

    @property
    def attrs(self) -> np.ndarray:
        """The ``(n_bidders, K)`` public attribute matrix ``a``."""
        return np.array([b.attrs for b in self.bidders], dtype=float)

    @property
    def capacities(self) -> tuple[int, ...]:
        """Per-seat capacity ``k_i`` (max lots won per stage)."""
        return tuple(b.capacity for b in self.bidders)

    @property
    def decays(self) -> tuple[float, ...]:
        """Per-seat diminishing-returns factor ``d_i``."""
        return tuple(b.decay for b in self.bidders)

    @property
    def synergy_rates(self) -> tuple[float, ...]:
        """Per-seat complementarity rate ``c_i``."""
        return tuple(b.synergy_rate for b in self.bidders)

    @property
    def gammas(self) -> tuple[float, ...]:
        """Per-seat resale weight ``gamma_i`` (all zero outside INTERDEP)."""
        return tuple(b.gamma for b in self.bidders)

    def stage(self, t: int) -> StageDraw:
        """The stage-``t`` draw, ``t`` 1-indexed as in design.md §3.1. Raises ``IndexError`` past the horizon."""
        if not 1 <= t <= self.horizon:
            raise IndexError(f"stage {t} outside 1..{self.horizon}")
        return self.stages[t - 1]

    def attribute_score(self) -> np.ndarray:
        """The public affinity matrix ``(n_bidders, n_items)`` of ``a_i . w_j`` — everything a rival holding
        only public facts knows about the shape of ``i``'s valuation curve (design.md §2.2). Zero under IPV
        only in effect, not in value: the matrix is still computable, but ``beta = 0`` makes it carry no
        information about realized values, which is what the IPV seat cards say."""
        return priors.attribute_score(self.attrs, self.loadings)

    def prefix(self, horizon: int) -> "AuctionSpec":
        """This spec truncated to its first ``horizon`` stages — how a ``T = 6`` or ``T = 8`` cell consumes a
        bank instance that carries :data:`BANK_STAGES` draws (design.md §7.1). A strict prefix, so the
        long-horizon cell is an extension of the committed cells on identical instances."""
        if not 1 <= horizon <= self.horizon:
            raise ValueError(f"prefix horizon {horizon} outside 1..{self.horizon}")
        return replace(self, horizon=horizon, stages=self.stages[:horizon])

    def to_json(self) -> dict:
        """JSON-ready dict of the whole spec (drops straight into ``Instance.payload``)."""
        return {
            "item_slots": [s.to_json() for s in self.item_slots],
            "attr_names": list(self.attr_names),
            "bidders": [b.to_json() for b in self.bidders],
            "horizon": self.horizon,
            "stages": [s.to_json() for s in self.stages],
            "mechanism": self.mechanism.to_json(),
            "beta": self.beta, "sigma_z": self.sigma_z, "sigma_eps": self.sigma_eps,
            "sigma_nu": self.sigma_nu,
            "value_structure": self.value_structure,
            "channel": self.channel, "dm_cap": self.dm_cap, "talk_rounds": self.talk_rounds,
            "disclose_public_facts": self.disclose_public_facts,
            "ring": self.ring.to_json() if self.ring is not None else None,
            "framing": self.framing,
            "meta": self.meta,
        }

    @staticmethod
    def from_json(d: dict) -> "AuctionSpec":
        """Rebuild an :class:`AuctionSpec` from :meth:`to_json` output — an exact round-trip, so a stored
        instance replays the SAME auction."""
        return AuctionSpec(
            item_slots=tuple(ItemSlot.from_json(s) for s in d["item_slots"]),
            attr_names=tuple(d["attr_names"]),
            bidders=tuple(BidderSpec.from_json(b) for b in d["bidders"]),
            horizon=int(d["horizon"]),
            stages=tuple(StageDraw.from_json(s) for s in d["stages"]),
            mechanism=Mechanism.from_json(d["mechanism"]),
            beta=float(d.get("beta", DEFAULT_BETA)),
            sigma_z=float(d.get("sigma_z", DEFAULT_SIGMA_Z)),
            sigma_eps=float(d.get("sigma_eps", DEFAULT_SIGMA_EPS)),
            sigma_nu=float(d.get("sigma_nu", DEFAULT_SIGMA_NU)),
            value_structure=d.get("value_structure", "apv"),
            channel=d.get("channel", "silent"),
            dm_cap=int(d.get("dm_cap", DEFAULT_DM_CAP)),
            talk_rounds=int(d.get("talk_rounds", DEFAULT_TALK_ROUNDS)),
            disclose_public_facts=bool(d.get("disclose_public_facts", False)),
            ring=RingSpec.from_json(d["ring"]) if d.get("ring") is not None else None,
            framing=d.get("framing", "datacenter"),
            meta=d.get("meta", {}),
        )


# --------------------------------------------------------------------------------------------------------- #
# Deterministic generation.
# --------------------------------------------------------------------------------------------------------- #
def synergy_target_size(n_items: int) -> int:
    """Size of the private synergy target SET at ``n_items`` lots: a pair below
    :data:`SYNERGY_TARGET_LARGE_THRESHOLD` lots, a triple at or above (design.md §2.2)."""
    return SYNERGY_TARGET_SIZE_LARGE if n_items >= SYNERGY_TARGET_LARGE_THRESHOLD else SYNERGY_TARGET_SIZE_SMALL


def generate_spec(seed: int, *, mechanism: Mechanism, value_structure: str = "apv",
                  horizon: int = BANK_STAGES, channel: str = "silent",
                  talk_rounds: int = DEFAULT_TALK_ROUNDS, dm_cap: int = DEFAULT_DM_CAP,
                  beta: float = DEFAULT_BETA, sigma_z: float = DEFAULT_SIGMA_Z,
                  sigma_eps: float = DEFAULT_SIGMA_EPS, sigma_nu: float = DEFAULT_SIGMA_NU,
                  persona_order: tuple[int, ...] | None = None, coherent: bool = True,
                  disclose_public_facts: bool = False, framing: str = "datacenter",
                  ring: RingSpec | None = None, meta: dict | None = None) -> AuctionSpec:
    """Generate a complete :class:`AuctionSpec` deterministically from ``seed``.

    The generator implements design.md §2.2 exactly, with the value equation itself living in
    :func:`~interlens.arena.auction.priors.realize_values` so there is one copy of it.

    Parameters
    ----------
    seed : int
        The instance seed. Two calls with the same seed and the same arguments produce byte-identical JSON.
    mechanism : Mechanism
        The format config; its ``n_items`` fixes the catalogue size.
    value_structure : str
        ``"ipv"`` / ``"apv"`` / ``"interdep"``. The switch is applied AFTER the latent draws, so the ``eps``
        stream is identical across structures at a fixed seed — which is what makes O1 <-> O2 a within-bank
        paired contrast rather than two populations (design.md §7.1).
    horizon : int
        Number of stage draws to generate. Bank instances use :data:`BANK_STAGES`; a cell consumes a prefix
        via :meth:`AuctionSpec.prefix`.
    channel, talk_rounds, dm_cap : str, int, int
        Communication affordances, passed through to the spec.
    beta, sigma_z, sigma_eps, sigma_nu : float
        Public structural constants; ``beta`` and ``sigma_z`` are forced to 0 under IPV.
    persona_order : tuple[int, ...] | None
        Permutation of :data:`~interlens.arena.auction.priors.PERSONAS` indices onto seats 0..4. ``None``
        draws one from ``seed``, which is how persona/seat identity varies across the bank while the five
        archetypes stay fixed. The persona-scrambled control X1 does NOT use this: it keeps the draws and
        permutes the CARDS, via :func:`scramble_public_cards`, which is applied to a bank instance at cell
        time rather than at generation time so X1 and O1 read the SAME frozen draws.
    coherent : bool
        Apply the once-per-instance coherence permutation (design.md §2.2, the ``_make_role_coherent``
        analogue): a persona's expected-argmax slot is never one its public attributes point away from. The
        permutation moves ``eps`` labels only, so the realized value multiset is unchanged and the draw stays
        RNG-neutral.
    disclose_public_facts, framing, ring, meta
        Passed through to the spec unchanged.

    Returns
    -------
    AuctionSpec
        A validated spec with ``horizon`` stage draws.
    """
    if value_structure not in VALUE_STRUCTURES:
        raise ValueError(f"value_structure must be one of {VALUE_STRUCTURES}, got {value_structure!r}")
    rng = np.random.default_rng(seed)
    n_items = mechanism.n_items
    K = len(priors.ATTR_NAMES)

    # -- persistent structure ------------------------------------------------------------------------------
    order = tuple(int(i) for i in rng.permutation(N_BIDDERS)) if persona_order is None else tuple(persona_order)
    if sorted(order) != list(range(N_BIDDERS)):
        raise ValueError(f"persona_order must be a permutation of 0..{N_BIDDERS - 1}, got {persona_order!r}")
    personas = [priors.PERSONAS[p] for p in order]

    loadings = priors.draw_loadings(rng, n_items, K)
    item_slots = tuple(ItemSlot(slot_id=j, name=priors.slot_name(j, n_items),
                                blurb_slug=priors.slot_blurb_slug(loadings[j]),
                                loading=tuple(float(x) for x in loadings[j]))
                       for j in range(n_items))

    # The IPV switch zeroes the persona term and the resale channel; the sigmas of the DRAWS are untouched so
    # the eps stream stays identical across structures at a fixed seed.
    eff_beta = 0.0 if value_structure == "ipv" else beta
    eff_sigma_z = 0.0 if value_structure == "ipv" else sigma_z
    gamma_on = value_structure == "interdep"

    bidders = tuple(BidderSpec(seat=i, persona_id=p.persona_id, display_name=p.display_name,
                               attrs=p.attrs, capacity=p.capacity,
                               gamma=p.gamma if gamma_on else 0.0,
                               synergy_rate=p.synergy_rate if n_items > 1 else 0.0,
                               decay=p.decay, budget_mult=p.budget_mult,
                               public_fact_keys=p.public_fact_keys,
                               private_fact_keys=p.private_fact_keys)
                    for i, p in enumerate(personas))

    attrs = np.array([b.attrs for b in bidders], dtype=float)
    affinity = priors.attribute_score(attrs, loadings)
    gammas = np.array([b.gamma for b in bidders], dtype=float)
    capacities = np.array([b.capacity for b in bidders], dtype=int)
    budget_mults = np.array([b.budget_mult for b in bidders], dtype=float)
    synergy_on = np.array([b.synergy_rate > 0 for b in bidders], dtype=bool)
    target_size = min(synergy_target_size(n_items), n_items)

    # -- stage draws ---------------------------------------------------------------------------------------
    stages = []
    for t in range(1, horizon + 1):
        base = rng.integers(BASE_VALUE_RANGE[0], BASE_VALUE_RANGE[1] + 1, size=n_items)
        z_std = rng.standard_normal(N_BIDDERS)
        eps_std = rng.standard_normal((N_BIDDERS, n_items))
        z = z_std * eff_sigma_z
        eps = eps_std * sigma_eps
        if coherent:
            eps = priors.make_coherent(eps, affinity)
        resale = (rng.integers(BASE_VALUE_RANGE[0], BASE_VALUE_RANGE[1] + 1, size=n_items)
                  if gamma_on else None)
        signals = (np.round(resale[None, :] * np.exp(rng.standard_normal((N_BIDDERS, n_items)) * sigma_nu))
                   .astype(np.int64) if gamma_on else None)
        values = priors.realize_values(base_values=base, loadings=loadings, attrs=attrs, beta=eff_beta,
                                       z=z, eps=eps, gammas=gammas, resale=resale)
        budgets = priors.stage_budgets(values, capacities, budget_mults)
        targets = []
        for i in range(N_BIDDERS):
            if synergy_on[i] and n_items > 1:
                pick = rng.choice(n_items, size=target_size, replace=False)
                targets.append(tuple(sorted(int(x) for x in pick)))
            else:
                targets.append(None)
        tie_break = tuple(int(x) for x in rng.permutation(N_BIDDERS))
        ceiling = int(values.max()) + mechanism.increment
        stages.append(StageDraw(
            stage=t,
            base_values=tuple(int(x) for x in base),
            z=tuple(float(x) for x in z),
            eps=tuple(tuple(float(x) for x in row) for row in eps),
            values=tuple(tuple(int(x) for x in row) for row in values),
            budgets=tuple(int(x) for x in budgets),
            synergy_target=tuple(targets),
            tie_break=tie_break,
            clock_ceiling=ceiling,
            resale=tuple(int(x) for x in resale) if resale is not None else None,
            signals=tuple(tuple(int(x) for x in row) for row in signals) if signals is not None else None,
        ))

    spec_meta = {"seed": int(seed), "persona_order": list(order), "coherent": bool(coherent)}
    spec_meta.update(meta or {})
    return AuctionSpec(item_slots=item_slots, attr_names=priors.ATTR_NAMES, bidders=bidders,
                       horizon=horizon, stages=tuple(stages), mechanism=mechanism,
                       beta=eff_beta, sigma_z=eff_sigma_z, sigma_eps=sigma_eps, sigma_nu=sigma_nu,
                       value_structure=value_structure, channel=channel, dm_cap=dm_cap,
                       talk_rounds=talk_rounds, disclose_public_facts=disclose_public_facts,
                       ring=ring, framing=framing, meta=spec_meta)


# --------------------------------------------------------------------------------------------------------- #
# X1 — the persona-scrambled control (design.md §4.2, §6 G2(b), §8).
# --------------------------------------------------------------------------------------------------------- #
#: The fields of :class:`BidderSpec` that make up the PUBLIC CARD, permuted as ONE UNIT by
#: :func:`scramble_public_cards`. Everything printed about a seat to its rivals is in this list, and nothing
#: else is: the prose paragraph is keyed by ``persona_id``, the printed public profile line is ``attrs``, and
#: ``capacity`` / ``synergy_rate`` / ``decay`` / ``gamma`` are the multi-item and interdependent-value figures
#: the roster prints beside it. ``budget_mult`` rides along because it is a public parameter of the seat even
#: though the frozen scaffold prints no budget tercile line -- leaving it behind would make the card a
#: half-scramble the moment a wording revision started printing it.
PUBLIC_CARD_FIELDS: tuple[str, ...] = ("persona_id", "display_name", "attrs", "capacity", "gamma",
                                       "synergy_rate", "decay", "budget_mult", "public_fact_keys")


def card_scramble_seed(instance_id: str) -> int:
    """The frozen scramble seed for one bank instance, derived from its ``instance_id``.

    A content hash rather than a counter, so the derangement is a property of the INSTANCE and is identical in
    every rerun, on every machine, in any arm order -- the scramble is frozen with the bank even though it is
    applied at cell time."""
    return int.from_bytes(hashlib.sha256(instance_id.encode("utf-8")).digest()[:8], "big")


def derangement(n: int, seed: int) -> tuple[int, ...]:
    """A seeded permutation of ``0..n-1`` with NO fixed point: ``perm[i] != i`` for every ``i``.

    Drawn by rejection from :class:`numpy.random.Generator`, which terminates almost surely (the derangement
    share of permutations tends to ``1/e``). A fixed point would leave one seat holding its own card, which
    would make X1 a partial control on that seat -- the one failure mode the control cannot tolerate, since
    G2(b) reads a cross-persona dispersion that a single un-scrambled seat would inflate."""
    if n < 2:
        raise ValueError(f"a derangement needs at least 2 elements, got n={n}")
    rng = np.random.default_rng(seed)
    while True:
        perm = tuple(int(x) for x in rng.permutation(n))
        if all(perm[i] != i for i in range(n)):
            return perm


def scramble_public_cards(spec: AuctionSpec, *, seed: int) -> AuctionSpec:
    """X1: permute the five PUBLIC CARDS across the seats under a seeded derangement, keeping every draw.

    What moves is the whole card as one unit -- :data:`PUBLIC_CARD_FIELDS`, i.e. the persona prose (keyed by
    ``persona_id``), the printed public attribute vector ``a_i``, and the public per-seat figures beside it.
    Seat ``i`` presents as, and *is*, the organization whose card it holds: the addressable seat id, the
    roster entry, the "your seat" line, and every mechanic the card states (capacity limit, adjacency
    premium, decay) are the card's, so nothing a bidder reads contradicts anything else it reads.

    What does NOT move is every seat's PRIVATE block -- its realized valuations, its budget, its synergy
    target set, its resale signals, and the tie-break permutation -- because those live on
    :class:`StageDraw`, which this function does not touch. **Valuations are not redrawn.** The scramble
    therefore breaks exactly one thing: the mapping from the public card to the valuation it used to
    describe. Persona text is still present at every seat (which is what controls Jia et al.'s
    persona-shifts-competence confound), and it is now uninformative about the draw (which is what destroys
    the prior's information content, the thing G2(b) tests O1 against).

    The computable free arms run under this too, and their posteriors are then systematically wrong, since a
    rational bidder forms them from the public attribute matrix. That is the intended reading, not a defect:
    it prices what the public prior was worth to a bidder that used it correctly.

    Parameters
    ----------
    spec : AuctionSpec
        The instance spec, already at the cell's mechanism / horizon / channel.
    seed : int
        The derangement seed; use :func:`card_scramble_seed` on the instance id so it is frozen with the bank.

    Returns
    -------
    AuctionSpec
        A new spec with permuted cards and a ``meta["card_scramble"]`` provenance block recording the
        derangement, the seed, and which fields moved.

    Raises
    ------
    ValueError
        Under ``interdep``, where ``gamma`` selects which seat receives the stage's resale signals: moving the
        published resale weight away from the seat holding the signals would be a half-scramble across the
        public/private line, so the control is refused rather than approximated. X1 is an ``apv`` cell.

    Example::

        spec = scramble_public_cards(spec, seed=card_scramble_seed(instance.instance_id))
        spec.meta["card_scramble"]["derangement"]      # e.g. [2, 3, 4, 0, 1]
    """
    if spec.value_structure == "interdep":
        raise ValueError("the persona scramble is not defined under interdep: gamma is both a printed card "
                         "figure and the switch selecting which seat holds the stage's resale signals, so "
                         "permuting it would split one seat's public and private information")
    perm = derangement(len(spec.bidders), seed)
    bidders = tuple(replace(spec.bidders[i], seat=i,
                            **{f: getattr(spec.bidders[perm[i]], f) for f in PUBLIC_CARD_FIELDS})
                    for i in range(len(spec.bidders)))
    meta = dict(spec.meta)
    meta["card_scramble"] = {"derangement": list(perm), "seed": int(seed),
                             "fields": list(PUBLIC_CARD_FIELDS),
                             "note": "seat i holds seat perm[i]'s public card; every stage draw is unmoved"}
    return replace(spec, bidders=bidders, meta=meta)
