"""Zero-reality formalism cut for tool-discovery universal scope completeness.

This checker does not claim the Brain lacks tool discovery in general. It asks a
narrower question required by the current absolute-dominance repair:

Can the exact terminal-bound policy, together with the exact frozen target
semantics, support a UNIVERSAL_FORMAL_SCOPE_PROOF for the family phrase
"unknown tool discovery"?

The answer must fail closed when the frozen target does not prove that its
unknown-tool dimension is restricted to hidden capabilities over a complete,
pre-enumerated tool-id set, while the bound policy has no discovery action.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_UNIVERSAL_SCOPE_FORMALISM_VERDICT_V1"

PROTOCOL = "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
REGISTRY = "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
BINDING = "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json"
CANDIDATE = "canonical/runtime/tool_discovery_information_safe_candidate.py"
DYNAMIC = "canonical/runtime/tool_discovery_dynamic_candidate_v3.py"
FIREWALL = "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json"

EXPECTED = {
    PROTOCOL: "eb4bca0fe6a015d49d2854998fbe046c979c7ea9",
    REGISTRY: "ee187f611a0e82b2de495ee377682f39bc31dd31",
    BINDING: "6bcabc0a7d0525532ce7b80e132278f7c99caa43",
    CANDIDATE: "64c02edd568d95ec5ed54b7b8122183ce5b82e17",
    DYNAMIC: "bbbee4d6baf8df937543644397abba38a67dce62",
    FIREWALL: "ec2d931860e7cd7d9f73a658706f8c33fca3a10d",
}


def _blob_sha(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path + ":NOT_OBJECT")
    return value


def _find_behavior(obj: Any, behavior_id: str) -> Mapping[str, Any] | None:
    if isinstance(obj, Mapping):
        if obj.get("behavior_id") == behavior_id:
            return obj
        for value in obj.values():
            got = _find_behavior(value, behavior_id)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for value in obj:
            got = _find_behavior(value, behavior_id)
            if got is not None:
                return got
    return None


def _action_literals(path: str) -> set[str]:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == "action":
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        out.add(value.value)
    return out


def evaluate() -> dict[str, Any]:
    drift = [p for p, expected in EXPECTED.items() if _blob_sha(p) != expected]

    protocol = _load(PROTOCOL)
    registry = _load(REGISTRY)
    binding = _load(BINDING)
    firewall = _load(FIREWALL)

    family = next(
        (
            row for row in protocol.get("protocols", [])
            if isinstance(row, Mapping)
            and row.get("family") == "TOOL_DISCOVERY_SELECTION_AND_LEARNING"
        ),
        None,
    )
    behavior = _find_behavior(registry, "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001")

    task_dimensions = list((family or {}).get("task_dimensions") or [])
    unknown_tool_literal = "unknown tool discovery" in task_dimensions

    required_output = str((behavior or {}).get("required_output_or_action") or "")
    contract_requires_discover = "Discover candidate tools if needed" in required_output

    visible = list(((binding.get("information_boundary") or {}).get("candidate_visible") or []))
    preenumerated_ids_visible = "TOOL_IDS_AND_DECLARED_COSTS" in visible

    candidate_actions = _action_literals(CANDIDATE)
    dynamic_actions = _action_literals(DYNAMIC)

    terminal_has_discover = "DISCOVER" in candidate_actions
    broader_candidate_has_discover = "DISCOVER" in dynamic_actions

    binding_text = json.dumps(binding, sort_keys=True)
    target_text = json.dumps(family or {}, sort_keys=True) + json.dumps(behavior or {}, sort_keys=True)

    complete_tool_universe_explicit = any(
        literal in binding_text or literal in target_text
        for literal in (
            "COMPLETE_TOOL_UNIVERSE",
            "ALL_TARGET_TOOL_IDS_PREENUMERATED",
            "EXHAUSTIVE_TOOL_ID_SET",
            "UNKNOWN_TOOL_DISCOVERY_MEANS_HIDDEN_CAPABILITY_ONLY",
        )
    )

    admissible_bases = set(firewall.get("admissible_absolute_dominance_bases") or [])
    firewall_requires_universal_or_exhaustive = {
        "EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
        "EXHAUSTIVE_FINITE_SUPERSET",
        "UNIVERSAL_FORMAL_SCOPE_PROOF",
    } <= admissible_bases

    inputs_valid = (
        not drift
        and family is not None
        and behavior is not None
        and unknown_tool_literal
        and contract_requires_discover
        and preenumerated_ids_visible
        and firewall_requires_universal_or_exhaustive
    )

    formalism_gap = (
        inputs_valid
        and not terminal_has_discover
        and not complete_tool_universe_explicit
    )

    if drift or not inputs_valid:
        status = "FAIL_CLOSED__SOURCE_OR_FORMALIZATION_DRIFT__ZERO_CREDIT"
        classification = "INVALID_INPUT_OR_AUTHORITY_DRIFT"
    elif formalism_gap:
        status = (
            "FAIL_CLOSED__UNIVERSAL_SCOPE_CERTIFICATE_BLOCKED_BY_"
            "UNKNOWN_TOOL_IDENTITY_DISCOVERY_FORMALISM_GAP__ZERO_CREDIT"
        )
        classification = "SPECIFICATION_OR_FORMALISM_RESIDUAL"
    else:
        status = "OPEN__UNIVERSAL_SCOPE_FORMALISM_GAP_NOT_ESTABLISHED__ZERO_CREDIT"
        classification = "UNRESOLVED"

    return {
        "schema": SCHEMA,
        "status": status,
        "classification": classification,
        "source_blob_drift": drift,
        "frozen_target": {
            "family_task_dimension_unknown_tool_discovery": unknown_tool_literal,
            "contract_requires_discover_candidate_tools_if_needed": contract_requires_discover,
            "contract_scope": (behavior or {}).get("scope"),
        },
        "terminal_binding": {
            "preenumerated_tool_ids_visible": preenumerated_ids_visible,
            "candidate_visible": visible,
            "explicit_complete_tool_universe_semantics": complete_tool_universe_explicit,
        },
        "exact_terminal_candidate_action_vocabulary": sorted(candidate_actions),
        "terminal_candidate_has_discover_action": terminal_has_discover,
        "broader_dynamic_candidate_action_vocabulary": sorted(dynamic_actions),
        "broader_dynamic_candidate_has_discover_action": broader_candidate_has_discover,
        "formalism_gap_established": formalism_gap,
        "universal_scope_certificate_currently_admissible": False,
        "minimum_missing_fact": (
            "INDEPENDENT_EXACT_SCOPE_SEMANTICS_PROVING_PREENUMERATED_TOOL_IDS_ARE_COMPLETE_FOR_THE_FROZEN_TARGET__"
            "OR_A_VERIFIED_DISCOVERY_INTERFACE_AND_UNIVERSAL_PROOF_COVERING_UNKNOWN_TOOL_IDENTITIES"
            if formalism_gap else None
        ),
        "hard_nonclaims": [
            "THIS_DOES_NOT_CLAIM_DYNAMIC_V3_IS_UNIVERSALLY_CORRECT",
            "THIS_DOES_NOT_CLAIM_THE_FAMILY_IS_IMPOSSIBLE_TO_CLOSE",
            "THIS_DOES_NOT_INVALIDATE_THE_180_OF_180_EXECUTED_SAMPLE",
            "THIS_DOES_NOT_GRANT_ACCEPTANCE_CAPABILITY_OR_FAMILY_CREDIT",
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
    return 1 if out["classification"] == "INVALID_INPUT_OR_AUTHORITY_DRIFT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
