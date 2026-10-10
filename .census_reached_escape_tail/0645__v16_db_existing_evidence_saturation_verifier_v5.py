from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "canonical/governance/V16_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V5.json"
EXPECTED = {
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V16.json": "c1bc4543860be08f9014f69a212ba2222d8dba7c",
    "canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V3.json": "8f64a698645e9ba0fe433560cbee3f084700b6e7",
    "canonical/governance/P2_INFORMATION_SAFE_UNIVERSAL_SELECTED_CELL_20261007_V1.json": "0ccc3ecbdbf2636b8f1e7f0daf959a48350cb82e",
    "canonical/verification/P2_INFORMATION_SAFE_UNIVERSAL_SELECTED_CELL_INDEPENDENT_VERIFICATION_20261007_V1.json": "f3e86554f87868587d4ce3f58f97714b2dbe4672",
    "canonical/governance/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_SELECTED_PROPERTY_CELL_20261007_V1.json": "28692768a21e95b51e847417cf5ba2343587e4aa",
    "canonical/verification/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_WOLFRAM_VERIFICATION_20261007_V1.json": "aefee446782989518c9794db1e73909bd3c4f55c",
    "canonical/governance/BROWSER_STATE_GENERATOR_UNIVERSAL_TOP_LAW_CELL_20261007_V1.json": "68e6b4abacb14d92429f34fda54612027b09dfcf",
    "canonical/verification/BROWSER_STATE_GENERATOR_UNIVERSAL_TOP_LAW_WOLFRAM_VERIFICATION_20261007_V1.json": "2d9b30654dce2a43de8c4fea905fa13478bc0893",
}
ADDED_IDS = {
    "PROFESSIONAL_ARTIFACT_P2_INFO_SAFE_V2_ALL_GENERATED_CASES",
    "PROFESSIONAL_ARTIFACT_T1_FROZEN_30_ZERO_UNSUPPORTED_MATERIAL_CONTENT",
    "BROWSER_STATE_INFORMATION_SAFE_ALL_SEEDS_ALL_ORDINALS_V1",
}
def blob_sha(path: Path) -> str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def load(rel: str) -> dict:
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))
def verify() -> dict:
    errors=[]
    for rel,expected in EXPECTED.items():
        p=ROOT/rel
        if not p.is_file(): errors.append("MISSING:"+rel)
        elif blob_sha(p)!=expected: errors.append("DRIFT:"+rel)
    m=load(MANIFEST)
    base=load("canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V3.json")
    base_ids={r["id"] for r in base["known_D_B_regions"]}
    added=m.get("added_certificates") or []
    added_ids={r.get("id") for r in added}
    if len(base_ids)!=10: errors.append("BASE_COUNT")
    if added_ids!=ADDED_IDS or len(added)!=3: errors.append("ADDED_SET")
    if base_ids & added_ids: errors.append("ADDED_NOT_NEW")
    if len(base_ids|added_ids)!=13: errors.append("UNION_COUNT")
    p2=load("canonical/governance/P2_INFORMATION_SAFE_UNIVERSAL_SELECTED_CELL_20261007_V1.json")
    p2v=load("canonical/verification/P2_INFORMATION_SAFE_UNIVERSAL_SELECTED_CELL_INDEPENDENT_VERIFICATION_20261007_V1.json")
    if p2.get("abc_consequence",{}).get("selected_cell_scope_complete") is not True: errors.append("P2_SCOPE")
    if p2.get("abc_consequence",{}).get("direct_e2e") is not True: errors.append("P2_E2E")
    if p2v.get("wolfram",{}).get("result",{}).get("All16ScoreCasesEqual") is not True: errors.append("P2_VERIFY")
    prof=load("canonical/governance/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_SELECTED_PROPERTY_CELL_20261007_V1.json")
    profv=load("canonical/verification/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_WOLFRAM_VERIFICATION_20261007_V1.json")
    cell=prof.get("selected_property_cell",{})
    if cell.get("population_complete") is not True or cell.get("brain_value")!=1 or cell.get("top_value")!=1: errors.append("PROF_TOP")
    if profv.get("wolfram_result") is not True: errors.append("PROF_VERIFY")
    browser=load("canonical/governance/BROWSER_STATE_GENERATOR_UNIVERSAL_TOP_LAW_CELL_20261007_V1.json")
    browserv=load("canonical/verification/BROWSER_STATE_GENERATOR_UNIVERSAL_TOP_LAW_WOLFRAM_VERIFICATION_20261007_V1.json")
    bcell=browser.get("selected_cell",{})
    if bcell.get("brain_value")!=1 or bcell.get("top_value")!=1: errors.append("BROWSER_TOP")
    finite=browserv.get("finite_class_check",{})
    if finite.get("all_within_action_budget_8") is not True or finite.get("all_terminal_outcomes_in_accepting_set") is not True: errors.append("BROWSER_VERIFY")
    sat=m.get("saturation_result",{})
    if sat.get("known_sound_D_B_region_certificate_count")!=13: errors.append("MANIFEST_COUNT")
    if sat.get("fresh_target_reality_consumed")!=0: errors.append("FRESH_REALITY")
    if m.get("accounting",{}).get("terminal_credit_delta")!=0: errors.append("CREDIT")
    authority=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V16.json")
    if authority.get("truth_repair",{}).get("terminal") is not False: errors.append("AUTHORITY_TERMINAL_DRIFT")
    return {"schema":"PROJECT_BRAIN_V16_DB_EXISTING_EVIDENCE_SATURATION_VERIFIER_V5","pass":not errors,"errors":errors,"base_certificate_count":len(base_ids),"added_certificate_count":len(added_ids),"known_sound_D_B_region_certificate_count":len(base_ids|added_ids),"fresh_target_reality_consumed":0,"terminal":False,"terminal_credit_delta":0}
if __name__=="__main__":
    out=verify()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
