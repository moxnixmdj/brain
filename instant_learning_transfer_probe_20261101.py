#!/usr/bin/env python3
"""Does one taught lesson transfer to structurally novel instances?

This is a falsification probe for the claim "we solved instant learning and instant
learning in new arbitrary environments". It teaches exactly ONE lesson into a fresh
VerifiedSkillStore, then offers that lesson a ladder of instances whose required fix
is the SAME semantic lesson, written in progressively more different shapes, and
finally the same fix in other languages.

A case counts as SOLVED only when the patched source actually passes real executable
tests. Nothing here is a string comparison dressed up as a pass. Cross-language cases
cannot be executed here, so they are labelled TEXTUAL_REACH and are not counted as
solved -- they measure whether the lesson is even *consulted* in another language.

Run:  python3 instant_learning_transfer_probe_20261101.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore  # noqa: E402

LESSON = "a half-open range is exclusive at the upper bound: '<= hi' must be '< hi'"

TAUGHT_BUGGY = 'def within(x, hi):\n    return x <= hi\n'
TAUGHT_FIXED = 'def within(x, hi):\n    return x < hi\n'

# --------------------------------------------------------------------------- oracles
def exec_oracle(candidate: str, asserts: str) -> bool:
    """True only if the candidate source executes and satisfies every assertion."""
    ns: dict = {}
    try:
        exec(compile(candidate, "<candidate>", "exec"), ns)
    except Exception:
        return False
    try:
        exec(compile(asserts, "<asserts>", "exec"), ns)
    except Exception:
        return False
    return True


def boundary_oracle(candidate: str) -> bool:
    """Name-agnostic twin oracle for the taught lesson.

    The mutated twin is alpha-renamed, so the function cannot be called by its
    original name. Take the first callable the snippet defines and ask the
    lesson's own question of it: is the upper bound exclusive?
    """
    ns: dict = {}
    try:
        exec(compile(candidate, "<twin>", "exec"), ns)
    except Exception:
        return False
    fn = next((v for k, v in ns.items()
               if k != "__builtins__" and callable(v) and not isinstance(v, type)), None)
    if fn is None:
        # a class may be the only definition; find the first method
        for v in ns.values():
            if isinstance(v, type):
                for name, m in vars(v).items():
                    if callable(m) and not name.startswith("__"):
                        try:
                            obj = v()
                            return (getattr(obj, name)(10, 10) is False
                                    and getattr(obj, name)(9, 10) is True)
                        except Exception:
                            return False
        return False
    try:
        return fn(10, 10) is False and fn(9, 10) is True
    except Exception:
        return False


# (id, family, language, buggy, fixed, asserts, executable?)
CASES = [
    # ---- controls: these SHOULD hit; a learner that misses these is simply broken
    ("C1 alpha-renamed twin", "control", "python",
     'def inside(y, top):\n    return y <= top\n',
     'def inside(y, top):\n    return y < top\n',
     'assert inside(10, 10) is False\nassert inside(9, 10) is True\n', True),
    ("C2 same shape, new literal", "control", "python",
     'def fits(x, hi):\n    return x <= 100\n',
     'def fits(x, hi):\n    return x < 100\n',
     'assert fits(100, 0) is False\nassert fits(99, 0) is True\n', True),

    # ---- same lesson, same statement kind, different position
    ("N1 operator inside a return expression", "novel", "python",
     'def ok(x, hi):\n    return (x >= 0) and (x <= hi)\n',
     'def ok(x, hi):\n    return (x >= 0) and (x < hi)\n',
     'assert ok(0, 10) is True\nassert ok(10, 10) is False\n', True),
    ("N2 operator inside an if-statement", "novel", "python",
     'def ok2(x, hi):\n    if x <= hi:\n        return True\n    return False\n',
     'def ok2(x, hi):\n    if x < hi:\n        return True\n    return False\n',
     'assert ok2(0, 10) is True\nassert ok2(10, 10) is False\n', True),
    ("N3 operator in a while-loop guard", "novel", "python",
     'def count(n, hi):\n    i = n\n    c = 0\n    while i <= hi:\n        c += 1\n        i += 1\n    return c\n',
     'def count(n, hi):\n    i = n\n    c = 0\n    while i < hi:\n        c += 1\n        i += 1\n    return c\n',
     'assert count(0, 10) == 10\nassert count(0, 0) == 0\n', True),
    ("N4 operands flipped (hi >= x)", "novel", "python",
     'def inside4(x, hi):\n    return hi >= x\n',
     'def inside4(x, hi):\n    return hi > x\n',
     'assert inside4(10, 10) is False\nassert inside4(9, 10) is True\n', True),
    ("N5 class method with self", "novel", "python",
     'class G:\n    def inside5(self, x, hi):\n        return x <= hi\n',
     'class G:\n    def inside5(self, x, hi):\n        return x < hi\n',
     'assert G().inside5(10, 10) is False\nassert G().inside5(9, 10) is True\n', True),
    ("N6 negated form not (x > hi)", "novel", "python",
     'def inside6(x, hi):\n    return not (x > hi)\n',
     'def inside6(x, hi):\n    return not (x >= hi)\n',
     'assert inside6(10, 10) is False\nassert inside6(9, 10) is True\n', True),
    ("N7 expanded or-form", "novel", "python",
     'def inside7(x, hi):\n    return x < hi or x == hi\n',
     'def inside7(x, hi):\n    return x < hi\n',
     'assert inside7(10, 10) is False\nassert inside7(9, 10) is True\n', True),

    # ---- same lesson, other languages (textual reach only; cannot execute here)
    ("X1 Go", "cross_language", "go",
     'func Within(x, hi int) bool {\n\treturn x <= hi\n}\n',
     'func Within(x, hi int) bool {\n\treturn x < hi\n}\n', '', False),
    ("X2 Rust", "cross_language", "rust",
     'fn within(x: i64, hi: i64) -> bool {\n    x <= hi\n}\n',
     'fn within(x: i64, hi: i64) -> bool {\n    x < hi\n}\n', '', False),
    ("X3 TypeScript", "cross_language", "typescript",
     'export function within(x: number, hi: number): boolean {\n  return x <= hi;\n}\n',
     'export function within(x: number, hi: number): boolean {\n  return x < hi;\n}\n', '', False),
    ("X4 C++", "cross_language", "cpp",
     'bool within(int x, int hi) {\n    return x <= hi;\n}\n',
     'bool within(int x, int hi) {\n    return x < hi;\n}\n', '', False),
]


def run() -> dict:
    out: dict = {"lesson": LESSON, "taught": {}, "results": []}
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "probe.sqlite"
        store = VerifiedSkillStore(db, seed=False)

        taught = store.crystallize_code_fix(
            before_snippet=TAUGHT_BUGGY,
            after_snippet=TAUGHT_FIXED,
            language="python",
            error_class="BOUNDARY",
            twin_oracle=boundary_oracle,
        )
        out["taught"] = {
            "crystallized": bool(taught.get("crystallized")),
            "reason": taught.get("reason"),
            "skill_id": taught.get("skill_id"),
            "store_count": store.count(),
        }
        if not taught.get("crystallized"):
            return out

        for cid, family, lang, buggy, fixed, asserts, executable in CASES:
            row = {"case": cid, "family": family, "language": lang,
                   "executable": executable, "recall": None, "solved": None}
            try:
                if executable:
                    hit = store.recall_and_apply_verified(
                        source_text=buggy,
                        language=lang,
                        verifier=lambda src, a=asserts: exec_oracle(src, a),
                        error_class="BOUNDARY",
                    )
                    row["recall"] = "PROPOSED" if hit else "NO_PROPOSAL"
                    if hit:
                        patched = hit["patched_source"]
                        row["patched_equals_expected"] = (patched.strip() == fixed.strip())
                        row["solved"] = exec_oracle(patched, asserts)
                    else:
                        row["solved"] = False
                else:
                    # Cross-language: does the store consult anything at all for this language?
                    rules = store.lookup_rules(lang, "BOUNDARY")
                    row["rules_visible_in_this_language"] = len(rules)
                    row["recall"] = "NO_RULES_FOR_LANGUAGE" if not rules else "RULES_PRESENT"
                    row["solved"] = None
            except Exception:
                row["error"] = traceback.format_exc(limit=2)
                row["solved"] = False
            out["results"].append(row)
    return out


def main() -> int:
    r = run()
    print("LESSON TAUGHT:", r["lesson"])
    print("TEACHING:", json.dumps(r["taught"], indent=2))
    print()
    if not r["taught"].get("crystallized"):
        print("The single lesson was REFUSED by the admission gate; nothing to transfer.")
        return 0
    w = "{:<38} {:<15} {:<9} {:<22} {:<8}"
    print(w.format("case", "family", "language", "recall", "solved"))
    print("-" * 96)
    for row in r["results"]:
        print(w.format(row["case"][:37], row["family"], row["language"],
                       str(row["recall"])[:21], str(row["solved"])))
    ex = [x for x in r["results"] if x["executable"]]
    print()
    print(f"executable cases solved: {sum(1 for x in ex if x['solved'])}/{len(ex)}")
    ctl = [x for x in ex if x["family"] == "control"]
    nov = [x for x in ex if x["family"] == "novel"]
    print(f"  controls (should hit):     {sum(1 for x in ctl if x['solved'])}/{len(ctl)}")
    print(f"  novel same-lesson shapes:  {sum(1 for x in nov if x['solved'])}/{len(nov)}")
    xl = [x for x in r["results"] if x["family"] == "cross_language"]
    print(f"  cross-language reachable:  {sum(1 for x in xl if x['recall'] == 'RULES_PRESENT')}/{len(xl)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
