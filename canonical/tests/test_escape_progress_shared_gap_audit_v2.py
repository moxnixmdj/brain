from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from canonical.runtime import escape_progress_shared_gap_audit_v1 as v1
from canonical.runtime import escape_progress_shared_gap_audit_v2 as v2

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ROOT / v2.MANIFEST_REL).read_text(encoding="utf-8"))
BINDING = json.loads((ROOT / v2.BINDING_REL).read_text(encoding="utf-8"))
FROZEN_V1 = json.loads(
    (ROOT / v2.FROZEN_V1_MANIFEST_REL).read_text(encoding="utf-8")
)
FROZEN_IDS = [row["obligation_id"] for row in FROZEN_V1["rows"]]


def _seal(row):
    material = dict(row)
    material["proof_sha256"] = v1._sha(material)
    return material


def _proofs():
    out = {}
    for row in MANIFEST["rows"]:
        oid = row["obligation_id"]
        if row["route_group"] == v2.GAP_A:
            out[oid] = _seal(
                {
                    "obligation_id": oid,
                    "route_group": v2.GAP_A,
                    "currently_acquirable": True,
                    "finite_outcome_ids": ["yes", "no"],
                    "outcome_map_complete": True,
                    "decision_region_size_before": 2,
                    "max_nonterminal_decision_region_size_after": 1,
                    "authenticated_truth_preserving": True,
                    "safe": True,
                }
            )
        else:
            out[oid] = _seal(
                {
                    "obligation_id": oid,
                    "route_group": v2.GAP_B,
                    "verified_action_id": "verified:" + oid,
                    "action_executable_now": True,
                    "progress_measure": {
                        "kind": "FINITE_NATURAL_RANK",
                        "current_rank": 2,
                        "minimum_rank": 0,
                        "well_founded": True,
                    },
                    "allowed_outcomes": [
                        {
                            "outcome_id": "done",
                            "terminal": True,
                            "strictly_decreases_measure": False,
                        },
                        {
                            "outcome_id": "progress",
                            "terminal": False,
                            "strictly_decreases_measure": True,
                        },
                    ],
                    "safe": True,
                }
            )
    return out


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def test_current_successor_manifest_validates_as_10_a_3_b_and_stays_open():
    result = v2.audit_repo()
    assert result["pass"] is True, result
    assert result["cc_r3_proved"] is False
    assert result["row_count"] == 13
    assert result["gap_a_count"] == 10
    assert result["gap_b_count"] == 3
    assert result["open_row_count"] == 13
    assert result["manifest_declared_counts"] == {
        v2.GAP_A: 10,
        v2.GAP_B: 3,
    }
    assert result["binding_declared_counts"] == {
        v2.GAP_A: 10,
        v2.GAP_B: 3,
    }
    assert result["terminal_credit_delta"] == 0


def test_finance_index_is_gap_a_in_current_successor():
    row = next(
        row
        for row in MANIFEST["rows"]
        if row["obligation_id"] == "FINANCE_ACCOUNTING_INDEX_GE_61"
    )
    assert row["route_group"] == v2.GAP_A


def test_complete_valid_content_addressed_proofs_close_13_of_13():
    result = v2.audit(
        MANIFEST,
        BINDING,
        _proofs(),
        frozen_obligation_ids=FROZEN_IDS,
    )
    assert result["pass"] is True, result
    assert result["cc_r3_proved"] is True
    assert result["closed_row_count"] == 13
    assert result["open_row_count"] == 0
    assert result["open_predicates"] == []


def test_gap_a_missing_strict_shrink_stays_open():
    proofs = _proofs()
    oid = next(
        row["obligation_id"]
        for row in MANIFEST["rows"]
        if row["route_group"] == v2.GAP_A
    )
    proof = dict(proofs[oid])
    proof.pop("proof_sha256")
    proof["max_nonterminal_decision_region_size_after"] = proof[
        "decision_region_size_before"
    ]
    proofs[oid] = _seal(proof)
    result = v2.audit(
        MANIFEST,
        BINDING,
        proofs,
        frozen_obligation_ids=FROZEN_IDS,
    )
    assert result["pass"] is True
    assert result["cc_r3_proved"] is False
    assert (
        f"{oid}:STRICT_DECISION_REGION_SHRINK_NOT_PROVED"
        in result["open_predicates"]
    )


def test_gap_b_nonprogress_outcome_stays_open():
    proofs = _proofs()
    oid = next(
        row["obligation_id"]
        for row in MANIFEST["rows"]
        if row["route_group"] == v2.GAP_B
    )
    proof = dict(proofs[oid])
    proof.pop("proof_sha256")
    proof["allowed_outcomes"] = [
        {
            "outcome_id": "stuck",
            "terminal": False,
            "strictly_decreases_measure": False,
        }
    ]
    proofs[oid] = _seal(proof)
    result = v2.audit(
        MANIFEST,
        BINDING,
        proofs,
        frozen_obligation_ids=FROZEN_IDS,
    )
    assert result["pass"] is True
    assert result["cc_r3_proved"] is False
    assert any(
        "OUTCOME_NOT_EXACTLY_TERMINAL_OR_DECREASING" in item
        for item in result["open_predicates"]
    )


def test_declared_count_mismatch_fails_closed():
    binding = deepcopy(BINDING)
    binding["shared_gaps"][v2.GAP_A]["obligation_count"] = 9
    result = v2.audit(
        MANIFEST,
        binding,
        frozen_obligation_ids=FROZEN_IDS,
    )
    assert result["pass"] is False
    assert result["cc_r3_proved"] is False
    assert any(
        "MANIFEST_BINDING_COUNT_MISMATCH" in item
        or "BINDING_SUCCESSOR_GAP_A_COUNT_MISMATCH" in item
        for item in result["errors"]
    )


def test_unknown_route_group_fails_closed():
    manifest = deepcopy(MANIFEST)
    manifest["rows"][0]["route_group"] = "UNKNOWN"
    result = v2.audit(
        manifest,
        BINDING,
        frozen_obligation_ids=FROZEN_IDS,
    )
    assert result["pass"] is False
    assert result["cc_r3_proved"] is False
    assert any("UNKNOWN_ROUTE_GROUP" in item for item in result["errors"])


def test_finance_reversion_to_gap_b_is_killed_by_current_counts():
    manifest = deepcopy(MANIFEST)
    finance = next(
        row
        for row in manifest["rows"]
        if row["obligation_id"] == "FINANCE_ACCOUNTING_INDEX_GE_61"
    )
    finance["route_group"] = v2.GAP_B
    result = v2.audit(
        manifest,
        BINDING,
        frozen_obligation_ids=FROZEN_IDS,
    )
    assert result["pass"] is False
    assert result["gap_a_count"] == 9
    assert result["gap_b_count"] == 4
    assert any("ROW_GROUP_COUNT_MISMATCH" in item for item in result["errors"])


def test_frozen_obligation_order_or_set_drift_fails_closed():
    manifest = deepcopy(MANIFEST)
    manifest["rows"][0], manifest["rows"][1] = (
        manifest["rows"][1],
        manifest["rows"][0],
    )
    result = v2.audit(
        manifest,
        BINDING,
        frozen_obligation_ids=FROZEN_IDS,
    )
    assert result["pass"] is False
    assert "FROZEN_OBLIGATION_ORDER_OR_SET_DRIFT" in result["errors"]


def test_unknown_proof_row_fails_closed():
    proofs = _proofs()
    proofs["NOT_A_FROZEN_ROW"] = _seal(
        {
            "obligation_id": "NOT_A_FROZEN_ROW",
            "route_group": v2.GAP_A,
            "currently_acquirable": True,
            "finite_outcome_ids": ["x"],
            "outcome_map_complete": True,
            "decision_region_size_before": 2,
            "max_nonterminal_decision_region_size_after": 1,
            "authenticated_truth_preserving": True,
            "safe": True,
        }
    )
    result = v2.audit(
        MANIFEST,
        BINDING,
        proofs,
        frozen_obligation_ids=FROZEN_IDS,
    )
    assert result["pass"] is False
    assert any("PROOFS_FOR_UNKNOWN_ROWS" in item for item in result["errors"])


def test_historical_v1_manifest_and_audit_are_unchanged_and_replayable():
    assert _git_blob(ROOT / v2.FROZEN_V1_MANIFEST_REL) == (
        v2.FROZEN_V1_MANIFEST_GIT_BLOB_SHA
    )
    assert _git_blob(ROOT / v2.HISTORICAL_AUDIT_REL) == (
        v2.HISTORICAL_AUDIT_GIT_BLOB_SHA
    )
    historical = v1.audit_repo()
    assert historical["pass"] is True
    assert historical["cc_r3_proved"] is False
    assert historical["gap_a_count"] == 9
    assert historical["gap_b_count"] == 4


def test_repo_input_blob_drift_fails_closed(tmp_path):
    # audit_repo content-addresses current successor inputs. A byte drift cannot
    # silently become scheduling authority.
    import shutil

    for rel in (
        v2.MANIFEST_REL,
        v2.BINDING_REL,
        v2.FROZEN_V1_MANIFEST_REL,
        v2.HISTORICAL_AUDIT_REL,
    ):
        src = ROOT / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)

    manifest_path = tmp_path / v2.MANIFEST_REL
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    try:
        v2.audit_repo(tmp_path)
    except v2.EscapeProgressAuditV2Error as exc:
        assert "SOURCE_GIT_BLOB_DRIFT" in str(exc)
    else:
        raise AssertionError("drifted successor manifest was accepted")
