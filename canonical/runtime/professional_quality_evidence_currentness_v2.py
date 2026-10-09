"""Professional-quality evidence currentness gate V2.

V1 detects stale content-addressed evidence. V2 additionally permits a stale
mutable CURRENT pointer to be rebound only when the new bytes preserve a small,
explicit support contract. No domain semantic or execution authority is added.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_EVIDENCE_CURRENTNESS_V2"
DEFAULT_MATRIX="canonical/governance/PROFESSIONAL_QUALITY_EXISTING_EVIDENCE_REUSE_MATRIX_20261009_V1.json"
ASSURANCE_POINTER="canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"
R2_POINTER="canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
MUTABLE_POINTER_PATHS=frozenset({ASSURANCE_POINTER,R2_POINTER})

def git_blob_sha(path: Path) -> str:
    data=path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii")+data).hexdigest()

def _load(path: Path) -> dict[str,Any] | None:
    try: value=json.loads(path.read_text())
    except (OSError,UnicodeDecodeError,json.JSONDecodeError): return None
    return value if isinstance(value,dict) else None

def support_contract(rel: str, path: Path) -> tuple[bool,str]:
    obj=_load(path)
    if obj is None:
        return False,"POINTER_NOT_JSON_OBJECT"
    if rel==ASSURANCE_POINTER:
        if obj.get("schema")!="PROJECT_BRAIN_CURRENT_ASSURANCE_CLOSURE_COMPILER_POINTER_V1":
            return False,"ASSURANCE_SCHEMA_CHANGED"
        if obj.get("terminal_authority") is not False:
            return False,"ASSURANCE_TERMINAL_AUTHORITY_CHANGED"
        if (obj.get("runtime") or {}).get("path")!="canonical/runtime/assurance_closure_compiler_v1.py":
            return False,"ASSURANCE_RUNTIME_CHANGED"
        live=obj.get("live_default")
        if live is None: live=(obj.get("activation") or {}).get("live_default")
        if live is not False:
            return False,"ASSURANCE_LIVE_DEFAULT_BOUNDARY_CHANGED"
        return True,"ASSURANCE_SUPPORT_CONTRACT_PRESERVED"
    if rel==R2_POINTER:
        if obj.get("schema")!="PROJECT_BRAIN_CURRENT_R2_DECISION_INTELLIGENCE_POINTER_V1":
            return False,"R2_SCHEMA_CHANGED"
        if obj.get("general_mechanism_missing") is not False:
            return False,"R2_GENERAL_MECHANISM_STATE_CHANGED"
        if obj.get("control_mechanism_status")!="CLOSED__TOTAL_FAIL_CLOSED_ADEQUACY_OR_ABSTAIN_CONTROL":
            return False,"R2_CONTROL_STATE_CHANGED"
        if (obj.get("direct_adequacy") or {}).get("fixed_point_controller_path")!="canonical/runtime/general_adequate_decision_fixed_point_v2.py":
            return False,"R2_FIXED_POINT_CHANGED"
        return True,"R2_SUPPORT_CONTRACT_PRESERVED"
    return False,"UNRECOGNIZED_MUTABLE_POINTER"

def evaluate(repo_root: str | Path, matrix_path: str=DEFAULT_MATRIX) -> dict[str,Any]:
    root=Path(repo_root)
    matrix=_load(root/matrix_path)
    if matrix is None:
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"MATRIX_UNAVAILABLE","terminal_authority":False,"terminal_credit_delta":0}
    rows=[]; fresh=0; rebound=0; stale=[]; broken=[]
    for rr in matrix.get("roots") or []:
        rid=rr.get("id")
        for ev in rr.get("evidence") or []:
            rel=ev.get("path"); expected=ev.get("git_blob_sha"); p=root/str(rel)
            reason=None
            if not p.is_file():
                actual=None; state="MISSING_EVIDENCE_FILE"; broken.append((rid,rel))
            else:
                actual=git_blob_sha(p)
                if actual==expected:
                    state="FRESH"; fresh+=1
                elif rel in MUTABLE_POINTER_PATHS:
                    ok,reason=support_contract(str(rel),p)
                    if ok:
                        state="VERIFIED_REBOUND"; rebound+=1
                    else:
                        state="STALE_REBIND_REQUIRED"; stale.append((rid,rel))
                else:
                    state="BROKEN_EVIDENCE_BINDING"; broken.append((rid,rel))
            rows.append({"root_id":rid,"path":rel,"expected_git_blob_sha":expected,"actual_git_blob_sha":actual,"state":state,"support_contract":reason})
    passed=not stale and not broken
    status=("FAIL_CLOSED__BROKEN_EVIDENCE_BINDING" if broken else "OPEN__MUTABLE_POINTER_SUPPORT_CONTRACT_FAILED" if stale else "PASS__ALL_EVIDENCE_CURRENT_OR_CONTRACT_VERIFIED_REBOUND")
    return {
        "schema":SCHEMA,"pass":passed,"status":status,
        "evidence_entry_count":len(rows),"fresh_count":fresh,
        "verified_rebind_count":rebound,"stale_rebind_count":len(stale),
        "broken_binding_count":len(broken),"rows":rows,
        "semantic_truth_authority":False,"execution_authority":False,
        "acceptance_authority":False,"terminal_authority":False,
        "terminal_credit_delta":0,"incremental_spend_usd":0,
    }
