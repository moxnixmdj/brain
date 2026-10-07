from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
V7="canonical/governance/V16_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V7.json"
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V16.json":"c1bc4543860be08f9014f69a212ba2222d8dba7c",
 "canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V3.json":"8f64a698645e9ba0fe433560cbee3f084700b6e7",
 "canonical/governance/V16_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V5.json":"6637b23cd90f3df20ec87f817ef38d1eb233ea79",
 "canonical/governance/V16_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V6.json":"cdb8f76d8ee158989a51f2ebcf108c4d1847ebd3",
 "canonical/governance/V16_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_SELECTED_PROPERTY_CELL_20261007_V1.json":"7b2cb008f34082ae0aa4be78f2444287cf6022b2",
 "canonical/verification/V16_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_SELECTED_PROPERTY_INDEPENDENT_WOLFRAM_VERIFICATION_20261007_V1.json":"200576296c16e3c5231e6a873a83129d8ea06545",
 "canonical/governance/V16_P3_FROZEN_DIRECT_CONJUNCTION_TOPLAW_20261007_V2.json":"1b3add6c488e7205981da391044fd7631e068aa8",
 "canonical/verification/V16_P3_FROZEN_DIRECT_CONJUNCTION_TOPLAW_WOLFRAM_VERIFICATION_20261007_V2.json":"6e87e01fb58e9b728645f6d01baca1d3cd1598a1",
 V7:"3dbe5cdd76cda141fd8efb5984cd2dad6a9ff9ab",
}
SYNTH="SYNTHESIS_TARGET_SCOPE_REQUIRED_CLAIM_COVERAGE_TOP_LAW"
P3="P3_T1_T3_FROZEN_60_WHOLE_DIRECT_SYNTHESIS_CONJUNCTION"

def blob(rel:str)->str:
    data=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load(rel:str):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def verify():
    e=[]
    for rel,want in EXPECTED.items():
        p=ROOT/rel
        if not p.is_file():
            e.append("SOURCE_MISSING:"+rel)
        elif blob(rel)!=want:
            e.append("SOURCE_DRIFT:"+rel+":"+blob(rel))

    base=load("canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V3.json")
    v5=load("canonical/governance/V16_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V5.json")
    v6=load("canonical/governance/V16_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V6.json")
    synth=load("canonical/verification/V16_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_SELECTED_PROPERTY_INDEPENDENT_WOLFRAM_VERIFICATION_20261007_V1.json")
    p3=load("canonical/governance/V16_P3_FROZEN_DIRECT_CONJUNCTION_TOPLAW_20261007_V2.json")
    p3v=load("canonical/verification/V16_P3_FROZEN_DIRECT_CONJUNCTION_TOPLAW_WOLFRAM_VERIFICATION_20261007_V2.json")
    v7=load(V7)

    base_ids=[x["id"] for x in base.get("known_D_B_regions",[])]
    v5_added=[x["id"] for x in v5.get("added_certificates",[])]
    live13=base_ids+v5_added
    if len(base_ids)!=10 or len(set(base_ids))!=10:
        e.append("BASE10_INVALID")
    if (v5.get("saturation_result") or {}).get("known_sound_D_B_region_certificate_count")!=13:
        e.append("LIVE_V5_NOT_13")
    if len(live13)!=13 or len(set(live13))!=13:
        e.append("LIVE13_ID_UNION_INVALID")

    if (v6.get("added_delta") or {}).get("region_id")!=SYNTH:
        e.append("V6_SYNTH_DELTA_MISSING")
    if SYNTH in live13:
        e.append("SYNTH_ALREADY_IN_LIVE13")
    vc=synth.get("verified_consequence") or {}
    if not (vc.get("K_c_minus_empty_for_this_property") is True and
            vc.get("sound_to_add_as_cached_D_B_region_certificate") is True and
            vc.get("synthesis_family_closed") is False and
            vc.get("terminal") is False):
        e.append("SYNTH_CERTIFICATE_INVALID")

    sc=p3.get("selected_cell") or {}
    th=p3.get("theorem") or {}
    if sc.get("id")!=P3 or sc.get("brain_required_check_vector")!=[1]*7 or sc.get("componentwise_top_vector")!=[1]*7:
        e.append("P3_CELL_INVALID")
    if th.get("target_information_required") is not False or th.get("fresh_reality_required") is not False:
        e.append("P3_INFORMATION_BOUNDARY_INVALID")
    wr=(p3v.get("wolfram") or {}).get("result") or {}
    if not (wr.get("P3AllTargetsLEBrain") is True and wr.get("P3AnyStrictDominator") is False and wr.get("P3TargetCount")==128):
        e.append("P3_WOLFRAM_INVALID")
    if P3 in live13 or P3==SYNTH:
        e.append("P3_DELTA_NOT_DISTINCT")

    want_ids=set(live13+[SYNTH,P3])
    got_ids=v7.get("known_certificate_region_ids") or []
    rec=v7.get("reconciliation") or {}
    if len(got_ids)!=15 or len(set(got_ids))!=15 or set(got_ids)!=want_ids:
        e.append("V7_EXACT_15_ID_UNION_INVALID")
    if rec.get("live_base_certificate_count")!=13 or rec.get("added_distinct_certificate_count")!=2 or rec.get("known_sound_region_certificate_count")!=15:
        e.append("V7_COUNT_INVALID")
    if rec.get("coverage_measure_not_claimed") is not True or rec.get("regions_may_overlap_semantically") is not True:
        e.append("V7_OVERCLAIM_GUARD_INVALID")
    if (v7.get("synthesis_residual_effect") or {}).get("synthesis_family_closed") is not False:
        e.append("FALSE_FAMILY_CLOSURE")
    if (v7.get("accounting") or {}).get("fresh_reality_units_consumed")!=0 or (v7.get("accounting") or {}).get("terminal_credit_delta")!=0:
        e.append("FALSE_CREDIT")

    return {
      "schema":"PROJECT_BRAIN_V16_DB_EXISTING_EVIDENCE_SATURATION_VERIFIER_V7",
      "status":"PASS__LIVE_13_UNION_TWO_SOUND_SYNTHESIS_CERTIFICATES_EQUALS_15__ZERO_CREDIT" if not e else "FAIL_CLOSED",
      "pass":not e,
      "errors":e,
      "live_base_count":13,
      "delta_count":2 if not e else None,
      "known_sound_region_certificate_count":15 if not e else None,
      "added_ids":[SYNTH,P3] if not e else None,
      "regions_may_overlap":True,
      "coverage_measure_claimed":False,
      "abc_closed":False,
      "d_finality_closed":False,
      "terminal":False,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    out=verify()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
