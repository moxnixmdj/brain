from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.composition_component_proof_contract_v1 import (
    ComponentContract,
    ProofReceipt,
    VerifiedBridgeCertificate,
    receipt_admissible_for_contract,
)


CONTRACT = ComponentContract(
    component_id="debugging",
    interface_id="coding+debugging+tool discovery",
    subject_id="composition/debugging/v1",
    scope_id="composition/coding-debugging-tool-discovery/debugging-scope/v1",
)


def good_receipt(**overrides):
    values = dict(
        proved_subject_id=CONTRACT.subject_id,
        proved_scope_id=CONTRACT.scope_id,
        independent_or_objective=True,
        current=True,
        contamination_clean=True,
        content_bound=True,
        preconditions_compatible=True,
    )
    values.update(overrides)
    return ProofReceipt(**values)


def test_exact_subject_and_scope_identity_admit():
    assert receipt_admissible_for_contract(
        CONTRACT, good_receipt(), verified_bridge_authority={}
    )


def test_name_overlap_or_wrong_subject_does_not_admit():
    receipt = good_receipt(
        proved_subject_id="family/self-verification-debugging-recovery/v1"
    )
    assert not receipt_admissible_for_contract(
        CONTRACT, receipt, verified_bridge_authority={}
    )


def test_independently_verified_subject_bridge_can_admit():
    cert = VerifiedBridgeCertificate(
        certificate_id="cert/recovery-to-debugging/v1",
        relation="SUBJECT_IMPLIES",
        source_id="family/self-verification-debugging-recovery/v1",
        target_id=CONTRACT.subject_id,
        independently_verified=True,
        content_bound=True,
    )
    receipt = good_receipt(
        proved_subject_id=cert.source_id,
        subject_implication_certificate_id=cert.certificate_id,
    )
    assert receipt_admissible_for_contract(
        CONTRACT,
        receipt,
        verified_bridge_authority={cert.certificate_id: cert},
    )


def test_self_asserted_or_wrong_endpoint_bridge_fails_closed():
    cert = VerifiedBridgeCertificate(
        certificate_id="cert/bad/v1",
        relation="SUBJECT_IMPLIES",
        source_id="family/self-verification-debugging-recovery/v1",
        target_id="some-other-component",
        independently_verified=True,
        content_bound=True,
    )
    receipt = good_receipt(
        proved_subject_id=cert.source_id,
        subject_implication_certificate_id=cert.certificate_id,
    )
    assert not receipt_admissible_for_contract(
        CONTRACT,
        receipt,
        verified_bridge_authority={cert.certificate_id: cert},
    )


def test_scope_bridge_is_endpoint_bound():
    cert = VerifiedBridgeCertificate(
        certificate_id="cert/scope/v1",
        relation="SCOPE_COVERS",
        source_id="broader/proved/scope",
        target_id=CONTRACT.scope_id,
        independently_verified=True,
        content_bound=True,
    )
    receipt = good_receipt(
        proved_scope_id=cert.source_id,
        scope_inclusion_certificate_id=cert.certificate_id,
    )
    assert receipt_admissible_for_contract(
        CONTRACT,
        receipt,
        verified_bridge_authority={cert.certificate_id: cert},
    )


def test_every_admissibility_bit_fails_closed():
    fields = (
        "independent_or_objective",
        "current",
        "contamination_clean",
        "content_bound",
        "preconditions_compatible",
    )
    for field in fields:
        assert not receipt_admissible_for_contract(
            CONTRACT,
            good_receipt(**{field: False}),
            verified_bridge_authority={},
        )
