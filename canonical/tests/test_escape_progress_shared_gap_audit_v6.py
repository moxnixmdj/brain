from copy import deepcopy
import json

from canonical.runtime import escape_progress_shared_gap_audit_v6 as a


def test_current_projection_is_twelve_acquisition_one_parked_gapb_zero_active():
    out=a.audit_repo()
    assert out["pass"] is True, out
    assert out["cc_r3_proved"] is False
    assert out["projected_gap_a_count"]==12
    assert out["projected_gap_b_structural_count"]==1
    assert out["active_gap_b_count"]==0
    assert out["parked_gap_b_count"]==1
    assert out["parked_rows"]==["TB_SCIENCE_GE_58_7"]
    assert out["authenticated_current_row_proof_count"]==0
    assert out["terminal_authority"] is False
    assert out["acceptance_credit_delta"]==0
    assert out["terminal_credit_delta"]==0


def test_projected_rows_preserve_frozen_ids_and_only_reclassify_two_rows():
    manifest=json.loads(a.MANIFEST_PATH.read_text(encoding="utf-8"))
    binding=json.loads(a.BINDING_PATH.read_text(encoding="utf-8"))
    projected=a._project(manifest,binding)
    before={r["obligation_id"]:r for r in manifest["rows"]}
    after={r["obligation_id"]:r for r in projected["rows"]}
    assert set(before)==set(after)
    changed={
        oid for oid in before
        if before[oid]["route_group"]!=after[oid]["route_group"]
    }
    assert changed=={"PROWORK_GDPVAL_GE_1846","CHARTOGRAPHY_TOOLS_GE_89"}
    for oid in changed:
        assert before[oid]["route_group"]==a.GAP_B
        assert after[oid]["route_group"]==a.GAP_A
        assert after[oid]["historical_route_group"]==a.GAP_B
    assert after["TB_SCIENCE_GE_58_7"]["route_group"]==a.GAP_B


def test_reclassification_mints_no_row_credit_or_closure():
    out=a.audit_repo()
    assert out["pass"] is True, out
    inner=out["authenticated_projected_audit"]
    assert inner["authenticated_row_proof_count"]==0
    assert inner["cc_r3_proved"] is False
    structural=inner["structural_audit"]
    assert structural["closed_row_count"]==0
    assert structural["open_row_count"]==13


def test_tampered_projection_fails_closed(monkeypatch):
    original=a._load
    def fake(path):
        doc=original(path)
        if path==a.BINDING_PATH:
            doc=deepcopy(doc)
            doc["current_effective_projection"]["route_group_overrides"]={
                "PROWORK_GDPVAL_GE_1846":a.GAP_A
            }
        return doc
    monkeypatch.setattr(a,"_load",fake)
    out=a.audit_repo()
    assert out["pass"] is False
    assert out["status"]=="FAIL_CLOSED"
    assert "ROUTE_GROUP_OVERRIDES_INVALID" in out["reason"]
