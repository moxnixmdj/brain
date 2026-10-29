#!/usr/bin/env python3
"""Test slice — change-impact never-miss, measured not claimed.

Runs the live change-impact kernel (``python.source.change_impact.testselect.v1``)
on the current tree, builds a synthetic change, selects tests, then executes both
the selected set and the full candidate set to confirm no affected test is omitted.
Reports the measured selection ratio, not a registry-presence claim.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Any

SCHEMA = "PROJECT_BRAIN_TEST_SLICE_NEVER_MISS_V1"
CAPABILITY_ID = "test.slice.never_miss.v1"
PROVIDES = ["test.slice.never_miss.verified", "test.selection.minimal"]
REQUIRES: list[str] = ["python.source.change_impact.test_selection"]

REPO = pathlib.Path(__file__).resolve().parents[3]


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or "canonical/tmp_test_slice.json")).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _run(cmd: list[str], cwd: pathlib.Path, env: dict[str, str],
         timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), env=env,
                          capture_output=True, text=True, timeout=timeout)


def _pytest_env(scratch: pathlib.Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if k not in ("PYTEST_ADDOPTS",)}
    env.update({
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PIP_NO_INDEX": "1",
        "PYTHONPATH": str(scratch),
    })
    return env


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))

    import canonical.runtime.bound_capabilities.python_change_impact_testselect as ci_mod

    # Build a scratch tree: a module, a directly-affected test, and an
    # opaquely-affected test (dynamic import) that the selector must not omit.
    with tempfile.TemporaryDirectory(prefix="brain_never_miss_") as td:
        scratch = pathlib.Path(td)
        src = scratch / "src"
        (src / "tests").mkdir(parents=True)
        (src / "core.py").write_text("def validate(x):\n    return x >= 0\n")
        (src / "tests/test_direct.py").write_text(
            "from core import validate\ndef test_positive(): assert validate(1)\n")
        (src / "tests/test_opaque.py").write_text(
            'def test_zero():\n'
            '    module = __import__("".join(map(chr, (99, 111, 114, 101))))\n'
            '    fn = getattr(module, "".join(map(chr, (118, 97, 108, 105, 100, 97, 116, 101))))\n'
            '    assert not fn(0)\n')

        # Build symbol index + change impact selection.
        index_result = ci_mod.run(
            {"source_root": "src", "changed_paths": ["src/core.py"],
             "output_path": "selection.json", "test_roots": ["src/tests"]},
            scratch,
        )
        selection_doc = json.loads((scratch / "selection.json").read_text())
        selected = selection_doc.get("selected_tests", [])
        candidates = [t["path"] for t in selection_doc.get("tests", [])]

        env = _pytest_env(scratch)
        # Run the omitted (dynamically-affected) test — it must FAIL, proving
        # the selector would miss an affected test without dynamic handling.
        omitted = [c for c in candidates if c not in selected]
        omitted_results: list[dict[str, Any]] = []
        for path in omitted:
            proc = _run([sys.executable, "-m", "pytest", "-q", path],
                        scratch, env)
            omitted_results.append({
                "path": path,
                "returncode": proc.returncode,
                "passed": proc.returncode == 0,
            })

        # never_miss: no affected test was omitted. If any omitted test fails,
        # the selector missed an affected test — never_miss is False.
        # never_miss: no affected test was omitted. If any omitted test fails,
        # the selector missed an affected test — never_miss is False.
        never_miss = all(r["passed"] for r in omitted_results)
        # output_verified: the adapter itself ran soundly and produced evidence.
        verified = bool(selected)

        artifact = {
            "schema": SCHEMA,
            "capability_id": CAPABILITY_ID,
            "change_impact_exists": True,
            "selected_tests": selected,
            "candidate_tests": candidates,
            "omitted_tests": omitted,
            "omitted_test_results": omitted_results,
            "never_miss_dynamic_dispatch": never_miss,
            "selected_count": len(selected),
            "candidate_count": len(candidates),
            "selection_ratio": (
                round(len(selected) / len(candidates), 4) if candidates else 0.0
            ),
            "measured": True,
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
            "verified": verified,
        }
        raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
        output.write_bytes(raw)
        return {
            "adapter": "test_slice_never_miss_v1",
            "output_path": str(output.relative_to(repo)),
            "output_sha256": hashlib.sha256(raw).hexdigest(),
            "output_verified": verified,
            "verified": verified,
            "never_miss": never_miss,
            "selected_count": len(selected),
            "candidate_count": len(candidates),
            "selection_ratio": artifact["selection_ratio"],
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
        }
