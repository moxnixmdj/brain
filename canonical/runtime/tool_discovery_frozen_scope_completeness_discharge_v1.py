"""Zero-reality scope-semantics discharge for frozen Tool Discovery terminal target.

The independently verified formalism cut left exactly two admissible exits:
(1) prove that the pre-enumerated tool IDs are complete for the frozen target, or
(2) build and universally prove a complete discovery interface.

This module attempts route (1) from exact, content-addressed terminal evaluator
semantics. It grants no acceptance/family credit by itself.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_BLOBS = {
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":
        "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json":
        "ee187f611a0e82b2de495ee377682f39bc31dd31",
    "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json":
        "6bcabc0a7d0525532ce7b80e132278f7c99caa43",
    "canonical/runtime/tool_discovery_information_safe_proof.py":
        "2450a9644119c9fdf9c43307a1d115098d6ba592",
    "canonical/runtime/tool_discovery_information_safe_proof_v2.py":
        "5e8a953864e13ec76768c3e8920644107c65a644",
    "canonical/runtime/tool_discovery_information_safe_candidate.py":
        "64c02edd568d95ec5ed54b7b8122183ce5b82e17",
    "canonical/governance/TOOL_DISCOVERY_SCOPE_FORMALISM_CUT_ACTIVATION_V1.json":
        "48ba33998e73b8eec2731be51a7ec78077ed0d4a",
    "canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_FORMALISM_CUT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":
        "e628d8d5b63c2020400129fcc9e0bc6fde6101b2",
    "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json":
        "ec2d931860e7cd7d9f73a658706f8c33fca3a10d",
}

ATOM = (
    "INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_"
    "SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL"
)


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _json(rel: str) -> dict[str, Any]:
    value = json.loads(_text(rel))
    if not isinstance(value, dict):
        raise AssertionError(rel + ":NOT_OBJECT")
    return value


def _fn(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError("MISSING_FUNCTION:" + name)


def _case_tools(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "case"
        and isinstance(node.slice, ast.Constant)
        and node.slice.value == "tools"
    )


def _case_oracle(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "case"
        and isinstance(node.slice, ast.Constant)
        and node.slice.value == "_oracle"
    )


def derive_frozen_scope_facts(v1_text: str, v2_text: str) -> dict[str, bool]:
    v1 = ast.parse(v1_text)
    v2 = ast.parse(v2_text)

    public_stage = _fn(v1, "_public_stage")
    oracle_best = _fn(v1, "_oracle_best_tool")
    hidden_caps = _fn(v1, "_hidden_caps")
    v1_generate = _fn(v1, "generate_case")
    v2_generate = _fn(v2, "generate_case")

    public_returns_all_case_tools = False
    for node in ast.walk(public_stage):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and key.value == "tools":
                if isinstance(value, ast.ListComp) and any(_case_tools(x) for x in ast.walk(value)):
                    public_returns_all_case_tools = True

    oracle_ranges_over_same_case_tools = any(
        isinstance(node, ast.For) and _case_tools(node.iter)
        for node in ast.walk(oracle_best)
    )

    hidden_capability_truth_separate_from_public_tool_rows = any(
        _case_oracle(node) for node in ast.walk(hidden_caps)
    )

    v1_case_contains_tools_and_oracle = False
    for node in ast.walk(v1_generate):
        if not isinstance(node, ast.Dict):
            continue
        keys = {
            key.value for key in node.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        if {"tools", "_oracle"} <= keys:
            v1_case_contains_tools_and_oracle = True
            break

    v2_inherits_v1_case = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "v1"
        and node.func.attr == "generate_case"
        for node in ast.walk(v2_generate)
    )

    def _targets(node: ast.AST) -> list[ast.AST]:
        if isinstance(node, ast.Assign):
            return list(node.targets)
        if isinstance(node, ast.AnnAssign):
            return [node.target]
        if isinstance(node, ast.AugAssign):
            return [node.target]
        return []

    v2_replaces_tool_universe = any(
        any(_case_tools(x) for target in _targets(node) for x in ast.walk(target))
        for node in ast.walk(v2_generate)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
    )

    compact_v2 = "".join(v2_text.split())
    v2_uses_v1_public_boundary = (
        "returnv1.public_stage(case,stage,receipts)" in compact_v2
        or "public=v1._public_stage(case,stage,receipts)" in compact_v2
    )

    return {
        "V1_PUBLIC_EXPOSES_COMPLETE_CASE_TOOL_IDENTITY_LIST": public_returns_all_case_tools,
        "V1_ORACLE_RANGES_OVER_EXACT_SAME_CASE_TOOL_LIST": oracle_ranges_over_same_case_tools,
        "V1_HIDDEN_CAPABILITY_TRUTH_IS_SEPARATE_ORACLE_STATE": hidden_capability_truth_separate_from_public_tool_rows,
        "V1_CASE_BINDS_TOOLS_AND_HIDDEN_ORACLE_SEPARATELY": v1_case_contains_tools_and_oracle,
        "V2_INHERITS_V1_GENERATED_IDENTITY_UNIVERSE": v2_inherits_v1_case,
        "V2_DOES_NOT_REPLACE_GENERATED_TOOL_IDENTITY_UNIVERSE": not v2_replaces_tool_universe,
        "V2_REUSES_V1_PUBLIC_INFORMATION_BOUNDARY": v2_uses_v1_public_boundary,
    }


def evaluate() -> dict[str, Any]:
    drift = {
        rel: {"expected": expected, "actual": blob_sha(ROOT / rel)}
        for rel, expected in EXPECTED_BLOBS.items()
        if blob_sha(ROOT / rel) != expected
    }
    if drift:
        return {
            "status": "FAIL_CLOSED__SOURCE_BLOB_DRIFT__ZERO_CREDIT",
            "source_blob_drift": drift,
            "scope_semantics_discharged": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    protocol = _json("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
    family = next(
        row for row in protocol["protocols"]
        if row.get("family") == "TOOL_DISCOVERY_SELECTION_AND_LEARNING"
    )
    contract_registry = _json("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")

    def find_behavior(obj: Any) -> dict[str, Any] | None:
        if isinstance(obj, dict):
            if obj.get("behavior_id") == "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001":
                return obj
            for value in obj.values():
                got = find_behavior(value)
                if got is not None:
                    return got
        elif isinstance(obj, list):
            for value in obj:
                got = find_behavior(value)
                if got is not None:
                    return got
        return None

    behavior = find_behavior(contract_registry)
    assert behavior is not None

    binding = _json("canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json")
    cut = _json("canonical/governance/TOOL_DISCOVERY_SCOPE_FORMALISM_CUT_ACTIVATION_V1.json")
    prior = _json("canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_FORMALISM_CUT_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
    firewall = _json("canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json")

    facts = derive_frozen_scope_facts(
        _text("canonical/runtime/tool_discovery_information_safe_proof.py"),
        _text("canonical/runtime/tool_discovery_information_safe_proof_v2.py"),
    )
    missing = sorted(k for k, v in facts.items() if v is not True)

    target_bindings_ok = all([
        "unknown tool discovery" in family.get("task_dimensions", []),
        "frozen tool ecosystems with hidden capability variants" in family.get("acceptance", ""),
        "Held-out tool ecosystems with hidden capability variants" in behavior.get("verification_route", ""),
        "Discover candidate tools if needed" in behavior.get("required_output_or_action", ""),
        binding.get("exact_bound_blobs", {}).get("oracle", {}).get("blob_sha")
            == EXPECTED_BLOBS["canonical/runtime/tool_discovery_information_safe_proof_v2.py"],
        binding.get("exact_bound_blobs", {}).get("candidate", {}).get("blob_sha")
            == EXPECTED_BLOBS["canonical/runtime/tool_discovery_information_safe_candidate.py"],
        "TOOL_IDS_AND_DECLARED_COSTS"
            in binding.get("information_boundary", {}).get("candidate_visible", []),
        "ACTUAL_TOOL_CAPABILITY_MATRIX"
            in binding.get("information_boundary", {}).get("hidden_from_candidate", []),
        binding.get("source_pool", {}).get("terminal_scope_claim")
            == "DIRECT_OBJECTIVE_INSTRUMENTATION_INSIDE_T2_T3__NOT_EXHAUSTIVE_PROOF_OF_ALL_OPEN_DOMAIN_TOOL_ECOSYSTEMS",
        "PREENUMERATED_TOOL_IDS_ARE_COMPLETE_FOR_THE_FROZEN_TARGET"
            in cut.get("minimum_missing_fact", ""),
        prior.get("status", "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),
        "UNIVERSAL_FORMAL_SCOPE_PROOF"
            in firewall.get("admissible_absolute_dominance_bases", []),
    ])

    passed = target_bindings_ok and not missing
    return {
        "schema": "PROJECT_BRAIN_TOOL_DISCOVERY_FROZEN_SCOPE_COMPLETENESS_DISCHARGE_V1",
        "status": (
            "PASS__PREENUMERATED_TOOL_IDS_COMPLETE_FOR_EXACT_FROZEN_TARGET__"
            "SCOPE_SEMANTICS_DISCHARGED__INDEPENDENT_PUBLIC_RUNNER_REQUIRED__ZERO_CREDIT"
            if passed else
            "FAIL_CLOSED__FROZEN_SCOPE_COMPLETENESS_NOT_PROVED__ZERO_CREDIT"
        ),
        "scope_semantics_discharged": passed,
        "target_proof_atom": ATOM,
        "target_predicate": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "basis_kind": "EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
        "proof_domain": "EXACT_FROZEN_TOOL_DISCOVERY_TERMINAL_TARGET_ONLY",
        "target_bindings_ok": target_bindings_ok,
        "source_facts": facts,
        "missing_source_facts": missing,
        "deduction": {
            "identity_universe": (
                "For every exact frozen evaluator case, candidate-visible public state contains "
                "the entire case['tools'] list, and the oracle computes sufficiency over that same list."
            ),
            "hidden_dimension": (
                "Capability truth is stored separately in case['_oracle']; it is not hidden by omitting tool identities."
            ),
            "v2_preservation": (
                "The bound V2 evaluator inherits V1-generated cases and does not replace the tool identity universe."
            ),
            "scope_consequence": (
                "Therefore, within the exact frozen terminal target, unknownness is capability uncertainty over a "
                "complete pre-enumerated identity universe; unknown tool identities are outside this exact target."
            ),
        },
        "hard_nonclaims": [
            "NO_CLAIM_OF_EXHAUSTIVE_ALL_OPEN_DOMAIN_TOOL_ECOSYSTEMS",
            "NO_PROMOTION_OF_DYNAMIC_V3",
            "NO_NEW_TOOL_DISCOVERY_INTERFACE_ASSUMED",
            "NO_ACCEPTANCE_OR_FAMILY_CREDIT_BEFORE_INDEPENDENT_VERIFICATION_AND_SEPARATE_REDUCTION",
            "NO_TERMINAL_REPLAY",
            "NO_NEW_REALITY",
        ],
        "terminal_cases_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("scope_semantics_discharged") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
