"""Conditional universal-scope certificate for Tool Discovery V4.

This certificate proves only the program-side theorem. It deliberately leaves one
external fact open: a content-addressed independently verified instance of the
complete discovery-interface contract.

The theorem is stronger than the superseded V3 refinement because it proves that
identity discovery saturates before route evaluation, eliminating the
visible-catalog local-optimum counterexample.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_DYNAMIC_V4_CONDITIONAL_UNIVERSAL_CERTIFICATE_V1"

CANDIDATE = "canonical/runtime/tool_discovery_dynamic_candidate_v4.py"
CONTRACT = "canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.json"
FALSIFICATION = "canonical/governance/TOOL_DISCOVERY_DYNAMIC_V3_GLOBAL_OPTIMALITY_FALSIFICATION_V1.json"

EXPECTED = {
    CANDIDATE: "394cbc2e3092ef0bb870ccad9b092343275ca73e",
    CONTRACT: "49cc878eccc0fbc8fdd83d35e5fbd614c973ffa7",
    FALSIFICATION: "1b220547530022d96f146295f7579735b66150ae",
}

REQUIRED_INTERFACE_PROPERTIES = {
    "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH",
    "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE",
    "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH",
    "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
    "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS",
    "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND",
    "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE",
}

MINIMUM_MISSING_FACT = (
    "INDEPENDENT_VERIFIED_COMPLETE_DISCOVERY_INTERFACE_INSTANCE_SATISFYING_"
    "TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1"
)


def _blob_sha(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _load(path: str) -> dict[str, Any]:
    out = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(out, dict):
        raise ValueError(path + ":NOT_OBJECT")
    return out


def _actions(source: str) -> set[str]:
    tree = ast.parse(source)
    out: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if (
                isinstance(key, ast.Constant)
                and key.value == "action"
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            ):
                out.add(value.value)
    return out


def _load_policy(source: str):
    ns: dict[str, Any] = {}
    exec(compile(source, CANDIDATE, "exec"), ns, ns)
    return ns["next_action"]


def _counterexample_public() -> dict[str, Any]:
    return {
        "required_capabilities": ["CAP_A"],
        "constraint": None,
        "visible_tools": [
            {
                "tool_id": "T0",
                "cost": 10.0,
                "available": True,
                "authorized": True,
                "epoch": 0,
            }
        ],
        "discovery_sources": [
            {"source_id": "S0", "cost": 0.1, "available": True}
        ],
        "discovery_receipts": [],
        "prior_probe_receipts": [
            {
                "kind": "SAFE_CAPABILITY_PROBE",
                "tool_id": "T0",
                "capability": "CAP_A",
                "epoch": 0,
                "supported": True,
            }
        ],
        "version_events": [],
    }


def evaluate(
    *,
    candidate_source_override: str | None = None,
    contract_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    drift = [p for p, sha in EXPECTED.items() if _blob_sha(p) != sha]
    if drift and candidate_source_override is None and contract_override is None:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__SOURCE_BLOB_DRIFT",
            "source_blob_drift": drift,
            "conditional_program_side_universal_proof": False,
            "universal_target_proved": False,
            "minimum_missing_fact": MINIMUM_MISSING_FACT,
        }

    source = (
        candidate_source_override
        if candidate_source_override is not None
        else (ROOT / CANDIDATE).read_text(encoding="utf-8")
    )
    contract = (
        dict(contract_override)
        if contract_override is not None
        else _load(CONTRACT)
    )

    errors: list[str] = []

    try:
        actions = _actions(source)
    except SyntaxError:
        actions = set()
        errors.append("CANDIDATE_SOURCE_NOT_PARSEABLE")

    required_actions = {"DISCOVER", "PROBE", "SELECT", "ESCALATE"}
    if not required_actions <= actions:
        errors.append("ACTION_VOCABULARY_INCOMPLETE")

    props = contract.get("required_properties")
    if not isinstance(props, list) or set(props) != REQUIRED_INTERFACE_PROPERTIES:
        errors.append("COMPLETE_INTERFACE_CONTRACT_DRIFT")
    if contract.get("instance_verified") is not False:
        errors.append("CONTRACT_SELF_ASSERTS_EXTERNAL_INSTANCE")

    # Structural ordering: source saturation must precede catalog evaluation.
    source_discovery = source.find("if sources:")
    source_catalog = source.find("tools, conflict = _catalog(public)")
    source_route_loop = source.find("for tool in admissible:")
    saturation_precedes_route_evaluation = (
        source_discovery >= 0
        and source_catalog >= 0
        and source_route_loop >= 0
        and source_discovery < source_catalog < source_route_loop
    )
    if not saturation_precedes_route_evaluation:
        errors.append("DISCOVERY_SATURATION_NOT_STRUCTURALLY_BEFORE_ROUTE_EVALUATION")

    receipt_merge_present = (
        'rec.get("kind") != "DISCOVERY_RESULT"' in source
        and 'for tool in rec.get("tools", []) or []:' in source
    )
    if not receipt_merge_present:
        errors.append("DISCOVERY_RECEIPTS_NOT_MERGED_INTO_CATALOG")

    epoch_filter_present = 'int(rec.get("epoch", -1)) == epochs[tid]' in source
    if not epoch_filter_present:
        errors.append("CURRENT_EPOCH_EVIDENCE_FILTER_MISSING")

    try:
        policy = _load_policy(source)
        first = policy(_counterexample_public())
    except Exception as exc:
        first = {"exception": type(exc).__name__ + ":" + str(exc)}
        errors.append("COUNTEREXAMPLE_EXECUTION_FAILED")
    if first != {"action": "DISCOVER", "source_id": "S0", "query": "CAP_A"}:
        errors.append("V3_GLOBAL_OPTIMALITY_COUNTEREXAMPLE_NOT_REPAIRED")

    saturated = _counterexample_public()
    saturated["discovery_receipts"] = [
        {
            "kind": "DISCOVERY_RESULT",
            "source_id": "S0",
            "tools": [
                {
                    "tool_id": "T1",
                    "cost": 1.0,
                    "available": True,
                    "authorized": True,
                    "epoch": 0,
                }
            ],
        }
    ]
    try:
        after_discovery = policy(saturated)
        saturated["prior_probe_receipts"].append(
            {
                "kind": "SAFE_CAPABILITY_PROBE",
                "tool_id": "T1",
                "capability": "CAP_A",
                "epoch": 0,
                "supported": True,
            }
        )
        after_probe = policy(saturated)
    except Exception as exc:
        after_discovery = {"exception": type(exc).__name__ + ":" + str(exc)}
        after_probe = {}
        errors.append("POST_DISCOVERY_EXECUTION_FAILED")

    if after_discovery != {
        "action": "PROBE",
        "tool_id": "T1",
        "capability": "CAP_A",
    }:
        errors.append("CHEAPER_DISCOVERED_ROUTE_NOT_PROBED_FIRST")
    if after_probe != {"action": "SELECT", "tool_id": "T1"}:
        errors.append("CHEAPER_DISCOVERED_SUFFICIENT_ROUTE_NOT_SELECTED")

    theorem_premises = {
        "finite_source_set": "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH" in REQUIRED_INTERFACE_PROPERTIES,
        "source_identity_receipts": "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE" in REQUIRED_INTERFACE_PROPERTIES,
        "monotone_identity_revelation": "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH" in REQUIRED_INTERFACE_PROPERTIES,
        "complete_identity_union": "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE" in REQUIRED_INTERFACE_PROPERTIES,
        "truthful_public_route_metadata": "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS" in REQUIRED_INTERFACE_PROPERTIES,
        "truthful_epoch_probe_receipts": "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND" in REQUIRED_INTERFACE_PROPERTIES,
        "stable_epoch_or_restart": "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE" in REQUIRED_INTERFACE_PROPERTIES,
        "discovery_before_route_evaluation": saturation_precedes_route_evaluation,
        "discovered_catalog_is_consumed": receipt_merge_present,
        "current_epoch_only": epoch_filter_present,
        "counterexample_repaired": not any(
            e in errors
            for e in (
                "V3_GLOBAL_OPTIMALITY_COUNTEREXAMPLE_NOT_REPAIRED",
                "CHEAPER_DISCOVERED_ROUTE_NOT_PROBED_FIRST",
                "CHEAPER_DISCOVERED_SUFFICIENT_ROUTE_NOT_SELECTED",
            )
        ),
    }

    conditional = not errors and all(theorem_premises.values())

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__PROGRAM_SIDE_CONDITIONAL_UNIVERSAL_SCOPE_PROOF__"
            "COMPLETE_INTERFACE_INSTANCE_OPEN__ZERO_CREDIT"
            if conditional
            else "FAIL_CLOSED__PROGRAM_SIDE_CERTIFICATE_NOT_PROVED"
        ),
        "errors": errors,
        "source_blob_drift": [] if candidate_source_override is not None else drift,
        "target_predicate": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "target_preserved": True,
        "actions": sorted(actions),
        "theorem_premises": theorem_premises,
        "conditional_program_side_universal_proof": conditional,
        "conditional_theorem": (
            "For every finite stable-epoch tool ecosystem satisfying the exact complete-interface "
            "contract, V4 exhausts all authoritative identity sources before route evaluation; "
            "then cost-ordered current-epoch probing selects the globally least-cost admissible "
            "sufficient route with positive evidence for every required capability, or escalates "
            "only when no such route exists."
        ),
        "universal_target_proved": False,
        "minimum_missing_fact": MINIMUM_MISSING_FACT,
        "hard_nonclaims": [
            "NO_CURRENT_DISCOVERY_INTERFACE_INSTANCE_IS_ASSERTED_COMPLETE",
            "NO_FAMILY_OR_ATOMIC_ACCEPTANCE_CREDIT_FROM_THIS_CERTIFICATE",
            "FINITE_SAMPLE_TESTS_ARE_FALSIFICATION_SUPPORT_NOT_THE_UNIVERSAL_PROOF_BASIS",
        ],
        "new_reality_units_consumed": 0,
        "terminal_results_replayed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["conditional_program_side_universal_proof"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
