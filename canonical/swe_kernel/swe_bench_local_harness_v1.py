#!/usr/bin/env python3
"""Honest Local SWE Harness (`swe_bench_local_harness_v1`).

What this is
------------
A measurable, un-gated baseline for the K3=0 SWE instrument, runnable with no
Docker, no network, no model, and no benchmark data download. It exists because
"progress" was previously unmeasurable locally: container benchmarks need Docker
(absent in this sandbox) and the gated sets need credentials, so every claim about
improvement had to be taken on faith from a report.

What this is NOT
----------------
Not SWE-bench Pro, not Terminal-Bench, not OSWorld. Those remain the real tests
(§6) and are still blocked here: `docker: command not found`. This harness
measures the mechanisms those benchmarks exercise -- read a repair off a failing
run, generalise it, keep it, recall it, refuse a fake -- on tasks we control.

Every task is a real repository on disk with a real failing test suite. Nothing
is stubbed. Every result is produced by `UnifiedModel.solve_swe_repo_native`, the
same front door a user calls.

Two ablations are mandatory per §6:
  * memory: store present vs store empty (does the store carry the capability?)
  * generality: generalised morphism vs raw trace (does abstraction add transfer?)

Usage
-----
    python3 -m canonical.swe_kernel.swe_bench_local_harness_v1 [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "SWE_BENCH_LOCAL_HARNESS_V1"
AUTHORITY = "NONE_SANDBOX"

# --------------------------------------------------------------------------------------
# Task fixtures. Each is (name, files, test_targets, candidate_files, held_out_variant)
# --------------------------------------------------------------------------------------

def _repo(root: pathlib.Path, files: Mapping[str, str]) -> pathlib.Path:
    root.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return root


TASKS: tuple[dict[str, Any], ...] = (
    {
        "id": "BINOP_INVERT",
        "why": "the classic: the failing assertion's own operands invert the operators",
        "files": {
            "calc.py": "def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n",
            "test_calc.py": "from calc import add, mul\n\n\ndef test_add():\n    assert add(2, 3) == 5\n\n\ndef test_mul():\n    assert mul(2, 3) == 6\n",
        },
        "tests": ["test_calc.py"],
        "candidates": ["calc.py"],
        "proposer": None,
        "expect_file_contains": "a + b",
    },
    {
        "id": "GUARD_NONE_FALLBACK",
        "why": "multi-statement guard + attribute access; needs a real fallback, not a literal",
        "files": {
            "mod.py": 'def get_name(user):\n    if user is None:\n        return None\n    return user["name"]\n',
            "test_mod.py": 'from mod import get_name\n\n\ndef test_none():\n    assert get_name(None) == ""\n\n\ndef test_ok():\n    assert get_name({"name": "bob"}) == "bob"\n',
        },
        "tests": ["test_mod.py"],
        "candidates": ["mod.py"],
        "proposer": "CORRECT_GUARD_FALLBACK",
        "expect_file_contains": ".get(",
    },
)

#: The held-out variant used for single-experience transfer. Different function name,
#: different parameter name, different key -- same law.
HELD_OUT = {
    "id": "HELD_OUT_DIFFERENT_VOCABULARY",
    "why": "same law, renamed everything: proves the morphism generalised identifiers and keys",
    "files": {
        "people.py": 'def read_nickname(rec):\n    if rec is None:\n        return None\n    return rec["nick"]\n',
        "test_people.py": 'from people import read_nickname\n\n\ndef test_missing():\n    assert read_nickname(None) == ""\n\n\ndef test_present():\n    assert read_nickname({"nick": "ada"}) == "ada"\n',
    },
    "tests": ["test_people.py"],
    "candidates": ["people.py"],
    "proposer": None,          # deliberately none: the store must carry it
    "expect_file_contains": ".get(",
}

PROPOSERS: dict[str, Callable[[Mapping[str, Any]], Sequence[Mapping[str, str]]]] = {
    # A stand-in for the only thing a proposer is allowed to be: an untrusted generator.
    # Its output is verified, admitted, or rejected exactly like anything else.
    "CORRECT_GUARD_FALLBACK": lambda packet: [
        {"mod.py": 'def get_name(user):\n    return (user or {}).get("name", "")\n'}
    ],
    # The overfit patch that shipped on 2026-11-26 before the admission gate existed.
    "OVERFIT_LITERAL": lambda packet: [
        {"mod.py": 'def get_name(user):\n    return ((user or "") and "bob")\n'}
    ],
}


def _run_task(
    task: Mapping[str, Any],
    *,
    workdir: pathlib.Path,
    store_path: pathlib.Path,
    proposer: Any = None,
    model: Any = None,
) -> dict[str, Any]:
    root = _repo(workdir / task["id"].lower(), task["files"])
    t0 = time.perf_counter()
    res = model.solve_swe_repo_native(
        str(root),
        test_targets=list(task["tests"]),
        candidate_files=list(task["candidates"]),
        keep_patch_applied=True,
        timeout_s=30.0,
        residual_proposer=proposer,
        skill_store_path=str(store_path),
    )
    elapsed = round(time.perf_counter() - t0, 3)
    swe = res.get("swe_result") or {}
    patched = "".join(
        (root / rel).read_text(encoding="utf-8", errors="replace")
        for rel in task.get("candidates") or []
    )
    # Independent re-verification: the harness does not trust the engine's own status.
    from canonical.swe_kernel.canonical_swe_spine_v1 import _honest_suite_verdict

    ok_now, _out = _honest_suite_verdict(root, list(task["tests"]), timeout_s=20.0)
    expected = task.get("expect_file_contains")
    return {
        "task": task["id"],
        "status": res.get("status"),
        "tier": swe.get("tier"),
        "pass_reported": bool(res.get("pass")),
        "pass_independently_verified": bool(ok_now),
        "expect_shape_present": bool(expected is None or expected in patched),
        "learned_skill_id": swe.get("learned_skill_id"),
        "recalled_morphism_id": swe.get("recalled_morphism_id"),
        "model_calls": int(swe.get("model_calls") or 0),
        "elapsed_s": elapsed,
    }


def run(*, json_out: str | None = None) -> dict[str, Any]:
    from canonical.runtime.brain_unified_model_v1 import open_model

    model = open_model()
    base = pathlib.Path(tempfile.mkdtemp(prefix="swe_harness_"))
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "not_the_real_benchmarks": [
            "SWE_BENCH_PRO_V2_NOT_RUN__DOCKER_UNAVAILABLE",
            "TERMINAL_BENCH_4_NOT_RUN__DOCKER_UNAVAILABLE",
            "OSWORLD_2_1_NOT_RUN__NO_DISPLAY_AND_NO_DOCKER",
        ],
        "model_digest": (model.status() or {}).get("model_digest"),
        "model_counts": (model.status() or {}).get("counts"),
        "arms": {},
    }

    # ---- Arm 1: empty store, no proposer. The cold-start floor. -------------------------
    empty_store = base / "empty_store.json"
    report["arms"]["EMPTY_STORE_NO_PROPOSER"] = {
        task["id"]: _run_task(task, workdir=base / "arm1", store_path=empty_store, model=model)
        for task in TASKS
    }
    # Helped-out task with an empty store: there is nothing to recall, so this must fail.
    report["arms"]["EMPTY_STORE_NO_PROPOSER"][HELD_OUT["id"]] = _run_task(
        HELD_OUT, workdir=base / "arm1", store_path=empty_store, model=model
    )

    # ---- Arm 2: seeded store, no proposer. Single-experience transfer. -----------------
    seeded_store = base / "seeded_store.json"
    teach = _run_task(
        TASKS[1], workdir=base / "arm2_teach", store_path=seeded_store,
        proposer=PROPOSERS["CORRECT_GUARD_FALLBACK"], model=model,
    )
    report["arms"]["SEEDED_STORE_NO_PROPOSER"] = {
        "TEACH_GUARD_NONE_FALLBACK": teach,
        HELD_OUT["id"]: _run_task(HELD_OUT, workdir=base / "arm2", store_path=seeded_store, model=model),
    }

    # ---- Arm 3: the overfit patch, with and without the admission gate. ---------------
    report["arms"]["OVERFIT_LITERAL_ADMISSION"] = {
        "GUARD_NONE_FALLBACK": _run_task(
            TASKS[1], workdir=base / "arm3", store_path=base / "arm3_store.json",
            proposer=PROPOSERS["OVERFIT_LITERAL"], model=model,
        )
    }

    # ---- Summary ----------------------------------------------------------------------
    def _passes(arm: str) -> int:
        return sum(1 for r in report["arms"][arm].values() if r["pass_independently_verified"])

    report["summary"] = {
        "arms": {
            arm: {
                "tasks": len(rows),
                "independently_verified_passes": _passes(arm),
                "total_model_calls": sum(r["model_calls"] for r in rows.values()),
            }
            for arm, rows in report["arms"].items()
        },
        "ablations": {
            "memory_empty_vs_seeded_transfer": {
                "empty_store_held_out_pass": report["arms"]["EMPTY_STORE_NO_PROPOSER"][HELD_OUT["id"]]["pass_independently_verified"],
                "seeded_store_held_out_pass": report["arms"]["SEEDED_STORE_NO_PROPOSER"][HELD_OUT["id"]]["pass_independently_verified"],
                "reading": "If these differ, the store carried the capability and nothing else did.",
            },
            "admission_gate": {
                "overfit_patch_status": report["arms"]["OVERFIT_LITERAL_ADMISSION"]["GUARD_NONE_FALLBACK"]["status"],
                "overfit_patch_verified": report["arms"]["OVERFIT_LITERAL_ADMISSION"]["GUARD_NONE_FALLBACK"]["pass_independently_verified"],
                "reading": "A suite-green patch that hardcodes the witness must be refused, not shipped.",
            },
        },
    }
    if json_out:
        pathlib.Path(json_out).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    shutil.rmtree(base, ignore_errors=True)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", dest="json_out", default=None)
    args = ap.parse_args(argv)
    rep = run(json_out=args.json_out)
    print(json.dumps(rep, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
