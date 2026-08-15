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
# No eager submodule imports, matching ``negotiation/__init__.py``: the modules pull in numpy and each
# other's tables, so importing this package should not cost that for a caller who wants one benchmark.
# Import submodules explicitly, e.g. ``from interlens.arena.auction.spec import AuctionSpec``.

"""Repeated multi-bidder auctions: the frozen spec, the persona-conditioned prior, exact allocation and
payment rules, equilibrium benchmarks, computable bidders and oracles, and the collusion metrics.

The sibling of :mod:`interlens.arena.negotiation`. Each module's docstring carries the primary citations for
what it implements; :mod:`.references` maps every citation key to its full reference with the exact page
range the module relies on.

Layout:

- :mod:`.spec` — ``AuctionSpec`` / ``BidderSpec`` / ``StageDraw`` / ``Mechanism``, and ``generate_spec``.
- :mod:`.priors` — the persona table, the generative model, fact-rendering data, and ``RivalPosterior``.
- :mod:`.allocation` — bundle values, the exact efficient allocation, VCG / clinching / uniform-price rules.
- :mod:`.benchmarks` — the exact per-stage equilibrium benchmarks every suppression metric divides against.
- :mod:`.actions` — the auction move vocabulary, ``BidLedger``, ``DMRouter``, and the action parser.
- :mod:`.bidders` — ``AuctionState``, the policy zoo, and their oracle variants.
- :mod:`.metrics` — stage-level and repeated-play metrics, as pure functions over records.
"""
