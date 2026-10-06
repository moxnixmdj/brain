from canonical.runtime.target_universe_surface_compiler_v1 import compile_surface_manifest

ENVELOPE = {
    "families": [
        {"id":"ADVANCED_AGENTIC_CODING"},
        {"id":"ARTIFACT_CREATION"},
        {"id":"VISION_AND_DENSE_DOCUMENT_UNDERSTANDING"},
    ]
}

SRC = [{"path":"source.json","git_blob_sha":"0"*40}]

def surface(sid, classification, acceptance_state, **extra):
    x = {
        "id": sid,
        "classification": classification,
        "acceptance_state": acceptance_state,
        "source_receipts": SRC,
    }
    x.update(extra)
    return x

def test_family_union_valid():
    out = compile_surface_manifest({
        "literal_target_universe_complete": False,
        "surfaces":[surface("S","INTRINSIC_FAMILY_UNION","BASIS_BOUND_PARITY_OPEN",families=["ARTIFACT_CREATION"])]
    }, ENVELOPE)
    assert out.invalid_surface_count == 0
    assert out.acceptance_basis_gap_count == 0
    assert out.finite_manifest_acceptance_basis_complete is True
    assert out.literal_target_universe_complete is False

def test_unknown_family_fails_closed():
    out = compile_surface_manifest({
        "literal_target_universe_complete": False,
        "surfaces":[surface("S","INTRINSIC_FAMILY_UNION","BASIS_BOUND_PARITY_OPEN",families=["NOPE"])]
    }, ENVELOPE)
    assert out.invalid_surface_ids == ("S",)
    assert out.finite_source_accounting_complete is False

def test_acceptance_gap_is_explicit_without_taxonomy_failure():
    out = compile_surface_manifest({
        "literal_target_universe_complete": False,
        "surfaces":[surface("VISUAL_POLISH","INTRINSIC_FAMILY_UNION","BASIS_GAP",families=["ADVANCED_AGENTIC_CODING","ARTIFACT_CREATION","VISION_AND_DENSE_DOCUMENT_UNDERSTANDING"])]
    }, ENVELOPE)
    assert out.invalid_surface_count == 0
    assert out.acceptance_basis_gap_count == 1
    assert out.finite_source_accounting_complete is True
    assert out.finite_manifest_acceptance_basis_complete is False

def test_deployment_only_requires_not_applicable():
    out = compile_surface_manifest({
        "literal_target_universe_complete": False,
        "surfaces":[surface("VOICE","DEPLOYMENT_OR_INTERFACE_ONLY","BASIS_BOUND_PARITY_OPEN",exclusion_reason="client transcription")]
    }, ENVELOPE)
    assert out.invalid_surface_ids == ("VOICE",)

def test_unresolved_escape_keeps_manifest_acceptance_open():
    out = compile_surface_manifest({
        "literal_target_universe_complete": False,
        "surfaces":[surface("X","UNRESOLVED_ESCAPE","BASIS_GAP",escape_statement="useful behavior not yet classified")]
    }, ENVELOPE)
    assert out.unresolved_escape_ids == ("X",)
    assert out.finite_manifest_acceptance_basis_complete is False

def test_missing_source_receipt_fails_closed():
    x = surface("S","INTRINSIC_FAMILY_UNION","BASIS_BOUND_PARITY_OPEN",families=["ARTIFACT_CREATION"])
    x["source_receipts"] = []
    out = compile_surface_manifest({"literal_target_universe_complete":False,"surfaces":[x]}, ENVELOPE)
    assert out.invalid_surface_ids == ("S",)

def test_literal_complete_without_separate_completeness_proof_is_rejected():
    try:
        compile_surface_manifest({
            "literal_target_universe_complete": True,
            "surfaces":[surface("S","INTRINSIC_FAMILY_UNION","BASIS_BOUND_PROVED",families=["ARTIFACT_CREATION"])]
        }, ENVELOPE)
    except ValueError as exc:
        assert "completeness proof" in str(exc)
    else:
        raise AssertionError("expected fail-closed completeness rejection")

def test_literal_complete_with_separate_content_addressed_proof_can_compile():
    out = compile_surface_manifest({
        "literal_target_universe_complete": True,
        "target_universe_completeness_proof_receipts":[{"path":"theorem.json","git_blob_sha":"1"*40}],
        "surfaces":[surface("S","INTRINSIC_FAMILY_UNION","BASIS_BOUND_PROVED",families=["ARTIFACT_CREATION"])]
    }, ENVELOPE)
    assert out.literal_target_universe_complete is True
    assert out.terminal_credit_delta == 0

def run_all():
    tests = [
        test_family_union_valid,
        test_unknown_family_fails_closed,
        test_acceptance_gap_is_explicit_without_taxonomy_failure,
        test_deployment_only_requires_not_applicable,
        test_unresolved_escape_keeps_manifest_acceptance_open,
        test_missing_source_receipt_fails_closed,
        test_literal_complete_without_separate_completeness_proof_is_rejected,
        test_literal_complete_with_separate_content_addressed_proof_can_compile,
    ]
    for test in tests:
        test()
    return len(tests)

if __name__ == "__main__":
    print(f"PASS {run_all()}/8")
