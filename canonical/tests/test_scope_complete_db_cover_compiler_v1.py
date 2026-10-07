from unittest.mock import patch

from canonical.runtime.scope_complete_db_cover_compiler_v1 import evaluate, partition_digest

SCOPE = "scope://opus55/useful-trace"

def cells():
    rows = [
        {
            "cell_id": "c1",
            "cell_definition_sha256": "sha256:" + "1"*64,
            "admission_candidate": {"route": "A_COMPLETE_OBJECTIVE", "payload": {}},
        },
        {
            "cell_id": "c2",
            "cell_definition_sha256": "sha256:" + "2"*64,
            "admission_candidate": {"route": "D_SOURCE_POSITIVE_ADEQUACY", "payload": {}},
        },
    ]
    for row in rows:
        row["membership_receipt"] = {
            "receipt_id": "m-" + row["cell_id"],
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "membership_proved": True,
            "scope_id": SCOPE,
            "cell_id": row["cell_id"],
            "cell_definition_sha256": row["cell_definition_sha256"],
        }
    return rows

def payload():
    rows = cells()
    return {
        "scope_id": SCOPE,
        "cells": rows,
        "scope_partition_receipt": {
            "receipt_id": "scope-proof",
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "scope_partition_complete": True,
            "scope_id": SCOPE,
            "partition_sha256": partition_digest(SCOPE, rows),
        },
    }

def test_all_cells_admitted_authorizes_u_empty_but_not_terminal():
    p = payload()
    with patch("canonical.runtime.scope_complete_db_cover_compiler_v1.db.evaluate") as a, patch(
        "canonical.runtime.scope_complete_db_cover_compiler_v1.source_db.evaluate"
    ) as d:
        a.return_value = {
            "pass": True,
            "db_admission_authorized": True,
            "cell_id": "c1",
            "status": "PASS_A",
        }
        d.return_value = {
            "pass": True,
            "db_admission_authorized": True,
            "cell_id": "c2",
            "status": "PASS_D",
        }
        out = evaluate(p)
    assert out["pass"] is True
    assert out["u_empty_authorized"] is True
    assert out["abc_closed_authorized"] is True
    assert out["d_finality_required"] is True
    assert out["terminal_authority"] is False

def test_scope_partition_digest_is_load_bearing():
    p = payload()
    p["scope_partition_receipt"]["partition_sha256"] = "sha256:" + "0"*64
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "SCOPE_PARTITION_DIGEST_MISMATCH"
    assert out["u_empty_authorized"] is False

def test_incomplete_scope_never_authorizes_u_empty():
    p = payload()
    p["scope_partition_receipt"]["scope_partition_complete"] = False
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "SCOPE_PARTITION_COMPLETENESS_UNPROVED"
    assert out["u_empty_authorized"] is False

def test_membership_receipt_must_bind_exact_cell_definition():
    p = payload()
    p["cells"][0]["membership_receipt"]["cell_definition_sha256"] = "sha256:" + "f"*64
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "CELL_MEMBERSHIP_DEFINITION_MISMATCH:c1"

def test_one_unproved_cell_blocks_global_closure():
    p = payload()
    with patch("canonical.runtime.scope_complete_db_cover_compiler_v1.db.evaluate") as a:
        a.return_value = {
            "pass": False,
            "db_admission_authorized": False,
            "cell_id": "c1",
            "status": "UNRESOLVED",
        }
        out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "CELL_DB_ADMISSION_UNPROVED:c1"
    assert out["u_empty_authorized"] is False

def test_admission_for_wrong_cell_cannot_be_reused():
    p = payload()
    with patch("canonical.runtime.scope_complete_db_cover_compiler_v1.db.evaluate") as a:
        a.return_value = {
            "pass": True,
            "db_admission_authorized": True,
            "cell_id": "other",
            "status": "PASS",
        }
        out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "CELL_DB_ADMISSION_ID_MISMATCH:c1"
