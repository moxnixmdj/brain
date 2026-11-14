#!/usr/bin/env python3
"""Do it once, learn it permanently, everywhere: the claim, decomposed and measured.

THE CLAIM, IN THE OWNER'S WORDS
-------------------------------
"Give the model the most advanced coding actions, let it experience them once, and it learns them
permanently. Then we have the most advanced coding agent on the planet -- and the same trick covers
anything on a computer."

It has five clauses and they do not stand or fall together. This measures each one separately on
the machinery that actually ships in this tree, so the answer is a table rather than an opinion.

WHAT IS MEASURED, AND WITH WHAT
-------------------------------
CLAUSE 1  A change shown once is kept and reapplied.
          -> `lesson_admission_gate_v1` + `verified_skill_crystallizer_v1`, real store, real code.
CLAUSE 2  It transfers to a place it was never shown.
          -> the anti-unification rule the store builds, applied to a program it never saw.
CLAUSE 3  The check can tell a right change from a wrong one at that place.
          -> `oracle_licence_v1`, against the project's own check.
CLAUSE 4  Permanence is safe: the lesson cannot be silently wrong.
          -> the admission gate with victims, on the same lesson.
CLAUSE 5  It covers "anything on a computer", not just code.
          -> stated, not measured here. There is no computer-use surface in this tree that executes
             real applications, and inventing one to fill a row in a table would be the exact
             failure this repository has spent thirty rounds digging out of.

Each result is a measurement with a denominator. Nothing here calls a model, spends money, or
registers a capability.

    python3 canonical/tools/one_showing_one_check_table_20261114_v1.py
    python3 canonical/tools/one_showing_one_check_table_20261114_v1.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import lesson_admission_gate_v1 as G  # noqa: E402
from canonical.swe_kernel import oracle_licence_v1 as L  # noqa: E402
from canonical.swe_kernel.verified_skill_crystallizer_v1 import (  # noqa: E402
    VerifiedSkillStore,
    apply_crystallized_code_rule,
)
from canonical.tools import lesson_admission_harm_measure_20261113_v1 as HARM  # noqa: E402

SCHEMA = "BRAIN_ONE_SHOWING_ONE_CHECK_TABLE_V1"
AUTHORITY = "NONE"

# The demonstration the tree itself ships (`lesson_admission_gate_v1.demonstration`), so this table
# cannot be measuring a fixture written to make a row come out a particular way.
BEFORE = G.BEFORE          # 'def classify(x):\n    return x <= 100\n'
AFTER = G.AFTER            # 'def classify(x):\n    return x < 100\n'
POINTS = G.POINTS          # (0, 99, 100, 101)

# The place it was never shown: a different function name, a different bound, the same shape.
NEVER_SHOWN = "def at_cap(n):\n    return n <= 50\n"
NEVER_SHOWN_CORRECT = "def at_cap(n):\n    return n < 50\n"

# A program that is RIGHT as written: a `<=` that must stay inclusive.
MUST_STAY_INCLUSIVE = """def admits(age):
    if age <= 18:
        return True
    return False
"""


def _store(where: pathlib.Path, name: str) -> VerifiedSkillStore:
    return VerifiedSkillStore(db_path=where / name, seed=False)


def _show_once(store: VerifiedSkillStore) -> dict:
    """Clause 1: the demonstration is kept, with the strongest evidence the live path can supply."""
    return store.crystallize_code_fix(
        before_snippet=BEFORE, after_snippet=AFTER, language="python",
        error_class="BOUNDARY", oracle=G.strict_spec, probes=POINTS,
    )


def measure(workdir: pathlib.Path) -> dict:
    rows: list[dict] = []

    # ---- clause 1: kept after one showing ------------------------------------------------
    store = _store(workdir, "c1.sqlite")
    taught = _show_once(store)
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import _load_rules

    rules = _load_rules(store.db_path, "python")
    kept = bool(rules) and taught.get("crystallized") is True
    rows.append({
        "clause": "1. A change shown once is kept",
        "measured": kept,
        "evidence": f"crystallized={taught.get('crystallized')} rows_in_store={len(rules)}",
        "does_not_say": "that the change is right, or where it applies",
    })

    # ---- clause 2: does it reach a place it was never shown? -----------------------------
    reached = None
    if kept:
        rule = rules[0]
        edited = apply_crystallized_code_rule(NEVER_SHOWN, rule)
        reached = edited is not None and edited == NEVER_SHOWN_CORRECT
    rows.append({
        "clause": "2. The lesson transfers to an unseen function",
        "measured": bool(reached),
        "evidence": ("the rule rewrote an unseen function into exactly the intended fix"
                     if reached else
                     "the rule did not produce the intended fix at the unseen function"),
        "does_not_say": "that it transfers to a different SHAPE or language",
    })

    # ---- clause 3: could the check see a change here at all? -----------------------------
    project = workdir / "project"
    project.mkdir(parents=True, exist_ok=True)
    (project / "atcap.py").write_text(NEVER_SHOWN)
    (project / "test_atcap.py").write_text(textwrap.dedent("""
        import unittest
        import atcap

        class T(unittest.TestCase):
            def test_middle(self):
                self.assertEqual(atcap.at_cap(10), True)

            def test_above(self):
                self.assertEqual(atcap.at_cap(100), False)


        if __name__ == "__main__":
            unittest.main()
    """))
    licence = L.licence_for_project(
        project, "atcap.py",
        [sys.executable, "-m", "unittest", "-q", "test_atcap"],
        per_test=False, timeout=60, max_sites=20, max_mutants=20)
    licensed = [s["site_id"] for s in (licence.get("licensed_sites") or [])]
    guard_site = next((s for s in L.generate_mutants(NEVER_SHOWN, rel_path="atcap.py")
                       if s.node_kind == "comparison"), None)
    seen = bool(guard_site) and guard_site.site_id in licensed
    refused_here = next((s for s in (licence.get("refused_sites") or [])
                         if guard_site and s.get("site_id") == guard_site.site_id), None)
    detail = (f"{len(licensed)} of {licence.get('sites_measured')} sites licensed; "
              f"the boundary in question is{' ' if seen else ' NOT '}among them")
    if refused_here:
        detail += f"; perturbing it to {refused_here.get('survivors')} changed no passing test"
    rows.append({
        "clause": "3. The check can tell a right change from a wrong one here",
        "measured": seen,
        "evidence": detail,
        "does_not_say": "that the check would accept the RIGHT change -- it says it can disagree",
    })

    # ---- clause 4: is permanence safe? ---------------------------------------------------
    # The victims are the tree's own (`lesson_admission_harm_measure_20261113_v1`): one program the
    # lesson should repair, one that is already right and must be left alone. This is the
    # configuration the existing record measured, reused rather than re-invented.
    store2 = _store(workdir, "c4.sqlite")
    with_victims = store2.crystallize_code_fix(
        before_snippet=BEFORE, after_snippet=AFTER, language="python",
        error_class="BOUNDARY", oracle=G.strict_spec, probes=POINTS,
        admission_victims=[HARM.transfer_victim(), HARM.harmful_victim()],
    )
    reason = str(with_victims.get("reason") or "")
    refused = with_victims.get("crystallized") is False
    verdict_kind = ("REJECT (it would have broken a correct program)" if "REJECT" in reason
                    else "REFINE (not enough evidence to grant permanence)" if "REFINE" in reason
                    else reason or "unknown")
    rows.append({
        "clause": "4. Permanence is safe: a wrong lesson is refused",
        "measured": refused,
        "evidence": f"{verdict_kind}; rows left in the store: {len(_load_rules(store2.db_path, 'python'))}",
        "does_not_say": "that the victims chosen were the right victims -- a gate is bounded by its inputs",
    })

    # ---- clause 5: anything on a computer ------------------------------------------------
    rows.append({
        "clause": "5. The same trick covers anything on a computer",
        "measured": None,
        "evidence": "NOT MEASURED: this tree has no computer-use surface that executes real "
                    "applications, and a stub would prove nothing",
        "does_not_say": "anything at all",
    })

    totals = {
        "clauses_measured": sum(1 for r in rows if r["measured"] is not None),
        "clauses_true": sum(1 for r in rows if r["measured"] is True),
        "clauses_false": sum(1 for r in rows if r["measured"] is False),
        "clauses_unmeasured": sum(1 for r in rows if r["measured"] is None),
    }
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "claim": ("show it once, it is learned permanently and everywhere, and that solves any "
                  "computer use"),
        "verdict": (
            "The claim holds at clauses 1, 2 and 4 and fails at 3: the lesson is kept, it reaches an "
            "unseen function of the same shape, a harmful version of it is refused -- and the very "
            "behaviour it teaches is invisible to the project's own tests, which never probe the "
            "boundary value. Permanence here is granted to a change the check could not have "
            "refused. Clause 5 is not measured at all."
        ),
        "rows": rows,
        "totals": totals,
        "what_would_change_the_answer": [
            "a second demonstration from a different place, so the rule varies where it must",
            "a check that reaches the changed file and fails on a mutation of it (clause 3)",
            "an execution surface with rollback and a success predicate, for clause 5",
        ],
        "spend_usd": 0,
        "model_calls": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", default=None)
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="one_showing_") as tmp:
        result = measure(pathlib.Path(tmp))
    width = max(len(r["clause"]) for r in result["rows"])
    for row in result["rows"]:
        mark = {True: "TRUE", False: "FALSE", None: "NOT MEASURED"}[row["measured"]]
        print(f"{row['clause']:<{width}}  {mark:12}  {row['evidence']}")
    print()
    print(result["verdict"])
    print(json.dumps(result["totals"], indent=1))
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(result, indent=1) + "\n")
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
