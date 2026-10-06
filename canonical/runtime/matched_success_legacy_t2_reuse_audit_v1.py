from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "canonical/governance/MATCHED_SUCCESS_LEGACY_T2_REUSE_AUDIT_V1.json"

SOURCE_BLOBS = {
    "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json": "72a5cd689f55df84de73693371264f02ef4e7226",
    "canonical/governance/MATCHED_SUCCESS_SCOPE_COMPILER_V1.json": "2e344ccaa611cda7764d4d70557f1e5bdec9cf3c",
    "canonical/governance/BROWSER_T2_OBJECTIVE_TERMINAL_BINDING_V1.json": "28e955d5d593d1de9cfab0f9cdcdae732fd315f1",
    "canonical/governance/DELEGATION_T2_OBJECTIVE_TERMINAL_BINDING_V1.json": "a1e441567b132d71713ed55dfc51f01d8de112d1",
    "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json": "6bcabc0a7d0525532ce7b80e132278f7c99caa43",
    "canonical/governance/M0_PORTFOLIO_MULTIPLEX_TERMINAL_BINDING_V1.json": "d34a284f7c1f99fd93d420f3a5aba93851b29ef6",
    "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json": "8703c6aa08227467a619a7ae90d0d61f8e54da39",
    "canonical/governance/TERMINAL_PARENT_PORTFOLIO_RUNNER_BINDING_V1.json": "a1630299d29ea9c07e55b4314c07ddb3228c3287",
    "canonical/runtime/terminal_parent_portfolio_runner_v1.py": "431b62e503a6a179f19339ae5e0ab6948424a650",
}

EVIDENCE_SOURCE = {
    "STALE_REBIND": "canonical/governance/BROWSER_T2_OBJECTIVE_TERMINAL_BINDING_V1.json",
    "FRESH_STATE_CONDITIONING": "canonical/governance/BROWSER_T2_OBJECTIVE_TERMINAL_BINDING_V1.json",
    "V2_WORKER_CAPABILITY_REMOVED": "canonical/governance/DELEGATION_T2_OBJECTIVE_TERMINAL_BINDING_V1.json",
    "V2_RESOURCE_CAPACITY_CHANGED": "canonical/governance/DELEGATION_T2_OBJECTIVE_TERMINAL_BINDING_V1.json",
    "SELECTED_TOOL_LOSES_CAPABILITY": "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json",
    "CHEAPER_TOOL_GAINS_CAPABILITY": "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json",
    "OBSERVABLE_MISMATCH_RECOVERY": "canonical/governance/BROWSER_T2_OBJECTIVE_TERMINAL_BINDING_V1.json",
    "CHEAPER_TOOL_UNAVAILABLE": "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json",
    "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE": "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json",
    "DEPENDENCY_RESPECTING_FANOUT_FANIN": "canonical/governance/DELEGATION_T2_OBJECTIVE_TERMINAL_BINDING_V1.json",
    "V3_FORK_JOIN": "canonical/governance/DELEGATION_T2_OBJECTIVE_TERMINAL_BINDING_V1.json",
    "V3_FANOUT_JOIN": "canonical/governance/DELEGATION_T2_OBJECTIVE_TERMINAL_BINDING_V1.json",
    "V3_DUAL_ROOT_FANIN": "canonical/governance/DELEGATION_T2_OBJECTIVE_TERMINAL_BINDING_V1.json",
    "ACTIVE_CONSTRAINT_ADMISSIBILITY": "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json",
    "CHEAPER_TOOL_UNAUTHORIZED": "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json",
    "AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT": "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json",
    "AMBIGUOUS": "canonical/governance/BROWSER_T2_OBJECTIVE_TERMINAL_BINDING_V1.json",
    "AMBIGUITY_IS_PRESERVED_RATHER_THAN_GUESSED": "canonical/governance/M0_PORTFOLIO_MULTIPLEX_TERMINAL_BINDING_V1.json",
    "NO_SUFFICIENT_ROUTE": "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json",
    "CORRECT_NO_ROUTE_ESCALATION": "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json",
}


def blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def evaluate() -> dict:
    errors = []
    for path, expected in SOURCE_BLOBS.items():
        actual = blob(path)
        if actual != expected:
            errors.append("SOURCE_BLOB_DRIFT:" + path + ":" + actual)

    gov = json.loads(GOV.read_text())
    norm = json.loads((ROOT / "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json").read_text())
    all_atoms = {
        src["atom"]
        for target in norm["targets"]
        if target["predicate_id"] in {
            "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
            "IF_SCOPE_BOUNDARY_NONINFERIOR",
            "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
        }
        for src in target["atom_sources"]
        if src["atom"].startswith("dimension:")
    }

    supported = set(gov["direct_legacy_substrate_witnesses"])
    missing = set(gov["missing_from_unchanged_legacy_t2"])

    if supported & missing:
        errors.append("SUPPORTED_MISSING_OVERLAP")
    if supported | missing != all_atoms:
        errors.append("DIMENSION_PARTITION_NOT_EXACT")
    if len(all_atoms) != 16 or len(supported) != 6 or len(missing) != 10:
        errors.append("DIMENSION_COUNTS_DRIFT")

    source_text = {
        path: (ROOT / path).read_text()
        for path in set(EVIDENCE_SOURCE.values())
    }
    for atom, row in gov["direct_legacy_substrate_witnesses"].items():
        if atom not in all_atoms:
            errors.append("UNKNOWN_SUPPORTED_ATOM:" + atom)
        for token in row["evidence"]:
            source = EVIDENCE_SOURCE.get(token)
            if source is None:
                errors.append("UNBOUND_EVIDENCE_TOKEN:" + token)
            elif token not in source_text[source]:
                errors.append("EVIDENCE_TOKEN_NOT_IN_BOUND_SOURCE:" + token)

    runner = (ROOT / "canonical/runtime/terminal_parent_portfolio_runner_v1.py").read_text()
    runner_binding = json.loads((ROOT / "canonical/governance/TERMINAL_PARENT_PORTFOLIO_RUNNER_BINDING_V1.json").read_text())
    if "component_results = {" not in runner or "parent_pass = bool(component_results) and all(" not in runner:
        errors.append("PARENT_RUNNER_COMPONENT_AND_STRUCTURE_DRIFT")
    if "FOR_EACH_PORTFOLIO__RUN_EACH_BOUND_MULTIPLEX_BEHAVIOR_ON_ITS_FROZEN_ROUTE_SPECIFIC_SCHEDULE__COMPUTE_PARENT_TERMINAL_ACCEPTANCE_AS_AND_OF_ALL_LOAD_BEARING_MULTIPLEX_COMPONENTS" not in runner_binding.get("parent_portfolio_rule", ""):
        errors.append("PARENT_RUNNER_BINDING_RULE_DRIFT")

    result = gov["reuse_result"]
    if result["legacy_t2_unchanged_is_scope_superset"] is not False:
        errors.append("SCOPE_SUPERSET_OVERCLAIM")
    if result["consumed_terminal_v3_results_reused_for_new_acceptance"] is not False:
        errors.append("CONSUMED_RESULT_REUSE_OVERCLAIM")
    if gov["fresh_reality_authority"] is not False:
        errors.append("FRESH_REALITY_OVERCLAIM")

    ok = not errors
    return {
        "schema": "PROJECT_BRAIN_MATCHED_SUCCESS_LEGACY_T2_REUSE_AUDIT_VERIFIER_V1",
        "status": "PASS__6_REUSABLE_SUBSTRATE_DIMENSIONS__10_INTEGRATED_DIMENSIONS_OPEN__ZERO_CREDIT" if ok else "FAIL_CLOSED",
        "pass": ok,
        "errors": sorted(errors),
        "normalized_dimension_count": len(all_atoms) if ok else None,
        "reusable_substrate_dimension_count": len(supported) if ok else None,
        "integrated_extension_dimension_count": len(missing) if ok else None,
        "legacy_t2_unchanged_is_scope_superset": False,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
    raise SystemExit(0 if evaluate()["pass"] else 1)
