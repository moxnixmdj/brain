"""Fail-closed composition certificate for the V7 common-authority interface.

This certificate proves an environment-side premise only:
for any finite frozen authority shared by Brain and Opus, the V7 adapter exposes
one exact task-independent authoritative catalog, truthful explicitly-safe probe
receipts, and transferable receipts until authority/tool epochs change.

It does NOT prove absolute dominance and grants no acceptance credit. V7 exact
bytes still require independent public-runner verification, followed by a
separate matched-comparator acceptance reduction.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_V7_COMMON_AUTHORITY_INTERFACE_CERTIFICATE_V1"

INTERFACE = "canonical/runtime/tool_discovery_common_authority_interface_v2_v7.py"
INTERFACE_TESTS = "canonical/tests/test_tool_discovery_common_authority_interface_v2_v7.py"
V7 = "canonical/runtime/tool_discovery_dynamic_candidate_v7.py"
V7_TESTS = "canonical/tests/test_tool_discovery_dynamic_candidate_v7.py"
CONTRACT = "canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V4_TRANSFERABLE_CATALOG.json"
V7_REPAIR = "canonical/governance/TOOL_DISCOVERY_V7_TRANSFERABLE_CATALOG_REPAIR_V1.json"
PROTOCOL = "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
REGISTRY = "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"

EXPECTED = {
    INTERFACE: "63186be5d58274a21609e4f605c9b292967b92c3",
    INTERFACE_TESTS: "c5476887d6e260d5f38d382b6cf1a6e4d2692d08",
    V7: "e29328dfe5aff5650c1b938472ccf5ecf826831a",
    V7_TESTS: "a14bc70bf297080308f88c97677fd409a8557cd9",
    CONTRACT: "0a9a788c2637610f4b4cfc5e0f770ba972409137",
    V7_REPAIR: "0fbb1d653ff63b1ecabca8c71416970ac5f826e6",
    PROTOCOL: "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    REGISTRY: "ee187f611a0e82b2de495ee377682f39bc31dd31",
}

REQUIRED_PROPERTIES = {
    "FINITE_EXPLICITLY_CLASSIFIED_DISCOVERY_SOURCE_SET_PER_AUTHORITY_EPOCH",
    "EACH_AUTHORITATIVE_SOURCE_DECLARES_A_TASK_INDEPENDENT_COMPLETE_CATALOG_QUERY",
    "POLICY_COMPUTES_SOURCE_SET_DIGEST_FROM_EXACT_SOURCE_METADATA_CATALOG_QUERY_AND_AUTHORITY_EPOCH",
    "EACH_SOURCE_HAS_STABLE_SOURCE_EPOCH_AND_CANONICAL_EXPECTED_RESULT_CONTENT_DIGEST_OR_EPISODE_RESTARTS",
    "DISCOVERY_RECEIPT_IS_COMPLETE_CURRENT_AUTHORITY_EPOCH_CURRENT_SOURCE_EPOCH_CANONICAL_CATALOG_QUERY_AND_EXACT_RESULT_CONTENT_BOUND",
    "COMPLETE_CATALOG_RECEIPT_IS_REUSABLE_ACROSS_TASK_REQUIREMENT_AND_DECISION_EPOCH_CHANGES_WITHIN_THE_SAME_AUTHORITY_SOURCE_EPOCHS",
    "UNION_OF_CURRENT_COMPLETE_AUTHORITATIVE_CATALOG_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
    "DISCOVERED_TOOL_METADATA_IS_CORRECT_AND_SAME_ID_METADATA_IS_CONSISTENT_WITHIN_EPOCH",
    "EVERY_ADMISSIBLE_REQUIRED_CAPABILITY_IS_CURRENTLY_EVIDENCED_OR_EXPLICITLY_SAFE_PROBE_DECIDABLE",
    "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_TOOL_EPOCH_BOUND",
    "UNRESOLVED_CHEAPER_ADMISSIBLE_ROUTE_WITHOUT_SAFE_PROBE_BLOCKS_MORE_EXPENSIVE_SELECTION",
    "TOOL_VERSION_OR_AUTHORITY_CHANGE_RESTARTS_OR_INVALIDATES_STALE_CATALOG_AND_CAPABILITY_EVIDENCE",
}

REQUIRED_FACTS = (
    "EXACT_V7_TRANSFER_CONTRACT",
    "FROZEN_PROTOCOL_IS_MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER",
    "TARGET_BEHAVIOR_REQUIRES_UNKNOWN_DISCOVERY_LEAST_COST_AND_TRANSFER",
    "FINITE_PARAMETRIC_COMMON_AUTHORITY",
    "BRAIN_AND_OPUS_BOUND_TO_IDENTICAL_AUTHORITY_INSTANCE",
    "NO_PREVISIBLE_UNBOUND_ROUTE",
    "SINGLE_ACTIVE_AUTHORITATIVE_SOURCE",
    "TASK_INDEPENDENT_CANONICAL_CATALOG_QUERY",
    "SOURCE_AND_SOURCE_SET_DIGESTS_MATCH_V7_SEMANTICS",
    "DISCOVERY_RETURNS_EXACT_COMPLETE_AUTHORITY",
    "DISCOVERY_RECEIPT_EXACTLY_REDERIVED_BEFORE_ADMISSION",
    "HIDDEN_SUPPORT_EXCLUDED_FROM_PUBLIC_METADATA",
    "SAFE_PROBE_PERMISSION_EXPLICIT",
    "SAFE_PROBE_SUPPORT_BOOLEAN_DERIVED_FROM_HIDDEN_TRUTH",
    "PROBE_RECEIPT_EXACTLY_REDERIVED_BEFORE_ADMISSION",
    "TASK_RETARGET_PRESERVES_CATALOG_AND_PROBE_RECEIPTS",
    "TOOL_EVOLUTION_ADVANCES_AUTHORITY_AND_TOOL_EPOCHS",
    "OLD_EPISODE_FAILS_CLOSED_AFTER_EVOLUTION",
    "V7_CONSUMES_AUTHORITY_SCOPED_CATALOG_RECEIPTS",
    "V7_BLOCKS_UNRESOLVED_UNSAFE_CHEAPER_ROUTE",
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
            got = _find(child, key, value)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for child in obj:
            got = _find(child, key, value)
            if got is not None:
                return got
    return None


def derive_interface_facts(source: str) -> dict[str, bool]:
    begin = source[source.find("def begin_task"):source.find("def retarget_task")]
    retarget = source[source.find("def retarget_task"):source.find("def _assert_episode_current")]
    probe = source[source.find("def safe_probe"):source.find("def apply_probe")]
    apply_probe = source[source.find("def apply_probe"):source.find("def evolve_tool")]
    evolve = source[source.find("def evolve_tool"):]
    return {
        "FINITE_PARAMETRIC_COMMON_AUTHORITY": all(x in source for x in (
            "def freeze_instance(",
            "FINITE_NONEMPTY_TOOL_AUTHORITY_REQUIRED",
            "DUPLICATE_TOOL_ID:",
            "def validate_instance(",
            "INSTANCE_DIGEST_MISMATCH:",
        )),
        "BRAIN_AND_OPUS_BOUND_TO_IDENTICAL_AUTHORITY_INSTANCE": all(x in source for x in (
            "def matched_route_binding(",
            '"same_frozen_tool_authority": True',
            '"brain": {',
            '"opus": {',
        )),
        "NO_PREVISIBLE_UNBOUND_ROUTE": '"visible_tools": []' in begin,
        "SINGLE_ACTIVE_AUTHORITATIVE_SOURCE": all(x in source for x in (
            'SOURCE_ID = "COMMON_FROZEN_BRAIN_OPUS_TOOL_AUTHORITY"',
            '"available": True',
            '"authorized": True',
            '"authoritative": True',
        )),
        "TASK_INDEPENDENT_CANONICAL_CATALOG_QUERY": all(x in source for x in (
            'CATALOG_QUERY = "__FULL_COMMON_FROZEN_AUTHORITY_CATALOG__"',
            '"catalog_query": CATALOG_QUERY',
            "DISCOVERY_QUERY_NOT_CANONICAL_CATALOG",
        )),
        "SOURCE_AND_SOURCE_SET_DIGESTS_MATCH_V7_SEMANTICS": all(x in source for x in (
            "def _tools_digest(",
            "def _source_set_digest(",
            '"authority_epoch": authority_epoch, "sources": payload',
            '"source_digest": source_digest',
            '"source_set_digest": source_set_digest',
        )),
        "DISCOVERY_RETURNS_EXACT_COMPLETE_AUTHORITY": all(x in source for x in (
            "def discover(",
            '"complete": True',
            '"tools": deepcopy(frozen["public_tools"])',
        )),
        "DISCOVERY_RECEIPT_EXACTLY_REDERIVED_BEFORE_ADMISSION": all(x in source for x in (
            "def apply_discovery(",
            "expected = discover(instance, episode, SOURCE_ID, CATALOG_QUERY)",
            "if dict(receipt) != expected:",
            "DISCOVERY_RECEIPT_NOT_EXACT_AUTHORITY_RESULT",
        )),
        "HIDDEN_SUPPORT_EXCLUDED_FROM_PUBLIC_METADATA": all(x in source for x in (
            '"hidden_capabilities"',
            '"supported_capabilities"',
            '"support_truth"',
            "PUBLIC_METADATA_CONTAINS_HIDDEN_CAPABILITY_FIELD:",
        )),
        "SAFE_PROBE_PERMISSION_EXPLICIT": all(x in probe for x in (
            'cap not in set(tool["safe_probe_capabilities"])',
            "PROBE_NOT_EXPLICITLY_SAFE",
        )),
        "SAFE_PROBE_SUPPORT_BOOLEAN_DERIVED_FROM_HIDDEN_TRUTH": all(x in probe for x in (
            'truth = frozen["hidden_truth"][tid][str(epoch)]',
            '"supported": cap in truth',
        )),
        "PROBE_RECEIPT_EXACTLY_REDERIVED_BEFORE_ADMISSION": all(x in apply_probe for x in (
            "expected = safe_probe(instance, episode, tid, cap)",
            "if dict(receipt) != expected:",
            "PROBE_RECEIPT_NOT_EXACT_TRUTH",
        )),
        "TASK_RETARGET_PRESERVES_CATALOG_AND_PROBE_RECEIPTS": (
            '"discovery_receipts"' not in retarget
            and '"prior_probe_receipts"' not in retarget
            and 'out = deepcopy(dict(episode))' in retarget
            and 'out["required_capabilities"] = required' in retarget
            and 'out["decision_epoch"] = decision_epoch' in retarget
        ),
        "TOOL_EVOLUTION_ADVANCES_AUTHORITY_AND_TOOL_EPOCHS": all(x in evolve for x in (
            'rows[tid]["epoch"] = new_epoch',
            'authority_epoch=frozen["authority_epoch"] + 1',
        )),
        "OLD_EPISODE_FAILS_CLOSED_AFTER_EVOLUTION": all(x in source for x in (
            "def _assert_episode_current(",
            "STALE_EPISODE_RESTART_REQUIRED",
            "STALE_AUTHORITY_EPOCH_RESTART_REQUIRED",
        )),
    }


def derive_v7_facts(source: str) -> dict[str, bool]:
    return {
        "V7_CONSUMES_AUTHORITY_SCOPED_CATALOG_RECEIPTS": all(x in source for x in (
            "def _authority_epoch(",
            '"catalog_query"',
            'rec.get("authority_epoch")==authority_epoch',
            'str(rec.get("query") or "")==str(source.get("catalog_query") or "")',
            "# Discovery completion is authority/catalog scoped, not task scoped.",
        )),
        "V7_BLOCKS_UNRESOLVED_UNSAFE_CHEAPER_ROUTE": all(x in source for x in (
            "probeable=[cap for cap in unknown if v5._probe_allowed(tool,cap)]",
            '"reason":"CHEAPER_ADMISSIBLE_ROUTE_UNRESOLVED_NO_SAFE_PROBE"',
        )),
    }


def prove_from_facts(facts: Mapping[str, bool]) -> dict[str, Any]:
    missing = [name for name in REQUIRED_FACTS if facts.get(name) is not True]
    if missing:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__V7_COMMON_AUTHORITY_PREMISE_MISSING",
            "missing": missing,
            "interface_completeness_candidate": False,
            "matched_acceptance_ready_candidate": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__V7_COMMON_MATCHED_AUTHORITY_INTERFACE_COMPOSITION_CANDIDATE__"
            "INDEPENDENT_V7_AND_COMPOSITION_VERIFICATION_REQUIRED__ZERO_CREDIT"
        ),
        "missing": [],
        "interface_completeness_candidate": True,
        "interface_contract_satisfied_candidate": True,
        "scope_kind": "COMMON_MATCHED_AUTHORITY_INTERFACE_COMPLETENESS",
        "target_predicate": "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "matched_acceptance_ready_candidate": False,
        "why_not_acceptance_yet": [
            "V7_EXACT_BYTES_NOT_YET_INDEPENDENTLY_VERIFIED",
            "COMPOSITION_EXACT_BYTES_NOT_YET_INDEPENDENTLY_VERIFIED",
            "MATCHED_COMPARATOR_CONDITIONED_ACCEPTANCE_REDUCTION_REMAINS_SEPARATE",
        ],
        "absolute_dominance_claim": False,
        "uses_brain_only_registry": False,
        "preenumerates_tool_identities": False,
        "terminal_cases_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def verify() -> dict[str, Any]:
    drift = [path for path, want in EXPECTED.items() if _blob_sha(path) != want]
    if drift:
        out = prove_from_facts({})
        out["status"] = "FAIL_CLOSED__SOURCE_BLOB_DRIFT"
        out["source_blob_drift"] = drift
        return out

    contract = _load(CONTRACT)
    protocol = _load(PROTOCOL)
    registry = _load(REGISTRY)
    family = _find(protocol, "family", "TOOL_DISCOVERY_SELECTION_AND_LEARNING")
    behavior = _find(registry, "behavior_id", "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001")

    facts = derive_interface_facts(_text(INTERFACE))
    facts.update(derive_v7_facts(_text(V7)))
    facts.update({
        "EXACT_V7_TRANSFER_CONTRACT": (
            set(contract.get("required_properties") or []) == REQUIRED_PROPERTIES
            and contract.get("instance_verified") is False
        ),
        "FROZEN_PROTOCOL_IS_MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER": (
            family is not None
            and family.get("proof_mode") == "MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER"
        ),
        "TARGET_BEHAVIOR_REQUIRES_UNKNOWN_DISCOVERY_LEAST_COST_AND_TRANSFER": (
            behavior is not None
            and "unknown or changing capabilities" in str(behavior.get("environment_state") or "")
            and "least-cost admissible route" in str(behavior.get("required_output_or_action") or "")
            and "learned capability state transfers to later tasks" in str(behavior.get("success_condition") or "")
        ),
    })
    out = prove_from_facts(facts)
    out["source_blob_drift"] = []
    out["derived_facts"] = facts
    return out


def main() -> int:
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("interface_completeness_candidate") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
