from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.composition_scoped_proof_admissibility_v1 import (
    ScopedProofEvidence,
    admissible_component_scoped_proof,
    classify_scope_only,
    whole_family_acceptance_is_logically_required,
)

RESOLUTION = ROOT / "canonical/governance/COMPOSITION_SCOPED_PROOF_SEMANTIC_RESOLUTION_20261005_V1.json"


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_frozen_source_literal_requires_scoped_proof_not_whole_family_acceptance():
    protocols = load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
    composition = next(
        item for item in protocols["protocols"]
        if item["family"] == "MULTI_CAPABILITY_COMPOSITION"
    )
    assert composition["acceptance"] == (
        "Every isolated component used in the claim has its own scoped proof; "
        "on the frozen mixed-capability portfolio Brain conservative terminal-success "
        "bound >= Opus matched bound and no critical composition invariant fails."
    )
    assert "whole family" not in composition["acceptance"].lower()


def test_scope_only_is_not_a_component_proof():
    assert classify_scope_only(
        scope_complete=True,
        subject_entails_component_obligation=False,
    ) == "SCOPE_ONLY__NO_COMPONENT_CREDIT"

    scope_only = ScopedProofEvidence(
        subject_contract_bound=True,
        subject_entails_component_obligation=False,
        scope_covers_interface=True,
        independent_or_objective=True,
        current=True,
        contamination_clean=True,
        content_bound=True,
        preconditions_compatible=True,
    )
    assert admissible_component_scoped_proof(scope_only) is False


def test_direct_component_proof_can_be_semantically_admissible_without_family_acceptance():
    direct = ScopedProofEvidence(
        subject_contract_bound=True,
        subject_entails_component_obligation=True,
        scope_covers_interface=True,
        independent_or_objective=True,
        current=True,
        contamination_clean=True,
        content_bound=True,
        preconditions_compatible=True,
    )
    assert admissible_component_scoped_proof(direct) is True
    assert whole_family_acceptance_is_logically_required(
        direct_component_proof_admissible=True
    ) is False


def test_every_load_bearing_admission_premise_fails_closed():
    fields = list(ScopedProofEvidence.__dataclass_fields__)
    baseline = {field: True for field in fields}
    for field in fields:
        candidate = dict(baseline)
        candidate[field] = False
        assert admissible_component_scoped_proof(ScopedProofEvidence(**candidate)) is False


def test_current_scope_only_counterexamples_remain_zero_credit():
    synth = load(
        "canonical/verification/"
        "SYNTHESIS_LOSSLESS_SCOPE_DECOMPOSITION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"
    )
    artifact = load(
        "canonical/verification/ARTIFACT_UNCOVERED_SCOPE_PARTITION_PROOF_20261002_V1.json"
    )
    resolution = json.loads(RESOLUTION.read_text(encoding="utf-8"))

    assert synth["verified"]["exact_dimension_set"] is True
    assert synth["verified"]["root3_scope_relation_closed"] is True
    assert synth["verified"]["acceptance_closed"] is False

    assert artifact["no_uncovered_contracted_leaf"] is True
    assert "does not supply the AA-Briefcase score" in artifact["objective"]
    assert "ARTIFACT_AA_BRIEFCASE_GE_1822_REMAINS_OPEN" in artifact["conclusion"]

    current = resolution["current_evidence_classification"]
    assert current["preserve_current_admitted_4"] is True
    assert current["automatic_new_component_credit"] == 0
    assert resolution["accounting"]["acceptance_credit_delta"] == 0
    assert resolution["fresh_reality_authority"] is False


def test_untyped_subject_fails_closed_even_if_some_receipt_claims_entailment():
    untyped = ScopedProofEvidence(
        subject_contract_bound=False,
        subject_entails_component_obligation=True,
        scope_covers_interface=True,
        independent_or_objective=True,
        current=True,
        contamination_clean=True,
        content_bound=True,
        preconditions_compatible=True,
    )
    assert admissible_component_scoped_proof(untyped) is False


def test_current_open_eight_are_literal_interfaces_without_subject_contracts():
    manifest = load("canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json")
    authority = load("canonical/governance/COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json")
    gap = load("canonical/governance/COMPOSITION_COMPONENT_PROOF_SUBJECT_TYPING_GAP_20261005_V1.json")

    assert manifest["family_bindings_complete"] is False
    assert manifest["receipt_bindings_complete"] is False
    assert all(x["required_properties"] == ["SCOPED_ACCEPTANCE_PROOF"] for x in manifest["interfaces"])
    assert all("proof_subject_id" not in x for x in manifest["interfaces"])

    assert authority["truth"]["current_admissible_scoped_proved"] == 4
    assert authority["truth"]["current_open"] == 8
    assert set(authority["open_components"]) == set(gap["observed_fact"]["current_open_components"])
    assert gap["observed_fact"]["manifest_has_explicit_component_proof_subject_contract"] is False
