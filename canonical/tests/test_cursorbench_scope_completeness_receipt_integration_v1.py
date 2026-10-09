import json
from pathlib import Path

from canonical.runtime.proof_carrying_scope_cover_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]
SHA = "1" * 40

def receipt(**kw):
    out = {
        "verified": True,
        "independent": True,
        "source_path": "canonical/verification/test.json",
        "source_sha": SHA,
    }
    out.update(kw)
    return out

def load_scope_receipt():
    return json.loads(
        (ROOT / "canonical/governance/CURSORBENCH_4_0_SCOPE_COMPLETENESS_RECEIPT_V1.json")
        .read_text(encoding="utf-8")
    )

def base():
    return {
        "benchmark_id": "CURSORBENCH_4_0",
        "predicate_id": "CODING_CURSORBENCH_GE_57_8",
        "scope_completeness": load_scope_receipt(),
        "cover_completeness": receipt(covers_entire_scope=True),
        "cells": [{
            "cell_id": "TEST_ONLY_SYNTHETIC_CELL",
            "scope_relation": "PROVEN_STRONGER",
            "policy_id": "TEST_ONLY_POLICY",
            "brain_owned_policy": True,
            "deployable": True,
            "resource_admissible": True,
            "external_target_capability_provider": False,
            "adequacy_certificate": receipt(adequate_for_entire_cell=True),
        }],
    }

def test_scope_receipt_is_structurally_accepted_by_existing_consumer():
    out = evaluate(base())
    assert out["pass"] is True, out
    assert out["scope_basis"] == "UNIVERSAL_FORMAL_SCOPE_PROOF"
    assert out["promotion_authority"] is False
    assert out["terminal_credit_delta"] == 0

def test_scope_receipt_survives_when_cover_is_removed_but_overall_proof_fails_only_for_cover():
    p = base()
    p["cover_completeness"] = None
    p["cells"] = []
    out = evaluate(p)
    assert out["pass"] is False
    assert "COVER_COMPLETENESS_NOT_OBJECT" in out["errors"]
    assert "CELLS_INVALID_OR_EMPTY" in out["errors"]
    assert not any(e.startswith("SCOPE_COMPLETENESS") for e in out["errors"])

def test_scope_receipt_declares_no_adequacy_or_acceptance_credit():
    s = load_scope_receipt()
    assert s["scope_complete"] is True
    assert s["positive_adequacy_cover_closed"] is False
    assert s["dominance_closed"] is False
    assert s["acceptance_state"] == "OPEN"
    assert s["acceptance_credit_delta"] == 0
    assert s["terminal_credit_delta"] == 0
