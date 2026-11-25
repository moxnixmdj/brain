#!/usr/bin/env python3
"""The fabric census must be reproducible, cross-checkable, and its --check must gate the right thing.

`--check` exists so the dispatch surface cannot drift from the receipts while the pretty numbers stay
current. These tests pin both halves: the check fires when a certified row is fabricated, and it does
*not* fire over ordinary tree growth (that is what makes it survivable in CI).
"""
from __future__ import annotations

import ast
import json
import pathlib
import subprocess
import sys

from canonical.tools import capability_fabric_v1 as fab

ROOT = pathlib.Path(fab.ROOT)
COMMITTED = ROOT / "canonical/capabilities/CAPABILITY_FABRIC_V1.json"


def test_derivation_is_deterministic_and_free() -> None:
    a, b = fab.build(), fab.build()
    assert a["fabric_sha256_16"] == b["fabric_sha256_16"]
    assert a["model_calls"] == 0 and a["cost_usd"] == 0.0
    assert a["counts"]["modules"] > 5000
    # Fragmentation is the finding; if it ever stops being true, this is where the doc gets updated.
    assert a["counts"]["components"] > 1000
    assert a["counts"]["distinct_schema_constants"] > 1000
    assert a["counts"]["max_fan_out"] <= 25
    assert a["model_calls"] == 0 and a["cost_usd"] == 0.0, "a 5,901-module tree composing at fan-out >25 would contradict the census"


def _ast_guard_count() -> int:
    """Independent implementation: parse each file and look for the guard, instead of matching text."""
    n = 0
    for path in ROOT.glob("canonical/**/*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, ValueError):
            continue
        for node in tree.body:
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
                left, comps = node.test.left, node.test.comparators
                if (isinstance(left, ast.Name) and left.id == "__name__" and comps
                        and isinstance(comps[0], ast.Constant) and comps[0].value == "__main__"):
                    n += 1
                    break
    return n


def test_census_agrees_with_an_independent_ast_scan() -> None:
    """The tool matches a regex; this parses the files. Agreement is evidence about scan coverage,
    not a tautology -- a missed directory or a changed glob shows up here and nowhere else."""
    fabric = fab.build()
    guards = _ast_guard_count()
    assert abs(fabric["counts"]["runnable_entry_points"] - guards) <= guards * 0.05 + 2, (
        fabric["counts"]["runnable_entry_points"], guards
    )
    assert fabric["counts"]["modules_exposing_def_main"] < guards, (
        "most runnable modules do not expose main(): 'one entry point' must be counted as entry points"
    )
    # every module is classified exactly once, and the census covers the whole surface
    assert sum(fabric["reachability"].values()) == fabric["counts"]["modules"]
    assert fabric["counts"]["modules_with_no_internal_importer"] > 3000, (
        "the orphan count is the pruning target; if it ever reads small, the census is wrong or the "
        "tree got genuinely smaller -- either way, do not silently re-baseline the doc"
    )


def test_certified_rows_are_bound_to_real_files_and_receipts() -> None:
    fabric = fab.build()
    rows = fabric["certified_capabilities"]
    assert len(rows) >= 16
    for cap, r in rows.items():
        if r["class"] == "TRUE_CAPABILITY":
            assert r["receipt_present"] is True, cap
            assert (ROOT / r["receipt"]).is_file(), cap
            mod = r["entry_module"]
            assert mod and (ROOT / mod).is_file(), f"{cap}: entry module {mod} not in the tree"
            assert r["solver_blob"] and len(r["solver_blob"]) == 40, cap
            assert r["verdict"] == "PASS" and r["fresh_pass_rate"] == 1.0, cap
        else:
            # a family may be owned without a bound route; the fabric must say so rather than hide it
            assert "receipt_present" in r, cap
    families = [r for r in rows.values() if r["class"] == "FRONTIER_FAMILY"]
    assert len(families) == 7, "the matrix lists 7 VERIFIED_OWNED_EQUAL_OR_BETTER families"
    assert any(r["entry_module"] is None for r in families), "two families still have no bound route path"


def test_check_gates_the_dispatch_surface_and_survives_tree_growth(tmp_path: pathlib.Path) -> None:
    def check(payload: dict) -> int:
        f = tmp_path / "fabric.json"
        f.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(ROOT / "canonical/tools/capability_fabric_v1.py"), "--check", str(f)],
            capture_output=True, text=True, check=False,
        ).returncode

    real = json.loads(COMMITTED.read_text(encoding="utf-8"))
    assert check(real) == 0, "the committed fabric must match the tree right now"
    grown = json.loads(json.dumps(real))
    grown["counts"]["modules"] += 40  # an unrelated PR adds files: not a gate failure
    assert check(grown) == 0
    forged = json.loads(json.dumps(real))
    forged["certified_capabilities"]["INVENTED_CAPABILITY_V1"] = {"class": "TRUE_CAPABILITY", "verdict": "PASS"}
    assert check(forged) == 1, "a certified row with no receipt behind it must fail the check"
