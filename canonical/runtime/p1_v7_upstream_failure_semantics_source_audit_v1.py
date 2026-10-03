"""Fail-closed audit for an existing upstream P1 V7 failure-semantics source.

This audit does not invent a semantic adapter. It asks only whether the currently
frozen, content-addressed upstream P1 evidence set already declares an additional
source that can transport the DIRECT_CONTRACT vs DERIVED_UPSTREAM distinction
which the independently verified identifiability theorem says is missing from the
current projected trajectory fields.

A negative result classifies an information/specification residual for this exact
frozen source set. It does not claim universal absence from all possible future
evidence, and grants zero acceptance/capability/family credit.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_P1_V7_UPSTREAM_FAILURE_SEMANTICS_SOURCE_AUDIT_V1"

SOURCES = {
    "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json": "8703c6aa08227467a619a7ae90d0d61f8e54da39",
    "canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json": "8b439403a05b4a912f06a8866db25f6e53b52473",
    "canonical/governance/CONTRACT_NATIVE_PRIVATE_SURFACE_PROOF_ROUTES_V1.json": "75cd1ad0ec0739ebd894cf6075af5837b93d83f8",
    "canonical/governance/FOUR_UNCOVERED_BEHAVIORAL_PROOF_CONTRACTS_V1.json": "8c7ffe3d9ff789eddd286496f6de3ce84472c909",
    "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json": "bd86b4c53992b47a4a60b64a60ba03db9a442cfc",
    "canonical/verification/P1_V7_DIRECT_SURFACE_TRANSPORT_AND_IDENTIFIABILITY_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json": "e9d0632bd85e2deb43247d6bc78e641cb6440db4",
    "canonical/verification/FOUR_DIRECT_PROOF_MUTATION_PREFLIGHT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "d4abf1dbda1328674489afca49bbece93c794cd1",
    "canonical/verification/TRAJECTORY_TYPED_IR_V4_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "ee69a93c45a2b16676c49bfb0a01749a5c4ea1e2",
    "canonical/verification/TRAJECTORY_INFORMATION_SAFE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "c571023e8b126c558f3995b2b0d348a7fbd084a0",
    "canonical/capabilities/opus55/TRAJECTORY_INVARIANT_CHECKER_HELDOUT_EVIDENCE_V1.json": "53edb3eb870250e690afefbe0db4e85100936357",
    "canonical/capabilities/opus55/TRAJECTORY_INVARIANT_CHECKER_CANDIDATE_V1.json": "d11f9c88d8bae44fcef14f9e27a5a23d65f6e91e",
}

EXPECTED_SURFACES = {
    "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
    "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
}
REQUIRED_SEMANTICS = {"DIRECT_CONTRACT", "DERIVED_UPSTREAM"}

def _load(path: str) -> dict[str, Any]:
    v=json.loads((ROOT/path).read_text(encoding="utf-8"))
    if not isinstance(v,dict):
        raise ValueError(path+":NOT_OBJECT")
    return v

def _blob_sha(path: str) -> str:
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def _contains(value: Any, literal: str) -> bool:
    if isinstance(value,str):
        return literal in value
    if isinstance(value,Mapping):
        return any(_contains(k,literal) or _contains(v,literal) for k,v in value.items())
    if isinstance(value,list):
        return any(_contains(x,literal) for x in value)
    return False

def _p1_receipts(wave: Mapping[str,Any]) -> list[Mapping[str,Any]]:
    out=[]
    parents=(((wave.get("reduction_input") or {}).get("wave") or {}).get("parent_portfolio_receipts") or {})
    for tier in ("T0","T2"):
        for row in parents.get(tier,[]) or []:
            if isinstance(row,Mapping) and row.get("behavior_id")=="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":
                out.append(row)
    return out

def evaluate(docs: Mapping[str, Mapping[str,Any]]) -> dict[str,Any]:
    errors=[]
    binding=docs["binding"]
    manifest=docs["manifest"]
    wave=docs["wave"]
    ident=docs["ident"]
    preflight=docs["preflight"]
    typed_v4=docs["typed_v4"]
    info_v2=docs["info_v2"]
    invariant_evidence=docs["invariant_evidence"]
    invariant_candidate=docs["invariant_candidate"]

    if set(binding.get("direct_surface_bindings") or []) != EXPECTED_SURFACES:
        errors.append("DIRECT_SURFACE_SET_DRIFT")

    verified=set(ident.get("verified_consequences") or [])
    required_ident={
        "CURRENT_FROZEN_TRANSPORT_PROJECTION_UNDERDETERMINES_V7_FAILURE_SEMANTICS",
        "NO_DETERMINISTIC_ADAPTER_USING_ONLY_CURRENT_PROJECTED_FIELDS_CAN_BE_UNIVERSALLY_SOUND",
        "MINIMUM_MISSING_FACT_IS_FAILURE_SEMANTICS_OR_AN_INDEPENDENTLY_PROVED_EQUIVALENT_DISCRIMINATOR",
    }
    if not required_ident <= verified:
        errors.append("IDENTIFIABILITY_PREMISE_NOT_VERIFIED")

    visible=set(binding.get("candidate_visible_information") or [])
    expected_visible={
        "NORMALIZED_EXECUTION_TRAJECTORY",
        "EXPLICIT_GOAL_PLAN_AND_TOOL_CONTRACTS",
        "STATIC_DYNAMIC_TEMPORAL_AUTHORITY_SCHEMA_AND_DEPENDENCY_INVARIANTS_WHEN_APPLICABLE",
        "INVARIANT_CHECK_RECEIPTS",
        "OBSERVED_TERMINAL_FAILURE",
        "VISIBLE_ACTION_TOOL_FILE_BROWSER_CODE_ARTIFACT_RESEARCH_AND_PROVENANCE_EVENTS",
        "EARNED_TOOL_OUTPUTS_AND_EXECUTION_RECEIPTS",
    }
    if visible != expected_visible:
        errors.append("VISIBLE_INFORMATION_SET_DRIFT")

    # Existing bound helpers establish mechanics/classes but do not declare the
    # missing direct-vs-derived semantics transport.
    if "P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF" not in set(preflight.get("verified_routes") or []):
        errors.append("DIRECT_PROOF_PREFLIGHT_DRIFT")
    mechanism_classes=set(((typed_v4.get("verified") or {}).get("mechanism_classes") or []))
    if not {"AUTHORITY","PROVENANCE","DEPENDENCY"} <= mechanism_classes:
        errors.append("TYPED_V4_MECHANISM_CLASS_DRIFT")
    if "GENERAL_ROOT_CAUSE_REASONING" not in set(invariant_candidate.get("explicitly_not_claimed") or []):
        errors.append("INVARIANT_CHECKER_SCOPE_DRIFT")
    unresolved=set(((invariant_evidence.get("causal_scope") or {}).get("still_unresolved") or []))
    if "GENERAL_ROOT_CAUSE_REASONING" not in unresolved:
        errors.append("INVARIANT_EVIDENCE_SCOPE_DRIFT")
    if not str(info_v2.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("INFO_SAFE_V2_NOT_INDEPENDENT_PASS")

    receipts=_p1_receipts(wave)
    if len(receipts)!=2:
        errors.append("EXPECTED_TWO_AGGREGATE_P1_RECEIPTS")
    aggregate_keys=sorted({k for r in receipts for k in r.keys()})
    event_level_transport_declared=any(
        k in {"failure_semantics","failure_semantics_source","failure_semantics_mapping",
              "direct_derived_discriminator","proof_preserving_failure_semantics_adapter"}
        for k in aggregate_keys
    )

    explicit_source_docs={
        "binding":binding,
        "manifest":manifest,
        "wave":wave,
        "preflight":preflight,
        "typed_v4":typed_v4,
        "info_v2":info_v2,
        "invariant_evidence":invariant_evidence,
        "invariant_candidate":invariant_candidate,
    }
    presence={
        name:{
            "failure_semantics_literal":_contains(doc,"failure_semantics"),
            "DIRECT_CONTRACT_literal":_contains(doc,"DIRECT_CONTRACT"),
            "DERIVED_UPSTREAM_literal":_contains(doc,"DERIVED_UPSTREAM"),
        }
        for name,doc in explicit_source_docs.items()
    }
    complete_explicit_source=[
        name for name,row in presence.items()
        if row["failure_semantics_literal"] and row["DIRECT_CONTRACT_literal"] and row["DERIVED_UPSTREAM_literal"]
    ]

    if errors:
        status="FAIL_CLOSED__SOURCE_OR_AUTHORITY_DRIFT__ZERO_CREDIT"
        classification="INVALID_INPUT_OR_AUTHORITY_DRIFT"
    elif complete_explicit_source or event_level_transport_declared:
        status="CANDIDATE_EXISTING_UPSTREAM_FAILURE_SEMANTICS_SOURCE_FOUND__SEMANTIC_VERIFICATION_REQUIRED__ZERO_CREDIT"
        classification="CANDIDATE_SOURCE_PRESENT"
    else:
        status="FAIL_CLOSED__NO_EXPLICIT_BOUND_UPSTREAM_FAILURE_SEMANTICS_SOURCE_IN_FROZEN_P1_EVIDENCE_SET__ZERO_CREDIT"
        classification="INFORMATION_OR_SPECIFICATION_RESIDUAL"

    return {
        "schema":SCHEMA,
        "status":status,
        "classification":classification,
        "errors":sorted(set(errors)),
        "surface_count":len(EXPECTED_SURFACES),
        "surfaces":sorted(EXPECTED_SURFACES),
        "identifiability_premise_verified":not any(e=="IDENTIFIABILITY_PREMISE_NOT_VERIFIED" for e in errors),
        "current_projection_is_insufficient":True if not errors else None,
        "explicit_source_presence":presence,
        "complete_explicit_source_documents":complete_explicit_source,
        "aggregate_p1_receipt_count":len(receipts),
        "aggregate_p1_receipt_keys":aggregate_keys,
        "event_level_transport_declared_in_aggregate_receipts":event_level_transport_declared,
        "scope_statement":"THIS_AUDIT_CLASSIFIES_ONLY_THE_EXACT_FROZEN_BOUND_UPSTREAM_SOURCE_SET__IT_DOES_NOT_PROVE_UNIVERSAL_ABSENCE_FROM_ALL_POSSIBLE_FUTURE_EVIDENCE",
        "next":(
            "IF_INDEPENDENTLY_VERIFIED__CLASSIFY_P1_FAILURE_SEMANTICS_AS_INFORMATION_OR_SPECIFICATION_RESIDUAL__"
            "KEEP_P1_QUARANTINE_ACTIVE__DO_NOT_GUESS_ADAPTER__"
            "ONLY_A_CONTENT_ADDRESSED_NEWLY_DISCOVERED_UPSTREAM_SOURCE_OR_SEPARATELY_AUTHORIZED_MINIMUM_REALITY_INFORMATION_CAN_DISCHARGE"
            if classification=="INFORMATION_OR_SPECIFICATION_RESIDUAL" else
            "INDEPENDENTLY_VERIFY_ANY_CANDIDATE_SOURCE_SEMANTICS_AND_SCOPE_BEFORE_CREDIT"
        ),
        "terminal_results_replayed":0,
        "new_reality_units_consumed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }

def execute() -> dict[str,Any]:
    drift=[p for p,sha in SOURCES.items() if _blob_sha(p)!=sha]
    if drift:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT__ZERO_CREDIT",
            "classification":"INVALID_INPUT_OR_AUTHORITY_DRIFT","errors":["BLOB_DRIFT:"+p for p in drift],
            "terminal_results_replayed":0,"new_reality_units_consumed":0,"incremental_spend_usd":0,
            "capability_credit_delta":0,"family_credit_delta":0,"execution_authority":False,"promotion_authority":False,
        }
    docs={
        "binding":_load("canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"),
        "manifest":_load("canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json"),
        "wave":_load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"),
        "ident":_load("canonical/verification/P1_V7_DIRECT_SURFACE_TRANSPORT_AND_IDENTIFIABILITY_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
        "preflight":_load("canonical/verification/FOUR_DIRECT_PROOF_MUTATION_PREFLIGHT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
        "typed_v4":_load("canonical/verification/TRAJECTORY_TYPED_IR_V4_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
        "info_v2":_load("canonical/verification/TRAJECTORY_INFORMATION_SAFE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
        "invariant_evidence":_load("canonical/capabilities/opus55/TRAJECTORY_INVARIANT_CHECKER_HELDOUT_EVIDENCE_V1.json"),
        "invariant_candidate":_load("canonical/capabilities/opus55/TRAJECTORY_INVARIANT_CHECKER_CANDIDATE_V1.json"),
    }
    return evaluate(docs)

def main() -> int:
    out=execute()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 1 if out["classification"]=="INVALID_INPUT_OR_AUTHORITY_DRIFT" else 0

if __name__=="__main__":
    raise SystemExit(main())
