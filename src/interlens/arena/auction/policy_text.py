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

"""What the computable seats SAY -- the templated broadcast and DM behavior of design.md §3.4.

The mute-channel lesson is binding: a computable seat that cannot speak loses via the microphone, not the
decision rule. So the rational and oracle seats speak and DM from templates, with every slot filled by a
quantity the policy already computes.

Two constraints pull against each other and both are hard.

**No leakage.** A policy seat never emits a number or a claim a rival could not have computed itself from
public information plus this seat's own already-public actions. Every slot below is either public-only or a
label over the seat's own public bids. The one exception is ``counter_lots``, which is derived from private
values and reveals a preference ORDERING rather than a number -- exactly as much disclosure as an LLM seat
makes when it names lots in a message, and permitted because the alternative (a policy seat that can accept or
refuse but never counter) is a strictly weaker communicator than the LLM seats it is compared against, which
reintroduces the mute-channel confound in a subtler form.

**Not trivially a bot.** A seat that emits one fixed sentence every stage is identified as non-LLM in one
stage, and every DM addressed to it after that is addressed to a known machine, which would confound Q5. So
each template has a small fixed set of surface variants chosen by a seeded index derived from the frozen
draws: ``variant = hash(instance_id, seat, stage, template_id) mod n_variants`` -- reproducible, arm-invariant,
and not a function of anything private.

**The oracle's templates are IDENTICAL to the rational seat's**, filled from the same public-only expressions.
An oracle that spoke from full information would leak every other seat's private draws through the channel and
invalidate every cell it appeared in; its information advantage shows up in its bids and in which proposals it
accepts, never in its text.

This module is prose that a policy EMITS, not a prompt a policy reads, which is why it lives beside the policy
classes rather than in ``scenarios/auction_prompts.py``. It is frozen and SHA-pinned on the same schedule as
the prompts, since an LLM seat's behavior is a function of what the policy seats say to it.
"""
from __future__ import annotations

import hashlib

#: Every reviewed surface variant, keyed by template id. Verbatim from
#: ``docs/templates/policy_seat_messages.md``.
VARIANTS: dict[str, tuple[str, ...]] = {
    "public_position.open": (
        "{display_name} here. On this catalogue our profile points at {fit_lots}; that is where we expect to "
        "be active.",
        "{display_name}. Reading this stage's catalogue against our estate, {fit_lots} are the lots that fit "
        "us. We will be bidding.",
        "{display_name}. Our interest this stage is concentrated in {fit_lots}, for the reasons on our card.",
    ),
    "public_position.holding": (
        "{display_name} holds {held_lots} at present and intends to defend them.",
        "{display_name}. We are standing high on {held_lots} and expect to stay there.",
    ),
    "public_position.empty": (
        "{display_name}. We are not standing high on anything at the moment and are still assessing.",
        "{display_name}. Nothing standing to us this round.",
    ),
    "public_position.single": (
        "{display_name}. This hall reads {fit_word} against our profile; we will bid accordingly.",
    ),
    "dm_reply.accept": (
        "{proposer} — that works for us. We will take {proposed_lots} and leave {proposer_lots} alone this "
        "stage.",
        "{proposer} — {margin_word} better for us than bidding it out. We will hold to {proposed_lots} and "
        "stay off {proposer_lots} this stage.",
    ),
    "dm_reply.decline": (
        "{proposer} — that does not work for us. Bidding {proposed_lots} out on our own comes out "
        "{margin_word} ahead, so we will be active across the catalogue this stage.",
        "{proposer} — no. The arithmetic favors us competing here.",
    ),
    "dm_reply.counter": (
        "{proposer} — not as put. {counter_lots} we can stay off; the rest we will be bidding on.",
        "{proposer} — {counter_lots} yes, the remainder no. That is as far as our numbers go.",
    ),
    "dm_reply.lapsed": (
        "{proposer} — this stage runs differently for us. We will be bidding on {counter_lots}.",
        "{proposer} — the numbers changed with the catalogue. We are active on {counter_lots} this stage.",
    ),
    "dm_initiate": (
        "{threat_seat} — our profiles both point at {fit_lot} and bidding it out costs us both. We would take "
        "{fit_lot} and stay off {counter_lots} this stage. Workable?",
        "{threat_seat} — we read you as our closest competition on {fit_lot}. Proposal for this stage: "
        "{fit_lot} to us, {counter_lots} to you, neither of us bidding the other's.",
        "{threat_seat} — {fit_lot} is contested between us on the public numbers. We are willing to leave "
        "{counter_lots} alone this stage if you leave {fit_lot} alone.",
    ),
}

#: The transfer clause appended at the ``dm_transfers`` rung when the arithmetic supports a payment.
TRANSFER_CLAUSE = "…and we will transfer {transfer_amount} to you at settlement this stage."


def variant_index(instance_id: str, seat: int, stage: int, template_id: str, n_variants: int) -> int:
    """The seeded surface-variant index, ``hash(instance_id, seat, stage, template_id) mod n_variants``.

    Uses SHA-256 rather than Python's ``hash``, which is salted per process and would make the same episode
    render differently on two runs -- the variant must be reproducible and arm-invariant, since a variant that
    moved between arms would be a confound in exactly the comparison Q5 is about."""
    key = f"{instance_id}|{seat}|{stage}|{template_id}".encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:8], "big") % max(1, n_variants)


def render(template_id: str, *, instance_id: str, seat: int, stage: int, **slots) -> str:
    """One templated line, at this episode's seeded surface variant."""
    options = VARIANTS[template_id]
    return options[variant_index(instance_id, seat, stage, template_id, len(options))].format(**slots)


def public_position(*, instance_id: str, seat: int, stage: int, display_name: str, fit_lots, held_lots,
                    single_item: bool, fit_word: str = "neutral", opening: bool = True) -> str:
    """The broadcast: presence and public-profile fit at stage start, holdings mid-stage. Nothing else.

    ``fit_lots`` is the public fit score ``a_i . w_j``, so a rival gains nothing it could not compute -- which
    is the point: the seat is present and legible on the channel without disclosing anything."""
    kw = dict(instance_id=instance_id, seat=seat, stage=stage, display_name=display_name)
    if single_item:
        return render("public_position.single", fit_word=fit_word, **kw)
    if opening:
        return render("public_position.open", fit_lots=", ".join(fit_lots), **kw)
    if held_lots:
        return render("public_position.holding", held_lots=", ".join(held_lots), **kw)
    return render("public_position.empty", **kw)


def dm_reply(decision, *, instance_id: str, seat: int, stage: int, proposer: str, proposed_lots,
             proposer_lots, counter_lots=None, lapsed: bool = False) -> str:
    """The reply to a DM'd division or price proposal, driven by the policy's own
    :class:`~.bidders.Decision`.

    Every reply carries the stage qualifier "this stage", and that is not decoration: the rational seat is
    stage-myopic by construction, so wording its agreement as stage-scoped makes a later defection a
    consistency of the seat rather than a broken promise. The seat is never made to claim a commitment its
    policy cannot honor."""
    kw = dict(instance_id=instance_id, seat=seat, stage=stage, proposer=proposer,
              proposed_lots=", ".join(proposed_lots) or "those lots",
              proposer_lots=", ".join(proposer_lots) or "the rest",
              margin_word=margin_word(decision))
    if lapsed:
        return render("dm_reply.lapsed", counter_lots=", ".join(counter_lots or ()) or "the catalogue", **kw)
    if decision.accept:
        return render("dm_reply.accept", **kw)
    if counter_lots:
        return render("dm_reply.counter", counter_lots=", ".join(counter_lots), **kw)
    return render("dm_reply.decline", **kw)


def dm_initiate(*, instance_id: str, seat: int, stage: int, threat_seat: str, fit_lot: str, counter_lots,
                transfer_amount: int | None = None) -> str:
    """The proposal this seat opens with, addressed to the rival whose PUBLIC profile most contests its best
    lot -- a public-prior computation, so the address itself leaks nothing about which lots it privately
    values."""
    line = render("dm_initiate", instance_id=instance_id, seat=seat, stage=stage, threat_seat=threat_seat,
                  fit_lot=fit_lot, counter_lots=", ".join(counter_lots) or "the rest")
    if transfer_amount is not None:
        line += " " + TRANSFER_CLAUSE.format(transfer_amount=int(transfer_amount))
    return line


def margin_word(decision) -> str:
    """``"clearly"`` when the gap exceeds 10% of the best-response value, ``"marginally"`` otherwise -- a
    qualitative label over two numbers that are never themselves emitted."""
    gain = decision.detail.get("proposal_surplus")
    alt = decision.detail.get("best_response_surplus")
    if gain is None or alt is None or not alt:
        return "clearly"
    return "clearly" if abs(float(gain) - float(alt)) > 0.10 * abs(float(alt)) else "marginally"
