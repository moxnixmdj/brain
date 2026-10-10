from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

UNKNOWN_REUSE = ROOT / "canonical/governance/UNKNOWN_DOMAIN_TOOL_DISCOVERY_EXACT_BEHAVIOR_REUSE_REDUCTION_20261007_V1.json"
SEMANTIC_FRONTIER = ROOT / "canonical/governance/FIVE_PRIMITIVE_ROLE_SINGLE_SEMANTIC_FRONTIER_20261007_V1.json"
REGISTRY = ROOT / "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
SPEC_EVIDENCE = ROOT / "canonical/capabilities/opus55/INDEPENDENT_ACCEPTANCE_MODEL_EVIDENCE_V1.json"
RESEARCH_VERIFICATION = ROOT / "canonical/verification/T3_RESEARCH_CONTROL_MULTIPLEX_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"

EXPECTED = {
    UNKNOWN_REUSE: "c197bb4a6b2b21177cd568698ec0a2112727b623",
    SEMANTIC_FRONTIER: "eb316b0a674a3542280c71706fffe850d22e44fa",
    REGISTRY: "ee187f611a0e82b2de495ee377682f39bc31dd31",
    SPEC_EVIDENCE: "800ea1db458ff585431c2efb5dd7b503647b3d28",
    RESEARCH_VERIFICATION: "c747c719b20b16ec847f224f2a860ef86fb193ca",
}

RESIDUAL = {
    "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001",
    "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001",
}

EXPECTED_ROLE_PROJECTION = {
    "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001": {
        "B1_GOAL_CONSTRAINT_SCOPE_AND_JUDGMENT",
        "B2_INFORMATION_TRANSFORMATION_REASONING_AND_PROBLEM_SOLVING",
    },
    "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001": {
        "B1_GOAL_CONSTRAINT_SCOPE_AND_JUDGMENT",
        "B2_INFORMATION_TRANSFORMATION_REASONING_AND_PROBLEM_SOLVING",
        "B4_EXTERNAL_ACTION_PLANNING_AND_ENVIRONMENT_CONTROL",
    },
}


def git_blob(path: Path) -> str:
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        return ""
    cp = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", f"HEAD:{rel}"],
        text=True,
        capture_output=True,
        check=False,
    )
    return cp.stdout.strip() if cp.returncode == 0 else ""


def project() -> dict:
    errors: list[str] = []

    for path, expected in EXPECTED.items():
        if git_blob(path) != expected:
            errors.append("SOURCE_DRIFT:" + path.name)

    unknown = json.loads(UNKNOWN_REUSE.read_text(encoding="utf-8"))
    sem = json.loads(SEMANTIC_FRONTIER.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    spec = json.loads(SPEC_EVIDENCE.read_text(encoding="utf-8"))
    research = json.loads(RESEARCH_VERIFICATION.read_text(encoding="utf-8"))

    residual = set(unknown["theorem"]["residual_required_behaviors_after"])
    if residual != RESIDUAL:
        errors.append("UNKNOWN_DOMAIN_RESIDUAL_DRIFT")

    contracts = {
        row["behavior_id"]: row
        for row in registry["active_contracted_residuals"]
        if row["behavior_id"] in RESIDUAL
    }
    if set(contracts) != RESIDUAL:
        errors.append("REQUIRED_BEHAVIOR_CONTRACT_MISSING")

    role_projection = sem["role_projection"]
    for behavior_id, roles in EXPECTED_ROLE_PROJECTION.items():
        for role in roles:
            if role not in role_projection:
                errors.append(f"SEMANTIC_ROLE_MISSING:{behavior_id}:{role}")

    common = sem["shared_frontier"]["representation"]
    if "TASK_CONDITIONED_STOCHASTIC_TRACE_POLICY" not in common:
        errors.append("SHARED_TRACE_POLICY_FRONTIER_MISSING")
    if sem["shared_frontier"]["generic_new_implementation_generator_required"] is not False:
        errors.append("GENERIC_IMPLEMENTATION_HUNT_REOPENED")

    if "WHOLE_SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001" not in set(spec["not_owned"]):
        errors.append("SPEC_ACCEPTANCE_NONOWNERSHIP_BOUNDARY_DRIFT")
    if research["execution_authority"] is not False:
        errors.append("RESEARCH_PREWAVE_EXECUTION_AUTHORITY_DRIFT")
    if research["terminal_results_observed"] != 0:
        errors.append("RESEARCH_TERMINAL_RESULT_BOUNDARY_DRIFT")

    spec_output = contracts["SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001"]["required_output_or_action"]
    research_output = contracts["ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001"]["required_output_or_action"]

    for token in ("acceptance", "counterexamples"):
        if token not in spec_output.lower():
            errors.append("SPEC_OUTPUT_SEMANTIC_TOKEN_MISSING:" + token)
    for token in ("query", "stop", "evidence requirement"):
        if token not in research_output.lower():
            errors.append("RESEARCH_OUTPUT_SEMANTIC_TOKEN_MISSING:" + token)

    ok = not errors
    return {
        "schema": "PROJECT_BRAIN_UNKNOWN_DOMAIN_TWO_BEHAVIOR_SHARED_SEMANTIC_FRONTIER_REDUCTION_V1",
        "status": (
            "PASS__TWO_UNKNOWN_DOMAIN_BEHAVIOR_OUTPUTS_PROJECT_TO_ONE_SHARED_SEMANTIC_FRONTIER__TWO_SEPARATE_ACCEPTANCE_OBLIGATIONS_REMAIN__ZERO_CREDIT"
            if ok else
            "FAIL_CLOSED"
        ),
        "pass": ok,
        "errors": errors,
        "residual_behaviors": sorted(RESIDUAL),
        "residual_behavior_count": 2,
        "shared_generic_semantic_frontier_count": 1 if ok else None,
        "duplicate_generic_mechanism_hunts_deleted": 1 if ok else None,
        "whole_behavior_acceptance_obligations_remaining": 2,
        "specification_acceptance_explicitly_not_owned": True,
        "research_control_current_terminal_result_absent": True,
        "terminal_closed": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(project(), indent=2, sort_keys=True))
