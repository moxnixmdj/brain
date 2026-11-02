"""A shared bounded comparison, with executable checks and negative controls."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from canonical.tools import shared_skill_transfer_benchmark_v1 as bench

ROOT = Path(__file__).resolve().parents[2]


def test_oracles_check_the_declared_semantics_and_avoid_accepting_the_bug():
    for name, (source, meaning) in bench.CASES.items():
        assert bench.verify(source, meaning) is (name == "negative_inclusive")
    assert bench.verify("def target(x, hi):\n    return x < hi\n", "exclusive")
    assert not bench.verify("def target(x, hi):\n    return x <= hi\n", "exclusive")


def test_shared_comparison_uses_a_fresh_store_and_refuses_negative_control(tmp_path):
    # This environment variable names the usual store; the benchmark must not use it.
    caller_db = tmp_path / "caller.sqlite"
    caller_db.write_bytes(b"caller-owned file")
    env = dict(os.environ, BRAIN_SKILL_STORE_PATH=str(caller_db))
    proc = subprocess.run(
        [sys.executable, "-m", "canonical.tools.shared_skill_transfer_benchmark_v1"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=30, check=True,
    )
    assert caller_db.read_bytes() == b"caller-owned file"
    report = json.loads(proc.stdout)
    assert report["qualification"]["admitted"] is True
    assert {arm["arm"] for arm in report["arms"]} == {"statement", "operator", "semantic"}
    for arm in report["arms"]:
        rows = {row["case"]: row for row in arm["cases"]}
        assert set(rows) == set(bench.CASES)
        assert rows["renamed"]["accepted"] is True
        assert rows["negative_inclusive"]["accepted"] is False
        assert rows["negative_inclusive"]["candidates_checked"] > 0
        assert all(row["elapsed_ms"] >= 0 for row in rows.values())
