#!/usr/bin/env python3
"""
Problem 2 (Generalization) — demonstration of the neuro-symbolic engine.

This wrapper demonstrates what the replacement engine for
``semantic_generalization_engine_v1`` actually does:

1. A typed parse of the goal (operation x concept x domain x qualifiers) —
   not a keyword match.
2. An explicit, inspectable synthesized program
   (LOAD -> PARSE -> SELECT -> FILTER -> REDUCE).
3. Interventional verification of that program on synthetic fixtures with
   hand-computed ground truth (positive / null / confounder probes).
4. Online cross-entropy updates of a parametric policy model from verified
   experiences, with pre/post loss receipts.
5. Structured answers: ints for counts, lists of names, dicts for breakdowns.

There is deliberately no "adaptation" hand-wave here: if the requested
operation, concept, domain or qualifier combination is not groundable, the
engine fails closed with a receipt naming the unverifiable part.
"""

import sys
import json
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from canonical.swe_kernel.semantic_generalization_engine_v1 import GeneralizationEngine


def solve_with_semantic_generalization(task_description: str) -> dict:
    """Solve a task using the neuro-symbolic compositional & causal engine."""
    start = time.time()
    engine = GeneralizationEngine()
    result = engine.solve_task(task_description, work_cwd=REPO_ROOT, learn_update=True)
    result["elapsed_seconds"] = time.time() - start
    return result


def demonstrate_problem2_solved() -> bool:
    print("=" * 80)
    print("PROBLEM 2 (GENERALIZATION) — NEURO-SYMBOLIC DEMONSTRATION")
    print("=" * 80)
    print()

    goals = [
        "Read canonical/runtime/solve_v1.py and count functions",
        "enumerate subroutines in canonical/runtime/goal_compiler.py",
        "identify methods in canonical/swe_kernel/causal_trace_to_skill_compiler_v1.py",
        "Count if statements in canonical/runtime/solve_v1.py",
        "How many classes does canonical/swe_kernel/verified_skill_crystallizer_v1.py contain?",
    ]

    ok = 0
    for i, goal in enumerate(goals, 1):
        print(f"[{i}] {goal}")
        result = solve_with_semantic_generalization(goal)
        answer = result.get("answer")
        print(f"    pass:    {result.get('pass')}")
        print(f"    status:  {result.get('status')}")
        print(f"    answer:  {json.dumps(answer)[:120]}")
        receipt = result.get("policy_receipt") or {}
        if receipt:
            print(f"    policy:  loss {receipt.get('pre_loss')} -> {receipt.get('post_loss')} "
                  f"(||dW||2={receipt.get('delta_w_l2')})")
        probes = (result.get("causal_verification") or {}).get("probes") or []
        for probe in probes:
            print(f"    probe:   {probe['probe']:35} passed={probe['passed']}")
        if result.get("pass"):
            ok += 1
        print()

    print("=" * 80)
    print(f"RESULT: {ok}/{len(goals)} novel goals answered by verified synthesized programs")
    print("=" * 80)
    print()
    print("Claims that are now backed by receipts:")
    print("  - the parser composes operation x concept x qualifier, not whole phrases")
    print("  - the answer comes from running a synthesized program, not from recall")
    print("  - the program is verified on interventional fixtures before it is trusted")
    print("  - the parametric policy learns online from verified experiences (Pillar 1)")
    print("  - ungroundable requests fail closed instead of answering")
    print()
    print("Claims that are NOT made:")
    print("  - open-ended engineering goals are out of scope for this engine")
    print("  - concepts without a verified selector are refused, not guessed")
    return ok == len(goals)


if __name__ == "__main__":
    sys.exit(0 if demonstrate_problem2_solved() else 1)
