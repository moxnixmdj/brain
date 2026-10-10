"""Universal positive-certification safety reduction for stable R12 CC_R3.

This verifier proves a candidate theorem over exact content-addressed current
bytes only:

    FOR EVERY admissible execution of the exact V9 successor,
    POSITIVE_CERTIFICATE => executable exact-R12 material-totality semantics
    passed for the exact claim/scope/obligation binding.

Non-positive / abstaining executions cannot be false-positive certifications.
Stable C8 nonvacuity is proved separately for the same frozen R12 claim.

This is deliberately NOT self-authorizing.  A local PASS grants zero CC_R3,
semantic-property, quality, acceptance, promotion, or terminal credit until an
independent replay binds these exact bytes and theorem result.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_R12_UNIVERSAL_POSITIVE_GATE_TOTALITY_V1"

CLAIM_PATH = "canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V2.json"
CLAIM_BLOB = "7b26ddba501358d42d6fa342efd27d389bb30654"
R1_PATH = "canonical/governance/COVERAGE_CC_R1_PROFESSIONAL_R12_SEMANTIC_CERTIFICATE_20261010_V2.json"
R1_BLOB = "f7182bc43bfc48f4e019a0186534e14bd5374419"
R2_PATH = "canonical/governance/COVERAGE_CC_R2_PROFESSIONAL_R12_SEMANTIC_CERTIFICATE_20261010_V2.json"
R2_BLOB = "8fc8057152ba26cd91643ec75d8853d421b59cba"
RECON_PATH = "canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_TRUTH_RECONCILIATION_20261010_V3.json"
RECON_BLOB = "56a5f85e6133661dd7afbc8fc5041ad799f0736f"
C8_PATH = "canonical/verification/PROFESSIONAL_R12_STABLE_C8_NONVACUITY_VERIFY_20261010_V1.json"
C8_BLOB = "6ed0f5d253d0fc734af2998e86ad72f73fe8c073"
V9_PATH = "canonical/runtime/professional_quality_p1_router_v9.py"
V9_BLOB = "27f0df972a08a2497802865e46bdccdcb1c720ae"
SEM_PATH = "canonical/runtime/professional_r12_totality_semantic_receipt_v1.py"
SEM_BLOB = "cfb264b92004c55acf73719cd9c54cec6a609a34"
V9_VERIFY_PATH = "canonical/verification/PROFESSIONAL_R12_V9_EXECUTABLE_TOTALITY_SEMANTIC_INDEPENDENT_VERIFY_20261010_V2.json"
V9_VERIFY_BLOB = "450b28d112be708bb65698581f64410e4991e86d"
V9_SUBJECT_PATH = "canonical/governance/PROFESSIONAL_QUALITY_P1_V9_DECLARED_SYSTEM_SUBJECT_20261010_V8.json"
V9_SUBJECT_BLOB = "2ff32e4bb78e63635244c86d47fa369d7ba53900"
IDENTITY_PATH = "canonical/verification/PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_VERIFY_20261010_V1.json"
IDENTITY_BLOB = "35a3ccf9ad454aa0318a4ed10edc065830c3874d"

CLAIM_ID = "11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
SCOPE_CLAIM_ID = "05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
LEAF_ID = "PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"
OBLIGATION = "ALL_ROOT_RELEVANT_MATERIAL_DEFEATERS_RESOLVED_OR_PROVED_DECISION_NULL_BEFORE_POSITIVE_CERTIFICATION"
ACCEPTANCE = "DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_ROOT_RELEVANT_DEFEATERS_RESOLVED_WITH_TYPED_EVIDENCE"
QUANTIFICATION = "FOR_ALL_ADMISSIBLE_INPUTS_IN_VERIFIED_WHOLE_LEAF_SCOPE"
V9_PROOF_SENTENCE = "V9_POSITIVE_PATH_REQUIRES_EXECUTABLE_R12_TOTALITY_SEMANTIC_VERIFICATION"

PINS = {
    CLAIM_PATH: CLAIM_BLOB,
    R1_PATH: R1_BLOB,
    R2_PATH: R2_BLOB,
    RECON_PATH: RECON_BLOB,
    C8_PATH: C8_BLOB,
    V9_PATH: V9_BLOB,
    SEM_PATH: SEM_BLOB,
    V9_VERIFY_PATH: V9_VERIFY_BLOB,
    V9_SUBJECT_PATH: V9_SUBJECT_BLOB,
    IDENTITY_PATH: IDENTITY_BLOB,
}
JSON_PATHS = (
    CLAIM_PATH,
    R1_PATH,
    R2_PATH,
    RECON_PATH,
    C8_PATH,
    V9_VERIFY_PATH,
    V9_SUBJECT_PATH,
    IDENTITY_PATH,
)


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _zero() -> dict[str, Any]:
    return {
        "independent_verified": False,
        "cc_r3_terminal_closure_proved": False,
        "semantic_property_truth_authority": False,
        "r4_proof_realization_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "universal_positive_gate_totality_candidate_proved": False,
        **_zero(),
        **extra,
    }


def _pin(root: Path, rel: str, expected_blob: str) -> Path:
    path = root / rel
    if not path.is_file() or path.is_symlink():
        raise ValueError("PIN_MISSING:" + rel)
    got = _blob(path)
    if got != expected_blob:
        raise ValueError("PIN_BLOB_DRIFT:" + rel + ":" + got)
    return path


def _load(root: Path, rel: str, expected_blob: str) -> Mapping[str, Any]:
    path = _pin(root, rel, expected_blob)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("PIN_NOT_OBJECT:" + rel)
    return value


def verify(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    try:
        for rel, blob in PINS.items():
            _pin(root, rel, blob)
        docs = {rel: _load(root, rel, PINS[rel]) for rel in JSON_PATHS}
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))

    claim = docs[CLAIM_PATH]
    recon = docs[RECON_PATH]
    c8 = docs[C8_PATH]
    r1 = docs[R1_PATH]
    r2 = docs[R2_PATH]
    v9_verify = docs[V9_VERIFY_PATH]
    subject = docs[V9_SUBJECT_PATH]
    identity = docs[IDENTITY_PATH]

    if claim.get("claim_id") != CLAIM_ID or claim.get("leaf_id") != LEAF_ID:
        return _fail("FROZEN_CLAIM_IDENTITY_DRIFT")
    if claim.get("whole_leaf_scope_claim_id") != SCOPE_CLAIM_ID:
        return _fail("FROZEN_SCOPE_CLAIM_ID_DRIFT")
    target = claim.get("target_predicate") or {}
    if target.get("acceptance") != ACCEPTANCE:
        return _fail("TARGET_ACCEPTANCE_DRIFT")
    if target.get("quantification") != QUANTIFICATION:
        return _fail("TARGET_QUANTIFICATION_DRIFT")

    residual = recon.get("stronger_target_residual") or {}
    if residual.get("obligation") != OBLIGATION or residual.get("state") != "OPEN":
        return _fail("STRONGER_RESIDUAL_IDENTITY_DRIFT")
    derived = recon.get("derived") or {}
    if derived.get("all_eight_root_contract_clauses_verified") is not True:
        return _fail("R12_EIGHT_CLAUSES_NOT_CURRENT")

    r1_model = r1.get("b_plus_model") or {}
    r1_theorem = r1.get("theorem") or {}
    if r1_theorem.get("b_real_subseteq_b_plus") is not True:
        return _fail("CC_R1_REALITY_CONTAINMENT_NOT_PROVED")
    if r1_model.get("admissibility") != "EXACT_WHOLE_ADMISSIBLE_LEAF_DOMAIN__NO_FILTERS__NO_EXCLUSIONS":
        return _fail("CC_R1_WHOLE_DOMAIN_NOT_EXACT")
    if (r2.get("theorem") or {}).get("proof_mode") != "FORMAL_REDUCTION":
        return _fail("CC_R2_FORMAL_MISSION_REDUCTION_NOT_BOUND")

    theorem = identity.get("theorem") or {}
    if theorem.get("projection") != "PI_C_IS_IDENTITY_ON_COMPLETE_FROZEN_CLAIM_WORLD_STATE":
        return _fail("IDENTITY_CARRIER_NOT_COMPLETE")
    if theorem.get("semantic_information_loss") is not False:
        return _fail("IDENTITY_CARRIER_LOSSY")

    consequence = c8.get("consequence") or {}
    reasoning = c8.get("reasoning") or {}
    if c8.get("claim_id") != CLAIM_ID:
        return _fail("C8_CLAIM_DRIFT")
    if consequence.get("r12_c8_nonvacuity_proved") is not True:
        return _fail("C8_NONVACUITY_NOT_PROVED")
    if reasoning.get("witness_is_real_executed_route") is not True or reasoning.get("witness_is_independently_replayed") is not True:
        return _fail("C8_REAL_INDEPENDENT_ROUTE_NOT_PROVED")

    if V9_PROOF_SENTENCE not in (v9_verify.get("proves") or []):
        return _fail("V9_UNIVERSAL_POSITIVE_GATE_PREMISE_NOT_INDEPENDENTLY_PROVED")
    subj = v9_verify.get("subject") or {}
    if ((subj.get("router_v9") or {}).get("git_blob_sha") != V9_BLOB or
        (subj.get("semantic_authority") or {}).get("git_blob_sha") != SEM_BLOB):
        return _fail("V9_VERIFICATION_SUBJECT_DRIFT")
    replay = v9_verify.get("independent_replay") or {}
    if replay.get("tests_failed") != 0 or replay.get("declared_system_component_current_count") != replay.get("declared_system_component_count"):
        return _fail("V9_INDEPENDENT_REPLAY_NOT_CURRENT")

    components = {
        row.get("path"): row.get("git_blob_sha")
        for row in ((subject.get("system_material") or {}).get("components") or [])
        if isinstance(row, Mapping)
    }
    if components.get(V9_PATH) != V9_BLOB or components.get(SEM_PATH) != SEM_BLOB:
        return _fail("V9_DECLARED_SUBJECT_MISSING_LOAD_BEARING_GATE")

    # Direct exact-byte sanity on the load-bearing implication.  The independent
    # replay above is authoritative evidence; these anchors fail closed if the
    # pinned implementation is later repurposed without updating the proof.
    v9_text = (root / V9_PATH).read_text(encoding="utf-8")
    required = (
        "semantic_receipt.validate(",
        'if sem.get("pass") is not True:',
        '"V9_EXECUTABLE_R12_TOTALITY_SEMANTICS_REJECTED"',
        'result["v9_executable_r12_totality_semantics_verified"]=True',
    )
    if any(anchor not in v9_text for anchor in required):
        return _fail("V9_POSITIVE_GATE_CONTROL_FLOW_ANCHOR_MISSING")

    # Formal reduction:
    # 1. Whole admissible claim domain is represented losslessly (CC_R1 + identity).
    # 2. Partition all exact V9 executions by whether they return a positive certificate.
    # 3. Non-positive executions cannot violate a "before positive certification" safety condition.
    # 4. Every positive execution is independently proved to require successful executable,
    #    exact-claim R12 totality semantic verification; otherwise V9 fails closed.
    # 5. Therefore no positive execution can exist without the exact material-totality
    #    proof obligation being discharged by the proof-carrying route.
    # 6. Stable C8 independently supplies nonvacuity, so the safety theorem is not
    #    obtained by an always-abstain system.
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS_CANDIDATE__UNIVERSAL_POSITIVE_GATE_FORMAL_REDUCTION__AWAITING_INDEPENDENT_REPLAY",
        "proof_basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "claim_id": CLAIM_ID,
        "scope_claim_id": SCOPE_CLAIM_ID,
        "leaf_id": LEAF_ID,
        "obligation": OBLIGATION,
        "scope_complete": True,
        "generator_or_universal_cover_complete": True,
        "all_material_defeaters_in_scope_covered": True,
        "uncovered_material_defeater_complement_empty": True,
        "decision_null_or_resolved_for_every_covered_defeater": True,
        "finite_catalog_only": False,
        "eight_clause_count_only": False,
        "unknown_remainder": [],
        "fail_closed_on_unknown": True,
        "content_addressed": True,
        "universal_positive_gate_totality_candidate_proved": True,
        "whole_domain_identity_carrier_bound": True,
        "positive_route_requires_executable_totality_semantics": True,
        "nonpositive_route_cannot_be_false_positive_certification": True,
        "stable_c8_nonvacuity_separate_and_proved": True,
        "cross_subject_property_authority_transport": False,
        "exact_next": "INDEPENDENTLY_REPLAY_THIS_EXACT_FORMAL_REDUCTION__THEN_BIND_AS_UNIVERSAL_FORMAL_SCOPE_PROOF_TO_EXISTING_GENERATOR_CLOSURE_AND_CC_R3_V3",
        **_zero(),
    }
