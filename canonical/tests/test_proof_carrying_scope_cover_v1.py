from canonical.runtime.proof_carrying_scope_cover_v1 import evaluate


def receipt(**kw):
    out = {
        "verified": True,
        "independent": True,
        "source_path": "canonical/verification/test.json",
        "source_sha": "a" * 40,
    }
    out.update(kw)
    return out


def payload():
    return {
        "benchmark_id": "CURSORBENCH_4_0",
        "predicate_id": "CODING_CURSORBENCH_GE_57_8",
        "scope_completeness": receipt(
            basis="UNIVERSAL_FORMAL_SCOPE_PROOF",
            all_admissible_target_inputs_proved=True,
            formal_completeness=True,
        ),
        "cover_completeness": receipt(covers_entire_scope=True),
        "cells": [{
            "cell_id": "ALL",
            "scope_relation": "PROVEN_STRONGER",
            "policy_id": "P",
            "brain_owned_policy": True,
            "deployable": True,
            "resource_admissible": True,
            "external_target_capability_provider": False,
            "adequacy_certificate": receipt(adequate_for_entire_cell=True),
        }],
    }


def test_one_policy_universal_cover_produces_candidate_only():
    out = evaluate(payload())
    assert out["pass"] is True, out
    assert out["selector_required"] is False
    assert out["candidate_evidence_template"]["proof_kind"] == "SCOPE_COMPLETE_STRONGER_PROOF"
    assert out["promotion_authority"] is False
    assert out["terminal_credit_delta"] == 0


def test_public_description_without_scope_completeness_fails_closed():
    p = payload()
    p["scope_completeness"] = {
        "verified": True,
        "independent": True,
        "source_path": "canonical/evidence/public_blog.json",
        "source_sha": "b" * 40,
        "basis": "PUBLIC_DESCRIPTION_ONLY",
    }
    out = evaluate(p)
    assert out["pass"] is False
    assert "SCOPE_COMPLETENESS_BASIS_INVALID" in out["errors"]


def test_cover_redundancy_without_entire_scope_proof_fails_closed():
    p = payload()
    p["cover_completeness"]["covers_entire_scope"] = False
    out = evaluate(p)
    assert out["pass"] is False
    assert "COVER_DOES_NOT_PROVE_ENTIRE_SCOPE" in out["errors"]


def test_unverified_cell_adequacy_fails_closed():
    p = payload()
    p["cells"][0]["adequacy_certificate"]["verified"] = False
    out = evaluate(p)
    assert out["pass"] is False
    assert any("ADEQUACY_CERTIFICATE" in e and "NOT_VERIFIED" in e for e in out["errors"])


def test_external_target_capability_provider_fails_closed():
    p = payload()
    p["cells"][0]["external_target_capability_provider"] = True
    out = evaluate(p)
    assert out["pass"] is False
    assert any("EXTERNAL_TARGET_CAPABILITY_PROVIDER_NOT_EXCLUDED" in e for e in out["errors"])


def test_multiple_policies_require_independent_precommitment_selector():
    p = payload()
    p["cells"].append({
        "cell_id": "SECOND",
        "scope_relation": "EXACT",
        "policy_id": "P2",
        "brain_owned_policy": True,
        "deployable": True,
        "resource_admissible": True,
        "external_target_capability_provider": False,
        "adequacy_certificate": receipt(adequate_for_entire_cell=True),
    })
    out = evaluate(p)
    assert out["pass"] is False
    assert out["selector_required"] is True
    assert "SELECTOR_NOT_OBJECT" in out["errors"]


def test_multiple_policies_pass_with_truthful_selector():
    p = payload()
    p["cells"].append({
        "cell_id": "SECOND",
        "scope_relation": "EXACT",
        "policy_id": "P2",
        "brain_owned_policy": True,
        "deployable": True,
        "resource_admissible": True,
        "external_target_capability_provider": False,
        "adequacy_certificate": receipt(adequate_for_entire_cell=True),
    })
    p["selector"] = receipt(
        precommitment=True,
        truthful_selected_discriminator_semantics=True,
        selects_only_certified_cells=True,
    )
    out = evaluate(p)
    assert out["pass"] is True, out
    assert out["selector_required"] is True


def test_cell_adequacy_must_cover_entire_cell():
    p = payload()
    p["cells"][0]["adequacy_certificate"]["adequate_for_entire_cell"] = False
    out = evaluate(p)
    assert out["pass"] is False
    assert any("ADEQUACY_CERTIFICATE_NOT_WHOLE_CELL" in e for e in out["errors"])
