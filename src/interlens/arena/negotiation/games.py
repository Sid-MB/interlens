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
# [rational_agents scaffold: games-presets] 2026-07-23

"""Swappable game presets: name a classic bargaining situation, get a ready-to-play game in one call.

The situation/game is a first-class swappable axis, like the oracle stack (DESIGN.md §4b): one registry maps a
name to a literature-grounded **preset**, a factory that returns ``(GameSpec, analysis, protocol_cfg)`` -- the
complete game spec, its enumeration-verified :func:`~interlens.arena.negotiation.solutions.analyze` dict, and the
scenario protocol knobs that turn the shared ``ScorableNegotiation`` state machine into that specific game
(single-shot / fixed-proposer / majority, etc.). Because the scorable formalism (discrete deal space + private
additive score sheets + thresholds + an agreement rule) already subsumes the classic bargaining family, **presets
are parameterizations, not new engines**: the same deal space, the same oracle stack (beliefs / acceptance /
best-response / equilibrium), the same annotation/atlas layer all run UNCHANGED on any preset -- that is the point.

Presets shipped:

======================  ============================================================  =========================
Preset                  Encoding                                                      Rational anchor
======================  ============================================================  =========================
``scorable`` (default)  the full §2 generator (a thin alias -- defaults in one place) the §4 oracle stack
``ultimatum``           N=2, J=1 pie split, tau=0, rounds=1, fixed proposer,          SPE (Rubinstein 1982 §5
                        responder-only single-shot vote                               one-round limit); human
                                                                                      rejection [guth1982]
``divide_dollar``       N parties, J=1 discrete-shares split, rotating proposer,       Baron-Ferejohn 1989 /
                        multi-round, unanimity or majority                            Okada 1996 (v = 1/n)
``bilateral_multiissue``  DoND-style N=2, J issues, private values (the generator)     Lewis et al. 2017 lineage
======================  ============================================================  =========================

Usage::

    from interlens.arena.negotiation import games

    game, analysis, protocol_cfg = games.make_preset("ultimatum", pie=10, n_options=11)
    game.n_parties                              # 2
    analysis["deal_space_size"]                 # 11 (one split per option)

    # the arena bridge: a solver-verified Instance + the scenario cfg to play it under
    instance, protocol_cfg = games.build_preset_instance("ultimatum")
    from interlens.arena.scenarios import ScorableNegotiation
    ScorableNegotiation().make_state(instance, "moves_only", seed=0, cfg=protocol_cfg)   # single-shot ultimatum

Every algorithm/preset cites its source by key (``references.py``): ultimatum SPE + human-rejection contrast
[guth1982] / [rubinstein1982]; divide-the-dollar [baron_ferejohn1989] / [okada1996]; DoND lineage [lewis2017].
The ``scorable`` alias re-uses the generator's defaults verbatim (never re-defaulted here).
"""
from __future__ import annotations

from typing import Callable

from ..schema import Instance
from .equilibrium import divide_the_dollar as _divide_dollar_tables
from .generate import build_instance, game_at_level, generate_game
from .sheets import GameSpec, ScoreSheet
from .solutions import analyze
from .space import DealSpace, Issue

# A preset factory: keyword knobs -> (game spec, enumeration-verified analysis, scenario protocol cfg).
Preset = Callable[..., "tuple[GameSpec, dict, dict]"]


def _num(x: float) -> str:
    """Compact numeric label (drops a trailing ``.0`` so integer shares read as ``10`` not ``10.0``)."""
    return f"{x:g}"


# ---------------------------------------------------------------------------------------- ultimatum --------
def ultimatum(*, pie: float = 10.0, n_options: int = 11, seed: int = 0) -> tuple[GameSpec, dict, dict]:
    """The **ultimatum game** [guth1982] as a scorable game: one proposer offers a split of a fixed ``pie``, one
    responder accepts (both get the split) or rejects (both get 0), take-it-or-leave-it.

    Encoding: N=2, J=1 issue ("Split") whose ``n_options`` discrete options are the shares -- option ``o`` gives
    the proposer ``o * pie/(n_options-1)`` and the responder the rest -- with thresholds ``tau=0`` (the BATNA is
    the no-deal payoff 0), ``rounds=1``, a fixed proposer (seat 0), and the responder-only single-shot vote
    (``protocol_cfg = {"single_shot": True, "fixed_proposer": True}``).

    Rational anchor -- the subgame-perfect equilibrium (the T=1 limit of Rubinstein 1982 alternating offers
    [rubinstein1982] §5): the responder accepts **any positive share** (rejecting pays 0, so any surplus >= 0 is
    weakly better), so the proposer keeps the whole pie. Under the harness's ``>= 0`` individual-rationality
    convention (``solutions.ir_mask`` default ``strict=False``) the responder is *indifferent* at a 0 share and
    (weakly) accepts, so the discrete SPE has the proposer keeping the entire pie (option ``n_options-1``); the
    classic "pie - epsilon" is the strict/continuous statement. The behavioral contrast [guth1982] -- humans
    reject low positive offers -- is the LLM-vs-rational gap this preset exposes.

    Note: this is a **pure division** (every split has the same total ``pie``), so EVERY split is Pareto-optimal
    and the acceptable set has ``dominated_acceptable_fraction = 0`` -- the score-sheet-repair knob
    (``dominated_target``) does not apply here (there is no dominated slack to leave in play).

    Parameters
    ----------
    pie : total value to split (proposer share + responder share = ``pie`` for every option).
    n_options : number of discrete splits (>= 2). ``11`` gives whole-unit shares ``0..pie`` for ``pie=10``; a
        larger value = finer granularity (closer to the continuous game).
    seed : accepted for a uniform preset interface; the ultimatum game is deterministic, so it is unused.

    Returns ``(GameSpec, analysis, protocol_cfg)``.
    """
    if n_options < 2:
        raise ValueError(f"ultimatum needs n_options >= 2 (a split needs both endpoints), got {n_options}")
    unit = pie / (n_options - 1)
    prop_share = [o * unit for o in range(n_options)]
    resp_share = [pie - p for p in prop_share]
    labels = tuple(f"P{_num(p)}/R{_num(r)}" for p, r in zip(prop_share, resp_share))
    space = DealSpace((Issue("Split", labels),))
    sheets = (
        ScoreSheet("Proposer", (tuple(float(p) for p in prop_share),), threshold=0.0),
        ScoreSheet("Responder", (tuple(float(r) for r in resp_share),), threshold=0.0),
    )
    game = GameSpec(space=space, sheets=sheets, rounds=1, info="full", chat=False,
                    proposer=0, veto=None, min_accept=None, discount=1.0,
                    meta={"preset": "ultimatum", "pie": float(pie), "n_options": int(n_options)})
    return game, analyze(space, sheets), {"single_shot": True, "fixed_proposer": True}


# ------------------------------------------------------------------------------------- divide_dollar --------
def divide_dollar(*, n_parties: int = 3, steps: int = 12, rounds: int | None = None,
                  rule: str = "unanimity", discount: float = 0.99, seed: int = 0) -> tuple[GameSpec, dict, dict]:
    """The **divide-the-dollar / legislative-bargaining** testbed [baron_ferejohn1989]: ``n_parties`` split a
    unit pie over multiple rounds with a rotating proposer, under a unanimity or majority agreement rule.

    Encoding: J=1 issue ("Allocation") whose options are every integer allocation of ``steps`` units among the
    parties (the compositions summing to ``steps``); party ``i``'s utility for an allocation is its own share
    ``units_i / steps in [0, 1]``, thresholds ``tau=0``. The deal space is reused from the equilibrium oracle's
    Okada anchor (:func:`~interlens.arena.negotiation.equilibrium.divide_the_dollar`), so the same game the
    oracle solves is the one the scenario plays. Rotating proposer + multi-round is the scenario's default
    protocol (``protocol_cfg = {}``).

    Rational anchor: the Banks-Duggan / Baron-Ferejohn stationary equilibrium. For the **unanimity** rule the
    Okada 1996 closed form [okada1996] gives the sanity value ``v_i = 1/n`` (proposer keeps ``1 - delta(n-1)/n``,
    each responder ``delta/n``) -- exactly what
    :class:`~interlens.arena.negotiation.equilibrium.EquilibriumOracle` recovers on this preset. The **majority**
    rule (``min_accept = floor(n/2)+1``) is the minimal-winning-coalition Baron-Ferejohn game; the equilibrium
    oracle models unanimity social acceptance, so the ``v = 1/n`` anchor is stated only for ``rule="unanimity"``.

    Like ``ultimatum`` this is a pure division: every allocation is Pareto-optimal
    (``dominated_acceptable_fraction = 0``), so the score-sheet-repair knob does not apply.

    Parameters
    ----------
    n_parties : number of parties splitting the pie (N in {2, 3} is the usual testbed; larger works but the deal
        space is ``C(steps+n-1, n-1)`` compositions -- keep it enumerable).
    steps : allocation granularity (the pie is ``steps`` indivisible units). Finer ``steps`` = the equilibrium
        value tracks ``1/n`` more precisely but a larger deal space.
    rounds : round-robin rounds before the forced final (default ``2 * n_parties``, so each seat proposes ~twice).
    rule : ``"unanimity"`` (all parties must clear their threshold -- the Okada ``v=1/n`` anchor) or ``"majority"``
        (``floor(n/2)+1`` parties -- the minimal-winning-coalition game).
    discount : per-round discount ``delta`` in ``(0, 1]`` stored on the game (the equilibrium/acceptance oracles'
        single source of truth); ``< 1`` makes interior concession rational rather than deadline brinkmanship.
    seed : accepted for a uniform preset interface; the game is deterministic, so it is unused.

    Returns ``(GameSpec, analysis, protocol_cfg)``.
    """
    if rule not in ("unanimity", "majority"):
        raise ValueError(f"divide_dollar rule must be 'unanimity' or 'majority', got {rule!r}")
    if n_parties < 2:
        raise ValueError(f"divide_dollar needs n_parties >= 2, got {n_parties}")
    tables = _divide_dollar_tables(n_parties, steps)     # deals = compositions, utility = share/steps, tau = 0
    n_deals = len(tables.deals)
    labels = tuple("-".join(str(int(x)) for x in comp) for comp in tables.deals)
    space = DealSpace((Issue("Allocation", labels),))
    names = [f"P{i}" for i in range(n_parties)]
    sheets = tuple(
        ScoreSheet(names[i], (tuple(float(tables.utility[o, i]) for o in range(n_deals)),), threshold=0.0)
        for i in range(n_parties))
    min_accept = None if rule == "unanimity" else (n_parties // 2 + 1)
    rounds = rounds if rounds is not None else 2 * n_parties
    game = GameSpec(space=space, sheets=sheets, rounds=rounds, info="full", chat=True,
                    proposer=0, veto=None, min_accept=min_accept, discount=discount,
                    meta={"preset": "divide_dollar", "n_parties": int(n_parties), "steps": int(steps),
                          "rule": rule})
    return game, analyze(space, sheets), {}


# --------------------------------------------------------------------------------- bilateral_multiissue -----
def bilateral_multiissue(*, n_issues: int = 3, n_options: int = 5, info: str = "private",
                         seed: int = 0, **overrides) -> tuple[GameSpec, dict, dict]:
    """A **DoND-style bilateral, multi-issue, private-value** negotiation [lewis2017]: two parties bargain over
    ``n_issues`` item types, each with private per-item values -- the classic "Deal or No Deal" item-division
    game, reproduced here as the scorable generator restricted to ``n_parties=2``.

    This is a thin call into :func:`~interlens.arena.negotiation.generate.generate_game` with ``n_parties=2``, so
    it inherits every score-sheet repair (the Pareto-slack / feasible-size / sparsity-IoU knobs) and its verified
    analysis; no repair is re-implemented. Standard multi-round protocol (``protocol_cfg = {}``).

    Parameters
    ----------
    n_issues : number of item-type issues ``J`` (Hua et al. / DoND use ~3).
    n_options : options per issue (the item-count levels).
    info : ``"private"`` (each party's values are private -- the DoND setting, where some inefficiency is rational
        by Myerson-Satterthwaite) or ``"full"`` (common knowledge, an efficiency upper bound).
    seed : generator seed (the game IS randomized here -- different seeds give different value sheets).
    **overrides : any other :func:`generate_game` knob (``dominated_target``, ``mix``, ``feasible_fraction``,
        ``rounds``, ``discount``, ...); defaults come from ``generate_game`` and are never re-set here.

    Returns ``(GameSpec, analysis, protocol_cfg)``.
    """
    game, analysis = generate_game(n_parties=2, n_issues=n_issues, n_options=n_options, info=info, seed=seed,
                                   **overrides)
    game.meta["preset"] = "bilateral_multiissue"
    return game, analysis, {}


# ------------------------------------------------------------------------------------------ scorable --------
def scorable(*, level: int = 0, seed: int = 0, ladder: list[dict] | None = None,
             **overrides) -> tuple[GameSpec, dict, dict]:
    """The default multi-party, multi-issue **scorable** game (DESIGN.md §2) -- a thin alias to the existing
    generator so the whole preset machinery has one uniform entry point.

    Delegates to :func:`~interlens.arena.negotiation.generate.game_at_level`, which maps the difficulty ``level``
    through the shipped :data:`~interlens.arena.negotiation.generate.INSTANCE_LADDER` (feasible-set size, the
    dominated-acceptable repair, the per-round discount) to :func:`generate_game`. **Every default lives in
    generate.py** and is never re-set here; ``**overrides`` (e.g. ``n_parties``, ``n_issues``, ``n_options``,
    ``info``, ``dominated_target``) pass straight through. Standard protocol (``protocol_cfg = {}``).

    Parameters
    ----------
    level : difficulty ladder index (0 = easiest / largest acceptable set).
    seed : generator seed.
    ladder : optional custom difficulty ladder (default :data:`INSTANCE_LADDER`).
    **overrides : any :func:`generate_game` knob (overrides the ladder's).

    Returns ``(GameSpec, analysis, protocol_cfg)``.
    """
    game, analysis = game_at_level(level, seed, ladder=ladder, **overrides)
    return game, analysis, {}


# ------------------------------------------------------------------------------------------ registry --------
PRESETS: dict[str, Preset] = {
    "scorable": scorable,
    "ultimatum": ultimatum,
    "divide_dollar": divide_dollar,
    "bilateral_multiissue": bilateral_multiissue,
}


def make_preset(name: str, **kwargs) -> tuple[GameSpec, dict, dict]:
    """Look up a preset by ``name`` and build it, returning ``(GameSpec, analysis, protocol_cfg)``. ``kwargs`` are
    the preset's own knobs (see each factory). Raises ``KeyError`` (listing the known presets) on an unknown name.
    """
    try:
        factory = PRESETS[name]
    except KeyError:
        raise KeyError(f"unknown game preset {name!r}; known presets: {sorted(PRESETS)}") from None
    return factory(**kwargs)


def build_preset_instance(name: str, *, level: int = 0, seed: int = 0,
                          instance_name: str = "scorable_negotiation",
                          **kwargs) -> tuple[Instance, dict]:
    """Build a solver-verified arena :class:`~interlens.arena.schema.Instance` from a preset, plus the scenario
    ``protocol_cfg`` to play it under -- the one-call bridge from a preset name to a runnable game.

    Reuses :func:`~interlens.arena.negotiation.generate.build_instance` for the ``(GameSpec, analysis) ->
    Instance`` wrap (``payload = GameSpec.to_json()``, ``solution`` = the analysis dict, exact ceiling/floor), so
    a preset instance is indistinguishable from a generated one to the scenario, oracle, annotation, and atlas
    layers. ``seed`` is threaded to the preset factory (used by randomized presets like ``bilateral_multiissue``
    / ``scorable``, ignored by the deterministic ``ultimatum`` / ``divide_dollar``) and stamped on the Instance;
    ``level`` is the Instance difficulty tag and (for ``scorable``) the generator ladder level. ``kwargs`` are the
    preset's knobs.

    Returns ``(instance, protocol_cfg)`` -- pass ``protocol_cfg`` as the scenario ``cfg`` (or merged into it) so
    the shared ``ScorableNegotiation`` state machine runs the preset's protocol variant.
    """
    preset_kwargs = dict(kwargs)
    preset_kwargs["seed"] = seed
    if name == "scorable":
        preset_kwargs.setdefault("level", level)   # only the scorable alias reads a difficulty level
    game, analysis, protocol_cfg = make_preset(name, **preset_kwargs)
    instance = build_instance(game, analysis, name=instance_name, level=level, seed=seed)
    return instance, protocol_cfg
