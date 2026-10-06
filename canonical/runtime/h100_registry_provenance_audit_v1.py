"""Dual-ledger provenance audit for compiled H100 registry entries.

This audit does not re-evaluate capability quality. It asks whether a capability
that was selected using development evidence and then persisted for future reuse
can still be called "zero learned" merely because it is represented as
deterministic code.

Two accounting ledgers are reported:
- SYNTACTIC_V0: deterministic code container is exempt.
- PROVENANCE_V1: persisted data-dependent capability state is learned-origin.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from canonical.runtime import h100_provenance_invariant_learned_information_v1 as prov

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_H100_REGISTRY_PROVENANCE_AUDIT_V1"

CUBIC_PRE=ROOT/"canonical/governance/H100_MINIMAL_PATCH_SEARCH_PRECOMMIT_V1.json"
CUBIC_VER=ROOT/"canonical/verification/H100_MINIMAL_PATCH_SEARCH_SEPARATE_RUNTIME_VERIFICATION_20261005_V1.json"
CUBIC_REG=ROOT/"canonical/runtime/h100_verified_capability_registry_v2.py"

CHAIN_PRE=ROOT/"canonical/governance/H100_COMPLETE_UNARY_CHAIN_SEARCH_PRECOMMIT_V1.json"
CHAIN_VER=ROOT/"canonical/verification/H100_COMPLETE_UNARY_CHAIN_SEARCH_SECOND_CARRIER_VERIFICATION_20261005_V1.json"
CHAIN_REG=ROOT/"canonical/runtime/h100_verified_capability_registry_v8.py"


class RegistryProvenanceAuditError(ValueError):
    pass


def _json(path:Path)->dict[str,Any]:
    obj=json.loads(path.read_text())
    if not isinstance(obj,dict):
        raise RegistryProvenanceAuditError("JSON_OBJECT_REQUIRED:"+str(path))
    return obj


def cubic_witness()->dict[str,Any]:
    pre=_json(CUBIC_PRE)
    ver=_json(CUBIC_VER)
    src=CUBIC_REG.read_text()

    grammar=list(pre["patch_grammar"])
    if len(grammar)!=3:
        raise RegistryProvenanceAuditError("CUBIC_GRAMMAR_COUNT_CHANGED")
    hard=set(map(str,pre.get("hard_nonclaims",[])))
    if "PATCH_GRAMMAR_WAS_DESIGNED_AFTER_OBSERVING_A_CUBIC_DEVELOPMENT_MISS" not in hard:
        raise RegistryProvenanceAuditError("CUBIC_POSTMISS_PROVENANCE_NOT_BOUND")
    selected=str(ver["observed"]["selected_patch_id"])
    if selected!="AFFINE_PLUS_X3":
        raise RegistryProvenanceAuditError("CUBIC_SELECTED_STRUCTURE_CHANGED")
    if '"fixed_power":3' not in src or "H100_MINIMAL_PATCH_SEARCH_SEPARATE_RUNTIME_VERIFICATION_20261005_V1.json" not in src:
        raise RegistryProvenanceAuditError("CUBIC_NOT_PERSISTED_IN_REGISTRY_V2")

    pa=prov.audit_compiled_selection(
        capability_id="CAP_AFFINE_CUBIC_V1",
        candidate_count=3,
        selected_after_observing_development_data=True,
        persisted_in_registry=True,
    )
    return {
        "id":"CUBIC_V2",
        "candidate_count":3,
        "selected_structure":selected,
        "fixed_length_selection_capacity_bits":pa["selection_capacity"]["fixed_length_selection_index_bits"],
        "max_selection_entropy_bits":pa["selection_capacity"]["max_selection_entropy_bits"],
        "provenance_v1_learned_origin":pa["provenance"]["learned_origin_state"],
        "syntactic_v0_reported_learned_bytes":0,
        "exact_mutual_information_bits_claimed":None,
        "registry_persistence_verified":True,
    }


def chain_witness()->dict[str,Any]:
    pre=_json(CHAIN_PRE)
    ver=_json(CHAIN_VER)
    src=CHAIN_REG.read_text()

    n=int(pre["expected_enumeration_count"]["cumulative_through_depth4"])
    if n!=1554:
        raise RegistryProvenanceAuditError("CHAIN_CANDIDATE_COUNT_CHANGED")
    fresh=list(pre["fresh_tasks"])
    if len(fresh)!=3:
        raise RegistryProvenanceAuditError("CHAIN_TASK_COUNT_CHANGED")
    obs=ver["observed"]
    if not bool(obs["all_depth4_exact_count_one"]):
        raise RegistryProvenanceAuditError("CHAIN_UNIQUE_SELECTION_NOT_VERIFIED")

    expected_ids=[
        "CAP_AFFINE_CHAIN_SQUARE_LOG_SQRT_SAT_V1",
        "CAP_AFFINE_CHAIN_SAT_SQUARE_LOG_SQRT_V1",
        "CAP_AFFINE_CHAIN_LOG_SAT_SQRT_LOG_V1",
    ]
    if any(cid not in src for cid in expected_ids):
        raise RegistryProvenanceAuditError("CHAIN_NOT_PERSISTED_IN_REGISTRY_V8")
    if "H100_COMPLETE_UNARY_CHAIN_SEARCH_SECOND_CARRIER_VERIFICATION_20261005_V1.json" not in src:
        raise RegistryProvenanceAuditError("CHAIN_REGISTRY_PROVENANCE_NOT_BOUND")

    one=prov.selection_capacity_bits(n)
    audits=[
        prov.audit_compiled_selection(
            capability_id=cid,
            candidate_count=n,
            selected_after_observing_development_data=True,
            persisted_in_registry=True,
        )
        for cid in expected_ids
    ]
    return {
        "id":"DEPTH4_V8",
        "candidate_count_per_task":n,
        "persisted_structure_count":len(expected_ids),
        "fixed_length_selection_capacity_bits_per_structure":one["fixed_length_selection_index_bits"],
        "aggregate_fixed_length_selection_capacity_bits":len(expected_ids)*one["fixed_length_selection_index_bits"],
        "max_selection_entropy_bits_per_structure":one["max_selection_entropy_bits"],
        "all_provenance_v1_learned_origin":all(x["provenance"]["learned_origin_state"] for x in audits),
        "syntactic_v0_reported_learned_bytes":0,
        "exact_mutual_information_bits_claimed":None,
        "registry_persistence_verified":True,
    }


def run()->dict[str,Any]:
    cubic=cubic_witness()
    chain=chain_witness()
    witness_count=1+int(chain["persisted_structure_count"])
    prov_nonzero=bool(cubic["provenance_v1_learned_origin"] and chain["all_provenance_v1_learned_origin"])
    return {
        "schema":SCHEMA,
        "status":"PASS__DUAL_LEDGER_DIVERGENCE_ESTABLISHED__PROVENANCE_V1_ZERO_RUNG_FALSIFIED__EXACT_BYTES_UNQUANTIFIED",
        "witnesses":[cubic,chain],
        "persistent_data_selected_structure_witness_count":witness_count,
        "syntactic_v0":{
            "zero_learned_claim_survives_for_these_registry_entries":True,
            "reason":"DETERMINISTIC_CODE_CONTAINER_EXEMPT_BY_DEFINITION",
        },
        "provenance_v1":{
            "zero_learned_claim_survives_for_these_registry_entries":not prov_nonzero,
            "nonzero_learned_origin_state_established":prov_nonzero,
            "exact_learned_origin_bytes":None,
            "reason":"SELECTED_STRUCTURE_VALUE_DEPENDS_ON_DEVELOPMENT_EVIDENCE_AND_PERSISTS_FOR_FUTURE_REUSE",
        },
        "minimum_revision_to_A_claim":"REPORT_ZERO_LEARNED_ONLY_AS_SYNTACTIC_V0__UNDER_PROVENANCE_V1_THE_CURRENT_COMPILED_RATCHET_HAS_NONZERO_LEARNED_ORIGIN_STATE",
        "hard_nonclaims":[
            "SELECTION_CAPACITY_BITS_ARE_NOT_EXACT_MUTUAL_INFORMATION",
            "AUDIT_DOES_NOT_CLASSIFY_EVERY_REGISTRY_ENTRY",
            "AUDIT_DOES_NOT_YET_QUANTIFY_TOTAL_PROVENANCE_V1_BYTES",
            "NO_TERMINAL_CREDIT",
        ],
        "h100_terminal_credit_delta":0,
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
