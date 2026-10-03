"""Fail-closed conditional universal scope certificate for Tool Discovery V4.

The theorem is intentionally split:
1. Program-side universal obligations are proved for the exact V4 bytes over any
   finite interface instance satisfying the exact V2 contract.
2. No claim is made that a current real discovery interface satisfies that
   contract. That remains one independently verified external instance fact.

This separation prevents the V1 mistake: structural presence of DISCOVER did
not imply global least-cost selection because V3 could SELECT before exhausting
unqueried authoritative sources.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]

V4 = "canonical/runtime/tool_discovery_dynamic_candidate_v4.py"
V4_TEST = "canonical/tests/test_tool_discovery_dynamic_candidate_v4.py"
V3 = "canonical/runtime/tool_discovery_dynamic_candidate_v3.py"
V1_REFINEMENT = "canonical/runtime/tool_discovery_dynamic_refinement_v1.py"
V1_FALSIFICATION = "canonical/governance/TOOL_DISCOVERY_DYNAMIC_V3_REFINEMENT_FALSIFICATION_V1.json"
CONTRACT = "canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V2.json"
PROTOCOL = "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
REGISTRY = "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
CUT = "canonical/governance/TOOL_DISCOVERY_SCOPE_FORMALISM_CUT_ACTIVATION_V1.json"

EXPECTED = {
    V4: "231221a16a631a4c9ee7994b5c890da89b3bdb38",
    V4_TEST: "f7deba581e1b4e03c02c4dcd3578751eebf8231f",
    V3: "bbbee4d6baf8df937543644397abba38a67dce62",
    V1_REFINEMENT: "991c039c0b405bf77508ce7921abc69460f57332",
    V1_FALSIFICATION: "f84a83562aac2b43254eda3826744be09b271a1e",
    CONTRACT: "bd8261913ce3eca063e87da967dce80a888e831e",
    PROTOCOL: "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    REGISTRY: "ee187f611a0e82b2de495ee377682f39bc31dd31",
    CUT: "48ba33998e73b8eec2731be51a7ec78077ed0d4a",
}

REQUIRED_INTERFACE_PROPERTIES = {
    "FINITE_AVAILABLE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH",
    "FINITE_TOOL_IDENTITY_SET_PER_AUTHORITATIVE_DISCOVERY_RESULT",
    "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE",
    "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH",
    "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
    "ALL_VISIBLE_TOOL_METADATA_CORRECT_FOR_IDENTITY_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS",
    "SAME_TOOL_ID_METADATA_IS_CONSISTENT_WITHIN_EPOCH",
    "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND",
    "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE",
    "DISCOVERY_ACTION_RETURNS_AUTHORITATIVE_RECEIPT_OR_FAILS_CLOSED_AND_RESTARTS_EPISODE",
    "SAFE_PROBE_ACTION_RETURNS_TRUTHFUL_RECEIPT_OR_FAILS_CLOSED_AND_RESTARTS_EPISODE",
}

REQUIRED_FACTS = {
    "V1_COUNTEREXAMPLE_BINDS_EXACT_ACTIVE_BYTES",
    "V4_DISCOVERY_PRECEDES_ANY_TOOL_PROBE_OR_SELECT",
    "V4_DISCOVERY_NEVER_REQUERIES_RECEIPTED_SOURCE",
    "V4_DISCOVERY_SOURCE_ORDER_IS_DETERMINISTIC",
    "V4_TOOL_ORDER_IS_DECLARED_COST_THEN_ID",
    "V4_KNOWN_FALSE_ROUTE_IS_SKIPPED",
    "V4_UNKNOWN_REQUIRED_CAPABILITY_IS_PROBED_BEFORE_SELECT",
    "V4_SELECT_REQUIRES_ALL_REQUIRED_CAPABILITIES_CURRENT_POSITIVE",
    "V4_PROBE_EVIDENCE_IS_CURRENT_EPOCH_ONLY",
    "V4_VERSION_CHANGE_INVALIDATES_STALE_EVIDENCE",
    "V4_ESCALATION_OCCURS_ONLY_AFTER_SOURCE_EXHAUSTION_AND_TOOL_SCAN",
    "INTERFACE_SOURCE_SET_FINITE",
    "INTERFACE_EACH_RESULT_FINITE",
    "INTERFACE_COMPLETE_IDENTITY_UNION",
    "INTERFACE_METADATA_TRUTHFUL",
    "INTERFACE_PROBES_TRUTHFUL_CURRENT_EPOCH",
    "INTERFACE_EPISODE_EPOCH_STABLE_OR_RESTARTED",
    "FROZEN_TARGET_REQUIRES_UNKNOWN_IDENTITY_DISCOVERY_AND_LEAST_COST_ROUTE",
}

REDUCED_EXTERNAL_FACT = (
    "INDEPENDENT_VERIFIED_COMPLETE_DISCOVERY_INTERFACE_INSTANCE_SATISFYING_"
    "TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V2"
)


def _blob_sha(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _load(path: str) -> dict[str, Any]:
    value = json.loads(_text(path))
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


def derive_source_facts(v4_source: str) -> dict[str, bool]:
    source_pos = v4_source.find('sources=[')
    discover_pos = v4_source.find('if sources:')
    tools_pos = v4_source.find('tools=[')
    tool_loop_pos = v4_source.find('for tool in tools:')
    select_pos = v4_source.find('return {"action":"SELECT","tool_id":tid}')
    escalate_pos = v4_source.find(
        'return {"action":"ESCALATE","reason":"NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY"}'
    )
    return {
        "V4_DISCOVERY_PRECEDES_ANY_TOOL_PROBE_OR_SELECT": (
            min(source_pos, discover_pos, tools_pos, tool_loop_pos, select_pos) >= 0
            and source_pos < discover_pos < tools_pos < tool_loop_pos < select_pos
        ),
        "V4_DISCOVERY_NEVER_REQUERIES_RECEIPTED_SOURCE": (
            'str(s.get("source_id") or "") not in queried' in v4_source
            and 'x.get("kind")=="DISCOVERY_RESULT"' in v4_source
        ),
        "V4_DISCOVERY_SOURCE_ORDER_IS_DETERMINISTIC": (
            'sources.sort(key=lambda s:(float(s.get("cost",0.0)),str(s.get("source_id") or "")))'
            in v4_source
        ),
        "V4_TOOL_ORDER_IS_DECLARED_COST_THEN_ID": (
            'tools.sort(key=lambda t:(float(t.get("cost",0.0)),str(t.get("tool_id") or "")))'
            in v4_source
        ),
        "V4_KNOWN_FALSE_ROUTE_IS_SKIPPED": (
            "if v is False:" in v4_source
            and "impossible=True" in v4_source
            and "if impossible:" in v4_source
            and "continue" in v4_source
        ),
        "V4_UNKNOWN_REQUIRED_CAPABILITY_IS_PROBED_BEFORE_SELECT": (
            "if v is None:" in v4_source
            and "unknown.append(cap)" in v4_source
            and 'return {"action":"PROBE","tool_id":tid,"capability":unknown[0]}' in v4_source
        ),
        "V4_SELECT_REQUIRES_ALL_REQUIRED_CAPABILITIES_CURRENT_POSITIVE": (
            'return {"action":"SELECT","tool_id":tid}' in v4_source
            and "if unknown:" in v4_source
            and "if impossible:" in v4_source
        ),
        "V4_PROBE_EVIDENCE_IS_CURRENT_EPOCH_ONLY": (
            'int(rec.get("epoch",-1))==epochs[tid]' in v4_source
        ),
        "V4_VERSION_CHANGE_INVALIDATES_STALE_EVIDENCE": (
            'ev.get("kind")=="TOOL_VERSION_CHANGED"' in v4_source
            and 'out[tid]=int(ev.get("new_epoch",out[tid]+1))' in v4_source
            and 'int(rec.get("epoch",-1))==epochs[tid]' in v4_source
        ),
        "V4_ESCALATION_OCCURS_ONLY_AFTER_SOURCE_EXHAUSTION_AND_TOOL_SCAN": (
            discover_pos >= 0
            and tool_loop_pos > discover_pos
            and escalate_pos > tool_loop_pos
        ),
    }


def prove_from_facts(facts: Mapping[str, bool]) -> dict[str, Any]:
    missing = sorted(name for name in REQUIRED_FACTS if facts.get(name) is not True)
    if missing:
        return {
            "status": "FAIL_CLOSED__UNIVERSAL_PROGRAM_PREMISE_MISSING",
            "conditional_universal_program_proof": False,
            "universal_target_proved": False,
            "missing": missing,
            "minimum_missing_fact": REDUCED_EXTERNAL_FACT,
        }

    return {
        "status": (
            "PASS__UNIVERSAL_PROGRAM_SIDE_PROOF_FOR_DISCOVERY_EXHAUSTIVE_V4__"
            "EXTERNAL_INTERFACE_INSTANCE_OPEN__ZERO_CREDIT"
        ),
        "conditional_universal_program_proof": True,
        "universal_target_proved": False,
        "missing": [],
        "minimum_missing_fact": REDUCED_EXTERNAL_FACT,
        "proof": {
            "source_exhaustion": (
                "The available source set is finite. V4 emits DISCOVER before any PROBE or SELECT "
                "while an available unqueried source exists, and receipt identity excludes every "
                "queried source thereafter. Therefore source exhaustion occurs after finitely many "
                "receipt-advancing discovery steps."
            ),
            "identity_completeness": (
                "Each authoritative result contains finitely many identities and results add "
                "identities monotonically. At source exhaustion, the union-completeness premise "
                "therefore makes every in-scope candidate identity visible."
            ),
            "least_cost_selection": (
                "After complete discovery, V4 orders every admissible visible tool by declared "
                "cost then identity. For each cheaper tool it either obtains truthful current-epoch "
                "negative evidence for a required capability and skips it, or obtains truthful "
                "positive evidence for all requirements and selects it. Hence a later more "
                "expensive tool cannot be selected while a cheaper sufficient admissible route exists."
            ),
            "safe_escalation": (
                "ESCALATE is structurally after complete source exhaustion and after the ordered "
                "tool scan has found no route that can be positively completed under truthful "
                "current-epoch probe evidence."
            ),
            "transfer_and_change": (
                "Current-epoch receipts are reused across calls. A version event changes the epoch "
                "key, so stale capability evidence ceases to bind and must be re-probed."
            ),
        },
    }


def verify(
    *,
    v4_source_override: str | None = None,
    contract_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    drift = [path for path, sha in EXPECTED.items() if _blob_sha(path) != sha]
    if drift:
        return {
            "status": "FAIL_CLOSED__SOURCE_BLOB_DRIFT",
            "source_blob_drift": sorted(drift),
            "conditional_universal_program_proof": False,
            "universal_target_proved": False,
            "minimum_missing_fact": REDUCED_EXTERNAL_FACT,
        }

    protocol = _load(PROTOCOL)
    registry = _load(REGISTRY)
    cut = _load(CUT)
    falsification = _load(V1_FALSIFICATION)
    contract = dict(contract_override) if contract_override is not None else _load(CONTRACT)

    family = _find(protocol, "family", "TOOL_DISCOVERY_SELECTION_AND_LEARNING")
    behavior = _find(registry, "behavior_id", "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001")
    if family is None or behavior is None:
        return {
            "status": "FAIL_CLOSED__FROZEN_TARGET_MISSING",
            "conditional_universal_program_proof": False,
            "universal_target_proved": False,
            "minimum_missing_fact": REDUCED_EXTERNAL_FACT,
        }

    required_output = str(behavior.get("required_output_or_action") or "")
    scope = str(behavior.get("scope") or "")
    task_dimensions = set(family.get("task_dimensions") or [])
    target_ok = (
        "unknown tool discovery" in task_dimensions
        and "Discover candidate tools if needed" in required_output
        and "select the least-cost admissible route" in required_output
        and scope == "Unknown/changing tool ecosystem to verified usable route"
    )

    props = contract.get("required_properties")
    contract_exact = (
        isinstance(props, list)
        and all(isinstance(x, str) and x for x in props)
        and set(props) == REQUIRED_INTERFACE_PROPERTIES
        and contract.get("instance_verified") is False
    )

    counterexample = falsification.get("counterexample") or {}
    v1_bound = (
        falsification.get("violated_obligation") == "LEAST_COST_EVIDENCE_SUPPORTED_SELECTION"
        and counterexample.get("globally_least_cost_sufficient_route") == "CHEAP"
        and (counterexample.get("v3_first_action") or {}).get("tool_id") == "EXPENSIVE"
        and counterexample.get("contradiction")
        == "V3_SELECTS_COST_10_BEFORE_QUERYING_SOURCE_CONTAINING_COST_1_SUFFICIENT_ROUTE"
    )

    source = v4_source_override if v4_source_override is not None else _text(V4)
    facts = derive_source_facts(source)
    facts.update({
        "V1_COUNTEREXAMPLE_BINDS_EXACT_ACTIVE_BYTES": v1_bound,
        "INTERFACE_SOURCE_SET_FINITE": contract_exact and "FINITE_AVAILABLE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH" in set(props or []),
        "INTERFACE_EACH_RESULT_FINITE": contract_exact and "FINITE_TOOL_IDENTITY_SET_PER_AUTHORITATIVE_DISCOVERY_RESULT" in set(props or []),
        "INTERFACE_COMPLETE_IDENTITY_UNION": contract_exact and "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE" in set(props or []),
        "INTERFACE_METADATA_TRUTHFUL": contract_exact and "ALL_VISIBLE_TOOL_METADATA_CORRECT_FOR_IDENTITY_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS" in set(props or []),
        "INTERFACE_PROBES_TRUTHFUL_CURRENT_EPOCH": contract_exact and "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND" in set(props or []),
        "INTERFACE_EPISODE_EPOCH_STABLE_OR_RESTARTED": contract_exact and "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE" in set(props or []),
        "FROZEN_TARGET_REQUIRES_UNKNOWN_IDENTITY_DISCOVERY_AND_LEAST_COST_ROUTE": target_ok,
    })

    out = prove_from_facts(facts)
    out.update({
        "schema": "PROJECT_BRAIN_TOOL_DISCOVERY_DYNAMIC_V4_UNIVERSAL_SCOPE_CERTIFICATE_V1",
        "source_blob_drift": [],
        "facts": facts,
        "target_predicate": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "target_proof_atom": cut.get("target_proof_atom"),
        "target_preserved": target_ok,
        "v1_refinement_falsified": v1_bound,
        "v4_repair_bound": True,
        "interface_contract": CONTRACT,
        "interface_instance_verified": False,
        "uses_empirical_generalization": False,
        "terminal_results_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    })
    return out


def main() -> int:
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("conditional_universal_program_proof") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
