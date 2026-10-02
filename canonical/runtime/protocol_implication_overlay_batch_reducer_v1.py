"""Compile independently verified pair residuals onto the global implication batch."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime.protocol_implication_batch_reducer_v1 import reduce_batch as base_reduce
from canonical.runtime.protocol_implication_scope_algebra_v2 import evaluate as evaluate_pair

SCHEMA="PROJECT_BRAIN_PROTOCOL_IMPLICATION_OVERLAY_BATCH_REDUCER_V1"
ROOT=Path(__file__).resolve().parents[2]

def _blob_sha(path: Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()

def _fail(*errors:str)->dict[str,Any]:
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors)),
        "target_count":0,"base_pair_count":0,"verified_overlay_pair_count":0,
        "total_pair_count":0,"improved_target_count":0,"acceptance_credit_delta":0,
        "family_credit_delta":0,"execution_authority":False,"promotion_authority":False,
        "new_reality_units_consumed":0}

def _metric_failures(row:Mapping[str,Any])->list[str]:
    return sorted(x.get("metric") for x in row.get("metric_results",[])
        if isinstance(x,Mapping) and x.get("pass") is not True and isinstance(x.get("metric"),str))

def _score(row:Mapping[str,Any])->tuple[int,int,int,str]:
    return (1 if row.get("scope_relation_missing") else 0,
        len(row.get("missing_atoms",[])),len(_metric_failures(row)),
        str(row.get("witness_id") or row.get("overlay_id") or ""))

def reduce_with_overlays(target_doc:Mapping[str,Any],witness_doc:Mapping[str,Any],
    contamination_doc:Mapping[str,Any],manifest:Mapping[str,Any],*,root:Path=ROOT)->dict[str,Any]:
    base=base_reduce(target_doc,witness_doc,contamination_doc)
    if not str(base.get("status","")).startswith("PASS"): return _fail("BASE_BATCH_NOT_PASS")
    overlays=manifest.get("overlays")
    if not isinstance(overlays,list): return _fail("OVERLAYS_NOT_LIST")
    known={x.get("predicate_id") for x in target_doc.get("targets",[]) if isinstance(x,Mapping)}
    overlay_rows=[]; errors=[]
    for i,item in enumerate(overlays):
        if not isinstance(item,Mapping): errors.append(f"OVERLAY_{i}_INVALID"); continue
        oid=item.get("id"); target_id=item.get("target_predicate_id")
        if not isinstance(oid,str) or not oid: errors.append(f"OVERLAY_{i}_ID_INVALID"); continue
        if target_id not in known: errors.append(f"OVERLAY_TARGET_UNKNOWN:{oid}"); continue
        docs={}
        for key in ("input","independent_verification","scope_falsification"):
            ref=item.get(key)
            if not isinstance(ref,Mapping) or not isinstance(ref.get("path"),str) or not isinstance(ref.get("git_blob_sha"),str):
                errors.append(f"OVERLAY_REF_INVALID:{oid}:{key}"); continue
            path=root/ref["path"]
            if not path.exists(): errors.append(f"OVERLAY_FILE_MISSING:{oid}:{key}"); continue
            if _blob_sha(path)!=ref["git_blob_sha"]: errors.append(f"OVERLAY_BLOB_MISMATCH:{oid}:{key}"); continue
            docs[key]=json.loads(path.read_text(encoding="utf-8"))
        if len(docs)!=3: continue
        inp=docs["input"]; receipt=docs["independent_verification"]; falsification=docs["scope_falsification"]; expected=item.get("expected",{})
        if not str(receipt.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
            errors.append(f"OVERLAY_VERIFICATION_NOT_PASS:{oid}"); continue
        if receipt.get("result",{}).get("target_predicate_id")!=target_id:
            errors.append(f"OVERLAY_RECEIPT_TARGET_MISMATCH:{oid}"); continue
        if falsification.get("scope_relation_verified") is not False or falsification.get("target_predicate_closed") is not False:
            errors.append(f"OVERLAY_SCOPE_FALSIFICATION_NOT_BOUND:{oid}"); continue
        algebra_input=inp.get("algebra_input")
        if not isinstance(algebra_input,Mapping): errors.append(f"OVERLAY_ALGEBRA_INPUT_INVALID:{oid}"); continue
        verdict=evaluate_pair(algebra_input); metric_missing=_metric_failures(verdict)
        scope_missing=verdict.get("status")=="TARGET_SCOPE_NOT_COVERED"
        if verdict.get("implies_target") is not expected.get("implies_target"): errors.append(f"OVERLAY_IMPLICATION_MISMATCH:{oid}"); continue
        if sorted(verdict.get("missing_atoms",[]))!=sorted(expected.get("missing_atoms",[])): errors.append(f"OVERLAY_MISSING_ATOMS_MISMATCH:{oid}"); continue
        if metric_missing!=sorted(expected.get("missing_metric_bounds",[])): errors.append(f"OVERLAY_METRIC_RESIDUAL_MISMATCH:{oid}"); continue
        if scope_missing is not expected.get("missing_scope_relation"): errors.append(f"OVERLAY_SCOPE_RESIDUAL_MISMATCH:{oid}"); continue
        overlay_rows.append({"target_predicate_id":target_id,"overlay_id":oid,"witness_id":"OVERLAY::"+oid,
            "status":verdict.get("status"),"implies_target":verdict.get("implies_target") is True,
            "missing_atoms":sorted(verdict.get("missing_atoms",[])),"metric_results":verdict.get("metric_results",[]),
            "candidate_scope_relation":verdict.get("candidate_scope_relation"),"scope_relation_missing":scope_missing,
            "verified_overlay":True,"verification_receipt":item["independent_verification"]["path"],
            "scope_falsification_receipt":item["scope_falsification"]["path"]})
    if errors: return _fail(*errors)
    all_pairs=list(base.get("pair_results",[]))+overlay_rows; target_results=[]; improved=0
    for target_id in sorted(known):
        base_rows=[r for r in base.get("pair_results",[]) if r.get("target_predicate_id")==target_id]
        rows=[r for r in all_pairs if r.get("target_predicate_id")==target_id]
        if not rows or not base_rows: return _fail(f"TARGET_PAIR_SURFACE_INCOMPLETE:{target_id}")
        base_best=min(base_rows,key=_score); best=min(rows,key=_score)
        if _score(best)<_score(base_best): improved+=1
        target_results.append({"predicate_id":target_id,"implied":any(r.get("implies_target") is True for r in rows),
            "best_current_source_id":best.get("overlay_id") or best.get("witness_id"),
            "best_current_source_kind":"VERIFIED_OVERLAY" if best.get("verified_overlay") else "BASE_WITNESS",
            "best_current_scope_relation_missing":best.get("scope_relation_missing") is True,
            "best_current_missing_atoms":sorted(best.get("missing_atoms",[])),
            "best_current_failed_metrics":_metric_failures(best),
            "base_best_hole_score":list(_score(base_best)[:3]),"current_best_hole_score":list(_score(best)[:3])})
    return {"schema":SCHEMA,"status":"PASS__VERIFIED_OVERLAYS_COMPILED__RESIDUALS_EXPLICIT__ZERO_CREDIT",
        "errors":[],"target_count":len(target_results),"base_pair_count":len(base.get("pair_results",[])),
        "verified_overlay_pair_count":len(overlay_rows),"total_pair_count":len(all_pairs),"improved_target_count":improved,
        "closed_target_count":sum(1 for x in target_results if x["implied"]),"target_results":target_results,
        "overlay_pair_results":overlay_rows,
        "rule":"ONLY_EXACT_INDEPENDENTLY_VERIFIED_PAIR_RESIDUALS_MAY_OVERLAY_THE_BASE_SURFACE__SCOPE_FALSIFICATION_REMAINS_LOAD_BEARING__NO_NEW_SCOPE_ATOM_METRIC_OR_CREDIT_INFERENCE",
        "acceptance_credit_delta":0,"family_credit_delta":0,"execution_authority":False,"promotion_authority":False,"new_reality_units_consumed":0}

def main()->int:
    t=json.loads((ROOT/"canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json").read_text())
    w=json.loads((ROOT/"canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json").read_text())
    c=json.loads((ROOT/"canonical/verification/OPUS55_BRAIN_WITNESS_CONTAMINATION_ADMISSIBILITY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json").read_text())
    m=json.loads((ROOT/"canonical/governance/VERIFIED_WITNESS_TARGET_OVERLAY_MANIFEST_V1.json").read_text())
    out=reduce_with_overlays(t,w,c,m)
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if str(out.get("status","")).startswith("PASS") else 1

if __name__=="__main__": raise SystemExit(main())
