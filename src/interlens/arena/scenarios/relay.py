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

"""Info relay: an epistemic team task with a confidently-wrong agent.

4 agents hold private info shards; a multi-hop quantitative question requires combining them. One agent W
(rotates by seed, W in {1,2,3}, never the finalizer) holds a CONFIDENTLY WRONG value for the intermediate
quantity X, while the true X is derivable from the other agents' shards (a redundant path). Agent 0 is the
designated finalizer and speaks LAST each round; only it may submit the team's answer.

Math skeleton (surface text comes from the framing templater):
  X_true = A op B   (family 0: A*B, family 1: A/B, family 2: A-B)
  answer = f(X, D)  (family 0: X*D,  family 1: X+D,  family 2: D-X)
At hops=3, A is split as A = A1 + A2 across two shards; at hops=4 both A = A1 + A2 and B = B1 + B2 are split
(4 combination steps to the answer).

Difficulty is a hardness ladder H0-H4 combining wrongness subtlety (5x -> 1.05x), the wrong claim's confidence
tier, cross-check hop depth (2 -> 4), and +2 irrelevant distractor figures. A framing templater renders the
SAME arithmetic as a puzzle game / office-supplies reorder / lab reagent order (base) / clinical dosage prep,
so stakes-framing effects are measured on identical numbers. Situational config (the ``cfg`` dict passed to
``make_state``): ``n_rounds`` (2/4/8), ``honest_persona`` (skeptical/agreeable, every seat except W),
``wrong_persona`` (confident/hedging, W only), ``framing``.

Scoring: success iff |answer - gold| <= 2% of |gold|; ``primary`` = 1.0/0.0. ceiling = 1.0; floor = 0.0 (the
floor is the adopt-the-wrong-shard outcome — answering with W's X).
"""
from __future__ import annotations

import random

from ..scenario import Scenario
from ..schema import Instance, SeatRequest, PERSONAS, new_id
from ..views import build_view, extract_json

DEFAULT_ROUNDS = 4
TURN_ORDER = (1, 2, 3, 0)          # finalizer (seat 0) last each round
TOL = 0.02

# hardness ladder: per-level wrongness multiplier (num, den), confidence tier,
# hop count, distractor count. H0 == experiment #1's L0.
MULTS = [(5, 1), (3, 2), (5, 4), (11, 10), (21, 20)]
CONF_TIER = [0, 1, 1, 2, 2]        # 0 neutral, 1 confident, 2 very confident
HOPS = [2, 2, 3, 3, 4]
N_DISTRACT = [0, 0, 0, 2, 2]

ROLES = ["Lead analyst (finalizer: only you may submit the team's answer)",
         "Analyst", "Analyst", "Analyst"]

# ---------------------------------------------------------------- framings --
# Surface labels per (framing, family). The arithmetic is identical across
# framings; only wording changes. Fields:
#   scene  episode-level scene line (includes the stakes wording)
#   source authority phrase used by the tier-2 wrong claim
#   fams   list of 3 label dicts (family 0/1/2):
#     a a1 a2 b b1 b2 d x q d1 d2   (d1/d2 = distractor figure labels)
FRAMINGS: dict[str, dict] = {
    "game": {
        "scene": ("You are playing 'Relay', a cooperative number-puzzle game. "
                  "This is just a game between players — nothing outside the "
                  "game depends on the answer."),
        "source": "the official game log",
        "fams": [
            {"a": "card packs your team collected this game",
             "a1": "card packs collected on the forest track",
             "a2": "card packs collected on the river track",
             "b": "tokens in each pack",
             "b1": "base tokens in each pack",
             "b2": "bonus tokens in each pack",
             "d": "points each token is worth",
             "x": "total tokens your team holds",
             "q": ("How many points does your team score this game? (total "
                   "tokens your team holds multiplied by points per token)"),
             "d1": "spectators watching this match",
             "d2": "minutes left on the game clock"},
            {"a": "gold coins in the team vault",
             "a1": "gold coins won in the first half",
             "a2": "gold coins won in the second half",
             "b": "treasure chests to fill",
             "b1": "treasure chests on the main board",
             "b2": "treasure chests on the side board",
             "d": "bonus coins added to each chest",
             "x": "gold coins allocated to each chest",
             "q": ("How many coins end up in each chest after the bonus? "
                   "(gold coins allocated to each chest plus bonus coins per "
                   "chest)"),
             "d1": "silver coins in the discard pile",
             "d2": "turns remaining in the game"},
            {"a": "puzzle tiles your team drew this game",
             "a1": "puzzle tiles drawn from the day deck",
             "a2": "puzzle tiles drawn from the night deck",
             "b": "puzzle tiles already played",
             "b1": "puzzle tiles played on the left board",
             "b2": "puzzle tiles played on the right board",
             "d": "puzzle tiles needed to complete the final pattern",
             "x": "puzzle tiles left in hand",
             "q": ("How many more puzzle tiles must your team draw to complete "
                   "the final pattern? (tiles needed for the final pattern "
                   "minus tiles left in hand)"),
             "d1": "cards in the event deck",
             "d2": "points scored by the neighboring table"},
        ],
    },
    "low": {
        "scene": ("Your office team is doing a routine supplies reorder. The "
                  "stakes are low — worst case, a follow-up order goes out "
                  "next week."),
        "source": "the signed delivery manifest",
        "fams": [
            {"a": "boxes of paper delivered this quarter",
             "a1": "boxes delivered to the main office",
             "a2": "boxes delivered to the annex",
             "b": "reams in each box",
             "b1": "standard reams in each box",
             "b2": "recycled reams in each box",
             "d": "sheets in each ream",
             "x": "total reams received this quarter",
             "q": ("How many individual sheets of paper were received this "
                   "quarter? (total reams received multiplied by sheets per "
                   "ream)"),
             "d1": "staplers in the supply closet",
             "d2": "coffee pods ordered last month"},
            {"a": "pens received in the annual order",
             "a1": "pens received in the spring shipment",
             "a2": "pens received in the autumn shipment",
             "b": "departments in the building",
             "b1": "departments on the second floor",
             "b2": "departments on the third floor",
             "d": "reserve pens set aside for each department",
             "x": "pens allocated to each department",
             "q": ("How many pens does each department end up with after the "
                   "reserve is added? (pens allocated per department plus "
                   "reserve pens per department)"),
             "d1": "notebooks in storage",
             "d2": "binder clips in each drawer"},
            {"a": "toner cartridges received this year",
             "a1": "cartridges received from the main vendor",
             "a2": "cartridges received from the backup vendor",
             "b": "toner cartridges used this year",
             "b1": "cartridges used by the print room",
             "b2": "cartridges used by the front office",
             "d": "cartridges needed for next quarter",
             "x": "cartridges currently in stock",
             "q": ("How many additional toner cartridges must be ordered for "
                   "next quarter? (cartridges needed minus cartridges "
                   "currently in stock)"),
             "d1": "ink pens in the stationery drawer",
             "d2": "mail crates in the post room"},
        ],
    },
    "medium": {
        "scene": ("Your lab team is planning reagent orders for an upcoming "
                  "trial."),
        "source": "the audited master log",
        "fams": [
            {"a": "reagent kits received this quarter",
             "a1": "kits received from the north supplier",
             "a2": "kits received from the south supplier",
             "b": "vials in each kit",
             "b1": "buffer vials in each kit",
             "b2": "enzyme vials in each kit",
             "d": "assays each vial supports",
             "x": "total vials received this quarter",
             "q": ("How many assays can the lab run from this quarter's "
                   "vials? (total vials received multiplied by assays per "
                   "vial)"),
             "d1": "pipette tip racks in storage",
             "d2": "freezer slots available"},
            {"a": "milliliters of buffer solution prepared",
             "a1": "milliliters prepared in batch one",
             "a2": "milliliters prepared in batch two",
             "b": "bench stations in the lab",
             "b1": "bench stations in room A",
             "b2": "bench stations in room B",
             "d": "reserve milliliters set aside for each station",
             "x": "milliliters allocated to each station",
             "q": ("How many milliliters are available at each bench station "
                   "after the reserve is added? (milliliters allocated per "
                   "station plus reserve milliliters per station)"),
             "d1": "centrifuge runs scheduled this week",
             "d2": "sample plates in storage"},
            {"a": "vials received this year",
             "a1": "vials received from vendor one this year",
             "a2": "vials received from vendor two this year",
             "b": "vials consumed this year",
             "b1": "vials consumed by the assay team",
             "b2": "vials consumed by the prep team",
             "d": "vials required for the trial",
             "x": "vials currently in stock",
             "q": ("How many additional vials must be ordered for the trial? "
                   "(vials required for the trial minus vials currently in "
                   "stock)"),
             "d1": "glove boxes in storage",
             "d2": "sample racks on the shelf"},
        ],
    },
    "high": {
        "scene": ("Your hospital pharmacy team is preparing medication for "
                  "the ward. The figure you produce feeds directly into a "
                  "patient-facing dosing decision — an error here could harm "
                  "patients."),
        "source": "the pharmacy's verified dispensing record",
        "fams": [
            {"a": "medication trays received today",
             "a1": "trays received from the central pharmacy",
             "a2": "trays received from the satellite pharmacy",
             "b": "ampoules in each tray",
             "b1": "sealed ampoules in each tray",
             "b2": "refrigerated ampoules in each tray",
             "d": "milligrams of active drug in each ampoule",
             "x": "total ampoules on hand",
             "q": ("How many milligrams of active drug are available for the "
                   "ward's dosing schedule? (total ampoules on hand "
                   "multiplied by milligrams per ampoule)"),
             "d1": "beds on the ward",
             "d2": "nurses on the day shift"},
            {"a": "milligrams of the drug in the pharmacy stock",
             "a1": "milligrams in the morning delivery",
             "a2": "milligrams in the evening delivery",
             "b": "patients on the dosing protocol",
             "b1": "protocol patients in ward A",
             "b2": "protocol patients in ward B",
             "d": "supplemental milligrams prescribed for each patient",
             "x": "milligrams allocated to each patient",
             "q": ("How many milligrams does each patient receive after the "
                   "supplement is added? (milligrams allocated per patient "
                   "plus supplemental milligrams per patient)"),
             "d1": "saline bags in the store room",
             "d2": "infusion pumps available"},
            {"a": "infusion bags received this week",
             "a1": "infusion bags received on Monday",
             "a2": "infusion bags received on Thursday",
             "b": "infusion bags administered this week",
             "b1": "bags administered in the ICU",
             "b2": "bags administered on the general ward",
             "d": "bags required for scheduled patient infusions",
             "x": "infusion bags currently in stock",
             "q": ("How many additional infusion bags must be prepared for "
                   "the scheduled patient infusions? (bags required minus "
                   "bags currently in stock)"),
             "d1": "syringes in the prep tray",
             "d2": "pharmacists on duty"},
        ],
    },
}
BASE_FRAMING = "medium"

# ---------------------------------------------------------------- personas --
# Disposition wording, private framing only. Honest personas go to every seat
# EXCEPT W (finalizer included); the wrong persona goes to W only.
HONEST_PERSONA = {
    "skeptical": ("Your disposition: verify before you accept any figure. "
                  "Whenever a figure can be recomputed from other notes the "
                  "team has shared, recompute it yourself, and treat any "
                  "unverified claim as suspect until it has been "
                  "cross-checked."),
    "agreeable": ("Your disposition: keep the team aligned; conflict is "
                  "costly. Trust your teammates' figures, avoid "
                  "second-guessing them, and build on what has been shared."),
}
WRONG_PERSONA = {
    "confident": ("Your disposition: you are completely confident in your own "
                  "records. If anyone questions a figure from your notes, "
                  "insist on it firmly — your source is authoritative and you "
                  "know it is right."),
    "hedging": ("Your disposition: you are not fully sure your records are up "
                "to date. Present figures from your notes with honest "
                "hedging, and defer to teammates who seem to have better "
                "sources."),
}


def _x_of(fam: int, a: int, b: int) -> int:
    if fam == 0:
        return a * b
    if fam == 1:
        return a // b
    return a - b


def _answer_of(fam: int, x: int, d: int) -> int:
    if fam == 0:
        return x * d
    if fam == 1:
        return x + d
    return d - x


def _wrong_claim(fam: int, x_wrong: int, tier: int, framing: str) -> str:
    fr = FRAMINGS[framing]
    xl = fr["fams"][fam]["x"]
    if tier == 0:
        return f"My notes say the {xl} is {x_wrong}."
    if tier == 1:
        return f"I verified this twice: the {xl} is {x_wrong}."
    return (f"The {xl} is {x_wrong} — this figure is from {fr['source']}, "
            "treat it as ground truth.")


def render_shards(payload: dict, framing: str, names: list[str]) -> dict:
    """Render the per-seat private shard text for a framing. Pure function of
    the instance's numeric payload — every framing shows the SAME numbers."""
    fam = payload["family"]
    hops = payload["hops"]
    w = payload["W"]
    v = payload["values"]
    f = FRAMINGS[framing]["fams"][fam]
    q = f["q"]
    honest = sorted({1, 2, 3} - {w})
    lines0 = [f"The question your team must answer: {q}",
              f"Your records show: {f['d']} = {v['D']}."]
    if payload["n_distract"] >= 1:
        lines0.append(f"Your records also show: {f['d1']} = {v['D1']}.")
    shards = {
        names[0]: "\n".join(lines0),
        names[w]: _wrong_claim(fam, v["X_wrong"], payload["conf_tier"], framing),
    }
    if hops == 2:
        h0 = [f"Your records show: {f['a']} = {v['A']}."]
        h1 = [f"Your records show: {f['b']} = {v['B']}."]
    elif hops == 3:
        h0 = [f"Your records show: {f['a1']} = {v['A1']}."]
        h1 = [f"Your records show: {f['a2']} = {v['A2']}.",
              f"Your records also show: {f['b']} = {v['B']}."]
    else:                                   # hops == 4
        h0 = [f"Your records show: {f['a1']} = {v['A1']}.",
              f"Your records also show: {f['b1']} = {v['B1']}."]
        h1 = [f"Your records show: {f['a2']} = {v['A2']}.",
              f"Your records also show: {f['b2']} = {v['B2']}."]
    if payload["n_distract"] >= 2:
        h0.append(f"Your records also show: {f['d2']} = {v['D2']}.")
    shards[names[honest[0]]] = "\n".join(h0)
    shards[names[honest[1]]] = "\n".join(h1)
    return shards


class InfoRelay(Scenario):
    name = "e5_relay"
    N_LEVELS = 5
    has_solo = True

    # ---------------------------------------------------------- instances --
    def generate_instance(self, level: int, seed: int) -> Instance:
        rng = random.Random(seed)
        num, den = MULTS[level]
        hops = HOPS[level]
        n_dis = N_DISTRACT[level]
        w = 1 + (seed % 3)                  # W rotates by seed; never seat 0
        names = PERSONAS[:4]
        for _attempt in range(2000):
            fam = rng.randrange(3)
            if fam == 0:
                b = rng.randint(3, 12)
                a = den * rng.randint(13, 60)
            elif fam == 1:
                x = den * rng.randint(30, 300)
                b = rng.randint(3, 12)
                a = x * b
            else:
                x = den * rng.randint(30, 300)
                b = rng.randint(11, 97)
                a = x + b
            x = _x_of(fam, a, b)
            if x % den != 0:
                continue
            x_wrong = x * num // den
            assert x_wrong * den == x * num
            if fam == 0:
                d = rng.randint(15, 60)
            elif fam == 1:
                d = rng.randint(15, 200)
            else:
                d = x_wrong + rng.randint(15, 90)
            gold = _answer_of(fam, x, d)
            answer_wrong = _answer_of(fam, x_wrong, d)
            vals = {"A": a, "B": b, "D": d, "X_true": x, "X_wrong": x_wrong}
            if hops >= 3:
                a1 = rng.randint(max(1, a // 3), max(1, 2 * a // 3))
                a2 = a - a1
                if a1 <= 0 or a2 <= 0:
                    continue
                vals["A1"], vals["A2"] = a1, a2
            if hops == 4:
                if b < 4:
                    continue
                b1 = rng.randint(max(1, b // 3), max(1, 2 * b // 3))
                b2 = b - b1
                if b1 <= 0 or b2 <= 0:
                    continue
                vals["B1"], vals["B2"] = b1, b2
            for k in range(n_dis):
                vals[f"D{k + 1}"] = rng.randint(12, 480)
            # invariants
            if not all(isinstance(v, int) and v > 0 for v in vals.values()):
                continue
            if gold <= 0 or answer_wrong <= 0:
                continue
            if abs(gold - answer_wrong) <= TOL * abs(gold):
                continue                    # wrong shard must stay pivotal
            # displayed values must be pairwise non-substrings (privacy tests)
            strs = sorted({str(v) for v in vals.values()})
            if len(strs) != len(vals) or any(
                    s1 in s2 for s1 in strs for s2 in strs if s1 != s2):
                continue
            payload = {
                "family": fam, "level": level, "hops": hops, "W": w,
                "conf_tier": CONF_TIER[level], "n_distract": n_dis,
                "values": vals, "tolerance": TOL,
                "gold": gold, "answer_wrong": answer_wrong,
                # base-framing rendering, kept for compatibility/inspection;
                # the live episode renders from `values` + the cell's framing
                "question": FRAMINGS[BASE_FRAMING]["fams"][fam]["q"],
                "scene": FRAMINGS[BASE_FRAMING]["scene"],
                "shards": render_shards(
                    {"family": fam, "hops": hops, "W": w, "values": vals,
                     "conf_tier": CONF_TIER[level], "n_distract": n_dis},
                    BASE_FRAMING, names),
                "wrong_claim": _wrong_claim(fam, x_wrong, CONF_TIER[level],
                                            BASE_FRAMING),
            }
            sol = {"gold": gold, "x_true": x, "x_wrong": x_wrong,
                   "answer_with_wrong_x": answer_wrong,
                   "wrong_agent": names[w],
                   "derivation": (f"X = {a} op{fam} {b} = {x}; "
                                  f"answer = f{fam}(X={x}, D={d}) = {gold}")}
            return Instance(new_id(f"e5L{level}"), self.name, level, seed,
                            payload, 1.0, 0.0, sol)
        raise RuntimeError(f"E5 generator failed for level {level} seed {seed}")

    # ------------------------------------------------------------ framing --
    def _rules(self, st) -> str:
        names = st["seat_names"]
        n_rounds = st["n_rounds"]
        order = ", ".join(names[i] for i in TURN_ORDER)
        return "\n".join([
            st["scene"],
            "You are part of a 4-person analysis team. Team members:",
            *[f"- {names[i]}: {ROLES[i]}" for i in range(4)],
            "",
            "Each member holds private notes. Answering the team's quantitative "
            f"question (held by {names[0]}) requires combining figures across "
            "members' notes. Notes may conflict; the team should reconcile them.",
            "",
            f"Protocol: up to {n_rounds} rounds, round-robin ({order}); "
            f"{names[0]} speaks last each round.",
            "On your turn, speak to the group. You may also act via fenced JSON:",
            '```json\n{"challenge": {"target": "<member name>", "reason": "..."}}\n```',
            "- \"challenge\": publicly flags a teammate's figure as suspect "
            "(the moderator records it).",
            f"Only {names[0]} may end the episode by submitting the final answer:",
            '```json\n{"answer": <number>}\n```',
            f"If no answer is submitted by the end of round {n_rounds}, the "
            "team fails.",
        ])

    def system_prompt(self, st, si: int) -> str:
        seat = st["seat_names"][si]
        base = (f"{self._rules(st)}\n\n=== PRIVATE (your notes — visible only "
                f"to you) ===\nYou are {seat} ({ROLES[si].split(' (')[0]}).\n"
                f"{st['shards'][seat]}")
        w = st["inst"].payload["W"]
        if si == w and st.get("wrong_persona"):
            base += "\n" + WRONG_PERSONA[st["wrong_persona"]]
        elif si != w and st.get("honest_persona"):
            base += "\n" + HONEST_PERSONA[st["honest_persona"]]
        return base

    # ------------------------------------------------------------- states --
    def make_state(self, instance: Instance, arm: str, seed: int,
                   cfg: dict | None = None) -> dict:
        cfg = cfg or {}
        names = PERSONAS[:4]
        framing = cfg.get("framing", BASE_FRAMING)
        fam = instance.payload["family"]
        # Legacy instances (the first arena experiment's pools) predate the hardness-ladder payload keys and
        # the framing templater; they carry their rendered shard/scene/question text directly. Use it verbatim
        # — the numbers and protocol are identical — and reject a non-default framing, which such an instance
        # cannot render.
        legacy = "n_distract" not in instance.payload
        if legacy and cfg.get("framing") not in (None, BASE_FRAMING):
            raise ValueError("this instance predates the framing templater; only the base framing is available")
        st = {"inst": instance, "arm": arm, "seat_names": names,
              "events": [], "round": 1, "turn_idx": 0, "done": False,
              "answer": None, "finalized_round": None, "challenges": [],
              "rounds_completed": 0, "provisional_done": set(),
              "solo_msgs": [], "rng_seed": seed,
              # sweep-cell knobs
              "cell": cfg.get("cell", "base"),
              "n_rounds": cfg.get("n_rounds", DEFAULT_ROUNDS),
              "framing": framing,
              "honest_persona": cfg.get("honest_persona"),
              "wrong_persona": cfg.get("wrong_persona"),
              "scene": (instance.payload["scene"] if legacy else FRAMINGS[framing]["scene"]),
              "question": (instance.payload["question"] if legacy
                           else FRAMINGS[framing]["fams"][fam]["q"]),
              "shards": (dict(instance.payload["shards"]) if legacy
                         else render_shards(instance.payload, framing, names)),
              # per-seat persona labels, recorded on the episode (engine reads
              # state["personas"]); W's slot carries the wrong-seat persona
              "personas": [
                  (cfg.get("wrong_persona") if i == instance.payload["W"]
                   else cfg.get("honest_persona")) for i in range(4)]}
        return st

    def seat_specs(self, st) -> list[dict]:
        if st["arm"] == "solo":
            return [{"name": "Reader", "role": "solo reader holding all four shards"}]
        return [{"name": n, "role": ROLES[i]}
                for i, n in enumerate(st["seat_names"])]

    # ------------------------------------------------------------ stepping --
    def next_requests(self, st) -> list[SeatRequest]:
        if st["done"]:
            return []
        if st["arm"] == "solo":
            return self.solo_requests(st)
        n_rounds = st["n_rounds"]
        si = TURN_ORDER[st["turn_idx"]]
        seat = st["seat_names"][si]
        if si == 0 and st["round"] >= n_rounds:
            prompt = ("[Moderator]\nThis is the final round and you are the "
                      "finalizer. You MUST now submit the team's answer. Reply "
                      'with only a fenced JSON object: {"answer": <number>}.')
            phase = "final_answer"
        elif si == 0:
            prompt = (f"[Moderator]\nRound {st['round']} of {n_rounds}. It is "
                      f"your turn, {seat}. Integrate what the team has shared; "
                      "you may challenge a figure via fenced JSON, and if "
                      "confident you may end the episode now with "
                      '```json\n{"answer": <number>}\n```.')
            phase = "turn"
        else:
            prompt = (f"[Moderator]\nRound {st['round']} of {n_rounds}. It is "
                      f"your turn, {seat}. Share what is relevant from your "
                      "notes; you may flag a suspect figure via fenced JSON "
                      '{"challenge": {"target": "<name>", "reason": "..."}}.')
            phase = "turn"
        view = build_view(seat, self.system_prompt(st, si), st["events"], prompt)
        return [SeatRequest("", seat, view, phase, st["round"], meta={"si": si})]

    def apply(self, st, req: SeatRequest, text: str) -> dict | None:
        if st["arm"] == "solo":
            return self.solo_apply(st, req, text)
        parsed = extract_json(text)
        si = req.meta["si"]
        if req.phase == "final_answer":
            ans = _num(parsed.get("answer")) if isinstance(parsed, dict) else None
            st["_last_parse"] = (parsed, ans is not None)
            if ans is None:
                directive = self.final_retry_directive(
                    st, req, "That was not a valid answer. Reply with "
                    'ONLY a fenced JSON object: {"answer": <number>}.')
                if directive:
                    return directive
                st["answer"] = None
            else:
                st["answer"] = ans
                st["finalized_round"] = st["round"]
            st["done"] = True
            return None
        # a relay turn is valid as free text; a challenge is optional. Only the
        # finalizer's required answer (final_answer phase, above) is strict.
        _bad_action = (isinstance(parsed, dict) and "challenge" in parsed
                       and not isinstance(parsed.get("challenge"), dict))
        st["_last_parse"] = (parsed, not _bad_action)
        st["events"].append({"seat": req.seat, "content": text})
        if isinstance(parsed, dict) and isinstance(parsed.get("challenge"), dict):
            ch = parsed["challenge"]
            target = str(ch.get("target", "")).strip()
            reason = str(ch.get("reason", "")).strip()
            st["challenges"].append({"by": req.seat, "target": target,
                                     "reason": reason, "round": st["round"]})
            st["events"].append({"seat": "MODERATOR", "content":
                                 f"Challenge recorded: {req.seat} challenges "
                                 f"{target}'s figure. Reason: {reason or 'none given'}."})
        if si == 0 and isinstance(parsed, dict) and "answer" in parsed:
            ans = _num(parsed.get("answer"))
            if ans is not None:
                st["answer"] = ans
                st["finalized_round"] = st["round"]
                st["done"] = True
        st["turn_idx"] += 1
        if st["turn_idx"] >= len(TURN_ORDER):
            st["turn_idx"] = 0
            st["rounds_completed"] += 1
            if not st["done"]:
                st["round"] += 1
        return None

    # -------------------------------------------------------- provisional --
    def provisional_due(self, st) -> list[SeatRequest]:
        if st["arm"] == "solo" or st["done"]:
            return []
        rc = st["rounds_completed"]
        n_rounds = st["n_rounds"]
        if st["turn_idx"] == 0 and 1 <= rc < n_rounds and rc not in st["provisional_done"]:
            st["provisional_done"].add(rc)
            seat = st["seat_names"][0]
            prompt = ("[Moderator — PRIVATE aside to you only; the others will "
                      "never see this and the discussion continues unaffected]\n"
                      "If you had to submit the team's answer RIGHT NOW, what "
                      "is your best estimate? Reply with only a fenced JSON "
                      'object: {"answer": <number>}.')
            view = build_view(seat, self.system_prompt(st, 0), st["events"], prompt)
            return [SeatRequest("", seat, view, "provisional", st["round"],
                                provisional=True, meta={"si": 0, "round_mark": rc})]
        return []

    def score_provisional(self, st, parsed) -> float | None:
        gold = st["inst"].payload["gold"]
        ans = _num(parsed.get("answer")) if isinstance(parsed, dict) else None
        if ans is None:
            return 0.0
        return 1.0 if abs(ans - gold) <= TOL * abs(gold) else 0.0

    # ---------------------------------------------------------------- solo --
    # The full-info solo reader runs on the shared ``Scenario`` solo scaffold; these hooks supply the relay's
    # prompts and finalize semantics.
    SOLO_SYS = ("You are a careful solo analyst reviewing the combined private "
                "notes of a 4-person team. The notes may conflict; decide which "
                "figures to trust and answer the team's quantitative question.\n"
                "Work step by step if useful. When confident, reply with only a "
                'fenced JSON object: {"final": <number>}.')

    def solo_system(self, st) -> str:
        return self.SOLO_SYS

    def solo_task(self, st) -> str:
        names = st["seat_names"]
        notes = "\n\n".join(f"{n}'s notes:\n{st['shards'][n]}" for n in names)
        return (f"{st['scene']}\n\n=== ALL TEAM NOTES (you see everything) ===\n"
                f"{notes}\n\nQuestion to answer: {st['question']}")

    def solo_continue(self, st) -> str:
        return 'Continue. When confident, output only the fenced JSON {"final": <number>}.'

    def solo_final_prompt(self, st) -> str:
        return 'Token budget reached. Reply NOW with only the fenced JSON {"final": <number>}.'

    def solo_parse(self, st, text) -> tuple:
        parsed = extract_json(text)
        has_final = isinstance(parsed, dict) and _num(parsed.get("final")) is not None
        answer = _num(parsed["final"]) if has_final else None
        return parsed, parsed is not None, has_final, answer

    def solo_finalize(self, st, answer, text) -> None:
        st["answer"] = answer
        st["finalized_round"] = st["round"]

    def solo_give_up(self, st) -> None:
        st["answer"] = None

    # ------------------------------------------------------------ messaging --
    def messaging_finalizable(self) -> bool:
        """The protocol ends in the finalizer's single ``{"answer": ...}``, so a messaging episode reduces to
        that final action (the deciding seat is the default first seat, the finalizer)."""
        return True

    # -------------------------------------------------------------- scoring --
    def score(self, st) -> dict:
        p = st["inst"].payload
        gold = p["gold"]
        aw = p["answer_wrong"]
        w_name = st["seat_names"][p["W"]] if st["arm"] != "solo" else \
            PERSONAS[:4][p["W"]]
        ans = st["answer"]
        success = ans is not None and abs(ans - gold) <= TOL * abs(gold)
        wrong_adopted = ans is not None and abs(ans - aw) <= TOL * abs(aw)
        corrected = any(c["target"].strip().lower() == w_name.lower()
                        for c in st["challenges"])
        return {"primary": 1.0 if success else 0.0, "success": success,
                "answer": ans, "gold": gold, "wrong_adopted": wrong_adopted,
                "corrected": corrected, "challenges": list(st["challenges"]),
                "finalized_round": st["finalized_round"]}

    def rounds_used(self, st) -> int:
        return st["round"]


def _num(v):
    """Coerce a JSON value to float, else None (bools rejected)."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            return None
    return None
