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
        "AttributeError",
        "def get_name(user):\n    return user.name\n",
        "class U:\n    name = 'ada'\nfrom broken_module import get_name\nassert get_name(None) is None\nassert get_name(U()) == 'ada'\n",
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

    # Held-out cross-variable transfer test using generalized ast_rule:subscript_to_get
    train_src = "def get_timeout(cfg):\n    return cfg['timeout']\n"
    train_test = "from broken_module import get_timeout\nassert get_timeout({}) is None\nassert get_timeout({'timeout': 5}) == 5\n"
    heldout_src = "def read_port(settings):\n    return settings['port']\n"
    heldout_test = "from broken_module import read_port\nassert read_port({}) is None\nassert read_port({'port': 8080}) == 8080\n"

    with tempfile.TemporaryDirectory() as td_mem, tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
        mem_path = Path(td_mem) / "mem.json"
        env1, meta1 = build_code_repair_env(train_src, train_test, candidates=None, workdir=td1)
        res1 = pa.run(
            env1,
            goal="repair_KeyError_generalized",
            actions=env1.candidates,
            goal_predicate=meta1["is_goal"],
            heuristic=meta1["heuristic"],
            env_kind=meta1["env_kind"],
            memory_path_=mem_path,
            budget=8,
        )
        env2, meta2 = build_code_repair_env(heldout_src, heldout_test, candidates=None, workdir=td2)
        res2 = pa.run(
            env2,
            goal="repair_KeyError_generalized",
            actions=env2.candidates,
            goal_predicate=meta2["is_goal"],
            heuristic=meta2["heuristic"],
            env_kind=meta2["env_kind"],
            memory_path_=mem_path,
            budget=8,
        )
        xfer_ok = str(res1.get("status", "")).startswith("PASS") and str(res2.get("status", "")).startswith("PASS")
        print(f"HELDOUT_XFER         status={res2.get('status')} cands1={env1.candidates} cands2={env2.candidates} xfer_ok={xfer_ok}")
    return 0 if (passed == len(CASES) and xfer_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
