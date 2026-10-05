"""Count-generic fail-closed terminal projection consistency for Project Brain.

Live strict acceptance is derived from:
1) the 19-family target envelope,
2) the frozen residual predicate registry,
3) the current atomic acceptance evidence ledger.

Families omitted from the residual registry are baseline-closed by construction of the
registry; residual families close iff every frozen predicate for that family is PROVED
and scope_complete in the current ledger. Historical family-specific receipts may remain
as provenance, but they do not drive live counters.
"""
from __future__ import annotations
import hashlib, json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

try:
    from canonical.runtime.material_condition_closure_v1 import compile_material_condition_closure
except ModuleNotFoundError:  # direct execution: python canonical/runtime/terminal_projection_consistency_v1.py
    from material_condition_closure_v1 import compile_material_condition_closure

ROOT=Path(__file__).resolve().parents[2]
PATHS={
    "authority":"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
    "closure":"canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json",
    "matrix":"canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json",
    "atomic_bindings":"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json",
    "predicate_registry":"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json",
    "target_envelope":"canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json",
    "material_condition_registry":"canonical/governance/OPUS55_MATERIAL_CONDITION_REGISTRY_V1.json",
    "material_condition_evidence":"canonical/governance/OPUS55_MATERIAL_CONDITION_EVIDENCE_BINDINGS_V1.json",
}

def _load(rel:str)->dict[str,Any]:
    value=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError(rel+":NOT_OBJECT")
    return value

def _git_blob_sha(rel:str)->str:
    data=(ROOT/rel).read_bytes()
    h=hashlib.sha1(); h.update(f"blob {len(data)}\0".encode()); h.update(data)
    return h.hexdigest()

def _derive(registry:Mapping[str,Any], atomic:Mapping[str,Any], envelope:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    families=[x.get("id") for x in envelope.get("families",[]) if isinstance(x,Mapping) and x.get("id")]
    if len(families)!=len(set(families)): errors.append("TARGET_ENVELOPE_DUPLICATE_FAMILY")
    if len(families)!=19: errors.append("TARGET_ENVELOPE_FAMILY_COUNT_NOT_19")
    family_set=set(families)

    residual=list(registry.get("residual_families") or [])
    if len(residual)!=len(set(residual)): errors.append("REGISTRY_DUPLICATE_RESIDUAL_FAMILY")
    if not set(residual)<=family_set: errors.append("REGISTRY_FAMILY_OUTSIDE_TARGET_ENVELOPE")

    preds=[x for x in registry.get("predicates",[]) if isinstance(x,Mapping)]
    ids=[x.get("id") for x in preds]
    if None in ids or len(ids)!=len(set(ids)): errors.append("REGISTRY_PREDICATE_IDS_INVALID")
    if not preds: errors.append("REGISTRY_PREDICATES_EMPTY")
    by_family=defaultdict(list)
    for p in preds:
        fam=p.get("family")
        if fam not in set(residual): errors.append("REGISTRY_PREDICATE_FAMILY_NOT_RESIDUAL:"+str(fam))
        by_family[fam].append(p.get("id"))
    if set(by_family)!=set(residual): errors.append("REGISTRY_RESIDUAL_FAMILY_WITHOUT_PREDICATE")

    claims=[x for x in atomic.get("claims",[]) if isinstance(x,Mapping) and x.get("predicate_id")]
    claim_ids=[x["predicate_id"] for x in claims]
    if len(claim_ids)!=len(set(claim_ids)): errors.append("ATOMIC_DUPLICATE_CLAIM")
    if not set(claim_ids)<=set(ids): errors.append("ATOMIC_CLAIM_OUTSIDE_REGISTRY")
    cmap={x["predicate_id"]:x for x in claims}
    proved={
        pid for pid in ids
        if (cmap.get(pid) or {}).get("state")=="PROVED"
        and (cmap.get(pid) or {}).get("scope_complete") is True
    }
    baseline=family_set-set(residual)
    accepted=set(baseline)
    for fam,pids in by_family.items():
        if pids and all(pid in proved for pid in pids):
            accepted.add(fam)
    return {
        "errors":errors,
        "target_families":family_set,
        "residual_families":set(residual),
        "baseline_families":baseline,
        "accepted_families":accepted,
        "open_families":family_set-accepted,
        "predicate_ids":set(ids),
        "proved_predicates":proved,
        "unresolved_predicates":set(ids)-proved,
    }

def evaluate_documents(authority:Mapping[str,Any], closure:Mapping[str,Any], matrix:Mapping[str,Any],
                       atomic:Mapping[str,Any], registry:Mapping[str,Any], envelope:Mapping[str,Any],
                       actual_blob_shas:Mapping[str,str]|None=None,
                       material_registry:Mapping[str,Any]|None=None,
                       material_evidence:Mapping[str,Any]|None=None,
                       material_source_receipt_blob_sha:str|None=None)->dict[str,Any]:
    d=_derive(registry,atomic,envelope)
    errors=list(d["errors"])
    accepted=d["accepted_families"]; opened=d["open_families"]
    proved=d["proved_predicates"]; unresolved=d["unresolved_predicates"]
    total_families=len(d["target_families"]); total_predicates=len(d["predicate_ids"])

    if material_registry is not None and material_evidence is not None:
        material=compile_material_condition_closure(
            material_registry,material_evidence,envelope,
            verified_source_universe_receipt_sha=material_source_receipt_blob_sha,
        )
        if not material.get("pass"):
            errors.extend("MATERIAL_CONDITION_GATE:"+str(e) for e in material.get("errors",[]))
    else:
        material={
            "pass":True,
            "condition_count":0,
            "proved_condition_count":0,
            "open_condition_count":0,
            "open_conditions":[],
            "source_universe_sealed":False,
            "terminal_condition_gate_pass":False,
        }

    sat=atomic.get("saturation") if isinstance(atomic.get("saturation"),Mapping) else {}
    if (sat.get("proved_predicate_count"),sat.get("unresolved_predicate_count"))!=(len(proved),len(unresolved)):
        errors.append("ATOMIC_LEDGER_SATURATION_MISMATCH")

    truth=authority.get("truth") if isinstance(authority.get("truth"),Mapping) else {}
    if truth.get("opus55_acceptance")!=f"{len(accepted)}/{total_families}_PASS__{len(opened)}/{total_families}_OPEN":
        errors.append("AUTHORITY_ACCEPTANCE_MISMATCH")
    claimed_achieved=truth.get("achieved")
    if claimed_achieved not in (True,False):
        errors.append("AUTHORITY_TERMINAL_ACHIEVED_NOT_BOOLEAN")
    acceptance_complete=(len(opened)==0 and len(unresolved)==0)
    terminal_finality_eligible=acceptance_complete and bool(material.get("terminal_condition_gate_pass"))
    if claimed_achieved is True and not acceptance_complete:
        errors.append("AUTHORITY_TERMINAL_TRUE_WITH_OPEN_ACCEPTANCE")
    if claimed_achieved is True and not material.get("terminal_condition_gate_pass"):
        errors.append("AUTHORITY_TERMINAL_TRUE_WITH_OPEN_MATERIAL_CONDITION_GATE")
    af=authority.get("atomic_acceptance_frontier") if isinstance(authority.get("atomic_acceptance_frontier"),Mapping) else {}
    if (af.get("proved"),af.get("unresolved"),af.get("total"))!=(len(proved),len(unresolved),total_predicates):
        errors.append("AUTHORITY_ATOMIC_FRONTIER_MISMATCH")
    if af.get("authorized_acceptance_case_actions")!=[]:
        errors.append("AUTHORITY_UNAUTHORIZED_CASE_ACTION_PRESENT")

    cs=closure.get("opus55_acceptance_summary") if isinstance(closure.get("opus55_acceptance_summary"),Mapping) else {}
    if (cs.get("calibrated_family_count"),cs.get("pending_family_count"))!=(len(accepted),len(opened)):
        errors.append("CLOSURE_ACCEPTANCE_COUNTS_MISMATCH")
    if set(cs.get("calibrated_families") or [])!=accepted:
        errors.append("CLOSURE_ACCEPTED_FAMILY_SET_MISMATCH")
    ca=cs.get("atomic_predicates") if isinstance(cs.get("atomic_predicates"),Mapping) else {}
    if (ca.get("proved"),ca.get("unresolved"),ca.get("total"))!=(len(proved),len(unresolved),total_predicates):
        errors.append("CLOSURE_ATOMIC_COUNTS_MISMATCH")
    crows={x.get("id"):x for x in closure.get("families",[]) if isinstance(x,Mapping) and x.get("id")}
    for fam in d["target_families"]:
        row=crows.get(fam)
        if not isinstance(row,Mapping):
            errors.append("CLOSURE_FAMILY_ROW_MISSING:"+fam); continue
        should=fam in accepted
        if bool(row.get("opus55_acceptance_calibrated"))!=should:
            errors.append("CLOSURE_FAMILY_CALIBRATION_MISMATCH:"+fam)
        if (row.get("opus55_acceptance_state")=="PASS")!=should:
            errors.append("CLOSURE_FAMILY_STATE_MISMATCH:"+fam)

    ms=matrix.get("postwave_acceptance_summary") if isinstance(matrix.get("postwave_acceptance_summary"),Mapping) else {}
    if (ms.get("calibrated_family_count"),ms.get("pending_acceptance_family_count"))!=(len(accepted),len(opened)):
        errors.append("MATRIX_ACCEPTANCE_COUNTS_MISMATCH")
    if set(ms.get("calibrated_families") or [])!=accepted:
        errors.append("MATRIX_ACCEPTED_FAMILY_SET_MISMATCH")
    ma=ms.get("atomic_acceptance") if isinstance(ms.get("atomic_acceptance"),Mapping) else {}
    if (ma.get("proved"),ma.get("unresolved"),ma.get("total"))!=(len(proved),len(unresolved),total_predicates):
        errors.append("MATRIX_ATOMIC_COUNTS_MISMATCH")
    mrows={x.get("family"):x for x in matrix.get("rows",[]) if isinstance(x,Mapping) and x.get("family")}
    for fam in d["target_families"]:
        row=mrows.get(fam)
        if not isinstance(row,Mapping):
            errors.append("MATRIX_FAMILY_ROW_MISSING:"+fam); continue
        status=str(row.get("postwave_opus55_acceptance_status",""))
        ispass=status=="PASS" or status.startswith("PASS_")
        if ispass!=(fam in accepted):
            errors.append("MATRIX_FAMILY_ACCEPTANCE_MISMATCH:"+fam)
        if row.get("postwave_ownership_credit")=="VERIFIED_OWNED_EQUAL_OR_BETTER" and fam not in accepted:
            errors.append("MATRIX_OWNERSHIP_WITHOUT_ACCEPTANCE:"+fam)

    sources=authority.get("sources") if isinstance(authority.get("sources"),Mapping) else {}
    for key in ("residual_plan","acceptance_residual_proof_kernel_v2"):
        row=sources.get(key)
        if not isinstance(row,Mapping) or not any(t in str(row.get("status","")) for t in ("HISTORICAL","SUPERSEDED")):
            errors.append("STALE_PLANNING_SOURCE_NOT_DEMOTED:"+key)

    if actual_blob_shas is not None:
        pointer_expectations={
            "terminal_closure_manifest":PATHS["closure"],
            "ownership_matrix":PATHS["matrix"],
            "acceptance_predicate_evidence_bindings_reconciled":PATHS["atomic_bindings"],
        }
        for key,rel in pointer_expectations.items():
            row=sources.get(key)
            if not isinstance(row,Mapping):
                errors.append("AUTHORITY_SOURCE_MISSING:"+key); continue
            if row.get("path")!=rel: errors.append("AUTHORITY_SOURCE_PATH_MISMATCH:"+key)
            if row.get("git_blob_sha")!=actual_blob_shas.get(rel):
                errors.append("AUTHORITY_SOURCE_BLOB_MISMATCH:"+key)

    unique=sorted(set(errors))
    return {
        "schema":"PROJECT_BRAIN_TERMINAL_PROJECTION_CONSISTENCY_VERDICT_V4",
        "status":"PASS" if not unique else "FAIL_CLOSED",
        "pass":not unique,"errors":unique,
        "acceptance_closed_families":len(accepted),
        "acceptance_open_families":len(opened),
        "accepted_families":sorted(accepted),
        "baseline_families":sorted(d["baseline_families"]),
        "atomic_predicates_proved":len(proved),
        "atomic_predicates_unresolved":len(unresolved),
        "material_conditions_total":material.get("condition_count",0),
        "material_conditions_proved":material.get("proved_condition_count",0),
        "material_conditions_open":material.get("open_condition_count",0),
        "material_condition_open_ids":material.get("open_conditions",[]),
        "material_condition_source_universe_sealed":bool(material.get("source_universe_sealed")),
        "material_condition_gate_pass":bool(material.get("terminal_condition_gate_pass")),
        "terminal_finality_eligible":terminal_finality_eligible,
        "terminal_goal_achieved":bool(claimed_achieved is True and terminal_finality_eligible),
        "capability_credit_delta":0,"family_credit_delta":0,
        "promotion_authority":False,"execution_authority":False,
        "rule":"TERMINAL_FINALITY_REQUIRES_DYNAMIC_FAMILY_ACCEPTANCE_CLOSURE__DYNAMIC_MATERIAL_CONDITION_CLOSURE__AND_INDEPENDENT_SOURCE_UNIVERSE_SEAL__NO_FIXED_PREDICATE_DENOMINATOR_IS_TERMINAL_SUFFICIENT",
    }

def evaluate_live()->dict[str,Any]:
    docs={k:_load(v) for k,v in PATHS.items()}
    shas={v:_git_blob_sha(v) for v in PATHS.values()}
    receipt_sha=None
    source_universe=docs["material_condition_registry"].get("source_universe")
    if isinstance(source_universe,Mapping) and source_universe.get("sealed") is True:
        receipt=source_universe.get("independent_seal_receipt")
        if isinstance(receipt,Mapping) and isinstance(receipt.get("path"),str):
            try:
                receipt_sha=_git_blob_sha(receipt["path"])
            except (FileNotFoundError, OSError):
                receipt_sha=None
    return evaluate_documents(docs["authority"],docs["closure"],docs["matrix"],docs["atomic_bindings"],
                              docs["predicate_registry"],docs["target_envelope"],shas,
                              docs["material_condition_registry"],docs["material_condition_evidence"],
                              receipt_sha)

def main()->int:
    out=evaluate_live(); print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__": raise SystemExit(main())
