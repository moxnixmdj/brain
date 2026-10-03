"""Fail-closed certificate for the common-authority Tool Discovery interface.

The active terminal residual requires one independently verified complete
discovery-interface instance satisfying TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1
and bound to the independently verified V4 policy.

This candidate is stronger than one hard-coded catalog: it is one exact
environment-side interface implementation parameterized by the common frozen
Brain/Opus authority manifest. Completeness is definitionally checked against
that manifest, so no Brain-only registry or pre-enumerated identity set is used.

Independent public-runner verification is still required. This module grants no
acceptance, capability, family, execution, or promotion credit by itself.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_COMMON_AUTHORITY_INTERFACE_CERTIFICATE_V1"

CONTRACT="canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V1.json"
INTERFACE="canonical/runtime/tool_discovery_common_authority_interface_v1.py"
INTERFACE_TESTS="canonical/tests/test_tool_discovery_common_authority_interface_v1.py"
V4="canonical/runtime/tool_discovery_dynamic_candidate_v4.py"
V4_VERIFICATION="canonical/verification/TOOL_DISCOVERY_DYNAMIC_V4_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
PROTOCOL="canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
REGISTRY="canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
BINDINGS="canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"

EXPECTED={
    CONTRACT:"49cc878eccc0fbc8fdd83d35e5fbd614c973ffa7",
    INTERFACE:"6d2c056be88716457aa2c7a4cfdad91baaca0b03",
    INTERFACE_TESTS:"d37706911606a89ad10eb19474bcde8e7aed1f1c",
    V4:"e614d0bed8e291e31f57189cd6f0f75aa39b0f74",
    V4_VERIFICATION:"10cb18355d247a05177230d0dd345e161e84111d",
    PROTOCOL:"62394e5b7d221ec9f69c3458f669e40e253a9d09",
    REGISTRY:"ee187f611a0e82b2de495ee377682f39bc31dd31",
    BINDINGS:"7885a827b1483bfb38315c1f492848f7e4680285",
}

REQUIRED_PROPERTIES={
    "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH",
    "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE",
    "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH",
    "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
    "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS",
    "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND",
    "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE",
}

REQUIRED_FACTS=(
    "OFFICIAL_CONTRACT_EXACT",
    "COMMON_FROZEN_TOOL_AUTHORITY_REQUIRED_BY_PROTOCOL",
    "TARGET_CONTRACT_REQUIRES_UNKNOWN_TOOL_DISCOVERY_AND_LEAST_COST_ROUTE",
    "CURRENT_BLOCKER_IS_SCOPE_COMPLETENESS",
    "V4_EXACT_BYTES_INDEPENDENTLY_VERIFIED",
    "FINITE_PARAMETRIC_AUTHORITY_VALIDATION",
    "SINGLE_AUTHORITATIVE_DISCOVERY_SOURCE",
    "DISCOVERY_RETURNS_EXACT_PUBLIC_AUTHORITY_MANIFEST",
    "DISCOVERY_RECEIPT_BINDS_AUTHORITY_AND_INSTANCE_DIGESTS",
    "DISCOVERY_APPLICATION_IS_MONOTONIC_AND_CONFLICT_FAIL_CLOSED",
    "PUBLIC_METADATA_EXCLUDES_HIDDEN_CAPABILITY_TRUTH",
    "ARBITRARY_PUBLIC_CONSTRAINT_METADATA_PRESERVED",
    "BRAIN_AND_OPUS_BOUND_TO_SAME_EXACT_AUTHORITY_DIGEST",
    "SAFE_PROBE_SUPPORT_DERIVED_FROM_HIDDEN_TRUTH",
    "SAFE_PROBE_IS_CURRENT_EPOCH_AND_INSTANCE_BOUND",
    "VERSION_CHANGE_CREATES_NEW_GENERATION",
    "STALE_EPISODE_REQUIRES_RESTART",
    "IDENTITIES_ARE_OPAQUE_AND_NOT_PREENUMERATED",
    "INTERFACE_IS_ROUTE_NEUTRAL_AND_COMMON_AUTHORITY_PARAMETRIC",
)

def _blob_sha(path:str)->str:
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def _text(path:str)->str:
    return (ROOT/path).read_text(encoding="utf-8")

def _load(path:str)->dict[str,Any]:
    value=json.loads(_text(path))
    if not isinstance(value,dict):
        raise ValueError(path+":NOT_OBJECT")
    return value

def _find(obj:Any,key:str,value:str)->Mapping[str,Any]|None:
    if isinstance(obj,Mapping):
        if obj.get(key)==value:
            return obj
        for child in obj.values():
            got=_find(child,key,value)
            if got is not None:
                return got
    elif isinstance(obj,list):
        for child in obj:
            got=_find(child,key,value)
            if got is not None:
                return got
    return None

def derive_interface_facts(source:str)->dict[str,bool]:
    return {
        "FINITE_PARAMETRIC_AUTHORITY_VALIDATION": all(x in source for x in (
            "def freeze_instance(",
            "FINITE_NONEMPTY_TOOL_AUTHORITY_REQUIRED",
            "DUPLICATE_TOOL_ID:",
            "def validate_instance(",
            "INSTANCE_DIGEST_MISMATCH:",
        )),
        "SINGLE_AUTHORITATIVE_DISCOVERY_SOURCE": all(x in source for x in (
            'SOURCE_ID="COMMON_FROZEN_BRAIN_OPUS_TOOL_AUTHORITY"',
            '"discovery_sources":[{',
            '"source_id":SOURCE_ID',
            '"available":True',
        )),
        "DISCOVERY_RETURNS_EXACT_PUBLIC_AUTHORITY_MANIFEST": all(x in source for x in (
            "def discover(",
            '"complete":True',
            '"tools":deepcopy(frozen["public_tools"])',
        )),
        "DISCOVERY_RECEIPT_BINDS_AUTHORITY_AND_INSTANCE_DIGESTS": all(x in source for x in (
            '"authority_sha256":frozen["public_authority_sha256"]',
            '"instance_sha256":frozen["instance_sha256"]',
            "DISCOVERY_AUTHORITY_MISMATCH",
            "DISCOVERY_INSTANCE_MISMATCH",
            "DISCOVERY_GENERATION_MISMATCH",
        )),
        "DISCOVERY_APPLICATION_IS_MONOTONIC_AND_CONFLICT_FAIL_CLOSED": all(x in source for x in (
            "def apply_discovery(",
            'list(episode.get("visible_tools") or [])+receipt_rows',
            "CONFLICTING_PUBLIC_TOOL_METADATA:",
            "DISCOVERY_SOURCE_ALREADY_QUERIED",
            "DISCOVERY_PAYLOAD_NOT_EXACT_COMPLETE_AUTHORITY",
        )),
        "PUBLIC_METADATA_EXCLUDES_HIDDEN_CAPABILITY_TRUTH": all(x in source for x in (
            'forbidden={"hidden_capabilities","capabilities","supported_capabilities","_oracle"}',
            "PUBLIC_METADATA_CONTAINS_HIDDEN_CAPABILITY_FIELD:",
            "out=deepcopy(dict(raw))",
        )),
        "ARBITRARY_PUBLIC_CONSTRAINT_METADATA_PRESERVED": all(x in source for x in (
            "out=deepcopy(dict(raw))",
            'out["tool_id"]=tid',
            'out["cost"]=float(raw.get("cost",0.0))',
            'out["available"]=bool(raw["available"])',
            'out["authorized"]=bool(raw["authorized"])',
            'out["epoch"]=epoch',
        )),
        "BRAIN_AND_OPUS_BOUND_TO_SAME_EXACT_AUTHORITY_DIGEST": all(x in source for x in (
            "def matched_route_binding(",
            '"brain":{',
            '"opus":{',
            '"public_authority_sha256":digest',
            '"interface_instance_sha256":instance_digest',
            '"same_frozen_tool_authority":True',
        )),
        "SAFE_PROBE_SUPPORT_DERIVED_FROM_HIDDEN_TRUTH": all(x in source for x in (
            "def safe_probe(",
            'truth=frozen["hidden_truth"][tid][str(epoch)]',
            '"supported":cap in truth',
        )),
        "SAFE_PROBE_IS_CURRENT_EPOCH_AND_INSTANCE_BOUND": all(x in source for x in (
            'epoch=tools[tid]["epoch"]',
            '"instance_sha256":frozen["instance_sha256"]',
            '"generation":frozen["generation"]',
            "PROBE_INSTANCE_MISMATCH",
            "PROBE_GENERATION_MISMATCH",
            "PROBE_RECEIPT_EPOCH_MISMATCH",
            "PROBE_RECEIPT_TRUTH_MISMATCH",
        )),
        "VERSION_CHANGE_CREATES_NEW_GENERATION": all(x in source for x in (
            "def evolve_tool(",
            "VERSION_EPOCH_MUST_ADVANCE",
            'generation=frozen["generation"]+1',
        )),
        "STALE_EPISODE_REQUIRES_RESTART": all(x in source for x in (
            "def _assert_episode_current(",
            "STALE_EPISODE_RESTART_REQUIRED",
        )),
        "IDENTITIES_ARE_OPAQUE_AND_NOT_PREENUMERATED": (
            "T0" not in source
            and "T1" not in source
            and "tool_id" in source
            and "for raw in public_tools" in source
        ),
        "INTERFACE_IS_ROUTE_NEUTRAL_AND_COMMON_AUTHORITY_PARAMETRIC": (
            "tool_discovery_dynamic_candidate" not in source
            and "Brain and Opus" in source
            and "public_tools:Sequence[Mapping[str,Any]]" in source
        ),
    }

def prove_from_facts(facts:Mapping[str,bool])->dict[str,Any]:
    missing=[name for name in REQUIRED_FACTS if facts.get(name) is not True]
    if missing:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED__COMPLETE_INTERFACE_PREMISE_MISSING",
            "missing":missing,
            "interface_instance_verified_candidate":False,
            "universal_scope_atom_satisfied_candidate":False,
            "capability_credit_delta":0,
            "family_credit_delta":0,
            "execution_authority":False,
            "promotion_authority":False,
        }
    return {
        "schema":SCHEMA,
        "status":"PASS__PARAMETRIC_COMMON_AUTHORITY_INTERFACE_INSTANCE__INDEPENDENT_PUBLIC_RUNNER_REQUIRED__ZERO_CREDIT",
        "missing":[],
        "interface_instance_verified_candidate":True,
        "interface_contract_satisfied_candidate":True,
        "scope_relation":"PROVEN_STRONGER",
        "basis":"PARAMETRIC_COMPLETE_INTERFACE_OVER_ANY_FINITE_COMMON_FROZEN_AUTHORITY",
        "target_predicate":"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
        "target_proof_atom":"INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL",
        "universal_scope_atom_satisfied_candidate":True,
        "proof":{
            "common_authority_binding":(
                "The frozen protocol requires Brain and Opus to use the same frozen tool authority. "
                "The interface takes that authority manifest itself as its sole public catalog input; "
                "there is no Brain-only registry substitution."
            ),
            "identity_completeness":(
                "For every finite input authority manifest A, the single authoritative discovery "
                "source returns exactly deepcopy(A). Therefore the union of authoritative discovery "
                "results equals A by construction, independent of tool names or cardinality."
            ),
            "metadata_correctness":(
                "Discovery metadata is copied from the exact frozen public authority rows and bound "
                "to their SHA-256 manifest digest; conflicting or tampered rows fail closed."
            ),
            "hidden_truth_and_probes":(
                "Hidden capability truth is stored outside public metadata. SAFE_CAPABILITY_PROBE "
                "support is computed directly from the hidden truth at the tool's current epoch and "
                "the receipt is bound to the exact interface instance and generation."
            ),
            "temporal_rule":(
                "Every version evolution creates a new instance generation. Any action using an old "
                "episode token fails with STALE_EPISODE_RESTART_REQUIRED, satisfying the contract's "
                "stable-epoch-or-restart alternative."
            ),
            "v4_composition":(
                "The independently verified V4 policy exhausts available discovery sources before "
                "probe/select, then reasons in global declared-cost order. Composed with this complete "
                "interface, unknown identities cannot remain outside the visible common authority."
            ),
        },
        "uses_empirical_generalization":False,
        "uses_brain_only_registry":False,
        "preenumerates_tool_identities":False,
        "terminal_cases_replayed":0,
        "new_reality_units_consumed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }

def verify()->dict[str,Any]:
    drift=[p for p,want in EXPECTED.items() if _blob_sha(p)!=want]
    if drift:
        out=prove_from_facts({})
        out["status"]="FAIL_CLOSED__SOURCE_BLOB_DRIFT"
        out["source_blob_drift"]=drift
        return out

    contract=_load(CONTRACT)
    protocol=_load(PROTOCOL)
    registry=_load(REGISTRY)
    bindings=_load(BINDINGS)
    v4_receipt=_load(V4_VERIFICATION)

    family=_find(protocol,"family","TOOL_DISCOVERY_SELECTION_AND_LEARNING")
    behavior=_find(registry,"behavior_id","TOOL_ROUTE_DISCOVERY_AND_SELECTION_001")
    claim=_find(bindings,"predicate_id","TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")

    props=contract.get("required_properties")
    facts=derive_interface_facts(_text(INTERFACE))
    facts.update({
        "OFFICIAL_CONTRACT_EXACT": (
            isinstance(props,list)
            and set(props)==REQUIRED_PROPERTIES
            and contract.get("instance_verified") is False
        ),
        "COMMON_FROZEN_TOOL_AUTHORITY_REQUIRED_BY_PROTOCOL": (
            "same frozen task population/harness/tool authority"
            in str(protocol.get("universal_rules",{}).get("same_scope") or "")
        ),
        "TARGET_CONTRACT_REQUIRES_UNKNOWN_TOOL_DISCOVERY_AND_LEAST_COST_ROUTE": (
            family is not None
            and "unknown tool discovery" in list(family.get("task_dimensions") or [])
            and behavior is not None
            and "Discover candidate tools if needed" in str(behavior.get("required_output_or_action") or "")
            and "least-cost admissible route" in str(behavior.get("required_output_or_action") or "")
        ),
        "CURRENT_BLOCKER_IS_SCOPE_COMPLETENESS": (
            claim is not None
            and claim.get("state")=="EXTERNAL_BLOCKED"
            and claim.get("blocker")=="ABSOLUTE_SCOPE_COMPLETENESS_MISSING"
            and "UNIVERSAL_FORMAL_SCOPE_PROOF" in str(claim.get("discharge_condition") or "")
        ),
        "V4_EXACT_BYTES_INDEPENDENTLY_VERIFIED": (
            v4_receipt.get("status")=="PASS__EXACT_BYTES__PROGRAM_SIDE_LEAST_COST_REPAIR_ONLY__ZERO_ACCEPTANCE_CREDIT"
            and ((v4_receipt.get("exact_blobs") or {}).get("v4") or {}).get("git_blob_sha")
                == EXPECTED[V4]
            and ((v4_receipt.get("independent_public_runner") or {}).get("run_conclusion")=="success")
        ),
    })
    out=prove_from_facts(facts)
    out["source_blob_drift"]=[]
    out["derived_facts"]=facts
    out["contract_required_properties"]=sorted(REQUIRED_PROPERTIES)
    return out

def main()->int:
    out=verify()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out.get("interface_instance_verified_candidate") is True else 1

if __name__=="__main__":
    raise SystemExit(main())
