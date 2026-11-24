#!/usr/bin/env python3
"""Unseen dynamic code-repair probe (2026-11-23).

Tests CodeRepairEnv with candidates=None (zero pre-declared candidate list,
zero model calls): the env must scan the real failing test traceback + AST,
derive minimal content-invariant repair candidates, and solve 4 distinct
defect classes (KeyError, ZeroDivisionError, IndexError, AssertionError).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import perfect_algorithm_v1 as pa
from canonical.swe_kernel.code_repair_scan_env_v1 import build_code_repair_env

CASES = [
    (
        "KeyError",
        "def get_timeout(cfg):\n    return cfg['timeout']\n",
        "from broken_module import get_timeout\nassert get_timeout({}) is None\nassert get_timeout({'timeout': 5}) == 5\n",
    ),
    (
        "ZeroDivisionError",
        "def safe_ratio(a, b):\n    return a / b\n",
        "from broken_module import safe_ratio\nassert safe_ratio(10, 0) == 0\nassert safe_ratio(10, 2) == 5\n",
    ),
    (
        "IndexError",
        "def safe_head(items):\n    return items[0]\n",
        "from broken_module import safe_head\nassert safe_head([]) is None\nassert safe_head([7]) == 7\n",
    ),
    (
        "AssertionError_cmp",
        "def is_adult(age):\n    return age > 18\n",
        "from broken_module import is_adult\nassert is_adult(18) is True\nassert is_adult(17) is False\n",
    ),
]


def main() -> int:
    passed = 0
    for name, broken, test_src in CASES:
        with tempfile.TemporaryDirectory() as td:
            env, meta = build_code_repair_env(broken, test_src, candidates=None, workdir=td)
            res = pa.run(
                env,
                goal=f"repair_{name}",
                actions=env.candidates,
                goal_predicate=meta["is_goal"],
                heuristic=meta["heuristic"],
                env_kind=meta["env_kind"],
                budget=16,
            )
            ok = str(res.get("status", "")).startswith("PASS")
            if ok:
                passed += 1
            print(f"{name:20s} status={res.get('status')} mode={res.get('mode')} candidates={len(env.candidates)}")
    print(f"TOTAL: {passed}/{len(CASES)}")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
