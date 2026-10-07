"""Content-bound adapter from plain goals to the Brain's verified bound plan compiler.

This adapter reuses the mature goal_compiler + BOUND_CAPABILITY_REGISTRY pair only
when their exact Git blob IDs match the pinned audited versions. It compiles a
plain goal to a deterministic bound plan or fails closed.

A compiled plan is NOT execution, effect authorization, or task success. The
adapter intentionally emits execution_authority=False so the Universal Verified
Adaptive Solver may reason about a plan without inheriting ASTRA's wider effect
surface.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any

from canonical.runtime.goal_compiler import compile_goal, GoalCompilationFailure

SCHEMA = "PROJECT_BRAIN_BOUND_GOAL_PLAN_ADAPTER_V1"
ROOT = Path(__file__).resolve().parents[2]
GOAL_COMPILER_PATH = "canonical/runtime/goal_compiler.py"
GOAL_COMPILER_BLOB = "c895df9898bc97e4017f9e42bf6b27357ab1f315"
REGISTRY_PATH = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
REGISTRY_BLOB = "7badee4878700f2cd4176beb8319d2a6a0bdf782"


def _git_blob(data: bytes) -> str:
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _bound_bytes(path: str, expected: str) -> bytes:
    raw = (ROOT / path).read_bytes()
    actual = _git_blob(raw)
    if actual != expected:
        raise ValueError("BOUND_BLOB_DRIFT:" + path + ":" + actual)
    return raw


def compile_bound_goal(goal: str) -> dict[str, Any]:
    try:
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("GOAL_REQUIRED")
        _bound_bytes(GOAL_COMPILER_PATH, GOAL_COMPILER_BLOB)
        registry_raw = _bound_bytes(REGISTRY_PATH, REGISTRY_BLOB)
        registry_doc = json.loads(registry_raw.decode("utf-8"))
        if registry_doc.get("schema") != "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1":
            raise ValueError("BOUND_REGISTRY_SCHEMA_INVALID")
        registry = registry_doc.get("capabilities")
        if not isinstance(registry, dict) or not registry:
            raise ValueError("BOUND_REGISTRY_CAPABILITIES_INVALID")

        compiled = compile_goal(goal, registry, ROOT)
        raw = json.dumps(
            compiled,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return {
            "schema": SCHEMA,
            "status": "PASS__BOUND_GOAL_PLAN_COMPILED",
            "pass": True,
            "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            "compiled_plan_sha256": sha256(raw).hexdigest(),
            "compiled_plan": compiled,
            "goal_compiler_git_blob_sha": GOAL_COMPILER_BLOB,
            "bound_registry_git_blob_sha": REGISTRY_BLOB,
            "bound_capability_count": len(registry),
            "execution_authority": False,
            "terminal_authority": False,
            "boundary": (
                "PROVES_ONLY_DETERMINISTIC_COMPILATION_TO_THE_PINNED_BOUND_CAPABILITY_PLAN;"
                "DOES_NOT_EXECUTE_ACTIONS_AUTHORIZE_EFFECTS_OR_PROVE_TASK_SUCCESS"
            ),
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED" if isinstance(exc, GoalCompilationFailure) else "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "execution_authority": False,
            "terminal_authority": False,
        }
