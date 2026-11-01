#!/usr/bin/env python3
"""Compare three existing repair-reuse paths on the same bounded lesson.

One Python boundary repair is taught into a new SQLite store. Each arm runs in
its own fresh Python process and opens that store. The target fixtures and finite
behavioral checks are known, constructed examples, not a blind benchmark and
not evidence of arbitrary coding ability. Candidate verification runs only the
fixed local fixtures in this file, never arbitrary user-supplied source.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEACH_BEFORE = "def within(x, hi):\n    return x <= hi\n"
TEACH_AFTER = "def within(x, hi):\n    return x < hi\n"
# Inputs are a predeclared finite regression set, not a proof over all values.
POINTS = [(-2, -2), (-1, 0), (0, 0), (0, 3), (3, 3), (4, 3), (10, 10), (9, 10)]
CASES = {
    "renamed": ("def target(x, hi):\n    return x <= hi\n", "exclusive"),
    "compound": ("def target(x, hi):\n    return x >= 0 and x <= hi\n", "nonnegative_exclusive"),
    "if_statement": ("def target(x, hi):\n    if x <= hi:\n        return True\n    return False\n", "exclusive"),
    "flipped": ("def target(x, hi):\n    return hi >= x\n", "exclusive"),
    "negated": ("def target(x, hi):\n    return not (x > hi)\n", "exclusive"),
    "disjunction": ("def target(x, hi):\n    return x < hi or x == hi\n", "exclusive"),
    # This code is already correct. Each arm must not turn it into an exclusive check.
    "negative_inclusive": ("def target(x, hi):\n    return x <= hi\n", "inclusive"),
}


def verify(source: str, meaning: str) -> bool:
    try:
        ns: dict = {}
        exec(compile(source, "<fixed-benchmark-candidate>", "exec"), ns)
        fn = ns["target"]
        for x, hi in POINTS:
            expected = ((x >= 0 and x < hi) if meaning == "nonnegative_exclusive"
                        else (x <= hi if meaning == "inclusive" else x < hi))
            if fn(x, hi) is not expected:
                return False
        return True
    except Exception:
        return False


def twin_oracle(source: str) -> bool:
    try:
        ns: dict = {}
        exec(compile(source, "<fixed-benchmark-twin>", "exec"), ns)
        fn = next(v for v in ns.values() if callable(v) and not isinstance(v, type))
        return all(fn(x, hi) is (x < hi) for x, hi in POINTS)
    except Exception:
        return False


def teach(db: Path) -> dict:
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
    store = VerifiedSkillStore(db_path=db, seed=False)
    start = time.perf_counter()
    result = store.crystallize_code_fix(
        before_snippet=TEACH_BEFORE, after_snippet=TEACH_AFTER,
        language="python", error_class="BOUNDARY", twin_oracle=twin_oracle,
    )
    return {"admitted": result.get("crystallized") is True,
            "skill_id": result.get("skill_id"),
            "elapsed_ms": round((time.perf_counter() - start) * 1000, 3)}


def evaluate(db: Path, arm: str) -> dict:
    from canonical.swe_kernel import boundary_disjunction_normalization_v1 as semantic
    from canonical.swe_kernel import operator_generalization_v1 as operator
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
    store = VerifiedSkillStore(db_path=db, seed=False)
    rules = store.lookup_rules("python", "BOUNDARY")
    if len(rules) != 1:
        raise RuntimeError("EXPECTED_EXACTLY_ONE_RETAINED_RULE")
    rule = rules[0]
    rows = []
    for name, (source, meaning) in CASES.items():
        start = time.perf_counter()
        checked = 0
        accepted = False

        def oracle(candidate: str) -> bool:
            nonlocal checked
            checked += 1
            return verify(candidate, meaning)

        if arm == "statement":
            result = store.recall_and_apply_verified(
                source_text=source, language="python", verifier=oracle, error_class="BOUNDARY")
            accepted = result is not None
        else:
            if arm == "operator":
                candidates = operator.propose_operator_swaps(source, rule)
            elif arm == "semantic":
                candidates = semantic.propose_semantic_swaps(
                    source, rule, operator_swaps=operator.propose_operator_swaps)
            else:
                raise ValueError("UNKNOWN_ARM")
            accepted = any(candidate != source and oracle(candidate) for candidate in candidates)
        rows.append({"case": name, "negative_control": name.startswith("negative_"),
                     "accepted": accepted, "candidates_checked": checked,
                     "elapsed_ms": round((time.perf_counter() - start) * 1000, 3)})
    return {"arm": arm, "cases": rows}


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        print(json.dumps(evaluate(Path(sys.argv[2]), sys.argv[3])))
        return 0
    if len(sys.argv) != 1:
        raise SystemExit("usage: python -m canonical.tools.shared_skill_transfer_benchmark_v1")
    with tempfile.TemporaryDirectory(prefix="brain_shared_skill_benchmark_") as tmp:
        db = Path(tmp) / "skills.sqlite"
        lesson = teach(db)
        if not lesson["admitted"]:
            raise RuntimeError("LESSON_NOT_ADMITTED")
        arms = []
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        for arm in ("statement", "operator", "semantic"):
            proc = subprocess.run(
                [sys.executable, "-m", "canonical.tools.shared_skill_transfer_benchmark_v1",
                 "--worker", str(db), arm],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=30, check=True,
            )
            arms.append(json.loads(proc.stdout))
        print(json.dumps({"schema": "BRAIN_SHARED_SKILL_TRANSFER_BENCHMARK_V1",
                          "scope": "one constructed Python boundary lesson; finite fixture oracles",
                          "qualification": lesson, "arms": arms}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
