#!/usr/bin/env python3
"""Where instant learning stops, measured instead of argued.

The claim under test
--------------------
"Give the model the most advanced coding actions, let it experience them ONCE,
and it learns them permanently. Then give it any new environment, and it learns
that too. So every problem on a computer is solved."

Four questions, each one measurement, each one able to say NO:

  1. DOES THE SKILL BANK STAY CORRECT AND CHEAP AS IT GROWS?
     Teach N distinct boundary lessons into `VerifiedSkillStore`, then ask it for
     the FIRST lesson by that lesson's own before-source. Report wall time and
     whether the edit is the right one. A bank that gets slow or wrong is not
     "permanent learning", it is library drift.

  2. DOES THE LESSON SURVIVE A PROCESS RESTART -- and does it stay narrow?
     Teach in one interpreter, apply in a fresh one. Then ask for three
     controls: a renamed function (should be edited), an already-correct
     function (should NOT be edited), an unrelated bug (should NOT be edited).

  3. IS A LESSON LEARNED IN ONE LANGUAGE OFFERED TO ANOTHER?
     `lookup_rules(language=...)` is the only door into the bank. If a Python
     lesson is invisible to Go, then "learn it once" is "once per language".

  4. DOES THE TRANSFER MECHANISM SURVIVE STATE NAMES CHANGING?
     This is the one that decides computer use. `changed_state_transfer_benchmark_v1`
     earns its wins from a carried TRANSITION MODEL -- a dict keyed on
     `str(state)`. Two instances of the same family share state names in the toy
     families. A real computer does not: `ComputerEnv.state()` is a content hash
     of the working directory, so a new directory is a new key for the same
     situation. Nothing about the dynamics is changed here; only the name of
     each state, by prefixing an instance tag.

WHAT EACH RESULT CAN AND CANNOT MEAN
------------------------------------
* A right edit plus a refused control is evidence the lesson is real and narrow.
  It is not evidence the lesson generalizes beyond the fixtures below.
* A wrong edit is the strongest possible negative: it is silent, it is cheap,
  and it edits source nobody asked about.
* Question 4 separates two mechanisms that the same status string has confused
  before: RECALLED_PLAN replays an action SEQUENCE (no state lookup, so names do
  not matter), CARRIED_MODEL plans through a state-keyed TABLE (names are
  everything). Any result that reports one number for "transfer" is measuring
  whichever of the two happened to fire.
* The toy families have 7-64 states. |S|x|A| is reported beside the number of
  transitions the teach run stored, because a model that has stored every
  transition of a 21-transition machine is a finished lookup table, not an
  induced rule -- and a lookup table cannot transfer outside its own |S|.

Authority: NONE. Producer-run measurement on constructed fixtures.
No capability, ownership, benchmark, terminal or sentience credit follows.
`truth.achieved` stays false. Spend $0. Model dependency 0.

Run:
    python3 -m canonical.tools.instant_learning_boundary_probe_v1
    python3 -m canonical.tools.instant_learning_boundary_probe_v1 --json out.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

POINTS = [(-2, -2), (-1, 0), (0, 0), (0, 3), (3, 3), (4, 3), (10, 10), (9, 10)]
OPS = {
    "<=": lambda x, h: x <= h, "<": lambda x, h: x < h,
    ">=": lambda x, h: x >= h, ">": lambda x, h: x > h,
    "==": lambda x, h: x == h, "!=": lambda x, h: x != h,
}

# Four genuinely different skeletons, so a bank of N is a bank of N shapes and
# not one shape re-taught. The operator flip varies independently.
SHAPES = (
    ("def {f}(x, hi):\n    return x {b} hi\n",
     "def {f}(x, hi):\n    return x {a} hi\n"),
    ("def {f}(x, hi):\n    if x {b} hi:\n        return True\n    return False\n",
     "def {f}(x, hi):\n    if x {a} hi:\n        return True\n    return False\n"),
    ("def {f}(x, hi, tag=0):\n    y = x + tag\n    return y {b} hi\n",
     "def {f}(x, hi, tag=0):\n    y = x + tag\n    return y {a} hi\n"),
    ("def {f}(lo, hi, x):\n    ok = x {b} hi\n    return ok and x >= lo\n",
     "def {f}(lo, hi, x):\n    ok = x {a} hi\n    return ok and x >= lo\n"),
)
FLIPS = (("<=", "<"), ("<", "<="), (">=", ">"), (">", ">="), ("==", "!="), ("!=", "=="))


# --------------------------------------------------------------------------- #
# oracles: the only thing allowed to say a candidate is right
# --------------------------------------------------------------------------- #
def _load(src: str) -> dict:
    ns: dict = {}
    exec(compile(src, "<instant-learning-probe>", "exec"), ns)  # noqa: S102 - fixed fixture text
    return ns


def any_fn_op(op: str):
    """True if SOME callable in the snippet behaves as `op` on every probe point."""
    def check(src: str) -> bool:
        try:
            ns = _load(src)
            fn = next(v for v in ns.values() if callable(v) and not isinstance(v, type))
            return all(fn(x, h) is OPS[op](x, h) for x, h in POINTS)
        except Exception:  # noqa: BLE001 - a candidate that raises is not a candidate
            return False
    return check


def named_fn_op(name: str, op: str):
    """True if the callable CALLED `name` behaves as `op`. Narrower than any_fn_op."""
    def check(src: str) -> bool:
        try:
            ns = _load(src)
            return all(ns[name](x, h) is OPS[op](x, h) for x, h in POINTS)
        except Exception:  # noqa: BLE001
            return False
    return check


# --------------------------------------------------------------------------- #
# 1. the bank grows
# --------------------------------------------------------------------------- #
def _build_bank(store, n: int):
    made = []
    for k in range(n):
        body_b, body_a = SHAPES[k % len(SHAPES)]
        b_op, a_op = FLIPS[(k // len(SHAPES)) % len(FLIPS)]
        fname = "fn_%d" % k
        before = body_b.format(f=fname, b=b_op)
        after = body_a.format(f=fname, a=a_op)
        result = store.crystallize_code_fix(
            before_snippet=before, after_snippet=after, language="python",
            error_class="BOUNDARY", twin_oracle=any_fn_op(a_op),
        )
        if result.get("crystallized"):
            made.append((fname, before, after, a_op))
    return made


def measure_bank_growth(sizes=(4, 24, 96, 240, 480)) -> list[dict]:
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

    rows = []
    for n in sizes:
        db = Path(tempfile.mkdtemp()) / "skills.sqlite"
        store = VerifiedSkillStore(db_path=db, seed=False)
        made = _build_bank(store, n)
        if not made:
            rows.append({"asked": n, "admitted": 0, "note": "nothing admitted"})
            continue
        fname, before, after, a_op = made[0]
        started = time.perf_counter()
        store.lookup_rules("python", "BOUNDARY")
        lookup_ms = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        out = store.recall_and_apply_verified(
            source_text=before, language="python",
            verifier=named_fn_op(fname, a_op), error_class="BOUNDARY",
        )
        apply_ms = (time.perf_counter() - started) * 1000
        right = bool(out) and out["patched_source"] == after
        rows.append({
            "asked": n, "admitted": len(made),
            "lookup_ms": round(lookup_ms, 3), "apply_ms": round(apply_ms, 3),
            "right_edit": bool(right),
            "wrong_edit": bool(out) and not right,
            "no_edit": out is None,
        })
    return rows


# --------------------------------------------------------------------------- #
# 2 + 3. restart, controls, and the language key
# --------------------------------------------------------------------------- #
_TEACH = r'''
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[3])
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
from canonical.tools.instant_learning_boundary_probe_v1 import any_fn_op
store = VerifiedSkillStore(db_path=Path(sys.argv[1]), seed=False)
out = store.crystallize_code_fix(
    before_snippet="def within(x, hi):\n    return x <= hi\n",
    after_snippet="def within(x, hi):\n    return x < hi\n",
    language=sys.argv[2], error_class="BOUNDARY", twin_oracle=any_fn_op("<"))
print(json.dumps({"admitted": bool(out.get("crystallized")), "reason": out.get("reason")}))
'''

_APPLY = r'''
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[2])
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
from canonical.tools.instant_learning_boundary_probe_v1 import named_fn_op
store = VerifiedSkillStore(db_path=Path(sys.argv[1]), seed=False)
CASES = {
    "same_function_new_process": ("def within(x, hi):\n    return x <= hi\n", "within", "<"),
    "renamed_function":          ("def guard(x, hi):\n    return x <= hi\n", "guard", "<"),
    "already_correct_control":   ("def within(x, hi):\n    return x < hi\n", "within", "<"),
    "unrelated_bug_control":     ("def within(x, hi):\n    return x >= hi\n", "within", "<"),
}
out = {}
for name, (src, fn, op) in CASES.items():
    res = store.recall_and_apply_verified(
        source_text=src, language="python",
        verifier=named_fn_op(fn, op), error_class="BOUNDARY")
    out[name] = {"edited": res is not None, "patched": (res or {}).get("patched_source")}
out["_offered"] = {lang: len(store.lookup_rules(lang, "BOUNDARY"))
                   for lang in ("python", "go", "typescript", "rust", "javascript", "java", "cpp")}
print(json.dumps(out))
'''


def measure_restart_and_language() -> dict:
    db = Path(tempfile.mkdtemp()) / "skills.sqlite"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    teach = subprocess.run(
        [sys.executable, "-B", "-c", _TEACH, str(db), "python", str(ROOT)],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120, check=True)
    taught = json.loads(teach.stdout)
    apply = subprocess.run(
        [sys.executable, "-B", "-c", _APPLY, str(db), str(ROOT)],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120, check=True)
    return {"teach": taught, "apply": json.loads(apply.stdout)}


# --------------------------------------------------------------------------- #
# 4. state names
# --------------------------------------------------------------------------- #
_RENAME = r'''
import json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import canonical.runtime as pkg
from transfer_learning_new_environment_probe_20261101 import Accum, Grid, Lock, Modulo, Toggles

RENAME = sys.argv[2] == "renamed"

def fresh(path):
    for name in list(sys.modules):
        if name.startswith("canonical.runtime.transfer_learning"):
            del sys.modules[name]
    if hasattr(pkg, "transfer_learning_v1"):
        delattr(pkg, "transfer_learning_v1")
    os.environ["BRAIN_TRANSFER_LEARNING_STATE"] = str(path)
    from canonical.runtime import transfer_learning_v1 as tl
    return tl

class Tag:
    """Same dynamics. Only the NAME of each state carries an instance tag."""
    def __init__(self, env, tag):
        self.env, self.tag = env, tag
    def reset(self):
        self.env.reset()
    def act(self, a):
        return self.env.act(a)
    def state(self):
        s = self.env.state()
        return ("%s:%r" % (self.tag, s)) if RENAME else s

def strip(s):
    return eval(s.split(":", 1)[1])   # our own repr of a tuple/str, never third-party data

FAMILIES = {
    "lock": (lambda i: Lock((4, 4, 4), (3, 3, 3), [(0,0,0),(1,0,0),(0,1,0)][i]),
             ["dial_0","dial_1","dial_2"], lambda s: all(v == 3 for v in s)),
    "toggles": (lambda i: Toggles(4, [bool((i >> b) & 1) for b in range(4)]),
                ["sw_0","sw_1","sw_2","sw_3"], lambda s: all(s)),
    "accumulator": (lambda i: Accum("abc", ["", "a", "ab"][i]),
                    ["put_a","put_b","put_c"], lambda s: s == "abc"),
    "grid": (lambda i: Grid((3, 2), [(0,0),(1,0),(0,1)][i]),
             ["mv_r","mv_l","mv_u","mv_d"], lambda s: s == (3, 2)),
    "modulo": (lambda i: Modulo(7, 5, i),
               ["add_1","add_2","add_3"], lambda s: s == 5),
}

cases = []
for name, (make, actions, goal) in FAMILIES.items():
    is_goal = (lambda s, g=goal: g(strip(s))) if RENAME else goal
    for index in (1, 2):
        path = Path(tempfile.mkdtemp()) / "ep.json"
        tl = fresh(path)
        source = tl.drive(Tag(make(0), "S"), actions, is_goal=is_goal,
                          goal_key="rename:" + name, budget=200, max_depth=12,
                          use_transfer=False)
        if not path.is_file():
            cases.append({"family": name, "case": index, "note": "teach did not persist"})
            continue
        memory = path.read_bytes()
        arm = {}
        for label, use in (("cold", False), ("warm", True)):
            path.write_bytes(memory)
            result = tl.drive(Tag(make(index), "T"), actions, is_goal=is_goal,
                              goal_key="rename:" + name, budget=200, max_depth=12,
                              use_transfer=use)
            arm[label] = {"pass": bool(result["pass"]),
                          "trials": result["trials_spent"],
                          "acts": result["interactions"]["act_calls"],
                          "authority": result["authority"]}
        cases.append({"family": name, "case": index, **arm})
print(json.dumps(cases))
'''


def measure_state_names() -> dict:
    out = {}
    for mode in ("as-is", "renamed"):
        proc = subprocess.run(
            [sys.executable, "-B", "-c", _RENAME, str(ROOT), mode],
            cwd=ROOT, capture_output=True, text=True, timeout=900, check=True)
        cases = json.loads(proc.stdout)
        solved = [c for c in cases if "cold" in c]
        out[mode] = {
            "cases": solved,
            "cold_trials": sum(c["cold"]["trials"] for c in solved),
            "warm_trials": sum(c["warm"]["trials"] for c in solved),
            "cold_acts": sum(c["cold"]["acts"] for c in solved),
            "warm_acts": sum(c["warm"]["acts"] for c in solved),
            "warm_authority": {
                a: sum(1 for c in solved if c["warm"]["authority"] == a)
                for a in sorted({c["warm"]["authority"] for c in solved})
            },
        }
    return out


# --------------------------------------------------------------------------- #
# the vocabulary a lookup table hides behind
# --------------------------------------------------------------------------- #
def measure_coverage() -> list[dict]:
    """|S|x|A| is what an exhaustive transition table needs. How much was stored?"""
    from transfer_learning_new_environment_probe_20261101 import (
        Accum, Grid, Lock, Modulo, Toggles)
    families = {
        "lock_3dial": (lambda: Lock((4, 4, 4), (3, 3, 3)),
                       ["dial_0", "dial_1", "dial_2"], 4 * 4 * 4, 3,
                       lambda s: all(v == 3 for v in s)),
        "toggles_4": (lambda: Toggles(4), ["sw_0", "sw_1", "sw_2", "sw_3"], 2 ** 4, 4,
                      lambda s: all(s)),
        "accum_word": (lambda: Accum("abc"), ["put_a", "put_b", "put_c"], 8, 3,
                       lambda s: s == "abc"),
        "grid_reach": (lambda: Grid((3, 2)),
                       ["mv_r", "mv_l", "mv_u", "mv_d"], 9, 4, lambda s: s == (3, 2)),
        "modulo_counter": (lambda: Modulo(7, 5, 0), ["add_1", "add_2", "add_3"], 7, 3,
                           lambda s: s == 5),
    }
    rows = []
    for name, (make, acts, n_states, n_actions, goal) in families.items():
        path = Path(tempfile.mkdtemp()) / "ep.json"
        os.environ["BRAIN_TRANSFER_LEARNING_STATE"] = str(path)
        for module in list(sys.modules):
            if module.startswith("canonical.runtime.transfer_learning"):
                del sys.modules[module]
        import canonical.runtime as pkg
        if hasattr(pkg, "transfer_learning_v1"):
            delattr(pkg, "transfer_learning_v1")
        from canonical.runtime import transfer_learning_v1 as tl
        tl.drive(make(), acts, is_goal=goal, goal_key="coverage", budget=400,
                 max_depth=12, use_transfer=False)
        stored = 0
        if path.is_file():
            for row in json.loads(path.read_text()):
                for table in (row.get("model") or {}).values():
                    stored += len(table)
        needed = n_states * n_actions
        rows.append({"family": name, "states": n_states, "actions": n_actions,
                     "transitions_needed": needed, "transitions_stored": stored,
                     "coverage": round(stored / needed, 3) if needed else None})
    return rows


def run() -> dict:
    return {
        "schema": "BRAIN_INSTANT_LEARNING_BOUNDARY_PROBE_V1",
        "scope": ("constructed Python boundary repairs and five constructed state machines; "
                  "not arbitrary coding, not GUI, not unbounded computer use"),
        "authority": "NONE",
        "bank_growth": measure_bank_growth(),
        "restart_and_language": measure_restart_and_language(),
        "state_names": measure_state_names(),
        "coverage": measure_coverage(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()
    report = run()
    text = json.dumps(report, indent=2)
    if args.json:
        args.json.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
