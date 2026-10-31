"""Search-based unit-test synthesis (Pynguin) as a bound capability.

Harvest: Pynguin (0.57.x, pip-installable, pure OSS) -- whole-suite
test generation with search-based input synthesis and harvested
assertions. The mutation gate proves WHICH code survives tests; this
capability is the generator side of the "kill every survivor" loop.

Contract:
  - synthesizes tests for every module under source_root (or module_name)
  - executes the generated suite against the real module as the verdict
    (tests_generated, tests_execute, execute_returncode) -- a suite that
    cannot run is NOT a synthesis, it is text
  - artifact records the pynguin statistics path and per-file counts

Both subprocess callsites are pinned SWE_TOOL_STEP sites (pynguin CLI,
unittest discovery) -- the same mediation every tool family runs under.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from typing import Any

SCHEMA = "PROJECT_BRAIN_PYTHON_TESTS_SYNTHESIZE_PYNGUIN_V1"
CAPABILITY_ID = "python.tests.synthesize.pynguin.v1"
REPO = pathlib.Path(__file__).resolve().parents[3]


class SynthesizeError(RuntimeError):
    pass


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    src = (repo / str(args.get("source_root") or "")).resolve()
    if repo not in src.parents or not src.is_dir():
        raise SynthesizeError("SOURCE_ROOT_NOT_DIRECTORY_UNDER_REPO")
    out_dir = src / "_pynguin_tests"
    out_dir.mkdir(parents=True, exist_ok=True)
    module_name = str(args.get("module_name") or "")
    if not module_name:
        mods = [p.stem for p in sorted(src.glob("*.py"))
                if p.name != "__init__.py"
                and not p.name.startswith("test_")]
        if not mods:
            raise SynthesizeError("NO_TARGET_MODULE")
        module_name = mods[0]
    budget = max(5, min(int(args.get("time_budget_s", 20)), 120))

    out_rel = str(out_dir.relative_to(repo))
    src_rel = str(src.relative_to(repo))
    # MOSA: many-objective search explicitly targeting branch coverage -- on
    # modules with hard-to-reach functions the default random search plateaued
    # at the easy functions and never touched the rest (measured: appended
    # helper got zero calls under RANDOM, 7 under MOSA, same wall clock).
    pynguin_argv = [
        sys.executable, "-m", "pynguin",
        "--project-path", src_rel,
        "--module-name", module_name,
        "--output-path", out_rel,
        "--maximum-search-time", str(budget),
        "--algorithm", str(args.get("algorithm") or "MOSA"),
        "--seed", str(args.get("search_seed") or 20261029),
    ]
    env = dict(os.environ)
    env["PYNGUIN_DANGER_AWARE"] = "true"
    proc = subprocess.run(
        pynguin_argv, cwd=str(repo), text=True, capture_output=True,
        timeout=budget + 90, env=env)
    pynguin_rc = proc.returncode
    pynguin_tail = ((proc.stdout or "") + "\n" + (proc.stderr or ""))[-800:]

    generated = sorted(out_dir.glob("test_*.py"))
    execute_rc = None
    discover_tail = ""
    if generated:
        # The generated suite MUST execute against the real module: that run
        # is the verdict. Discovery from the repo with the source dir on the
        # path mirrors how the repair loops run their suites.
        venv = dict(os.environ)
        # ABSOLUTE: the validation cwd is out_dir, so a relative entry would
        # resolve against the wrong directory
        venv["PYTHONPATH"] = os.pathsep.join(
            [str(src)] + ([venv["PYTHONPATH"]] if venv.get("PYTHONPATH") else []))
        # Discovery runs from INSIDE the output dir with -t . : unittest
        # requires every package level between repo root and the start dir to
        # be importable otherwise (Start directory is not importable), and the
        # generated tests import the target module via PYTHONPATH anyway.
        vproc = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-v",
             "-s", ".", "-t", "."],
            cwd=str(out_dir), text=True, capture_output=True,
            timeout=max(30, budget), env=venv)
        execute_rc = vproc.returncode
        discover_tail = ((vproc.stdout or "") + "\n"
                         + (vproc.stderr or ""))[-800:]

    tests_generated = len(generated)
    executed = tests_generated > 0 and execute_rc == 0
    artifact = {
        "schema": SCHEMA, "capability_id": CAPABILITY_ID,
        "module_name": module_name,
        "pynguin_returncode": pynguin_rc,
        "pynguin_tail": pynguin_tail,
        "tests_generated": tests_generated,
        "tests_execute": executed,
        "execute_returncode": execute_rc,
        "execute_tail": discover_tail,
        "output_dir": out_rel,
        "verified": bool(executed),
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
    output = (repo / str(args.get("output_path")
                         or "canonical/tmp_pynguin_report.json")).resolve()
    if output == repo or repo not in output.parents:
        raise SynthesizeError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(json.dumps(artifact, sort_keys=True,
                                  separators=(",", ":")).encode())
    return {"adapter": "python_tests_synthesize_pynguin_v1",
            "capability_id": CAPABILITY_ID,
            "output_path": str(output.relative_to(repo)),
            "output_sha256": __import__("hashlib").sha256(
                output.read_bytes()).hexdigest(),
            "output_verified": True,
            "verified": bool(executed),
            "tests_generated": tests_generated,
            "tests_execute": executed,
            "model_dependency_count": 0, "incremental_spend_usd": 0}
