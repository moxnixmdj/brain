"""Conditional refinement compiler for dynamic Tool Discovery.

This module answers a deliberately narrow terminal question:

Given the exact Brain-owned dynamic Tool Discovery policy and the frozen target
semantics, what environment contract is sufficient to remove the verified
"unknown tool identity" formalism gap?

It does not assert that any current environment satisfies that contract.  It
binds the program structure, frozen target literals, and the exact remaining
external fact.  Acceptance stays open until an independent verifier validates
these bytes and an independently verified interface instance satisfies the
contract.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_DYNAMIC_REFINEMENT_V1"

DYNAMIC = "canonical/runtime/tool_discovery_dynamic_candidate_v3.py"
PROTOCOL = "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
REGISTRY = "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
CUT = "canonical/governance/TOOL_DISCOVERY_SCOPE_FORMALISM_CUT_ACTIVATION_V1.json"
CONTRACT = "canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.json"

EXPECTED = {
    DYNAMIC: "bbbee4d6baf8df937543644397abba38a67dce62",
    PROTOCOL: "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    REGISTRY: "ee187f611a0e82b2de495ee377682f39bc31dd31",
    CUT: "48ba33998e73b8eec2731be51a7ec78077ed0d4a",
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

PRIOR_MINIMUM_MISSING_FACT = (
    "INDEPENDENT_EXACT_SCOPE_SEMANTICS_PROVING_PREENUMERATED_TOOL_IDS_ARE_COMPLETE_FOR_THE_FROZEN_TARGET__"
    "OR_A_VERIFIED_DISCOVERY_INTERFACE_AND_UNIVERSAL_PROOF_COVERING_UNKNOWN_TOOL_IDENTITIES"
)
REDUCED_EXTERNAL_FACT = (
    "INDEPENDENT_VERIFIED_COMPLETE_DISCOVERY_INTERFACE_INSTANCE_SATISFYING_"
    "TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1"
)


def _blob_sha(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path + ":NOT_OBJECT")
    return value


def _find(obj: Any, key: str, value: str) -> Mapping[str, Any] | None:
    if isinstance(obj, Mapping):
        if obj.get(key) == value:
            return obj
        for child in obj.values():
            found = _find(child, key, value)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for child in obj:
            found = _find(child, key, value)
            if found is not None:
                return found
    return None


def _action_literals(source: str) -> set[str]:
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


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "conditional_refinement_obligations_pass": False,
        "universal_target_proved": False,
        "minimum_missing_fact": REDUCED_EXTERNAL_FACT,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def evaluate(
    *,
    dynamic_source_override: str | None = None,
    interface_contract_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    drift = [path for path, sha in EXPECTED.items() if _blob_sha(path) != sha]
    if drift:
        return _fail(*["SOURCE_BLOB_DRIFT:" + x for x in drift])

    protocol = _load(PROTOCOL)
    registry = _load(REGISTRY)
    cut = _load(CUT)
    contract = (
        dict(interface_contract_override)
        if interface_contract_override is not None
        else _load(CONTRACT)
    )

    family = _find(protocol, "family", "TOOL_DISCOVERY_SELECTION_AND_LEARNING")
    behavior = _find(registry, "behavior_id", "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001")
    if family is None or behavior is None:
        return _fail("FROZEN_TOOL_DISCOVERY_TARGET_NOT_FOUND")

    target_literals = {
        "unknown_tool_discovery": "unknown tool discovery" in list(family.get("task_dimensions") or []),
        "discover_candidate_tools_if_needed": (
            "Discover candidate tools if needed"
            in str(behavior.get("required_output_or_action") or "")
        ),
        "scope": behavior.get("scope"),
    }
    if not target_literals["unknown_tool_discovery"]:
        return _fail("UNKNOWN_TOOL_DISCOVERY_LITERAL_MISSING")
    if not target_literals["discover_candidate_tools_if_needed"]:
        return _fail("DISCOVER_REQUIREMENT_LITERAL_MISSING")

    source = (
        dynamic_source_override
        if dynamic_source_override is not None
        else (ROOT / DYNAMIC).read_text(encoding="utf-8")
    )
    try:
        actions = _action_literals(source)
    except SyntaxError:
        return _fail("DYNAMIC_SOURCE_NOT_PARSEABLE")

    required_actions = {"DISCOVER", "PROBE", "SELECT", "ESCALATE"}
    missing_actions = sorted(required_actions - actions)
    if missing_actions:
        return _fail(*["DYNAMIC_ACTION_MISSING:" + x for x in missing_actions])

    structural_markers = {
        "visible_tools": 'public.get("visible_tools",[])' in source,
        "discovery_sources": 'public.get("discovery_sources",[])' in source,
        "discovery_receipts": 'public.get("discovery_receipts",[])' in source,
        "queried_filter": 'str(s.get("source_id") or "") not in queried' in source,
        "tool_cost_order": 'tools.sort(key=lambda t:(float(t.get("cost",0.0)),str(t.get("tool_id") or "")))' in source,
        "source_cost_order": 'sources.sort(key=lambda s:(float(s.get("cost",0.0)),str(s.get("source_id") or "")))' in source,
        "current_epoch_probe_filter": 'int(rec.get("epoch",-1))==epochs[tid]' in source,
    }
    if not all(structural_markers.values()):
        return _fail(*[
            "DYNAMIC_STRUCTURAL_MARKER_MISSING:" + key
            for key, ok in structural_markers.items()
            if not ok
        ])

    props = contract.get("required_properties")
    if (
        not isinstance(props, list)
        or any(not isinstance(x, str) or not x for x in props)
        or set(props) != REQUIRED_INTERFACE_PROPERTIES
    ):
        return _fail("INTERFACE_CONTRACT_PROPERTIES_NOT_EXACT")

    if contract.get("instance_verified") is not False:
        return _fail("CANDIDATE_CONTRACT_MUST_NOT_SELF_ASSERT_VERIFIED_INSTANCE")

    prior = cut.get("minimum_missing_fact")
    if prior != PRIOR_MINIMUM_MISSING_FACT:
        return _fail("FORMALISM_CUT_MINIMUM_FACT_DRIFT")

    proof_obligations = [
        {
            "id": "DISCOVERY_PROGRESS",
            "program_basis": "DISCOVER chooses only an available source not already present in discovery receipts.",
            "contract_basis": [
                "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH",
                "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE",
            ],
            "conditional_guarantee": (
                "Within a stable decision epoch, repeated successful DISCOVER transitions "
                "cannot query one source indefinitely; after at most the finite source count "
                "of receipt-advancing discoveries, no unqueried source remains."
            ),
        },
        {
            "id": "UNKNOWN_IDENTITY_COVERAGE",
            "program_basis": (
                "When no currently visible route is selectable/probeable, the policy emits "
                "DISCOVER before final ESCALATE while an unqueried available source remains."
            ),
            "contract_basis": [
                "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH",
                "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
            ],
            "conditional_guarantee": (
                "No admissible tool identity inside the declared target scope is missed solely "
                "because it was absent from the initial visible tool list."
            ),
        },
        {
            "id": "LEAST_COST_EVIDENCE_SUPPORTED_SELECTION",
            "program_basis": (
                "Visible admissible tools are ordered by declared cost then tool_id; known-false "
                "routes are skipped, unknown required capabilities are probed, and SELECT occurs "
                "only after current-epoch positive evidence covers all required capabilities."
            ),
            "contract_basis": [
                "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS",
                "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND",
                "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE",
            ],
            "conditional_guarantee": (
                "Across receipt-advancing calls in one stable epoch, the first selected route is "
                "the least-cost admissible route not falsified by truthful current-epoch evidence "
                "and positively evidenced for every required capability."
            ),
        },
        {
            "id": "SOUND_NO_ROUTE_ESCALATION",
            "program_basis": (
                "ESCALATE is reached only after the visible-tool loop produces neither PROBE nor "
                "SELECT and the available unqueried discovery-source list is empty."
            ),
            "contract_basis": sorted(REQUIRED_INTERFACE_PROPERTIES),
            "conditional_guarantee": (
                "Under a complete authoritative discovery interface and truthful probe metadata, "
                "NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_DISCOVERY is emitted only after the declared "
                "scope has no evidence-supported sufficient route."
            ),
        },
    ]

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CONDITIONAL_REFINEMENT_OBLIGATIONS_COMPILED__"
            "EXTERNAL_INTERFACE_INSTANCE_OPEN__ZERO_CREDIT"
        ),
        "errors": [],
        "source_blob_drift": [],
        "target_predicate": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "target_proof_atom": cut.get("target_proof_atom"),
        "target_preserved": True,
        "target_literals": target_literals,
        "dynamic_candidate": {
            "path": DYNAMIC,
            "actions": sorted(actions),
            "structural_markers": structural_markers,
        },
        "interface_contract": {
            "path": CONTRACT,
            "required_properties": sorted(REQUIRED_INTERFACE_PROPERTIES),
            "instance_verified": False,
        },
        "proof_obligations": proof_obligations,
        "conditional_refinement_obligations_pass": True,
        "universal_target_proved": False,
        "prior_minimum_missing_fact": PRIOR_MINIMUM_MISSING_FACT,
        "minimum_missing_fact": REDUCED_EXTERNAL_FACT,
        "residual_reduction": (
            "IF_THESE_EXACT_BYTES_ARE_INDEPENDENTLY_VERIFIED__THE_PROGRAM_SIDE_OF_THE_"
            "VERIFIED_TOOL_DISCOVERY_FORMALISM_GAP_IS_REDUCED_TO_ONE_EXTERNAL_INTERFACE_"
            "INSTANCE_FACT__NO_ACCEPTANCE_CREDIT"
        ),
        "causal_cut_candidate": {
            "effect": "SUPPLIES_IDENTIFIABILITY_INFORMATION",
            "primitive_fact_id": cut.get("target_proof_atom"),
            "blocker_id": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        },
        "hard_nonclaims": [
            "NO_CURRENT_DISCOVERY_SOURCE_IS_ASSERTED_COMPLETE",
            "NO_UNIVERSAL_SCOPE_CREDIT_FROM_THIS_CANDIDATE",
            "NO_ACCEPTANCE_CAPABILITY_FAMILY_EXECUTION_OR_PROMOTION_CREDIT",
            "NO_NEW_ACCEPTANCE_CASES_OR_TERMINAL_REPLAY",
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
    return 0 if str(out.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
