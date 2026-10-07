from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "canonical/governance/NATIVE_ARTIFACT_V12_SELECTED_CONTEXT_ABC_BUNDLE_20261007_V1.json"

SOURCE_SHAS = {
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V12.json": "3ab55ad2e9df6a7f94acb2e1950569bdc18c8136",
    "canonical/governance/V12_TARGET_LAW_UNCERTAINTY_RESIDUAL_THEOREM_20261007_V1.json": "014d7d5102093251789673dff0a191203663a90d",
    "canonical/governance/NATIVE_ARTIFACT_EXACT_LEAF_GLOBAL_REUSE_CANDIDATE_20261005_V1.json": "1e0adb8bfaf24adde27455e13e55fe102088bbf5",
    "canonical/verification/NATIVE_ARTIFACT_EXACT_LEAF_GLOBAL_REUSE_CONNECTOR_VERIFICATION_20261005_V1.json": "61e8b61e9b48d869c1623251b4ce1a780f6c737b",
    "canonical/governance/D0_NATIVE_STRUCTURED_ARTIFACT_EDIT_CLOSURE_V1.json": "82977b79a0284a2ac51b1075146d528dbba2d6aa",
    "canonical/verification/NATIVE_ARTIFACT_CROSS_FORMAT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "34d8a3b7a99363902d6212759125ac71fa54a986",
    "canonical/verification/NATIVE_ARTIFACT_RENDER_PRESERVATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json": "1a0b4ca6627aaf28eb25f6990682e87319d14d6d",
    "canonical/runtime/native_artifact_cross_format_candidate_v1.py": "f3e5090647dd9029ab9f46efd06dc0c0d0addbc3",
    "canonical/runtime/native_artifact_cross_format_proof_v1.py": "904eb61171f5ee775ff7824c1be7778d7acc4a23",
    "canonical/runtime/native_artifact_render_preservation_proof_v1.py": "39374e775d54cdc58315d7a1f877d834282a64f7",
    "canonical/runtime/ooxml_package_transaction.py": "970be62854c918b306ae3f62989009bfbd0e8fc7",
    "canonical/runtime/pdf_native_edit_transaction.py": "b9f673ffe0474d00a598089077ad93db40c00dd8",
}

def load(path):
    v=json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(v,dict)
    return v

def blob_sha(path):
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def verify():
    errors=[]
    for rel,expected in SOURCE_SHAS.items():
        p=ROOT/rel
        if not p.is_file(): errors.append("MISSING:"+rel)
        elif blob_sha(p)!=expected: errors.append("DRIFT:"+rel)

    b=load(BUNDLE)
    leaf=load(ROOT/"canonical/governance/NATIVE_ARTIFACT_EXACT_LEAF_GLOBAL_REUSE_CANDIDATE_20261005_V1.json")
    ev=load(ROOT/"canonical/verification/NATIVE_ARTIFACT_EXACT_LEAF_GLOBAL_REUSE_CONNECTOR_VERIFICATION_20261005_V1.json")
    d0=load(ROOT/"canonical/governance/D0_NATIVE_STRUCTURED_ARTIFACT_EDIT_CLOSURE_V1.json")

    pb=leaf.get("proof_basis",{})
    if not (pb.get("scope_complete") is True and pb.get("objective_ceiling") is True and pb.get("brain_value")==1 and pb.get("theoretical_ceiling_value")==1):
        errors.append("LEAF_CEILING")
    rc=ev.get("recomputed",{})
    if not (rc.get("scope_complete") is True and rc.get("objective_ceiling") is True and rc.get("brain_value")==1 and rc.get("theoretical_ceiling_value")==1):
        errors.append("INDEPENDENT_CEILING")
    donor=d0.get("donor_independence",{})
    if not (donor.get("brain_transaction_logic_owned") is True and donor.get("external_model_or_api_required") is False and donor.get("paid_service_required") is False):
        errors.append("OWNERSHIP")

    sem=b.get("complete_terminal_semantics",{})
    dom=b.get("dominance",{})
    cons=b.get("consequence",{})
    if not (sem.get("brain_value")==1 and sem.get("theoretical_ceiling")==1 and sem.get("source_state")=="PROVED_SCOPE_COMPLETE"):
        errors.append("BUNDLE_SEMANTICS")
    if not (dom.get("route")=="ABSOLUTE_TOP_ELEMENT" and dom.get("K_c_minus")=="EMPTY" and dom.get("target_identity_or_score_required") is False):
        errors.append("DOMINANCE")
    if not (cons.get("expands_D_B") is True and cons.get("closes_only_exact_leaf") is True and cons.get("B7_role_closed") is False and cons.get("professional_quality_closed") is False and cons.get("semantic_target_selection_closed") is False):
        errors.append("SCOPE_GUARD")
    if b.get("accounting",{}).get("terminal_credit_delta") != 0:
        errors.append("CREDIT")

    required={
      "NO_WHOLE_B7_ROLE_CLOSURE","NO_ARTIFACT_CREATION_FAMILY_CLOSURE",
      "NO_HIGH_LEVEL_ARTIFACT_TARGET_SELECTION_OR_QUALITY_CREDIT",
      "NO_GLOBAL_D_FINALITY","NO_TERMINAL_CREDIT"
    }
    if not required.issubset(set(b.get("hard_nonclaims",[]))):
        errors.append("NONCLAIMS")

    return {
      "pass":not errors,"errors":errors,
      "selected_cell":"B7_NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_EXACT_LEAF",
      "K_c_minus_empty":not errors,
      "target_information_required":False if not errors else None,
      "B7_role_closed":False,"global_D_closed":False,"terminal":False,
      "terminal_credit_delta":0
    }

if __name__=="__main__":
    out=verify()
    print(json.dumps(out,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
