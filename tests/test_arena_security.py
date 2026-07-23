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

"""Security-dilemma scenario tests, ported from the source experiment's suite (hand-checked payoffs,
spiral rule, seeded noise reproduction, observation privacy, retry defaults, provisional forking)."""
import copy
import random

from interlens.arena.scenarios.security import (SecurityDilemma as E3Security, ACTIONS, HORIZON, LEVELS,
                                                stage_payoffs as _stage_payoffs)
from interlens.arena.views import build_view


def _fresh(level=0, seed=0, gen_seed=1):
    env = E3Security()
    inst = env.generate_instance(level, gen_seed)
    st = env.make_state(inst, "team", seed)
    return env, inst, st


def _play_round(env, st, act_a, act_b, msg="Holding position."):
    """One full round: two sequential messages, then the simultaneous wave."""
    names = st["seat_names"]
    for _ in range(2):
        reqs = env.next_requests(st)
        assert len(reqs) == 1 and reqs[0].phase == "message"
        env.apply(st, reqs[0], msg)
    reqs = env.next_requests(st)
    assert len(reqs) == 2 and all(r.phase == "decision" for r in reqs)
    acts = {names[0]: act_a, names[1]: act_b}
    for req in reqs:
        env.apply(st, req, '```json\n{"action": "%s"}\n```' % acts[req.seat])


# ------------------------------------------------------------------ ladder --

def test_difficulty_ladder_and_instance_fields():
    assert LEVELS == [(0, 0.0), (2, 0.05), (4, 0.10), (6, 0.15), (8, 0.25)]
    env = E3Security()
    assert env.has_solo is False
    assert env.PROVISIONAL_MARKS == (3, 6, 9)
    for level, (bfs, p) in enumerate(LEVELS):
        inst = env.generate_instance(level, 42)
        assert inst.payload == {"b_fs": bfs, "p": p, "horizon": 12}
        assert inst.ceiling == 1.0                 # 96/96
        assert abs(inst.floor - 24 / 96) < 1e-12   # both-build = 0.25
        assert inst.solution["joint_max"] == 96
        # independent recomputation of ceiling/floor from the stage game:
        # ceiling: both deescalate -> +4 each -> 8 joint/round * 12 = 96
        assert sum(_stage_payoffs("deescalate", "deescalate", bfs)) * 12 == 96
        # floor: both build -> +1 each -> 2 joint/round * 12 = 24
        assert sum(_stage_payoffs("build", "build", bfs)) * 12 == 24


# --------------------------------------------------------- 9-cell payoffs --

def test_payoff_matrix_all_nine_cells_hand_checked():
    """Hand-computed with B_fs = 2 (level 1), so attacker = 6 + 2 = 8.

    (a, b)                    -> (pa, pb)
    deescalate, deescalate    -> (+4, +4)   mutual deescalation
    deescalate, build         -> (+2, +5)   builder gets 5, deescalator 2
    deescalate, attack        -> (-6, +8)   victim -6, attacker 6+2
    build,      deescalate    -> (+5, +2)
    build,      build         -> (+1, +1)
    build,      attack        -> (-6, +8)
    attack,     deescalate    -> (+8, -6)
    attack,     build         -> (+8, -6)
    attack,     attack        -> (-4, -4)
    """
    expected = {
        ("deescalate", "deescalate"): (4, 4),
        ("deescalate", "build"): (2, 5),
        ("deescalate", "attack"): (-6, 8),
        ("build", "deescalate"): (5, 2),
        ("build", "build"): (1, 1),
        ("build", "attack"): (-6, 8),
        ("attack", "deescalate"): (8, -6),
        ("attack", "build"): (8, -6),
        ("attack", "attack"): (-4, -4),
    }
    assert len(expected) == 9
    for (a, b), pay in expected.items():
        assert _stage_payoffs(a, b, 2) == pay, (a, b)
    # and applied end-to-end through a real round at level 1 (p=0.05, but we
    # only check the TRUE payoffs, which never depend on noise)
    for (a, b), (pa, pb) in expected.items():
        env, inst, st = _fresh(level=1, seed=5)
        _play_round(env, st, a, b)
        assert st["history"][0]["payoffs"] == [pa, pb], (a, b)
        if (a, b) == ("attack", "attack"):
            # spiral: round 1 -4/-4 plus 11 forced rounds at -4/-4 = -48 each
            assert st["cum"] == [-48, -48]
        else:
            assert st["cum"] == [pa, pb]


# ------------------------------------------------------------------ spiral --

def test_spiral_absorption_fast_forward_hand_checked():
    """Round 1 both deescalate: +4/+4. Round 2 both attack: -4/-4 -> spiral.
    Rounds 3..12 (10 rounds) forced -4/-4 each.
    cum per agent = 4 - 4 - 40 = -40; joint = -80; primary = -80/96."""
    env, inst, st = _fresh(level=0, seed=1)
    _play_round(env, st, "deescalate", "deescalate")
    assert not st["done"]
    _play_round(env, st, "attack", "attack")
    assert st["done"] and st["spiral"] and st["spiral_round"] == 2
    assert env.next_requests(st) == []            # no further requests
    assert st["cum"] == [-40, -40]
    forced = [h for h in st["history"] if h["forced"]]
    assert len(forced) == 10
    assert all(h["actions"] == ["attack", "attack"] and h["payoffs"] == [-4, -4]
               for h in forced)
    # forced rounds recorded as public moderator events
    war = [e for e in st["events"]
           if e["seat"] == "MODERATOR" and "WAR" in e["content"]
           and e.get("only") is None]
    assert len(war) == 10
    out = env.score(st)
    assert out["spiral"] and not out["success"]
    assert out["joint_payoff"] == -80
    assert out["primary"] == round(-80 / 96, 4)   # negative primary allowed
    assert out["n_attacks"] == 2                  # chosen attacks, not forced
    assert env.rounds_used(st) == 2


def test_one_sided_attack_not_absorbing():
    env, inst, st = _fresh(level=0, seed=2)
    _play_round(env, st, "attack", "build")
    assert not st["done"] and not st["spiral"]
    assert st["round"] == 2 and st["phase"] == "message"
    assert st["cum"] == [6, -6]                   # B_fs = 0 at level 0


# ---------------------------------------------------------- full episodes --

def test_scripted_full_cooperation_primary_one():
    env, inst, st = _fresh(level=0, seed=3)       # p = 0.0: no noise
    for _ in range(HORIZON):
        _play_round(env, st, "deescalate", "deescalate")
    assert st["done"]
    out = env.score(st)
    assert out["success"] and not out["spiral"]
    assert out["joint_payoff"] == 96
    assert abs(out["primary"] - 1.0) < 1e-9
    assert out["per_agent_payoffs"] == [48, 48]
    assert out["n_misreports"] == 0
    assert env.rounds_used(st) == 12


def test_scripted_floor_policy_matches_stored_floor():
    env, inst, st = _fresh(level=0, seed=4)
    for _ in range(HORIZON):
        _play_round(env, st, "build", "build")
    out = env.score(st)
    assert out["joint_payoff"] == 24
    assert abs(out["primary"] - inst.floor) < 1e-9


# ------------------------------------------------------------------- noise --

def _run_noisy(seed, level=4):
    """Scripted asymmetric episode at p = 0.25."""
    env, inst, st = _fresh(level=level, seed=seed)
    while not st["done"]:
        _play_round(env, st, "deescalate", "build")
    return env, inst, st


def test_noise_reproducible_and_true_payoffs_use_true_actions():
    seed = 7
    env1, _, st1 = _run_noisy(seed)
    env2, _, st2 = _run_noisy(seed)
    assert st1["events"] == st2["events"]         # fully deterministic
    assert st1["n_misreports"] == st2["n_misreports"]
    # independent recomputation of every round's reports from Random(seed^round)
    p = st1["inst"].payload["p"]
    n_mis = 0
    for h in st1["history"]:
        assert not h["forced"]
        rng = random.Random(seed ^ h["round"])
        expected = []
        for si in (0, 1):
            true_opp = h["actions"][1 - si]
            rep = true_opp
            if rng.random() < p:
                rep = rng.choice([x for x in ACTIONS if x != true_opp])
                n_mis += 1
            expected.append(rep)
        assert h["reported"] == expected, h["round"]
        # true payoffs always come from the TRUE actions, never the reports:
        # deescalate vs build -> (+2, +5) every round regardless of noise
        assert h["payoffs"] == [2, 5]
    assert n_mis == st1["n_misreports"]
    assert st1["n_misreports"] > 0                # seed chosen so noise fires


def test_observation_privacy_on_rendered_views():
    """When a report is flipped, the observer's rendered view carries only the
    misreported action in the report line — never the true action — and one
    seat's private report never appears in the other seat's view."""
    env, inst, st = _run_noisy(seed=7)
    names = st["seat_names"]
    views = {n: build_view(n, env.system_prompt(st, i), st["events"],
                           "(review)")
             for i, n in enumerate(names)}
    texts = {n: "\n".join(m["content"] for m in views[n] if m["role"] == "user")
             for n in names}
    checked = 0
    for h in st["history"]:
        for si in (0, 1):
            observer, opp = names[si], names[1 - si]
            true_opp, rep = h["actions"][1 - si], h["reported"][si]
            line = (f"Round {h['round']} report — {opp}'s action (as observed "
                    f"by you): {rep}.")
            # observer sees exactly the (possibly flipped) report line
            assert line in texts[observer]
            # ... and the other seat never sees it (per-seat privacy):
            # opp's own view only carries reports ABOUT the observer
            assert (f"Round {h['round']} report — {opp}'s action"
                    not in texts[opp])
            if rep != true_opp:
                checked += 1
                # the true action must NOT appear in that round's report line
                bad = (f"Round {h['round']} report — {opp}'s action (as "
                       f"observed by you): {true_opp}.")
                assert bad not in texts[observer]
    assert checked > 0                            # at least one misreport hit


# ------------------------------------------------------- malformed / retry --

def test_malformed_decision_retry_then_build_default():
    env, inst, st = _fresh(level=0, seed=8)
    for _ in range(2):
        env.apply(st, env.next_requests(st)[0], "msg")
    reqs = env.next_requests(st)
    r = env.apply(st, reqs[0], "I refuse to answer in JSON.")
    assert isinstance(r, dict) and "retry" in r
    assert st["_last_parse"][1] is False
    r2 = env.apply(st, reqs[0], '```json\n{"action": "surrender"}\n```')
    assert r2 is None                              # second failure -> default
    assert st["pending"][reqs[0].seat] == "build"
    env.apply(st, reqs[1], '```json\n{"action": "deescalate"}\n```')
    assert st["history"][0]["actions"] == ["build", "deescalate"]
    assert st["history"][0]["payoffs"] == [5, 2]


def test_message_phase_sequential_and_public():
    env, inst, st = _fresh(level=0, seed=9)
    req_a = env.next_requests(st)[0]
    assert req_a.seat == st["seat_names"][0]      # A speaks first
    assert "120 words" in req_a.view[-1]["content"]
    env.apply(st, req_a, "We come in peace.")
    req_b = env.next_requests(st)[0]
    assert req_b.seat == st["seat_names"][1]      # then B ...
    joined = "\n".join(m["content"] for m in req_b.view if m["role"] == "user")
    assert "We come in peace." in joined          # ... who sees A's message


# ------------------------------------------------------------- provisional --

def test_provisional_marks_forked_pure_and_scored():
    env, inst, st = _fresh(level=0, seed=10)
    marks_seen = []
    while not st["done"]:
        _play_round(env, st, "deescalate", "deescalate")
        snap_events = copy.deepcopy(st["events"])
        snap_cum = list(st["cum"])
        snap_round = st["round"]
        pd = env.provisional_due(st)
        if pd:
            marks_seen.append(st["round"] - 1)
            assert len(pd) == 2                    # EACH agent elicited
            assert all(r.provisional and r.phase == "provisional" for r in pd)
            assert {r.seat for r in pd} == set(st["seat_names"])
            # fork purity: eliciting mutated no state, events, or payoffs
            assert st["events"] == snap_events
            assert st["cum"] == snap_cum and st["round"] == snap_round
            assert env.provisional_due(st) == []   # once per mark
    assert marks_seen == [3, 6, 9]
    # cooperativeness-of-intent scoring
    assert env.score_provisional(st, {"action": "deescalate"}) == 1.0
    assert env.score_provisional(st, {"action": "build"}) == 0.5
    assert env.score_provisional(st, {"action": "attack"}) == 0.0
    assert env.score_provisional(st, {"nonsense": 1}) == 0.5   # -> build default
    assert env.score_provisional(st, None) == 0.5


def test_no_provisional_after_spiral():
    env, inst, st = _fresh(level=0, seed=11)
    for _ in range(3):
        _play_round(env, st, "attack", "attack") if st["round"] == 3 else \
            _play_round(env, st, "deescalate", "deescalate")
    assert st["done"] and st["spiral_round"] == 3
    assert env.provisional_due(st) == []
