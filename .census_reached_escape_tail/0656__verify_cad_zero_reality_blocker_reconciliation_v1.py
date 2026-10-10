"""Fail-closed validator for the CAD zero-reality blocker reconciliation."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

REC="canonical/reasoning/2026-10-02_CAD_ZERO_REALITY_BLOCKER_RECONCILIATION_V1.json"

def git_blob_sha(path: Path) -> str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def verify(root: Path) -> dict:
    r=json.loads((root/REC).read_text(encoding="utf-8"))
    errors=[]
    for key,row in r.get("exact_sources",{}).items():
        p=root/row["path"]
        if not p.exists():
            errors.append("MISSING:"+key)
            continue
        if git_blob_sha(p)!=row["blob_sha"]:
            errors.append("BLOB_DRIFT:"+key)
    m1a=json.loads((root/r["exact_sources"]["m1a_complete_bundle"]["path"]).read_text())
    m1b=json.loads((root/r["exact_sources"]["m1b_complete_bundle"]["path"]).read_text())
    cont=json.loads((root/r["exact_sources"]["m1b_continuous_geometry"]["path"]).read_text())
    smooth=json.loads((root/r["exact_sources"]["m1b_smooth_surface"]["path"]).read_text())
    ocr=json.loads((root/r["exact_sources"]["tesseract_ocr_dependency"]["path"]).read_text())
    cad=json.loads((root/r["exact_sources"]["cad_end_to_end_route"]["path"]).read_text())
    if "ZERO_REALITY_PREFIX_EXECUTED_VERIFIED_AND_SATURATED" not in m1a.get("status",""):
        errors.append("M1A_NOT_SATURATED")
    if "ZERO_REALITY_PREFIX_EXECUTED_AND_VERIFIED" not in m1b.get("status",""):
        errors.append("M1B_NOT_VERIFIED")
    if "VERIFIED_BRAIN_OWNED_BOUNDED_CONTINUOUS_GEOMETRY_PREFIX" not in cont.get("status",""):
        errors.append("CONTINUOUS_GEOMETRY_NOT_VERIFIED")
    if "VERIFIED_BRAIN_OWNED_SMOOTH_SURFACE_COMPONENT" not in smooth.get("status",""):
        errors.append("SMOOTH_SURFACE_NOT_VERIFIED")
    if "VERIFIED_CLOSED_BOUNDED_OCR_DEPENDENCY_SURFACE" not in ocr.get("status",""):
        errors.append("OCR_ATOM_NOT_CLOSED")
    comp=set(cad.get("candidate_composition",[]))
    required={
      "M1A_DRAWING_NORMALIZATION_OCR_NOTATION_ASSOCIATION_AND_FEATURE_CONSTRAINT_GRAPH",
      "M1B_ANALYTIC_CSG_LINE_ARC_REVOLVE_COMPILER",
      "M1B_SPLINE_REVOLVE_AND_MULTI_SECTION_LOFT_COMPILER",
      "CADQUERY_KERNEL_SOLID_MATERIALIZATION",
    }
    if not required <= comp:
        errors.append("CAD_ROUTE_COMPOSITION_INCOMPLETE")
    remaining=set(r.get("remaining_blockers",[]))
    must_remain={
      "M1A_WHOLE_COMPOSED_RAW_DRAWING_ROUTE_SCOPE_EQUIVALENCE_AND_MUTATION_PREFLIGHT_PENDING",
      "FROZEN_TERMINAL_ENVELOPE_GEOMETRY_CLASS_COVERAGE_BEYOND_VERIFIED_ANALYTIC_CSG_LINE_ARC_REVOLVE_SPLINE_REVOLVE_AND_MULTI_SECTION_LOFT_GRAMMARS_NOT_YET_PROVEN",
      "SCOPE_EQUIVALENT_PROOF_GATE_V2_NOT_YET_PASS",
      "POST_FREEZE_TERMINAL_POPULATION_AND_INDEPENDENT_ORACLE_BINDING_PENDING",
    }
    if remaining!=must_remain:
        errors.append("REMAINING_BLOCKER_SET_DRIFT")
    if r.get("execution_authority") is not False or r.get("promotion_authority") is not False:
        errors.append("AUTHORITY_OVERCLAIM")
    if r.get("capability_credit_delta")!=0 or r.get("family_credit_delta")!=0:
        errors.append("CREDIT_OVERCLAIM")
    return {
      "schema":"PROJECT_BRAIN_CAD_ZERO_REALITY_BLOCKER_RECONCILIATION_VERDICT_V1",
      "status":"PASS" if not errors else "FAIL_CLOSED",
      "errors":sorted(set(errors)),
      "execution_authority":False,
      "promotion_authority":False,
      "capability_credit_delta":0,
      "family_credit_delta":0,
    }

if __name__=="__main__":
    import sys
    out=verify(Path("."))
    print(json.dumps(out,sort_keys=True))
    raise SystemExit(0 if out["status"]=="PASS" else 1)
