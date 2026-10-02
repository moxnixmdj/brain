"""Route-specific terminal executor for the frozen CAD T0 128-slot population.

This module composes only already-frozen components:
- post-freeze deterministic population generator,
- source-only Brain candidate,
- hidden evaluator oracle adapter,
- information-safe multiplex scorer.

It creates no beacon and grants no capability/family credit. Callers must supply
the frozen candidate-package commitment and a post-freeze beacon.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from canonical.runtime import cad_t0_geometry_population as population
from canonical.runtime import cad_t0_oracle_adapter as oracle
from canonical.runtime import cad_t0_multiplex_scorer as scorer
from canonical.runtime import cad_t0_route_specific_candidate_v1 as candidate

SCHEMA = "PROJECT_BRAIN_CAD_T0_ROUTE_SPECIFIC_TERMINAL_EXECUTOR_V1"
BEHAVIOR_ID = "CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001"
COUNT = 128

DEPENDENCIES = {
    "canonical/runtime/cad_t0_route_specific_candidate_v1.py": "aa32750b220a023617938b7be9476f6b3aac6704",
    "canonical/runtime/cad_t0_geometry_population.py": "64ca276410e2c1dbcd55cfad057e3eec0709790a",
    "canonical/runtime/cad_t0_oracle_adapter.py": "a6e76e1865b9bd9829dbbcf38886486636f76e8a",
    "canonical/runtime/cad_t0_multiplex_scorer.py": "89833581dc4ac67498753feb94e2ff69bad3b7f1",
    "canonical/governance/CAD_T0_POST_REFREEZE_BINDING_V4.json": "a636d1292e6f92d240fab420a9ee75ced7a05104",
}


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\\0" + data).hexdigest()


def static_dependency_preflight(root: Path = Path(".")) -> dict[str, Any]:
    errors = []
    rows = {}
    for rel, expected in sorted(DEPENDENCIES.items()):
        path = root / rel
        if not path.is_file():
            errors.append("DEPENDENCY_MISSING:" + rel)
            rows[rel] = {"exists": False, "expected_blob": expected}
            continue
        actual = _git_blob_sha(path)
        ok = actual == expected
        if not ok:
            errors.append("DEPENDENCY_BLOB_DRIFT:" + rel)
        rows[rel] = {
            "exists": True,
            "expected_blob": expected,
            "actual_blob": actual,
            "match": ok,
        }
    binding_path = root / "canonical/governance/CAD_T0_POST_REFREEZE_BINDING_V4.json"
    try:
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append("CAD_BINDING_READ:" + type(exc).__name__)
        binding = {}
    if binding.get("behavior_id") != BEHAVIOR_ID:
        errors.append("CAD_BINDING_BEHAVIOR_ID_MISMATCH")
    if binding.get("prewave_admissible") is not True:
        errors.append("CAD_BINDING_NOT_PREWAVE_ADMISSIBLE")
    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "dependencies": rows,
        "errors": errors,
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def _require(value: str, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(name + "_REQUIRED")
    return value


def run_case(hidden_case: dict[str, Any]) -> dict[str, Any]:
    public = population.public_case(hidden_case)
    try:
        candidate_out, result = candidate.solve_with_result(public)
        prepared = oracle.prepare_hidden_case(hidden_case)
        observation = oracle.observe_candidate(prepared, candidate_out, result)
        verdict = scorer.score_case(prepared, candidate_out, observation)
        passed = verdict.get("pass") is True
        reason = None if passed else ";".join(verdict.get("errors") or ["CAD_SCORE_FAIL"])
    except Exception as exc:
        candidate_out = {}
        verdict = {"pass": False}
        passed = False
        reason = "EXCEPTION:" + type(exc).__name__ + ":" + str(exc)
    family = None
    hidden_oracle = hidden_case.get("_oracle")
    if isinstance(hidden_oracle, dict):
        family = hidden_oracle.get("family")
    return {
        "case_id": hidden_case.get("case_id"),
        "family": family,
        "pass": passed,
        "reason": reason,
        "candidate_hidden_oracle_present": "_oracle" in candidate_out,
    }


def execute_cad_route(*, commitment: str, beacon: str, root: Path = Path(".")) -> dict[str, Any]:
    _require(commitment, "COMMITMENT")
    _require(beacon, "BEACON")
    preflight = static_dependency_preflight(root)
    if not preflight["pass"]:
        return {
            "schema": SCHEMA,
            "behavior_id": BEHAVIOR_ID,
            "status": "FAIL_CLOSED_PREEXECUTION",
            "pass": False,
            "preflight": preflight,
            "case_count": 0,
            "terminal_result": False,
            "no_case_replacement": True,
            "no_tuning_replay": True,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    try:
        authority = json.loads((root / "canonical/governance/TERMINAL_WAVE_EXECUTION_AUTHORITY_V1.json").read_text(encoding="utf-8"))
        manifest = json.loads((root / "canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "schema": SCHEMA, "behavior_id": BEHAVIOR_ID,
            "status": "FAIL_CLOSED_AUTHORITY_READ", "pass": False,
            "error": type(exc).__name__, "case_count": 0,
            "terminal_result": False, "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }
    if authority.get("execution_authority") is not True or manifest.get("launch_authority") is not True or manifest.get("bound_executor_count") != 12:
        return {
            "schema": SCHEMA, "behavior_id": BEHAVIOR_ID,
            "status": "FAIL_CLOSED_LAUNCH_NOT_AUTHORIZED", "pass": False,
            "case_count": 0, "terminal_result": False,
            "execution_authority": bool(authority.get("execution_authority")),
            "launch_authority": bool(manifest.get("launch_authority")),
            "bound_executor_count": manifest.get("bound_executor_count"),
            "capability_credit_delta": 0, "family_credit_delta": 0,
        }

    cases = population.generate_post_freeze(commitment, beacon)
    if len(cases) != COUNT:
        raise RuntimeError("FROZEN_POPULATION_COUNT_MISMATCH")
    rows = [run_case(case) for case in cases]
    leaked = [row for row in rows if row["candidate_hidden_oracle_present"]]
    passed = sum(int(row["pass"]) for row in rows)
    families = Counter(str(row["family"]) for row in rows)
    ok = passed == COUNT and not leaked and set(families) == set(population.FAMILIES)
    return {
        "schema": SCHEMA,
        "behavior_id": BEHAVIOR_ID,
        "status": "PASS" if ok else "FAIL_CLOSED",
        "population_version": population.SCHEMA,
        "case_count": COUNT,
        "pass_count": passed,
        "failed_count": COUNT - passed,
        "pass": ok,
        "family_counts": dict(sorted(families.items())),
        "cases": rows,
        "candidate_hidden_oracle_leak_count": len(leaked),
        "no_case_replacement": True,
        "no_tuning_replay": True,
        "terminal_result": True,
        "capability_credit_delta": "DEFER_TO_TERMINAL_REDUCER",
        "family_credit_delta": "DEFER_TO_TERMINAL_REDUCER",
    }
