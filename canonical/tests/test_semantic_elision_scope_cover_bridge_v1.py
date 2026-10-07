from canonical.runtime.semantic_elision_scope_cover_bridge_v1 import evaluate

R = {"path": "canonical/verification/PROOF.json", "git_blob_sha": "0" * 40}

def base():
    return {
        "scope_id": "B2",
        "scope_partition_complete": True,
        "scope_partition_proof_receipts": [R],
        "cells": [
            {
                "cell_id": "cA",
                "membership_proved": True,
                "db_admission_route": "A_COMPLETE_OBJECTIVE",
                "db_admission_proved": True,
                "db_admission_proof_receipts": [R],
            },
            {
                "cell_id": "cB",
                "membership_proved": True,
                "db_admission_route": "B_ROBUST_COMMON_POLICY",
                "db_admission_proved": True,
                "db_admission_proof_receipts": [R],
            },
            {
                "cell_id": "cC",
                "membership_proved": True,
                "db_admission_route": "C_DIRECT_END_TO_END_ACCEPTANCE",
                "db_admission_proved": True,
                "db_admission_proof_receipts": [R],
            },
        ],
    }

def test_mixed_abc_routes_close_scope():
    out = evaluate(base())
    assert out["pass"] is True
    assert out["scope_cover_proved"] is True
    assert out["u_subtraction_authorized"] is True
    assert out["route_counts"]["A_COMPLETE_OBJECTIVE"] == 1
    assert out["route_counts"]["B_ROBUST_COMMON_POLICY"] == 1
    assert out["route_counts"]["C_DIRECT_END_TO_END_ACCEPTANCE"] == 1

def test_incomplete_scope_never_subtracts_u():
    p = base()
    p["scope_partition_complete"] = False
    out = evaluate(p)
    assert out["pass"] is False
    assert out["u_subtraction_authorized"] is False
    assert out["reason"] == "SCOPE_PARTITION_COMPLETENESS_UNPROVED"

def test_cell_without_db_admission_blocks_scope():
    p = base()
    p["cells"][1]["db_admission_proved"] = False
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "CELL_DB_ADMISSION_UNPROVED:cB"

def test_unknown_route_fails_closed():
    p = base()
    p["cells"][0]["db_admission_route"] = "MAGIC"
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "CELL_ADMISSION_ROUTE_INVALID:cA"

def test_cell_receipt_required():
    p = base()
    p["cells"][2]["db_admission_proof_receipts"] = []
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "CELL_DB_ADMISSION_PROOF_RECEIPTS_INVALID:cC"
