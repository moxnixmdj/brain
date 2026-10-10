from __future__ import annotations
import hashlib,json
from pathlib import Path
from canonical.runtime import escape_progress_shared_gap_audit_v3 as audit

ROOT=Path(__file__).resolve().parents[2]
RECLASS=ROOT/"canonical/governance/ESCAPE_PROGRESS_GDPVAL_CHARTOGRAPHY_CAUSAL_RECLASSIFICATION_20261010_V1.json"
MANIFEST=ROOT/"canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V3.json"
BINDING=ROOT/"canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V7.json"
GDP=ROOT/"canonical/governance/GDPVAL_FIRST_RESIDUAL_MECHANICAL_ROUTE_EXPANSION_20261009_V2.json"
CHART=ROOT/"canonical/governance/CHARTOGRAPHY_QWEN3_VL4B_VISION_ACQUISITION_ACTIVATION_V1.json"
GDP_BLOB="c38ca6ee010a63d6dc218aa2c9d85831e39441ed"
CHART_BLOB="d5b46fc2f784a206cda9bb7c6f1ee951300eccc0"

def _blob(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+bytes([0])+b).hexdigest()

def test_gap_b_reclassification_is_source_entailed_and_structurally_sound():
    assert _blob(GDP)==GDP_BLOB
    assert _blob(CHART)==CHART_BLOB
    g=json.loads(GDP.read_text())
    c=json.loads(CHART.read_text())
    r=json.loads(RECLASS.read_text())
    m=json.loads(MANIFEST.read_text())
    b=json.loads(BINDING.read_text())

    assert g["measured_effect"]["v2_compilable_first_residuals"]==92
    assert g["measured_effect"]["remaining_unresolved_first_residuals"]==128
    assert "route availability" in g["theorem_boundary"]["statement"].lower()
    effects=" ".join(g["scheduler_effect"])
    assert "GDPVAL_CANDIDATE_OR_SCOPE_COMPLETE_CONSTRUCTIVE_PROOF" in effects

    assert c["authority"]["scheduling"] is True
    assert c["authority"]["execution"] is False
    assert "EXACT_EXECUTION_SUBJECT_FIT_AND_RESOURCE_PREFLIGHT" in c["scheduler_delta"]["preserve"]
    assert c["scheduler_delta"]["bf16_full_gpu_fit"].startswith("UNPROVED")

    rr={x["obligation_id"]:x for x in r["rows"]}
    assert rr["PROWORK_GDPVAL_GE_1846"]["corrected_group"]==audit.GAP_A
    assert rr["CHARTOGRAPHY_TOOLS_GE_89"]["corrected_group"]==audit.GAP_A
    assert r["derived_scheduler_counts"]["active_gap_b_count"]==0

    rows={x["obligation_id"]:x for x in m["rows"]}
    assert rows["PROWORK_GDPVAL_GE_1846"]["route_group"]==audit.GAP_A
    assert rows["CHARTOGRAPHY_TOOLS_GE_89"]["route_group"]==audit.GAP_A
    assert rows["TB_SCIENCE_GE_58_7"]["route_group"]==audit.GAP_B
    assert sum(x["route_group"]==audit.GAP_A for x in m["rows"])==12
    assert sum(x["route_group"]==audit.GAP_B for x in m["rows"])==1

    out=audit.audit(m,b,{})
    assert out["pass"] is True,out
    assert out["cc_r3_proved"] is False
    assert len(out["open_predicates"])==13
