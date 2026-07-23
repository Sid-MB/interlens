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

"""Coding-collaboration scenario tests, ported from the source experiment's suite (real-sandbox scoring on
known-good and known-violating modules, hand-computed constraint checkers, generator joint-satisfiability,
early-consensus and max-rounds flows, provisional purity, solo arm, cross-seat constraint privacy)."""
import copy

from interlens.arena.scenarios.coding import (CodingCollab as E4Coding, TASKS, CONSTRAINTS, COMPATIBLE,
                                              LEVEL_N_CONSTRAINTS, N_AGENTS, N_ROUNDS,
                                              check_constraint, check_all, run_tests,
                                              extract_python, count_nonblank as _count_nonblank)


def _decl(ok=True):
    return '```json\n{"constraints_ok": ' + ("true" if ok else "false") + "}\n```"


def _draft_msg(code, ok=True):
    return f"Here is my draft.\n```python\n{code}\n```\n{_decl(ok)}"


# ------------------------------------------------------------- sandbox -----

def test_sandbox_known_good_reference_scores_1():
    """Every reference solution passes its full suite through the REAL sandbox
    and, scored against its instance's dealt constraints, the stored reference
    solution scores exactly 1.0 (verifies ceiling==1.0 independently)."""
    for tname, task in TASKS.items():
        total = task["tests"].count("def test_")
        assert total >= 8, (tname, total)
        for sid, code in task["solutions"].items():
            passed, tot = run_tests(code, task["tests"])
            assert (passed, tot) == (total, total), (tname, sid, passed, tot)


def test_sandbox_known_violating_scores_below_1_with_right_bits():
    env = E4Coding()
    # hand-built payload: interval_merge with two dealt constraints
    payload = {"task": "interval_merge",
               "spec": TASKS["interval_merge"]["spec"],
               "test_src": TASKS["interval_merge"]["tests"],
               "n_constraints": 2,
               "constraint_ids": ["no_for_while", "require_sorted_builtin"],
               "deal": [[], [], []]}
    # reference solution A uses a for-loop but calls sorted(): passes all 9
    # tests, holds 1 of 2 constraints -> primary = (9/9) * (1/2) = 0.5 exactly
    out = env._score_code(payload, TASKS["interval_merge"]["solutions"]["A"])
    assert out["tests_passed"] == out["tests_total"] == 9
    assert out["per_constraint"] == {"no_for_while": False,
                                     "require_sorted_builtin": True}
    assert out["constraints_held"] == 1 and out["constraints_total"] == 2
    assert abs(out["primary"] - 0.5) < 1e-9 and out["primary"] < 1.0
    assert not out["success"]


def test_sandbox_broken_draft_scores_0():
    env = E4Coding()
    inst = env.generate_instance(2, 3)
    out = env._score_code(inst.payload, "def broken(:\n    pass")
    assert out["primary"] == 0.0 and not out["success"]
    assert out["tests_passed"] == 0
    assert out["tests_total"] == inst.payload["test_src"].count("def test_")
    assert all(v is False for v in out["per_constraint"].values())


def test_empty_draft_is_floor_0():
    env = E4Coding()
    inst = env.generate_instance(0, 1)
    st = env.make_state(inst, "team", 0)
    # no draft ever posted -> floor
    out = env._score_code(inst.payload, "")
    assert out["primary"] == inst.floor == 0.0
    assert not out["had_draft"]


# ---------------------------------------------------------- constraints ----

def test_constraint_checkers_hand_computed():
    """Fully hand-computed case: verify each checker on a known snippet."""
    code = (
        "import math\n"                    # an import
        "def f(x: int) -> int:\n"
        '    """doc."""\n'
        "    return f(x - 1) if x else 0\n"  # direct recursion, hinted, doc
        "def _h(y):\n"                     # private, unhinted, no docstring
        "    d = {k: k for k in [y]}\n"    # dict comprehension
        "    for _ in d:\n"                # a for statement
        "        pass\n"
        "    return sorted(d)\n"           # sorted() call
    )
    got = check_all(sorted(CONSTRAINTS), code)
    assert got == {
        "max_lines_25": True,              # 9 non-blank lines <= 25
        "max_lines_40": True,
        "no_dict_comprehension": False,
        "no_for_while": False,
        "no_imports": False,
        "no_recursion": False,             # f calls f
        "require_docstrings": False,       # _h lacks one
        "require_sorted_builtin": True,
        "require_type_hints": False,       # _h unannotated
        "single_function_public": True,    # only f is public top-level
    }
    assert _count_nonblank(code) == 9
    # SyntaxError -> every constraint False
    assert all(v is False for v in check_all(sorted(CONSTRAINTS), "def (").values())


def test_compatible_map_matches_checkers():
    for cid, sols in COMPATIBLE.items():
        for tname, task in TASKS.items():
            for sid, code in task["solutions"].items():
                assert (f"{tname}:{sid}" in sols) == check_constraint(cid, code)
    # the full 10-constraint set (level 4) is jointly satisfiable somewhere
    full = [s for s in ("interval_merge:B", "grouper:B")
            if all(s in COMPATIBLE[c] for c in CONSTRAINTS)]
    assert full


# ------------------------------------------------------------- generator ---

def test_generator_joint_satisfiability_all_levels_and_seeds():
    env = E4Coding()
    for level in range(5):
        for seed in (1, 2, 3):
            inst = env.generate_instance(level, seed)
            p = inst.payload
            n = LEVEL_N_CONSTRAINTS[level]
            assert p["n_constraints"] == n
            dealt = [c["id"] for group in p["deal"] for c in group]
            assert sorted(dealt) == p["constraint_ids"]
            assert len(set(dealt)) == n == len(dealt)
            # ceil/floor split across the 3 agents
            sizes = sorted(len(g) for g in p["deal"])
            assert sum(sizes) == n and sizes[-1] - sizes[0] <= 1
            if level == 4:
                assert max(sizes) == 4
            # INDEPENDENT recomputation: the stored reference solution
            # satisfies every dealt constraint via the static checkers
            code = inst.solution["code"]
            tname, sid = inst.solution["solution_id"].split(":")
            assert code == TASKS[tname]["solutions"][sid] and tname == p["task"]
            assert all(check_constraint(c, code) for c in dealt)
            assert inst.ceiling == 1.0 and inst.floor == 0.0
            # determinism
            inst2 = env.generate_instance(level, seed)
            assert inst2.payload == p and inst2.solution == inst.solution


def test_generator_reference_solution_passes_sandbox_at_hardest_level():
    env = E4Coding()
    inst = env.generate_instance(4, 7)  # all 10 constraints dealt
    out = env._score_code(inst.payload, inst.solution["code"])
    assert out["primary"] == 1.0 and out["success"]
    assert all(out["per_constraint"].values())


# ------------------------------------------------------------- team flow ---

def test_scripted_team_episode_early_termination():
    env = E4Coding()
    inst = env.generate_instance(1, 5)
    st = env.make_state(inst, "team", 0)
    good = inst.solution["code"]
    # round 1: agent 0 posts the reference draft, everyone declares ok
    for turn in range(3):
        reqs = env.next_requests(st)
        assert len(reqs) == 1 and reqs[0].phase == "turn"
        text = _draft_msg(good) if turn == 0 else f"Looks good to me.\n{_decl(True)}"
        assert env.apply(st, reqs[0], text) is None
        assert st["_last_parse"][1]
    assert st["done"] and st["finalized_by"] == "early_consensus"
    assert env.rounds_used(st) == 1
    assert st["draft"] == good.strip()   # fences are stripped on extraction
    out = env.score(st)
    assert out["primary"] == 1.0 and out["success"] and out["had_draft"]
    assert out["tests_passed"] == out["tests_total"]
    assert all(out["per_constraint"].values())
    assert env.next_requests(st) == []


def test_scripted_team_episode_max_rounds_no_consensus():
    env = E4Coding()
    inst = env.generate_instance(0, 8)
    st = env.make_state(inst, "team", 0)
    n = 0
    while not st["done"]:
        req = env.next_requests(st)[0]
        env.apply(st, req, f"Still thinking.\n{_decl(False)}")
        n += 1
        assert n <= N_ROUNDS * N_AGENTS
    assert n == N_ROUNDS * N_AGENTS
    assert st["finalized_by"] == "max_rounds" and env.rounds_used(st) == N_ROUNDS
    out = env.score(st)
    assert out["primary"] == 0.0 and not out["had_draft"]


def test_latest_fence_becomes_working_draft_and_declarations_update():
    env = E4Coding()
    inst = env.generate_instance(0, 8)
    st = env.make_state(inst, "team", 0)
    good = inst.solution["code"]
    req = env.next_requests(st)[0]
    # two fences in one message: the LATEST one wins
    text = (f"First try:\n```python\nBROKEN =\n```\nActually this:\n"
            f"```python\n{good}\n```\n{_decl(False)}")
    env.apply(st, req, text)
    assert st["draft"] == good.strip()
    assert st["declarations"][req.seat] is False
    # a later message without a fence keeps the draft
    req = env.next_requests(st)[0]
    env.apply(st, req, f"No new code from me.\n{_decl(True)}")
    assert st["draft"] == good.strip()


# ------------------------------------------------------------ provisional --

def test_provisional_due_marks_and_text_hook_purity():
    env = E4Coding()
    inst = env.generate_instance(1, 4)
    st = env.make_state(inst, "team", 0)
    good = inst.solution["code"]
    marks = []
    while not st["done"]:
        req = env.next_requests(st)[0]
        env.apply(st, req, f"Discussing round {st['round']}.\n{_decl(False)}")
        pd = env.provisional_due(st)
        if pd:
            preq = pd[0]
            marks.append(preq.meta["round_mark"])
            assert preq.provisional and preq.phase == "provisional"
            assert preq.seat == st["seat_names"][0]
            assert preq.max_tokens == 2000
            assert preq.meta["local_max_new_tokens"] == 2000
            assert preq.meta["code_provisional"] is True
            # engine-limitation workaround: JSON hook opts out, text hook scores
            assert env.score_provisional(st, None) is None
            snap = (copy.deepcopy(st["events"]), st["draft"],
                    dict(st["declarations"]), st["round"], st["rounds_played"])
            s = env.score_provisional_text(st, f"```python\n{good}\n```")
            assert s == 1.0
            assert env.score_provisional_text(st, "no fence here") == 0.0
            # purity: eliciting + scoring never touched game state
            assert (st["events"], st["draft"], st["declarations"], st["round"],
                    st["rounds_played"]) == (snap[0], snap[1], snap[2], snap[3], snap[4])
            assert not any("PRIVATE aside" in e["content"] for e in st["events"])
            assert env.provisional_due(st) == []   # once per mark
    assert marks == [1, 2, 3, 4]   # round 5 boundary sets done -> skipped


# ------------------------------------------------------------------ solo ---

def test_solo_flow():
    env = E4Coding()
    inst = env.generate_instance(2, 6)
    st = env.make_state(inst, "solo", 0)
    reqs = env.next_requests(st)
    assert reqs[0].phase == "solo_work" and reqs[0].seat == "Coder"
    first_user = reqs[0].view[1]["content"]
    assert "ALL CONSTRAINTS" in first_user
    for group in inst.payload["deal"]:            # every constraint visible
        for c in group:
            assert c["text"] in first_user
    # a fence WITHOUT final:true keeps going
    env.apply(st, reqs[0], f"```python\n{inst.solution['code']}\n```\nchecking...")
    assert not st["done"]
    req = env.next_requests(st)[0]
    env.apply(st, req, '```json\n{"final": true}\n```')
    assert st["done"] and st["finalized_by"] == "solo"
    out = env.score(st)
    assert out["primary"] == 1.0 and out["success"]


def test_solo_budget_forced_finalize_uses_latest_fence():
    env = E4Coding()
    inst = env.generate_instance(0, 6)
    st = env.make_state(inst, "solo", 0)
    req = env.next_requests(st)[0]
    env.apply(st, req, f"draft so far\n```python\n{inst.solution['code']}\n```")
    st["budget_exhausted"] = True
    reqs = env.next_requests(st)
    assert reqs and reqs[0].phase == "solo_final"
    env.apply(st, reqs[0], "out of budget, no code")
    assert st["done"] and st["finalized_by"] == "solo_forced"
    assert env.score(st)["success"]


# --------------------------------------------------------------- privacy ---

def test_view_privacy_constraints_never_leak_across_seats():
    env = E4Coding()
    # level 3+ guarantees every agent holds >= 2 constraints
    inst = env.generate_instance(3, 9)
    st = env.make_state(inst, "team", 0)
    deal = inst.payload["deal"]
    assert all(len(g) >= 2 for g in deal)
    # play a round so views also contain events
    for _ in range(3):
        req = env.next_requests(st)[0]
        env.apply(st, req, f"General discussion, no code yet.\n{_decl(False)}")
    for si in range(N_AGENTS):
        seat = st["seat_names"][si]
        view = env.next_requests(st)[0] if st["turn_in_round"] == si else None
        rendered = "\n".join(
            m["content"]
            for m in (view.view if view is not None
                      else __import__("interlens.arena.views", fromlist=["build_view"]).build_view(
                          seat, env.system_prompt(st, si), st["events"], "x")))
        for oj in range(N_AGENTS):
            for c in deal[oj]:
                assert (c["text"] in rendered) == (oj == si), (si, oj, c["id"])


def test_seat_specs_and_extract_python():
    env = E4Coding()
    inst = env.generate_instance(0, 1)
    st = env.make_state(inst, "team", 0)
    specs = env.seat_specs(st)
    assert [s["name"] for s in specs] == st["seat_names"] and len(specs) == 3
    assert env.seat_specs(env.make_state(inst, "solo", 0))[0]["name"] == "Coder"
    assert extract_python("no code") is None
    assert extract_python("```python\nx = 1\n```") == "x = 1"
