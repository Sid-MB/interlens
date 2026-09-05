# `interlens.arena.scenarios.coding`

Coding collaboration with private constraints: 3 seats jointly write ONE Python module.

The team writes one module against a PUBLIC spec + pytest suite; each seat additionally holds PRIVATE,
mechanically checkable style constraints it must get honored WITHOUT revealing verbatim (paraphrasing and
steering the code toward them is allowed). On each round-robin turn a seat discusses and may post a complete
module draft in a ```python fence (the latest full fence anywhere becomes the working draft), and ends with a
fenced JSON declaration `{"constraints_ok": true|false}`. The episode ends early, at a round boundary, once
a draft exists and all three latest declarations are true; otherwise after 5 rounds. The final submission is
the latest working draft.

Scoring is exact and sandboxed: `primary` = (fraction of pytest tests passing) x (fraction of ALL dealt
constraints satisfied); `success` iff `primary == 1.0`; ceiling 1.0, floor 0.0 (no draft). The sandbox
runs the model-written module against the task's pytest suite in an isolated subprocess
(`sys.executable -I`, fresh tmpdir, 30 s wall timeout); constraints are checked by AST static analysis.
The generator deals `LEVEL_N_CONSTRAINTS[level]` constraints across the 3 seats and verifies joint
satisfiability against a bundled reference solution, so every instance is solvable at `primary == 1.0`.

The solo arm gives one seat every constraint openly (the collaboration-free ceiling); its budget-forced
finalization submits the latest draft when the engine flags `budget_exhausted`.

Provisional forking: after each full round the finalizer (seat 0) is privately asked for a complete module
right now; `score_provisional_text` runs the full primary scorer on that fork, purely (state untouched).

Provenance: the collaboration-arena experiments' E4 environment, ported verbatim onto the `Scenario`
contract (task bank, constraint library, sandbox, and instance seeds unchanged — stored episodes replay and
stored instances regenerate byte-identically).

## Attributes {#attributes}

| Name | Type | Summary |
|---|---|---|
| `COMPATIBLE` | `dict[str, list[str]]` |  |
| `CONSTRAINTS` | `dict[str, tuple]` |  |
| `LEVEL_N_CONSTRAINTS` |  |  |
| `N_AGENTS` |  |  |
| `N_ROUNDS` |  |  |
| `ROLES` |  |  |
| `TASKS` | `dict[str, dict]` |  |

## Classes

| Name | Summary |
|---|---|
| [`CodingCollab`](CodingCollab.md) |  |

## Functions

| Name | Summary |
|---|---|
| [`check_all`](check_all.md) |  |
| [`check_constraint`](check_constraint.md) | checker(code_str) -> bool via ast/static analysis; SyntaxError -> False. |
| [`count_nonblank`](count_nonblank.md) |  |
| [`extract_python`](extract_python.md) | Latest full ```python fence anywhere in the text, else None. |
| [`run_tests`](run_tests.md) | Run test_src against code_str (as `solution`) in an isolated sandbox. |
