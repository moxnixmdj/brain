from __future__ import annotations
import hashlib,json
from pathlib import Path
from canonical.runtime.terminal_frontier_factorizer_v2 import ATOMIC,META

ROOT=Path(__file__).resolve().parents[2]
MAN=ROOT/"canonical/governance/V9_SELECTED_CELL_MANIFEST_20261007_V2.json"

EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V9.json":"1ec7f2c86534d046e51ddda00001ed287039fc0a",
 "canonical/runtime/terminal_frontier_factorizer_v2.py":"7bf57811d1b745cc2b92596f6c1c87ff5693aa1c",
 "canonical/governance/META8_SELECTED_CONTEXT_ABC_ABSORPTION_20261007_V1.json":"1eb85b2b58ee53942716e70dbc7f523f08b3f302",
 "canonical/governance/ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V1.json":"1fba51d15bcfdf6accd90948155517f7c9b98bbb",
}

def blob(rel):
    p=ROOT/rel
    if not p.exists(): return ""
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def verify():
    errors=[]
    for rel,want in EXPECTED.items():
        if blob(rel)!=want: errors.append("SOURCE_DRIFT:"+rel)
    m=json.loads(MAN.read_text(encoding="utf-8"))
    atomic=set(ATOMIC); meta=set(META)
    bundles=m["route_bundles"]
    assigned=[x for xs in bundles.values() for x in xs]
    if len(assigned)!=21: errors.append("ATOMIC_ASSIGNMENT_COUNT")
    if set(assigned)!=atomic:
        miss=sorted(atomic-set(assigned)); extra=sorted(set(assigned)-atomic)
        if miss: errors.append("ATOMIC_MISSING:"+",".join(miss))
        if extra: errors.append("ATOMIC_EXTRA:"+",".join(extra))
    dup=sorted(x for x in set(assigned) if assigned.count(x)>1)
    if dup: errors.append("ATOMIC_DUP:"+",".join(dup))
    refinements=m["meta_refinements"]
    if set(refinements)!=meta: errors.append("META_SET_MISMATCH")
    if len(refinements)!=8: errors.append("META_COUNT")
    cd=refinements["CREATIVE_DIAGRAM_SURFACE_NONINFERIOR__META"]
    if set(cd.get("preserved_subcells") or [])!={"CREATIVE_TEXT_GENERATION_QUALITY_NONINFERIOR","TEXT_BASED_DIAGRAM_REALIZATION_NONINFERIOR"}:
        errors.append("CREATIVE_SUBCELLS_LOST")
    for key in ("MULTILINGUAL_PERFORMANCE","LONG_CONTEXT"):
        if refinements[key].get("kind")!="CROSS_CUTTING_CONTEXT_REFINEMENT":
            errors.append("CROSS_CUTTING_KIND:"+key)
    if m["accounting_projection"]!={"current_authority_rows":29,"independent_atomic_leaves":21,"meta_refinement_rows":8,"terminal":False}:
        errors.append("ACCOUNTING_PROJECTION")
    return {
      "schema":"PROJECT_BRAIN_V9_SELECTED_CELL_MANIFEST_V2_VERIFIER",
      "status":"PASS__21_ATOMIC_LEAVES_13_ROUTE_BUNDLES_8_META_REFINEMENTS__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
      "pass":not errors,"errors":errors,
      "atomic_leaf_count":21 if not errors else None,
      "route_bundle_count":13 if not errors else None,
      "meta_refinement_count":8 if not errors else None,
      "current_authority_rows":29 if not errors else None,
      "terminal_credit_delta":0
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
