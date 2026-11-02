#!/usr/bin/env python3
"""Reproducible benchmark for PR-C2: TEST_SUITE-gated apply-time pattern narrowing.

Measures:
1. Stored lesson stays context-anchored (`pattern_tokens[0] == ['kw', 'return']`).
2. Cross-shape positive recall (`return`, `if`, `while`, `and`, `method`) lifts from
   `2/5` (context-anchored only) to `5/5` under `ProjectTestOracle` (`TEST_SUITE`),
   verified by an independent fresh-interpreter exhaustive grid audit.
3. Negative controls (`at_most`, `inclusive_loop`, `lower_bound`, `unrelated`) suffer
   `0/4` misapplications.
4. Weak verifiers (`CALLER_PREDICATE`, `SYNTAX`, `COMPILATION`) receive `0` broadened
   candidates (`weak_verifier_broadened_proposals == 0`).
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Any

_REPO_ROOT = str(pathlib.Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle
from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
    VerifiedSkillStore,
    apply_crystallized_code_rule,
)

SCHEMA = "PROJECT_BRAIN_PR_C2_APPLY_TIME_BROADENING_BENCHMARK_V1"

CONTRACT = {
    "schema_version": 1,
    "scope_id": "benchmark/prc2-exclusive-boundary/v1",
    "verification_kind": "TEST_SUITE",
    "dependencies": {"protocol": "1"},
    "preconditions": {"role": "boundary"},
}
CONTEXT = {"dependencies": {"protocol": "1"}, "preconditions": {"role": "boundary"}}

TEACH_BEFORE = "def within(x, hi):\n    return x <= hi\n"
TEACH_AFTER = "def within(x, hi):\n    return x < hi\n"

POSITIVE_SHAPES: dict[str, str] = {
    "return_stmt": "def target(x, hi):\n    return x <= hi\n",
    "if_stmt": "def target(x, hi):\n    if x <= hi:\n        return True\n    return False\n",
    "while_stmt": (
        "def target(x, hi):\n"
        "    cur = x\n"
        "    while cur <= hi:\n"
        "        return True\n"
        "    return False\n"
    ),
    "and_expr": "def target(x, hi):\n    return x >= -100 and x <= hi\n",
    "method_stmt": (
        "class Checker:\n"
        "    def ok(self, x, hi):\n"
        "        return x <= hi\n"
        "def target(x, hi):\n"
        "    return Checker().ok(x, hi)\n"
    ),
}

NEGATIVE_CONTROLS: dict[str, tuple[str, str]] = {
    "at_most": ("def target(x, hi):\n    return x <= hi\n", "x <= hi"),
    "inclusive_loop": (
        "def target(x, hi):\n    if x <= hi:\n        return True\n    return False\n",
        "x <= hi",
    ),
    "lower_bound": ("def target(x, hi):\n    return x >= 0 and x <= hi\n", "x >= 0 and x <= hi"),
    "unrelated": ("def target(x, hi):\n    return x + hi == 10\n", "x + hi == 10"),
}


def _write_project(root: pathlib.Path, source: str, expr: str, fn_name: str = "target") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "subject.py").write_text(source, encoding="utf-8")
    (root / "test_subject.py").write_text(
        "import unittest\n"
        f"from subject import {fn_name}\n"
        "class Checks(unittest.TestCase):\n"
        "    def test_boundary(self):\n"
        "        for x, hi in [(-3, -3), (-1, 0), (0, 0), (2, 3), (3, 3), (4, 3)]:\n"
        f"            self.assertEqual({fn_name}(x, hi), {expr})\n",
        encoding="utf-8",
    )


def _external_audit(root: pathlib.Path, expr: str) -> bool:
    code = (
        "import sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from subject import target\n"
        "for x in range(-20, 21):\n"
        "    for hi in range(-20, 21):\n"
        f"        assert target(x, hi) == ({expr})\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code, str(root)],
        capture_output=True,
        timeout=20,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )
    return proc.returncode == 0


def run_benchmark() -> dict[str, Any]:
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="brain_prc2_bench_") as td:
        base = pathlib.Path(td)
        train_dir = base / "train"
        _write_project(train_dir, TEACH_BEFORE, "x < hi", fn_name="within")

        store = VerifiedSkillStore(base / "skills.sqlite", seed=False)
        taught = store.crystallize_code_fix(
            before_snippet=TEACH_BEFORE,
            after_snippet=TEACH_AFTER,
            language="python",
            error_class="BOUNDARY",
            contract=CONTRACT,
            training_verifier=ProjectTestOracle(
                train_dir, "subject.py", ["test_subject.py"], CONTRACT["scope_id"]
            ),
        )
        rules = store.lookup_rules("python", "BOUNDARY")
        stored_rule = rules[0]
        stored_context_anchored = list(stored_rule["pattern_tokens"][0]) == ["kw", "return"]

        positives: dict[str, dict[str, Any]] = {}
        direct_hits = 0
        scoped_hits = 0
        for name, src in POSITIVE_SHAPES.items():
            direct_cand = apply_crystallized_code_rule(src, stored_rule)
            if direct_cand is not None:
                direct_hits += 1
            pdir = base / f"pos_{name}"
            excl_expr = "x >= -100 and x < hi" if name == "and_expr" else "x < hi"
            _write_project(pdir, src, excl_expr)
            oracle = ProjectTestOracle(
                pdir, "subject.py", ["test_subject.py"], CONTRACT["scope_id"]
            )
            hit = store.recall_and_apply_verified(
                source_text=src,
                language="python",
                error_class="BOUNDARY",
                verifier=oracle,
                required_verification_kind="TEST_SUITE",
                scope_id=CONTRACT["scope_id"],
                context=CONTEXT,
            )
            audit_ok = False
            if hit is not None:
                (pdir / "subject.py").write_text(str(hit["patched_source"]), encoding="utf-8")
                audit_ok = _external_audit(pdir, excl_expr)
                if audit_ok:
                    scoped_hits += 1
            positives[name] = {
                "direct_context_anchored_match": direct_cand is not None,
                "scoped_test_suite_hit": hit is not None,
                "recall_strategy": hit.get("recall_strategy") if hit else None,
                "scope_tier": hit.get("scope_tier") if hit else None,
                "external_audit_pass": audit_ok,
            }

        negatives: dict[str, dict[str, Any]] = {}
        misapplications = 0
        for name, (src, expr) in NEGATIVE_CONTROLS.items():
            ndir = base / f"neg_{name}"
            _write_project(ndir, src, expr)
            oracle = ProjectTestOracle(
                ndir, "subject.py", ["test_subject.py"], CONTRACT["scope_id"]
            )
            hit = store.recall_and_apply_verified(
                source_text=src,
                language="python",
                error_class="BOUNDARY",
                verifier=oracle,
                required_verification_kind="TEST_SUITE",
                scope_id=CONTRACT["scope_id"],
                context=CONTEXT,
            )
            if hit is not None:
                misapplications += 1
            negatives[name] = {
                "misapplied": hit is not None,
                "external_audit_preserved": _external_audit(ndir, expr),
            }

        # Weak-verifier negative control: CALLER_PREDICATE must NEVER see broadened proposals.
        weak_store = VerifiedSkillStore(base / "weak.sqlite", seed=False)
        weak_store.crystallize_code_fix(
            before_snippet=TEACH_BEFORE,
            after_snippet=TEACH_AFTER,
            language="python",
            error_class="BOUNDARY",
            twin_oracle=lambda cand: "<=" not in cand,
        )
        weak_seen: list[str] = []
        for shape_name in ("if_stmt", "while_stmt", "and_expr"):
            weak_store.recall_and_apply_verified(
                source_text=POSITIVE_SHAPES[shape_name],
                language="python",
                error_class="BOUNDARY",
                verifier=lambda cand: (weak_seen.append(cand), True)[1],
                required_verification_kind="CALLER_PREDICATE",
            )

        return {
            "schema": SCHEMA,
            "taught_crystallized": bool(taught.get("crystallized")),
            "stored_context_anchored": stored_context_anchored,
            "direct_recall_count": direct_hits,
            "scoped_test_suite_recall_count": scoped_hits,
            "positive_total": len(POSITIVE_SHAPES),
            "negative_control_misapplications": misapplications,
            "negative_total": len(NEGATIVE_CONTROLS),
            "weak_verifier_broadened_proposals": len(weak_seen),
            "positives": positives,
            "negatives": negatives,
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
            "authority": "NONE_SANDBOX_MEASUREMENT",
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }


def main() -> int:
    print(json.dumps(run_benchmark(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
