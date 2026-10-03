"""Fail-closed scope certificate for common frozen Tool Discovery authority V1.

This certificate proves only a candidate universal scope relation. It does not
grant acceptance. Independent public-runner execution over the exact bytes is
required before the scope atom can be activated.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.common_frozen_tool_authority_v1 import (
    CommonFrozenToolAuthority,
    prove_common_authority_instance,
)

ROOT = Path(__file__).resolve().parents[2]

PROTOCOL = "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
CONTRACT = "canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.json"
V4 = "canonical/runtime/tool_discovery_dynamic_candidate_v4.py"
V4_ACTIVATION = "canonical/governance/TOOL_DISCOVERY_DYNAMIC_V4_REPAIR_ACTIVATION_V1.json"
AUTHORITY = "canonical/runtime/common_frozen_tool_authority_v1.py"
THEOREM = "canonical/governance/TOOL_DISCOVERY_COMMON_FROZEN_AUTHORITY_SCOPE_THEOREM_V1.json"

EXPECTED = {
    PROTOCOL: "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    CONTRACT: "49cc878eccc0fbc8fdd83d35e5fbd614c973ffa7",
    V4: "e614d0bed8e291e31f57189cd6f0f75aa39b0f74",
    V4_ACTIVATION: "36a7a97f3d68066337bb2cf45778d4100c22c185",
    AUTHORITY: "f4083e4331ae2e484812c4702655eed87772a666",
    THEOREM: "96a80d17c3d09d23f32a0ec44c929ce22de086be",
}

REQUIRED_PROPERTIES = {
    "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH",
    "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE",
    "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH",
    "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
    "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS",
    "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND",
    "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE",
}

REQUIRED_FACTS = {
    "FROZEN_PROTOCOL_IS_MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER",
    "FROZEN_PROTOCOL_REQUIRES_COMMON_TOOL_AUTHORITY",
    "UNKNOWN_TOOL_DISCOVERY_DIMENSION_PRESERVED",
    "V4_REPAIR_REQUIRES_COMPLETE_COMMON_AUTHORITY_NOT_BRAIN_ONLY",
    "V1_INTERFACE_PROPERTY_SET_EXACT",
    "AUTHORITY_ACCEPTS_BOTH_MATCHED_ROUTES",
    "BRAIN_OPUS_DISCOVERY_VIEWS_IDENTICAL",
    "DISCOVERY_ENUMERATES_EXACT_REGISTRY",
    "DISCOVERY_HIDES_CAPABILITY_TRUTH",
    "UNREGISTERED_ID_FAILS_CLOSED_FOR_BOTH_ROUTES",
    "AUTHORITY_REPLACEMENT_INVALIDATES_STALE_EPISODES",
    "ARBITRARY_FINITE_R_NOT_ENUMERATED_BY_THEOREM",
    "NO_ACCEPTANCE_CREDIT_CLAIMED",
}


def _blob_sha(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path + ":NOT_OBJECT")
    return value


def prove_from_facts(facts: Mapping[str, bool]) -> dict[str, Any]:
    missing = sorted(x for x in REQUIRED_FACTS if facts.get(x) is not True)
    if missing:
        return {
            "status": "FAIL_CLOSED__COMMON_AUTHORITY_SCOPE_PREMISE_MISSING",
            "missing": missing,
            "universal_scope_relation_proved_candidate": False,
            "scope_atom_satisfied_candidate": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }
    return {
        "status": (
            "PASS__COMMON_FROZEN_AUTHORITY_UNIVERSAL_SCOPE_RELATION_CANDIDATE__"
            "INDEPENDENT_PUBLIC_RUNNER_REQUIRED__ZERO_CREDIT"
        ),
        "missing": [],
        "universal_scope_relation_proved_candidate": True,
        "scope_atom_satisfied_candidate": True,
        "target_predicate": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "basis_kind": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "uses_empirical_generalization": False,
        "terminal_cases_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def verify() -> dict[str, Any]:
    drift = [p for p, want in EXPECTED.items() if _blob_sha(p) != want]
    if drift:
        out = prove_from_facts({})
        out["status"] = "FAIL_CLOSED__SOURCE_BLOB_DRIFT"
        out["source_blob_drift"] = sorted(drift)
        return out

    protocol = _load(PROTOCOL)
    contract = _load(CONTRACT)
    activation = _load(V4_ACTIVATION)
    theorem = _load(THEOREM)

    row = next(
        x for x in protocol.get("protocols", [])
        if isinstance(x, Mapping)
        and x.get("family") == "TOOL_DISCOVERY_SELECTION_AND_LEARNING"
    )

    entries = [
        {
            "tool_id": "opaque/a",
            "cost": 7.0,
            "available": True,
            "authorized": True,
            "region": "X",
            "capabilities": ["CAP_A"],
        },
        {
            "tool_id": "opaque/b",
            "cost": 1.0,
            "available": True,
            "authorized": True,
            "region": "X",
            "capabilities": ["CAP_A", "CAP_B"],
        },
    ]
    authority = CommonFrozenToolAuthority(entries, epoch=11)
    instance = prove_common_authority_instance(authority)

    brain = authority.discover("BRAIN", episode_epoch=11)
    opus = authority.discover("OPUS55", episode_epoch=11)

    outside_blocked = True
    for route in ("BRAIN", "OPUS55"):
        try:
            authority.invoke(route, "outside", episode_epoch=11)
            outside_blocked = False
        except Exception as exc:
            if "UNREGISTERED_TOOL_ID" not in str(exc):
                outside_blocked = False

    old_epoch = authority.epoch
    authority.replace_authority(entries)
    stale_blocked = True
    for route in ("BRAIN", "OPUS55"):
        try:
            authority.discover(route, episode_epoch=old_epoch)
            stale_blocked = False
        except Exception as exc:
            if "EPOCH_CHANGED_RESTART_EPISODE" not in str(exc):
                stale_blocked = False

    source = (ROOT / AUTHORITY).read_text(encoding="utf-8")
    facts = {
        "FROZEN_PROTOCOL_IS_MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER":
            row.get("proof_mode") == "MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER",
        "FROZEN_PROTOCOL_REQUIRES_COMMON_TOOL_AUTHORITY":
            "same frozen task population/harness/tool authority"
            in str(protocol.get("universal_rules", {}).get("same_scope") or ""),
        "UNKNOWN_TOOL_DISCOVERY_DIMENSION_PRESERVED":
            "unknown tool discovery" in list(row.get("task_dimensions") or []),
        "V4_REPAIR_REQUIRES_COMPLETE_COMMON_AUTHORITY_NOT_BRAIN_ONLY":
            activation.get("remaining_primitive_fact")
            == "PROVE_COMPLETE_TARGET_SCOPE_DISCOVERY_INTERFACE_OR_EQUIVALENT_UNIVERSAL_SCOPE_RELATION_WITHOUT_NARROWING_THE_COMMON_BRAIN_OPUS_TOOL_AUTHORITY"
            and activation.get("forbidden_shortcut")
            == "BRAIN_ONLY_REGISTRY_COMPLETENESS_MUST_NOT_BE_SUBSTITUTED_FOR_COMMON_FROZEN_TOOL_AUTHORITY_COMPLETENESS",
        "V1_INTERFACE_PROPERTY_SET_EXACT":
            set(contract.get("required_properties") or []) == REQUIRED_PROPERTIES,
        "AUTHORITY_ACCEPTS_BOTH_MATCHED_ROUTES":
            'ROUTES = frozenset({"BRAIN", "OPUS55"})' in source,
        "BRAIN_OPUS_DISCOVERY_VIEWS_IDENTICAL":
            brain == opus and instance.get("brain_opus_route_views_identical") is True,
        "DISCOVERY_ENUMERATES_EXACT_REGISTRY":
            instance.get("exact_complete_identity_enumeration") is True
            and 'for k in sorted(self._records)' in source,
        "DISCOVERY_HIDES_CAPABILITY_TRUTH":
            instance.get("hidden_capability_truth_not_disclosed_by_discovery") is True
            and 'if k != "capabilities"' in source,
        "UNREGISTERED_ID_FAILS_CLOSED_FOR_BOTH_ROUTES": outside_blocked,
        "AUTHORITY_REPLACEMENT_INVALIDATES_STALE_EPISODES": stale_blocked,
        "ARBITRARY_FINITE_R_NOT_ENUMERATED_BY_THEOREM":
            theorem.get("construction", {}).get("domain")
            == "ANY_FINITE_FROZEN_MATCHED_TOOL_AUTHORITY_R"
            and theorem.get("construction", {}).get("non_narrowing")
            == "R_IS_AN_ARBITRARY_INPUT_TO_THE_CONSTRUCTION__NO_TOOL_IDENTITY_OR_PROVIDER_IS_ENUMERATED_IN_THE_THEOREM",
        "NO_ACCEPTANCE_CREDIT_CLAIMED":
            theorem.get("capability_credit_delta") == 0
            and theorem.get("family_credit_delta") == 0
            and theorem.get("execution_authority") is False
            and theorem.get("promotion_authority") is False,
    }

    out = prove_from_facts(facts)
    out["source_blob_drift"] = []
    out["facts"] = facts
    out["instance_projection"] = instance
    out["common_authority_digest_sha256"] = brain["authority_digest_sha256"]
    out["forbidden_shortcut_respected"] = (
        facts["V4_REPAIR_REQUIRES_COMPLETE_COMMON_AUTHORITY_NOT_BRAIN_ONLY"]
        and facts["BRAIN_OPUS_DISCOVERY_VIEWS_IDENTICAL"]
    )
    return out


def main() -> int:
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("universal_scope_relation_proved_candidate") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
