from pathlib import Path
import json

from canonical.runtime.coverage_cc_r3_r3_promotion_safety_verify_v1 import verify_certificate
from canonical.runtime.root_theorem_falsifier_v1 import evaluate_canonical_registry_authority

ROOT=Path(__file__).resolve().parents[2]
CLAIM=ROOT/"canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_R3_PROMOTION_SAFETY_20261010_V1.json"
CERT=ROOT/"canonical/governance/COVERAGE_CC_R3_R3_PROMOTION_SAFETY_CERTIFICATE_20261010_V1.json"

def test_cc_r3_semantic_certificate_and_canonical_authority_shape():
    claim=json.loads(CLAIM.read_text(encoding="utf-8"))
    semantic=verify_certificate(
        root=ROOT,
        certificate_path=CERT,
        active_claim=claim,
        root_id="CC_R3_TERMINAL_CLOSURE_V1",
    )
    assert semantic["pass"] is True, semantic
    authority=evaluate_canonical_registry_authority()
    assert authority["status"]=="R4_CANONICAL_ROOT_CERTIFICATES_OPEN", authority
    assert authority["authorized"] is False
    registry=authority["registry"]
    assert registry["pass"] is True, registry
    assert registry["proved_root_ids"]==["CC_R3_TERMINAL_CLOSURE_V1"]
    assert sorted(registry["open_root_ids"])==sorted([
        "CC_R1_REALITY_CONTAINMENT_V1",
        "CC_R2_MISSION_SOUNDNESS_V1",
    ])
    assert registry["r4_proof_closure"] is False
    assert registry["terminal_credit_delta"]==0
