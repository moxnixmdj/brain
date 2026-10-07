from __future__ import annotations
import hashlib, json
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_TERMINAL_SEMANTIC_QUOTIENT_V1"

def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def _sha(v:Any)->str:
    return hashlib.sha256(_canon(v).encode()).hexdigest()

def compile_minimal_quotient(rows:Sequence[Mapping[str,Any]])->dict[str,Any]:
    """Finite exact compiler for the minimum terminal-relevant semantic quotient.

    Each row must bind one raw-state id to its COMPLETE terminal-relevant signature.
    The signature contains exactly the evaluator/hard-constraint/decision facts whose
    differences can change terminal correctness. Meaning classes are induced by
    equality of that signature, not by wording or model consensus.
    """
    if not isinstance(rows, Sequence) or isinstance(rows,(str,bytes)) or not rows:
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"ROWS_REQUIRED"}

    seen=set()
    normalized=[]
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":f"ROW_NOT_OBJECT:{i}"}
        rid=row.get("raw_id")
        sig=row.get("terminal_signature")
        complete=row.get("signature_complete")
        if not isinstance(rid,str) or not rid or rid in seen:
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":f"RAW_ID_INVALID:{i}"}
        if complete is not True:
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":f"SIGNATURE_COMPLETENESS_UNPROVED:{rid}"}
        if not isinstance(sig,Mapping):
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":f"SIGNATURE_INVALID:{rid}"}
        seen.add(rid)
        normalized.append((rid,dict(sig)))

    by_sig={}
    for rid,sig in normalized:
        key=_sha(sig)
        by_sig.setdefault(key,{"signature":sig,"members":[]})["members"].append(rid)

    classes=[]
    for key,v in sorted(by_sig.items()):
        classes.append({
            "semantic_class_id":"SEM-"+key[:16],
            "terminal_signature_sha256":key,
            "terminal_signature":v["signature"],
            "raw_ids":sorted(v["members"]),
        })

    raw_to_class={rid:c["semantic_class_id"] for c in classes for rid in c["raw_ids"]}
    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__MINIMUM_TERMINAL_RELEVANT_QUOTIENT_ON_BOUND_FINITE_DOMAIN",
        "raw_count":len(normalized),
        "class_count":len(classes),
        "classes":classes,
        "raw_to_class":raw_to_class,
        "theorem_boundary":"EXACT_ONLY_IF_EACH_TERMINAL_SIGNATURE_IS_COMPLETE_FOR_ALL_LOAD_BEARING_EVALUATORS_HARD_CONSTRAINTS_AND_DECISIONS",
        "terminal_authority":False,
        "capability_credit_delta":0,
    }

def verify_binding(rows:Sequence[Mapping[str,Any]], binding:Mapping[str,str])->dict[str,Any]:
    compiled=compile_minimal_quotient(rows)
    if compiled.get("pass") is not True:
        return compiled
    expected=compiled["raw_to_class"]
    if not isinstance(binding,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"BINDING_REQUIRED"}
    missing=sorted(set(expected)-set(binding))
    extra=sorted(set(binding)-set(expected))
    if missing or extra:
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"BINDING_DOMAIN_MISMATCH","missing":missing,"extra":extra}

    false_merges=[]
    class_to_raw={}
    for rid,cid in binding.items():
        class_to_raw.setdefault(str(cid),[]).append(rid)
    sig_by_raw={r["raw_id"]:r["terminal_signature"] for r in rows}
    for cid,members in class_to_raw.items():
        sigs={_sha(sig_by_raw[r]) for r in members}
        if len(sigs)>1:
            false_merges.append({"binding_class":cid,"raw_ids":sorted(members),"terminal_signature_hashes":sorted(sigs)})
    if false_merges:
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED__TERMINALLY_DISTINGUISHABLE_STATES_MERGED","false_merges":false_merges}

    # Redundant splits are safe but nonminimal.
    expected_partition={frozenset(c["raw_ids"]) for c in compiled["classes"]}
    proposed_partition={frozenset(v) for v in class_to_raw.values()}
    minimal=(expected_partition==proposed_partition)
    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__SEMANTIC_BINDING_SOUND"+("__AND_MINIMAL" if minimal else "__NONMINIMAL_REFINEMENT"),
        "sound_no_false_merge":True,
        "minimal":minimal,
        "expected_minimal_class_count":compiled["class_count"],
        "proposed_class_count":len(class_to_raw),
        "terminal_authority":False,
        "capability_credit_delta":0,
    }
