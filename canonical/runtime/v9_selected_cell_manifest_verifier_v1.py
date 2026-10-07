from __future__ import annotations
import json, hashlib
from pathlib import Path
from canonical.runtime.terminal_frontier_factorizer_v2 import ATOMIC, META

ROOT=Path(__file__).resolve().parents[2]
MAN=ROOT/"canonical/governance/V9_SELECTED_CELL_MANIFEST_20261007_V1.json"
V9=ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V9.json"
TH=ROOT/"canonical/governance/ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V1.json"

EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V9.json":"1ec7f2c86534d046e51ddda00001ed287039fc0a",
 "canonical/runtime/terminal_frontier_factorizer_v2.py":"7bf57811d1b745cc2b92596f6c1c87ff5693aa1c",
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
    v9=json.loads(V9.read_text(encoding="utf-8"))
    th=json.loads(TH.read_text(encoding="utf-8"))

    truths=set(ATOMIC)|set(META)
    bundles=m.get("route_bundles") or {}
    assigned=[]
    for bid,items in bundles.items():
        if not isinstance(bid,str) or not bid: errors.append("BUNDLE_ID_INVALID")
        if not isinstance(items,list) or not items: errors.append("BUNDLE_EMPTY:"+str(bid)); continue
        assigned.extend(map(str,items))
    aset=set(assigned)
    dup=sorted(x for x in aset if assigned.count(x)>1)
    if dup: errors.append("LEAF_DUPLICATE:"+",".join(dup))
    missing=sorted(truths-aset)
    extra=sorted(aset-truths)
    if missing: errors.append("LEAF_MISSING:"+",".join(missing))
    if extra: errors.append("LEAF_EXTRA:"+",".join(extra))
    if len(assigned)!=29: errors.append("ASSIGNED_COUNT_NOT_29")

    if v9["preserved_truth"]["open_truth_obligations"]!=29: errors.append("V9_TRUTH_COUNT_DRIFT")
    if v9["preserved_truth"]["terminal"] is not False: errors.append("V9_TERMINAL_DRIFT")

    known={str(x["id"]):str(x["class"]) for x in th.get("predicates") or []}
    declared={str(k):str(v) for k,v in (m.get("metric_classes") or {}).items()}
    for leaf,klass in declared.items():
        if leaf not in truths: errors.append("METRIC_CLASS_UNKNOWN_LEAF:"+leaf)
        if leaf in known and known[leaf]!=klass:
            errors.append("METRIC_CLASS_MISMATCH:"+leaf)
    for leaf in truths & set(known):
        if leaf not in declared and known[leaf] in {
            "ADDITIVE_THRESHOLD","GATED_WEIGHTED_THRESHOLD","RELATIVE_RATING_THRESHOLD","MATCHED_NONINFERIORITY"
        }:
            errors.append("MISSING_DECLARED_METRIC_CLASS:"+leaf)

    return {
      "schema":"PROJECT_BRAIN_V9_SELECTED_CELL_MANIFEST_VERIFIER_V1",
      "status":"PASS__29_LEAVES_EXACTLY_PARTITIONED__ROUTE_REUSE_HINTS_ZERO_CREDIT" if not errors else "FAIL_CLOSED",
      "pass":not errors,
      "errors":errors,
      "truth_leaf_count":29 if not errors else None,
      "route_bundle_count":len(bundles) if not errors else None,
      "metric_class_count":len(declared) if not errors else None,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
