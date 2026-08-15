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

"""The auction move vocabulary, the bid ledger, and DM routing (design.md §12 item 2).

This module EXTENDS ``arena/actions.py`` rather than editing it: the negotiation move vocabulary
(``Propose``/``Accept``/``Reject``/``Walk``) is untouched, and the shared machinery it already owns —
:class:`~interlens.arena.actions.Action`, :class:`~interlens.arena.actions.ParseResult`, and the
:data:`~interlens.arena.actions.SYNTAX` / :data:`~interlens.arena.actions.LEGALITY` error classes that drive
retry-once-with-specific-feedback — is imported and reused.

Three pieces, mirroring the negotiation layer one for one:

- **The action dataclasses** — one per row of design.md §3.3's action grammar, plus the three side-channel
  moves (:class:`Speak`, :class:`DirectMessage`, :class:`Transfer`) that ride alongside the binding move in
  the four-channel envelope of §3.2.
- **:class:`BidLedger`** — the sibling of ``OfferRegistry``: monotonic ids, standing-high tracking per lot,
  irrevocable exits, and the eligibility ratchet, all as a PURE FUNCTION of the action sequence, so replay
  reconstructs the ledger exactly and an analysis never has to trust a stored summary.
- **:class:`DMRouter`** — delivers addressed messages to their recipients only, enforces ``dm_cap``, and
  records the full directed graph (sender, recipient, stage, round, text) that the DM-graph panel and the
  per-dyad mutual-information estimator both read.

Economic errors are MEASURED, never blocked (design.md §3.2): bidding above your own valuation parses
cleanly and is counted downstream. Bidding above BUDGET is different — payments must be collectible — so it
is a :data:`~interlens.arena.actions.LEGALITY` error here, retried once and then truncated by the scenario.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from ...parsing import last_json
from ..actions import LEGALITY, SYNTAX, Action, ParseResult, Pass

__all__ = ["Bid", "PassLot", "SAATurn", "Schedule", "Demand", "Stay", "Exit", "Claim", "Wait", "Speak",
           "DirectMessage", "Transfer", "Pass", "auction_action_from_json", "BidLedger", "StandingBid",
           "DMRouter", "DirectMessageRecord", "TransferBook", "TurnEnvelope", "parse_auction_action",
           "parse_envelope", "whole_number", "resolve_item"]


# ----------------------------------------------------------------- actions ---

@dataclass(frozen=True)
class Bid(Action):
    """A priced bid of ``amount`` on lot ``item`` (a slot index). The single-lot families carry ``item = 0``;
    SAA turns may carry several :class:`Bid` moves, one per lot."""

    kind: ClassVar[str] = "bid"
    item: int
    amount: int

    def to_json(self) -> dict:
        return {"action": self.kind, "item": self.item, "amount": self.amount}


@dataclass(frozen=True)
class PassLot(Action):
    """Decline to bid on lot ``item`` this round. Under the eligibility ratchet this is IRREVOCABLE for the
    rest of the stage (design.md §3.3, SAA), which is what makes passing a strategic commitment rather than
    a shrug."""

    kind: ClassVar[str] = "pass_lot"
    item: int

    def to_json(self) -> dict:
        return {"action": self.kind, "item": self.item}


@dataclass(frozen=True)
class SAATurn(Action):
    """One whole SAA turn: the raises and the permanent passes a seat declared together.

    The reviewed action grammar lets a bidder raise on any number of lots and pass permanently on any number
    of lots in a single turn, so an SAA turn is not one move but a SET of them, and the set has to be
    validated as a unit (its total is what the budget binds on, and a lot may not appear in both halves).
    :func:`parse_auction_action` deliberately validates exactly one binding move and therefore does not read
    this shape; the scenario parses the list and folds each :class:`Bid` / :class:`PassLot` into the ledger
    individually, so the ledger's purity property is untouched."""

    kind: ClassVar[str] = "saa_turn"
    bids: tuple = ()
    passes: tuple = ()

    def to_json(self) -> dict:
        return {"action": self.kind, "bids": [b.to_json() for b in self.bids],
                "passes": [p.to_json() for p in self.passes]}


@dataclass(frozen=True)
class Schedule(Action):
    """A weakly-decreasing per-unit bid vector for a uniform-price stage."""

    kind: ClassVar[str] = "schedule"
    amounts: tuple[int, ...]

    def to_json(self) -> dict:
        return {"action": self.kind, "amounts": list(self.amounts)}


@dataclass(frozen=True)
class Demand(Action):
    """A demand for ``units`` at the current clock price in a clinching stage; must be weakly decreasing
    across rounds [ausubel2004]."""

    kind: ClassVar[str] = "demand"
    units: int

    def to_json(self) -> dict:
        return {"action": self.kind, "units": self.units}


@dataclass(frozen=True)
class Stay(Action):
    """Remain active at the current ascending-clock price (English)."""

    kind: ClassVar[str] = "stay"


@dataclass(frozen=True)
class Exit(Action):
    """Leave the ascending clock. IRREVOCABLE and PUBLIC — the visibility is the mechanism through which the
    linkage principle operates, so exits are transcript events, not a summary [milgrom_weber1982]."""

    kind: ClassVar[str] = "exit"


@dataclass(frozen=True)
class Claim(Action):
    """Take the lot at the current descending-clock price (Dutch). The first claim ends the stage."""

    kind: ClassVar[str] = "claim"


@dataclass(frozen=True)
class Wait(Action):
    """Let the descending clock fall one increment (Dutch). Nothing is revealed between rounds, which is what
    makes the format strategically equivalent to first-price [vickrey1961, pp. 20-23]."""

    kind: ClassVar[str] = "wait"


@dataclass(frozen=True)
class Speak(Action):
    """Public broadcast cheap talk. Available only when ``channel != "silent"``; carried alongside the
    binding move rather than instead of it."""

    kind: ClassVar[str] = "speak"
    text: str

    def to_json(self) -> dict:
        return {"action": self.kind, "text": self.text}


@dataclass(frozen=True)
class DirectMessage(Action):
    """A private message to named recipients. Available under ``dm`` / ``dm_transfers``, capped at
    ``dm_cap`` recipients per turn — the cap bounds cost and keeps the DM graph interpretable, since a bidder
    that DMs all four rivals every turn is broadcasting (design.md §3.2)."""

    kind: ClassVar[str] = "dm"
    to: tuple[str, ...]
    text: str

    def to_json(self) -> dict:
        return {"action": self.kind, "to": list(self.to), "text": self.text}


@dataclass(frozen=True)
class Transfer(Action):
    """A side payment the harness EXECUTES at settlement. Available only under ``dm_transfers``; that single
    switch is the strong-cartel / weak-cartel contrast [mcafee_mcmillan1992, pp. 582-589], because under
    plain ``dm`` a promise to pay is words and nothing more."""

    kind: ClassVar[str] = "transfer"
    to: str
    amount: int

    def to_json(self) -> dict:
        return {"action": self.kind, "to": self.to, "amount": self.amount}


_AUCTION_ACTIONS: dict[str, type] = {a.kind: a for a in
                                     (Bid, PassLot, SAATurn, Schedule, Demand, Stay, Exit, Claim, Wait,
                                      Speak, DirectMessage, Transfer)}


def auction_action_from_json(d: dict) -> Action:
    """Reconstruct a typed auction :class:`Action` from its stored dict — the inverse of ``to_json``. Raises
    ``ValueError`` for a dict that does not name an auction action kind."""
    kind = d.get("action") or d.get("type") or d.get("kind")
    kind = str(kind).strip().lower() if isinstance(kind, str) else None
    cls = _AUCTION_ACTIONS.get(kind)
    if cls is None:
        raise ValueError(f"not a serialized auction action: {d!r}")
    if cls is Bid:
        return Bid(item=int(d["item"]), amount=int(d["amount"]))
    if cls is PassLot:
        return PassLot(item=int(d["item"]))
    if cls is SAATurn:
        return SAATurn(bids=tuple(Bid(item=int(b["item"]), amount=int(b["amount"])) for b in d.get("bids", ())),
                       passes=tuple(PassLot(item=int(x["item"])) for x in d.get("passes", ())))
    if cls is Schedule:
        return Schedule(amounts=tuple(int(x) for x in d["amounts"]))
    if cls is Demand:
        return Demand(units=int(d["units"]))
    if cls is Speak:
        return Speak(text=str(d.get("text", "")))
    if cls is DirectMessage:
        return DirectMessage(to=tuple(d.get("to", ())), text=str(d.get("text", "")))
    if cls is Transfer:
        return Transfer(to=str(d["to"]), amount=int(d["amount"]))
    return cls()


# -------------------------------------------------------------- bid ledger ---

@dataclass
class StandingBid:
    """One registered bid and its live state — the sibling of ``arena.actions.Offer``.

    ``live`` flips to False when the bid is superseded by a higher standing bid on the same lot. Superseded
    bids are kept, never deleted, so the ledger is a complete record of the price path."""

    bid_id: str
    stage: int
    round: int
    seat: int
    item: int
    amount: int
    live: bool = True

    def to_json(self) -> dict:
        """JSON-ready dict."""
        return {"bid_id": self.bid_id, "stage": self.stage, "round": self.round, "seat": self.seat,
                "item": self.item, "amount": self.amount, "live": self.live}

    @staticmethod
    def from_json(d: dict) -> "StandingBid":
        """Rebuild a :class:`StandingBid` from :meth:`to_json` output."""
        return StandingBid(d["bid_id"], int(d["stage"]), int(d["round"]), int(d["seat"]), int(d["item"]),
                           int(d["amount"]), bool(d.get("live", True)))


class BidLedger:
    """Monotonic bid ids, standing-high tracking, exits, and the eligibility ratchet.

    The sibling of ``arena.actions.OfferRegistry`` and it holds the same purity property: the ledger is a
    PURE FUNCTION of the applied action sequence, so ``replay.py`` reconstructs it identically from a stored
    episode and no analysis has to trust a stored summary. ``to_json`` / ``from_json`` also persist it
    directly.

    Parameters
    ----------
    n_items : int
        Number of lots, so per-lot state is allocated up front.
    prefix : str
        Bid-id prefix; ids are ``B1``, ``B2``, ... in application order across the whole episode.
    activity_rule : str
        ``"eligibility_ratchet"`` makes a :class:`PassLot` irrevocable within its stage (a bidder that passes
        on lot ``j`` may not bid on ``j`` again that stage); ``"none"`` records the pass without binding it.
    """

    def __init__(self, n_items: int, *, prefix: str = "B", activity_rule: str = "none"):
        self.n_items = int(n_items)
        self.prefix = prefix
        self.activity_rule = activity_rule
        self.bids: list[StandingBid] = []
        self.exited: dict[int, list[int]] = {}          # stage -> seats that exited the clock
        self.passed: dict[int, set[tuple[int, int]]] = {}   # stage -> {(seat, item)} that passed
        self._counter = 0

    # -- writes --------------------------------------------------------------------------------------------
    def apply(self, action: Action, seat: int, *, stage: int, round: int) -> str | None:
        """Fold one parsed action into the ledger. :class:`Bid` registers (returning the new bid id and
        superseding any lower standing bid on that lot), :class:`PassLot` records the pass, :class:`Exit`
        records the irrevocable clock exit; everything else is a no-op here (the scenario owns settlement)."""
        if isinstance(action, Bid):
            self._counter += 1
            rec = StandingBid(f"{self.prefix}{self._counter}", stage, round, seat, action.item, action.amount)
            prev = self.standing(action.item, stage)
            if prev is not None and prev.amount <= action.amount:
                prev.live = False
            elif prev is not None:
                rec.live = False                        # a bid below the standing high never stands
            self.bids.append(rec)
            return rec.bid_id
        if isinstance(action, PassLot):
            self.passed.setdefault(stage, set()).add((seat, action.item))
        elif isinstance(action, Exit):
            self.exited.setdefault(stage, []).append(seat)
        return None

    # -- reads ---------------------------------------------------------------------------------------------
    def standing(self, item: int, stage: int) -> StandingBid | None:
        """The live standing high bid on ``item`` in ``stage``, or ``None``."""
        live = [b for b in self.bids if b.item == item and b.stage == stage and b.live]
        return live[-1] if live else None

    def standing_prices(self, stage: int, *, reserve: int = 0) -> list[int]:
        """Per-lot standing price in ``stage`` (``reserve`` where no bid stands)."""
        return [(self.standing(j, stage).amount if self.standing(j, stage) else reserve)
                for j in range(self.n_items)]

    def standing_winners(self, stage: int) -> list[int | None]:
        """Per-lot standing high bidder in ``stage`` (``None`` where no bid stands)."""
        return [(self.standing(j, stage).seat if self.standing(j, stage) else None)
                for j in range(self.n_items)]

    def eligible(self, seat: int, item: int, stage: int) -> bool:
        """Whether ``seat`` may still bid on ``item`` this stage under the activity rule."""
        if self.activity_rule != "eligibility_ratchet":
            return True
        return (seat, item) not in self.passed.get(stage, set())

    def active_seats(self, stage: int, n_bidders: int) -> list[int]:
        """Seats that have not exited the clock in ``stage``."""
        gone = set(self.exited.get(stage, []))
        return [s for s in range(n_bidders) if s not in gone]

    def stage_bids(self, stage: int) -> list[StandingBid]:
        """Every bid recorded in ``stage``, live or superseded, in application order."""
        return [b for b in self.bids if b.stage == stage]

    def to_json(self) -> dict:
        """JSON-ready dict of the whole ledger."""
        return {"n_items": self.n_items, "prefix": self.prefix, "activity_rule": self.activity_rule,
                "counter": self._counter, "bids": [b.to_json() for b in self.bids],
                "exited": {str(k): list(v) for k, v in self.exited.items()},
                "passed": {str(k): [list(p) for p in sorted(v)] for k, v in self.passed.items()}}

    @staticmethod
    def from_json(d: dict) -> "BidLedger":
        """Rebuild a :class:`BidLedger` from :meth:`to_json` output."""
        led = BidLedger(int(d["n_items"]), prefix=d.get("prefix", "B"),
                        activity_rule=d.get("activity_rule", "none"))
        led._counter = int(d.get("counter", 0))
        led.bids = [StandingBid.from_json(b) for b in d.get("bids", [])]
        led.exited = {int(k): list(v) for k, v in d.get("exited", {}).items()}
        led.passed = {int(k): {(int(a), int(b)) for a, b in v} for k, v in d.get("passed", {}).items()}
        return led


# ------------------------------------------------------------- DM routing ---

@dataclass(frozen=True)
class DirectMessageRecord:
    """One delivered private message. The DM graph and the per-dyad MI estimator are both built from these,
    so every field the analysis needs (sender, recipient, stage, round, phase) is on the record itself.

    ``phase`` is the scenario phase the message was attached to — a DM rides on whatever turn its sender
    wrote, so one sent on a bidding turn and one sent in a message round are different acts and must not read
    the same in the channel log."""

    stage: int
    round: int
    sender: str
    recipient: str
    text: str
    phase: str | None = None

    def to_json(self) -> dict:
        """JSON-ready dict."""
        return {"stage": self.stage, "round": self.round, "sender": self.sender,
                "recipient": self.recipient, "text": self.text, "phase": self.phase}

    @staticmethod
    def from_json(d: dict) -> "DirectMessageRecord":
        """Rebuild a :class:`DirectMessageRecord` from :meth:`to_json` output."""
        return DirectMessageRecord(int(d["stage"]), int(d["round"]), d["sender"], d["recipient"], d["text"],
                                   d.get("phase"))


class DMRouter:
    """Delivers addressed private messages to their recipients only, and records the directed graph.

    Privacy is STRUCTURAL, as in ``scorable.py::_publish()``: the router hands a message to the named
    recipients and to nobody else, so a seat cannot leak private state by mis-tagging it. Unknown recipients
    and self-addressed messages are dropped rather than delivered, and the count of dropped recipients is
    reported so a mis-addressed DM shows up as a protocol-hygiene number rather than vanishing.

    Parameters
    ----------
    seats : tuple[str, ...]
        Display names of the five seats, in seat order.
    dm_cap : int
        Maximum recipients per turn; recipients beyond the cap are dropped (design.md §3.2).
    """

    def __init__(self, seats: tuple[str, ...], *, dm_cap: int = 2):
        self.seats = tuple(seats)
        self.dm_cap = int(dm_cap)
        self.records: list[DirectMessageRecord] = []
        self.dropped: int = 0

    def route(self, dm: DirectMessage, sender: str, *, stage: int, round: int,
              phase: str | None = None) -> list[DirectMessageRecord]:
        """Deliver one :class:`DirectMessage` and return the records created (also appended to
        :attr:`records`). Recipients past :attr:`dm_cap`, unknown names, and the sender itself are dropped.
        ``phase`` is stamped on every record so the channel log says which turn each message rode on."""
        wanted = [r for r in dm.to if r in self.seats and r != sender]
        self.dropped += len(dm.to) - len(wanted)
        kept, seen = [], set()
        for r in wanted:
            if r not in seen and len(kept) < self.dm_cap:
                kept.append(r)
                seen.add(r)
            else:
                self.dropped += 1
        made = [DirectMessageRecord(stage, round, sender, r, dm.text, phase) for r in kept]
        self.records.extend(made)
        return made

    def inbox(self, recipient: str, *, stage: int | None = None) -> list[DirectMessageRecord]:
        """Every message delivered to ``recipient`` (optionally within one stage), in order — the DM history
        that rides in that seat's view and nobody else's."""
        return [r for r in self.records if r.recipient == recipient and (stage is None or r.stage == stage)]

    def graph(self, *, stage: int | None = None) -> dict[tuple[str, str], int]:
        """The directed message-count graph ``{(sender, recipient): count}``, optionally for one stage."""
        out: dict[tuple[str, str], int] = {}
        for r in self.records:
            if stage is not None and r.stage != stage:
                continue
            out[(r.sender, r.recipient)] = out.get((r.sender, r.recipient), 0) + 1
        return out

    def to_json(self) -> dict:
        """JSON-ready dict — DM payloads are part of the transcript export, since the graph cannot be
        reconstructed without them (design.md §10)."""
        return {"seats": list(self.seats), "dm_cap": self.dm_cap, "dropped": self.dropped,
                "records": [r.to_json() for r in self.records]}

    @staticmethod
    def from_json(d: dict) -> "DMRouter":
        """Rebuild a :class:`DMRouter` from :meth:`to_json` output."""
        r = DMRouter(tuple(d["seats"]), dm_cap=int(d.get("dm_cap", 2)))
        r.dropped = int(d.get("dropped", 0))
        r.records = [DirectMessageRecord.from_json(x) for x in d.get("records", [])]
        return r


class TransferBook:
    """Declared side payments, and their execution at settlement (``dm_transfers`` only).

    Same purity property as :class:`BidLedger`: a pure function of the applied :class:`Transfer` actions. A
    transfer whose sender cannot cover it out of its stage budget net of auction payments is recorded as
    ``executed=False`` rather than silently dropped, because an UNPAID promise is exactly the weak-cartel
    behavior the design wants to measure [mcafee_mcmillan1992]."""

    def __init__(self):
        self.declared: list[dict] = []

    def declare(self, transfer: Transfer, sender: str, *, stage: int) -> None:
        """Record one declared transfer."""
        self.declared.append({"stage": stage, "sender": sender, "to": transfer.to,
                              "amount": int(transfer.amount), "executed": False})

    def settle(self, stage: int, capacity: dict[str, float]) -> dict[str, float]:
        """Execute the stage's declared transfers against each sender's remaining ``capacity`` (budget minus
        auction payments), in declaration order. Returns the net transfer per seat (positive = received)."""
        net = {s: 0.0 for s in capacity}
        for rec in self.declared:
            if rec["stage"] != stage or rec["executed"]:
                continue
            s, r, amt = rec["sender"], rec["to"], float(rec["amount"])
            if s in capacity and r in net and capacity[s] >= amt > 0:
                capacity[s] -= amt
                net[s] -= amt
                net[r] += amt
                rec["executed"] = True
        return net

    def to_json(self) -> dict:
        """JSON-ready dict."""
        return {"declared": list(self.declared)}

    @staticmethod
    def from_json(d: dict) -> "TransferBook":
        """Rebuild a :class:`TransferBook` from :meth:`to_json` output."""
        book = TransferBook()
        book.declared = list(d.get("declared", []))
        return book


# ------------------------------------------------------------------ parse ---

@dataclass
class TurnEnvelope:
    """One turn's four channels (design.md §3.2), separated: the private ``scratchpad`` (never published),
    public ``message``, addressed ``dms``, an optional ``transfer``, and the one binding ``action``."""

    scratchpad: str = ""
    message: str = ""
    dms: list[DirectMessage] = field(default_factory=list)
    transfer: Transfer | None = None
    action: Action | None = None
    raw: Any = None


def parse_envelope(text: str | None) -> TurnEnvelope:
    """Split a turn's fenced JSON object into its four channels WITHOUT validating the binding move.

    Kept separate from :func:`parse_auction_action` so a seat that produced a legal message but an illegal
    bid still has its message published on the retry — the same separation ``scorable.py`` maintains between
    the chat channel and the formal move."""
    obj = last_json(text)
    env = TurnEnvelope(raw=obj)
    if not isinstance(obj, dict):
        return env
    env.scratchpad = str(obj.get("scratchpad", "") or "")
    env.message = str(obj.get("message", "") or "")
    for d in obj.get("dm", ()) or ():
        if isinstance(d, dict) and d.get("to") is not None:
            to = d["to"]
            env.dms.append(DirectMessage(to=tuple(to) if isinstance(to, (list, tuple)) else (str(to),),
                                         text=str(d.get("text", ""))))
    tr = obj.get("transfer")
    if isinstance(tr, dict) and tr.get("to") is not None:
        try:
            env.transfer = Transfer(to=str(tr["to"]), amount=int(tr["amount"]))
        except (KeyError, TypeError, ValueError):
            env.transfer = None
    return env


def _whole(x) -> int | None:
    """``x`` as a whole number, or ``None`` if it is not one (a float with a fractional part included — all
    prices in this design are integers, so ``210.5`` is a syntax error rather than a silent rounding)."""
    if isinstance(x, bool):
        return None
    if isinstance(x, int):
        return int(x)
    if isinstance(x, float) and float(x).is_integer():
        return int(x)
    if isinstance(x, str):
        s = x.strip().replace(",", "").lstrip("$")
        try:
            return _whole(float(s))
        except ValueError:
            return None
    return None


def parse_auction_action(text: str | None, *, family: str, item_names: tuple[str, ...],
                         standing: list[int] | None = None, increment: int = 1, granularity: int = 1,
                         reserve: int = 0, budget: int | None = None, n_units: int = 1,
                         eligible=None, clock_price: int | None = None) -> ParseResult:
    """Read and validate ONE binding auction move — the single consolidated entry point, the sibling of
    ``arena.actions.parse_action``.

    Distinguishes :data:`~interlens.arena.actions.SYNTAX` (no well-formed move could be read: absent JSON,
    unknown kind, unknown lot name, non-whole amount) from :data:`~interlens.arena.actions.LEGALITY` (a
    well-formed move that the mechanism forbids: below the standing bid plus increment, off the bid
    granularity, above the seat's budget, on a lot it has already passed, a non-monotone schedule), so a
    scenario can retry once with the parser's own message and log the two classes separately as data
    [chen2023_aucarena].

    **Bidding above your own valuation is neither** — it parses cleanly and is counted downstream as an
    economic error (design.md §3.2), which is why this function never sees the seat's values.

    Parameters
    ----------
    text : str | None
        The model's raw turn.
    family : str
        The mechanism family, which fixes the legal move kinds.
    item_names : tuple[str, ...]
        Display names of the lots, in slot order; a move may name a lot by name or by index.
    standing : list[int] | None
        Current standing high price per lot (``None`` = no bids yet, treated as ``reserve``).
    increment, granularity, reserve : int
        Mechanism parameters; a bid must be at least ``standing + increment`` (or ``reserve``) and a multiple
        of ``granularity``.
    budget : int | None
        The seat's remaining stage budget; a bid above it is a LEGALITY error (payments must be collectible).
    n_units : int
        Units on offer, for the multi-unit families.
    eligible : Callable[[int], bool] | None
        Predicate on lot index under the activity rule; a bid on an ineligible lot is a LEGALITY error.
    clock_price : int | None
        The current clock price, for the clock families.
    """
    obj = last_json(text)
    if not isinstance(obj, dict):
        return ParseResult.bad(SYNTAX, "No JSON object found. Reply with one fenced JSON object carrying an "
                                       "\"action\" field.", raw=obj)
    holder = obj.get("action")
    if isinstance(holder, dict):
        kind = holder.get("type") or holder.get("action") or holder.get("kind")
    else:
        kind, holder = holder, obj
    kind = str(kind).strip().lower() if isinstance(kind, str) else None
    if kind in (None, "none", "pass"):
        return ParseResult.bad(SYNTAX, "No action named. Legal actions in this format: "
                                       f"{_legal_kinds(family)}.", raw=obj)
    if kind not in _AUCTION_ACTIONS or kind not in _legal_kind_set(family):
        return ParseResult.bad(SYNTAX, f"Unknown or illegal action {kind!r} for this format. Legal: "
                                       f"{_legal_kinds(family)}.", raw=obj)

    if kind in ("stay", "exit", "claim", "wait"):
        return ParseResult.good(_AUCTION_ACTIONS[kind](), raw=obj)

    if kind in ("bid", "pass_lot"):
        item = _resolve_item(holder.get("item"), item_names)
        if item is None:
            return ParseResult.bad(SYNTAX, f"Unknown lot {holder.get('item')!r}; lots are "
                                           f"{list(item_names)}.", raw=obj)
        if kind == "pass_lot":
            return ParseResult.good(PassLot(item=item), raw=obj)
        amount = _whole(holder.get("amount"))
        if amount is None:
            return ParseResult.bad(SYNTAX, "The \"amount\" field must be a whole number of dollars.", raw=obj)
        if eligible is not None and not eligible(item):
            return ParseResult.bad(LEGALITY, f"You passed on {item_names[item]} earlier this stage and may "
                                             f"not bid on it again.", raw=obj)
        floor = reserve if standing is None or standing[item] < reserve else standing[item] + increment
        if amount < floor:
            return ParseResult.bad(LEGALITY, f"A bid on {item_names[item]} must be at least {floor}.", raw=obj)
        if amount % granularity:
            return ParseResult.bad(LEGALITY, f"Bids must be multiples of {granularity}.", raw=obj)
        if budget is not None and amount > budget:
            return ParseResult.bad(LEGALITY, f"A bid of {amount} exceeds your remaining budget of {budget}.",
                                   raw=obj)
        return ParseResult.good(Bid(item=item, amount=amount), raw=obj)

    if kind == "schedule":
        raw_amounts = holder.get("amounts")
        if not isinstance(raw_amounts, (list, tuple)) or len(raw_amounts) != n_units:
            return ParseResult.bad(SYNTAX, f"\"amounts\" must be a list of {n_units} whole numbers, one per "
                                           f"unit.", raw=obj)
        amounts = [_whole(a) for a in raw_amounts]
        if any(a is None for a in amounts):
            return ParseResult.bad(SYNTAX, "Every entry of \"amounts\" must be a whole number.", raw=obj)
        if any(amounts[k] < amounts[k + 1] for k in range(len(amounts) - 1)):
            return ParseResult.bad(LEGALITY, "A demand schedule must be weakly decreasing across units.",
                                   raw=obj)
        if budget is not None and sum(amounts) > budget:
            return ParseResult.bad(LEGALITY, f"The schedule's total {sum(amounts)} exceeds your remaining "
                                             f"budget of {budget}.", raw=obj)
        return ParseResult.good(Schedule(tuple(int(a) for a in amounts)), raw=obj)

    units = _whole(holder.get("units"))
    if units is None or not 0 <= units <= n_units:
        return ParseResult.bad(SYNTAX, f"\"units\" must be a whole number between 0 and {n_units}.", raw=obj)
    if budget is not None and clock_price is not None and units * clock_price > budget:
        return ParseResult.bad(LEGALITY, f"Demanding {units} units at {clock_price} exceeds your remaining "
                                         f"budget of {budget}.", raw=obj)
    return ParseResult.good(Demand(units=units), raw=obj)


#: Legal binding-move kinds per mechanism family (design.md §3.3). Side-channel moves (speak/dm/transfer)
#: ride in the envelope and are never the binding move, so they are absent here.
LEGAL_KINDS: dict[str, tuple[str, ...]] = {
    "sealed_single": ("bid",),
    "english": ("stay", "exit"),
    "dutch": ("wait", "claim"),
    "saa": ("bid", "pass_lot"),
    "uniform_price": ("schedule",),
    "clinching": ("demand",),
}


def _legal_kind_set(family: str) -> tuple[str, ...]:
    """Legal binding-move kinds for ``family``."""
    try:
        return LEGAL_KINDS[family]
    except KeyError:
        raise ValueError(f"unknown mechanism family {family!r}; known: {sorted(LEGAL_KINDS)}") from None


def _legal_kinds(family: str) -> str:
    """The legal kinds as a model-facing string for the retry message."""
    return ", ".join(_legal_kind_set(family))


def _resolve_item(raw, item_names: tuple[str, ...]) -> int | None:
    """Resolve a lot reference to a slot index: an integer index, or a display name matched
    case-insensitively with surrounding whitespace ignored. ``None`` when it names no lot. A single-lot
    format defaults a missing reference to lot 0, so a bare ``{"action": "bid", "amount": 210}`` is legal
    where there is only one thing to bid on."""
    if raw is None:
        return 0 if len(item_names) == 1 else None
    idx = _whole(raw)
    if idx is not None and 0 <= idx < len(item_names):
        return int(idx)
    if isinstance(raw, str):
        key = raw.strip().lower()
        for j, name in enumerate(item_names):
            if name.strip().lower() == key:
                return j
    return None


#: Public aliases for the two reference helpers. The scenario lane's SAA grammar carries a LIST of lots per
#: turn (``{"action": "bid", "bids": [...], "lots": [...]}``, the reviewed template), which
#: :func:`parse_auction_action` does not read because it validates exactly one binding move; the scenario
#: therefore parses that list itself and needs the same whole-number and lot-reference rules rather than a
#: second, subtly different copy of them.
whole_number = _whole
resolve_item = _resolve_item
