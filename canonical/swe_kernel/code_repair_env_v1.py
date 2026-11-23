#!/usr/bin/env python3
"""Code-repair drive: one demonstrated repair -> admitted rule -> replay on fresh defects.

This is the honest one-call end-to-end for the code-repair direction: the
Perfect Algorithm specialist twin for code-repair. It is NOT the scan-level
file-transform machinery; it is the demonstration-driven, gated specialist
path the repo's own gate built for that goal family, driven here as a single
honest flow.

What it does:
  1. learns ONE admitted rule from a single demonstrated (broken, fixed) pair;
  2. admits it ONLY on fresh, held-out defective variants (the admission gate);
  3. persists the admitted rule to the external, inspectable store;
  4. replays the rule on a fresh defect it was never taught on, honestly
     reported -- and executes the real repaired file against a real test when
     fresh_test_files is given;
  5. refuses honestly on zero held-out victims.

What it does NOT do: this is not the generic scan loop, and it does not claim
that the file-transform scan can close code-repair goals (§17 measured it
refuses).

Model calls: 0. Network: 0. Spend: $0.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import perfect_algorithm_v1 as pa

SCHEMA = "PROJECT_BRAIN_CODE_REPAIR_DRIVE_V1"
AUTHORITY = "NONE__SPECIALIST_PATH_ADMISSION_GATE"


def drive_code_repair(
    *,
    goal: str,
    demo_before: str,
    demo_after: str,
    victims: Sequence[Any],
    fresh_source: str,
    fresh_oracle: Callable[[str, Any], Any],
    fresh_probes: Sequence[Any],
    fresh_test_files: tuple[str, str] | None = None,
    memory_path_: str | Path | None = None,
    memory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The honest code-repair flow: one demonstrated lesson -> admitted rule ->
    replay on a fresh defect.

    demo_before/demo_after are the one demonstrated (broken, fixed) pair.
    victims are held-out defective variants the gate measures against -- the
    whole test. fresh_source is a never-taught defective source; the rule must
    fire and repair it. fresh_test_files, when given, is (module_name,
    test_src) -- the repaired file is materialized and the real test is run
    in a subprocess.
    """
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "goal": goal,
        "authority": AUTHORITY,
        "persisted": False,
        "replay": None,
        "fresh_real_test": None,
    }

    if not victims:
        out["schema"] = SCHEMA
        out["verdict"] = "REFUSED"
        out["reason"] = "NO_VICTIMS_OFFERED"
        out["authority"] = "NONE"
        return out

    mem = memory if memory is not None else pa.load_memory(memory_path_)
    teach = pa.learn_and_admit_code_repair(
        demo_before, demo_after, victims,
        memory=mem, memory_path_=memory_path_,
    )
    out["learn"] = {
        "verdict": teach.get("verdict"),
        "reason": teach.get("reason"),
        "persist": bool(teach.get("persist")),
        "rule_id": (teach.get("generalization") or {}).get("rule_id"),
        "counts": ((teach.get("gate") or {}).get("counts") or {}),
        "rule_kind": (teach.get("generalization") or {}).get("kind"),
    }
    if not teach.get("persist"):
        out["verdict"] = teach.get("verdict")
        out["reason"] = teach.get("reason")
        return out

    out["persisted"] = True
    rule = teach.get("rule") or {}
    out["verdict"] = teach.get("verdict")

    # ---- replay on a fresh, never-taught defect ----
    replay = pa.replay_code_repair(rule, fresh_source, fresh_oracle, fresh_probes)
    out["replay"] = {
        "verdict": replay.get("verdict"),
        "passed": bool(replay.get("passed")),
        "rule_fired": bool(replay.get("rule_fired")),
        "detail": replay.get("detail"),
        "repaired_source": replay.get("repaired_source"),
    }

    if fresh_test_files is not None and replay.get("repaired_source"):
        module_name, test_src = fresh_test_files
        tmp = Path(tempfile.mkdtemp(prefix="code_repair_drive_"))
        try:
            (tmp / f"{module_name}.py").write_text(str(replay["repaired_source"]))
            (tmp / "test_fresh.py").write_text(test_src)
            proc = subprocess.run([sys.executable, "test_fresh.py"],
                                  cwd=str(tmp), capture_output=True, text=True,
                                  timeout=15)
            out["fresh_real_test"] = {
                "module": module_name,
                "returncode": proc.returncode,
                "stdout": (proc.stdout or "").strip()[:200],
                "verified": proc.returncode == 0 and "PASS" in (proc.stdout or ""),
            }
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    out["authority"] = (
        AUTHORITY
        if out["fresh_real_test"] and out["fresh_real_test"]["verified"]
        else "NONE__SPECIALIST_PATH_ADMISSION_GATE_NO_REAL_EXECUTION"
    )
    return out
