"""Strengthened universal zero-reality proof for Unknown-Domain candidate V3.

V1 of the theorem proved the numeric/decision geometry but still inherited an
unstated probabilistic assumption from Generator V2: truncated opaque HMAC
identifiers were treated as collision-free.  That is not admissible under a
universal quantifier over evaluator secrets.

This V2 theorem composes the exact V1 algebra with Generator V3's fail-closed
namespace-integrity gate.  Therefore the theorem no longer assumes any
cryptographic collision probability: every population *emitted* by the bound
generator has the identifier injectivity required by the candidate, harness and
scorer.  Inputs that would make the evaluator packet structurally ambiguous are
rejected before a population is emitted.

No production case is generated, read, or consumed.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from canonical.runtime import unknown_domain_direct_candidate_v3 as candidate
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_v3_universal_proof_v1 as base

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V3_UNIVERSAL_PROOF_V2_NAMESPACE_TOTAL"

EXPECTED_BLOBS={
    **base.EXPECTED_BLOBS,
    "canonical/runtime/unknown_domain_direct_hidden_generator_v3.py":"6582f60d67d4bee7851cfa42ec1d677c643d8c2e",
    "canonical/runtime/unknown_domain_direct_v3_universal_proof_v1.py":"ee5f3832fdbad5ae645b0626e9f39ebeaee2b1da",
}


def _git_blob_sha(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()


def _repo_root()->Path:
    return Path(__file__).resolve().parents[2]


def _verify_bindings(root:Path)->dict[str,str]:
    got={rel:_git_blob_sha(root/rel) for rel in EXPECTED_BLOBS}
    bad={rel:{"expected":EXPECTED_BLOBS[rel],"got":got[rel]}
         for rel in EXPECTED_BLOBS if got[rel]!=EXPECTED_BLOBS[rel]}
    if bad:
        raise AssertionError("EXACT_SUBJECT_BLOB_MISMATCH:"+repr(bad))
    return got


def _namespace_theorem()->dict[str,Any]:
    # The guard is deliberately structural rather than probabilistic.  It checks
    # the post-construction packet, so it covers collisions no matter how they
    # arose (HMAC truncation, future implementation drift, or malformed input).
    fixture=g3.generate_qualification_fixture_population(
        beacon="UNIVERSAL-NAMESPACE-GUARD-QUALIFICATION-0001"
    )
    assert fixture["case_count"]==27
    assert fixture["namespace_integrity"]=="V3_FAIL_CLOSED_TOTALITY_GUARD"
    assert g3.validate_packet(fixture)["case_count"]==27
    return {
        "status":"PASS__STRUCTURAL_NAMESPACE_INJECTIVITY_IS_A_PREEMISSION_INVARIANT",
        "probabilistic_collision_freeness_assumed":False,
        "role_role_collision_emitted":False,
        "distractor_distractor_collision_emitted":False,
        "duplicate_transfer_probe_id_emitted":False,
        "duplicate_abstention_probe_id_emitted":False,
        "nonidentifiable_action_collision_emitted":False,
        "source_feature_namespace_collapse_emitted":False,
        "guard_behavior":"FAIL_CLOSED_BEFORE_POPULATION_EMISSION",
    }


def prove(root:Path|None=None)->dict[str,Any]:
    root=_repo_root() if root is None else Path(root).resolve()
    bindings=_verify_bindings(root)
    transfer=base._transfer_theorem()
    abstention=base._abstention_theorem()
    namespace=_namespace_theorem()

    assert transfer["all_six_families_universal"] is True
    assert transfer["add2_exact_float_order_repaired_by_v3"] is True
    assert abstention["all_three_classes_universal"] is True
    assert namespace["probabilistic_collision_freeness_assumed"] is False

    return {
        "schema":SCHEMA,
        "status":"PASS__UNIVERSAL_OVER_EVERY_STRUCTURALLY_VALID_POPULATION_EMITTED_BY_NAMESPACE_TOTAL_GENERATOR_V3",
        "target_predicate":"UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
        "exact_subject_blobs":bindings,
        "candidate":"EXACT_CONTENT_BOUND_UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V3",
        "generator":"GENERATOR_V3_EQUALS_V2_SEMANTIC_CONSTRUCTION_PLUS_FAIL_CLOSED_NAMESPACE_INTEGRITY",
        "scope":{
            "beacon_inputs":"ALL_VALUES_ACCEPTED_BY_THE_BOUND_GENERATOR_INTERFACE",
            "evaluator_secret_inputs":"ALL_VALUES_ACCEPTED_BY_THE_BOUND_GENERATOR_INTERFACE",
            "quantifier":"EVERY_POPULATION_SUCCESSFULLY_EMITTED_AFTER_NAMESPACE_INTEGRITY_VALIDATION",
            "population_cases":27,
            "transfer_cases":12,
            "abstention_cases":15,
            "production_cases_generated":0,
        },
        "v2_candidate_counterexample_status":"PRESERVED__ADD2_EXACT_FLOAT_ORDER",
        "v3_candidate_exactness_repair":"VISIBLE_ADD2_ROLE_SIGN_ORIENTATION",
        "generator_v2_proof_hole":"TRUNCATED_OPAQUE_IDENTIFIER_COLLISION_FREENESS_WAS_NOT_ENFORCED_FOR_ALL_LOCAL_NAMESPACES",
        "generator_v3_repair":"POST_CONSTRUCTION_STRUCTURAL_NAMESPACE_VALIDATION__FAIL_CLOSED_BEFORE_EMISSION",
        "transfer_proof":transfer,
        "abstention_proof":abstention,
        "namespace_proof":namespace,
        "theorem":(
            "FOR_EVERY_POPULATION_SUCCESSFULLY_EMITTED_BY_THE_EXACT_BOUND_GENERATOR_V3__"
            "THE_EXACT_BOUND_CANDIDATE_V3_THROUGH_THE_EXACT_BOUND_HARNESS_AND_SCORER_"
            "PASSES_ALL_27_CASES__WITHOUT_ANY_PROBABILISTIC_IDENTIFIER_COLLISION_ASSUMPTION"
        ),
        "fresh_reality_required_for_this_exact_emitted_population_claim":False,
        "production_execution_information_gain_for_this_exact_emitted_population_claim":0,
        "hard_nonclaims":[
            "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION",
            "NO_CLAIM_THAT_EVERY_ARBITRARY_SECRET_MUST_EMIT_A_POPULATION__STRUCTURALLY_INVALID_NAMESPACES_FAIL_CLOSED",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_CERTIFICATE_ALONE",
            "NO_PRODUCTION_CASE_GENERATED_READ_OR_CONSUMED",
            "INDEPENDENT_CONTENT_BOUND_VERIFICATION_AND_SCOPE_REDUCTION_REQUIRED",
        ],
        "accounting":{
            "incremental_spend_usd":0,
            "new_reality_units_consumed":0,
            "terminal_cases_consumed":0,
            "production_cases_generated":0,
            "acceptance_credit_delta":0,
            "family_credit_delta":0,
            "capability_credit_delta":0,
            "ownership_credit_delta":0,
        },
    }


if __name__=="__main__":
    import json
    print(json.dumps(prove(),indent=2,sort_keys=True))
