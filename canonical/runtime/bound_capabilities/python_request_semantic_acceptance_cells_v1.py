from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import re
from typing import Any, Mapping, Sequence

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.bound_capabilities import python_repository_acceptance_measurement_v1 as measured

SCHEMA="PROJECT_BRAIN_PYTHON_REQUEST_SEMANTIC_ACCEPTANCE_CELLS_V1"
CAPABILITY_ID="python.software.request.semantic_cells.v1"
MODEL_DEPENDENCY_COUNT=0
EXTERNAL_MODEL_RUNTIME_CALLS=0

class SemanticCellError(RuntimeError):
    pass

_QUOTED=r'["“]([^"”]+)["”]'

def _canon(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)

def _sha_obj(x:Any)->str:
    return hashlib.sha256(_canon(x).encode("utf-8")).hexdigest()

def _safe_rel(raw:Any)->str:
    if not isinstance(raw,str) or not raw.strip() or "\x00" in raw:
        raise SemanticCellError("PATH_INVALID")
    p=pathlib.PurePosixPath(raw.replace("\\","/").strip())
    if p.is_absolute() or any(part in {"",".",".."} for part in p.parts):
        raise SemanticCellError("PATH_INVALID")
    return p.as_posix()

def _safe_candidate_path(root:pathlib.Path,raw:Any)->pathlib.Path:
    rel=_safe_rel(raw)
    rawp=root/rel
    if rawp.is_symlink():
        raise SemanticCellError("SYMLINK_REJECTED:"+rel)
    p=rawp.resolve()
    if p==root or root not in p.parents:
        raise SemanticCellError("PATH_OUTSIDE_CANDIDATE")
    return p

def _logical_segments(text:str)->list[tuple[int,int,str]]:
    out=[];start=0;ascii_quote=False;curly_quote=False;i=0
    def emit(a:int,b:int)->None:
        while a<b and text[a].isspace(): a+=1
        while b>a and text[b-1].isspace(): b-=1
        if a<b and text[a:b].strip(): out.append((a,b,text[a:b]))
    while i<len(text):
        ch=text[i]
        if ch=='"' and not curly_quote:
            ascii_quote=not ascii_quote
        elif ch=="“" and not ascii_quote:
            curly_quote=True
        elif ch=="”" and curly_quote and not ascii_quote:
            curly_quote=False
        outside=not ascii_quote and not curly_quote
        if outside and ch=="\n":
            emit(start,i+1);start=i+1;i+=1;continue
        if outside and ch in ".!?":
            j=i+1
            while j<len(text) and text[j] in ".!?": j+=1
            emit(start,j);start=j;i=j;continue
        i+=1
    emit(start,len(text))
    if ascii_quote or curly_quote:
        raise SemanticCellError("UNBALANCED_QUOTED_SOURCE")
    return out

def _classify(segment:str)->dict[str,Any]|None:
    s=" ".join(segment.strip().split())
    pats=[
      ("FILE_NOT_CONTAINS",rf'(?i)^(?:the\s+)?file\s+{_QUOTED}\s+must\s+not\s+contain\s+{_QUOTED}[.!]?$'),
      ("FILE_CONTAINS",rf'(?i)^(?:the\s+)?file\s+{_QUOTED}\s+must\s+contain\s+{_QUOTED}[.!]?$'),
      ("FILE_ABSENT",rf'(?i)^(?:the\s+)?file\s+{_QUOTED}\s+must\s+not\s+exist[.!]?$'),
      ("FILE_EXISTS",rf'(?i)^(?:the\s+)?file\s+{_QUOTED}\s+must\s+exist[.!]?$'),
      ("PYTHON_AST_PARSE",rf'(?i)^python\s+file\s+{_QUOTED}\s+must\s+(?:parse|compile)[.!]?$'),
      ("PATH_UNCHANGED",rf'(?i)^(?:do\s+not\s+modify|must\s+not\s+modify)\s+{_QUOTED}[.!]?$'),
    ]
    for kind,pat in pats:
        m=re.fullmatch(pat,s)
        if not m: continue
        g=list(m.groups())
        if kind in {"FILE_CONTAINS","FILE_NOT_CONTAINS"}:
            return {"kind":kind,"path":_safe_rel(g[0]),"literal":g[1]}
        return {"kind":kind,"path":_safe_rel(g[0])}
    m=re.fullmatch(rf'(?i)^only\s+modify\s+{_QUOTED}[.!]?$',s)
    if m:
        return {"kind":"CHANGED_PATHS_SUBSET","allowed_paths":[_safe_rel(m.group(1))]}
    return None

def compile_cells(
    task_text:str,
    *,
    source_id:str="user",
    routing_target_effects:Sequence[str]=("candidate.ready",),
)->dict[str,Any]:
    try:
        contract=compile_contract(task_text,source_id=source_id,routing_target_effects=list(routing_target_effects))
        if contract.get("pass") is not True:
            raise SemanticCellError("RAW_TASK_CONTRACT_FAILED")
        raw=list(contract["acceptance_contract"]["obligations"])
        required=[str(x) for x in contract["acceptance_contract"]["required_obligation_ids"]]
        cells=[];unbound=[];covered=[]
        for start,end,text in _logical_segments(task_text):
            rows=[r for r in raw if start<=int(r["span"][0]) and int(r["span"][1])<=end]
            if not rows:
                raise SemanticCellError("LOGICAL_SEGMENT_HAS_NO_RAW_OBLIGATION")
            ids=[str(r["obligation_id"]) for r in rows]
            covered.extend(ids)
            verifier=_classify(text)
            row={
              "cell_id":"SCELL:"+_sha_obj({"ids":ids,"span":[start,end],"verifier":verifier}),
              "raw_text":text,
              "logical_span":[start,end],
              "obligation_ids":ids,
              "verifier":verifier,
              "status":"BOUND_SOURCE_GROUNDED" if verifier is not None else "UNBOUND",
            }
            cells.append(row)
            if verifier is None: unbound.extend(ids)
        if len(covered)!=len(set(covered)) or set(covered)!=set(required):
            raise SemanticCellError("RAW_OBLIGATION_COVERAGE_MISMATCH")
        return {
          "schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"COMPILED",
          "pass":True,"task_contract":contract,"task_contract_sha256":contract["task_contract_sha256"],
          "cells":cells,"required_obligation_ids":required,
          "source_grounded_cell_count":sum(x["verifier"] is not None for x in cells),
          "unbound_obligation_ids":sorted(set(unbound)),
          "all_raw_obligations_semantically_bound":not unbound,
          "model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,
          "terminal_authority":False,
        }
    except Exception as exc:
        return {
          "schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"FAIL_CLOSED","pass":False,
          "errors":[type(exc).__name__+":"+str(exc)],"terminal_authority":False,
        }

def _manifest(root:pathlib.Path)->tuple[list[dict[str,Any]],str]:
    return measured._tree_manifest(root,max_files=20000,max_bytes=500_000_000)

def _changed(before:list[dict[str,Any]],after:list[dict[str,Any]])->list[str]:
    a={r["path"]:r["sha256"] for r in before};b={r["path"]:r["sha256"] for r in after}
    return sorted(p for p in set(a)|set(b) if a.get(p)!=b.get(p))

def _eval(verifier:Mapping[str,Any],candidate:pathlib.Path,changed:list[str])->tuple[bool,str,dict[str,Any]]:
    kind=str(verifier.get("kind") or "");details={"kind":kind}
    if kind=="CHANGED_PATHS_SUBSET":
        allowed={_safe_rel(x) for x in verifier.get("allowed_paths") or []}
        ok=set(changed)<=allowed;details.update({"allowed_paths":sorted(allowed),"changed_paths":changed})
        return ok,"CHANGED_PATHS_WITHIN_SCOPE" if ok else "CHANGED_PATH_OUTSIDE_SCOPE",details
    if kind=="PATH_UNCHANGED":
        path=_safe_rel(verifier.get("path"));ok=path not in set(changed);details.update({"path":path,"changed_paths":changed})
        return ok,"PATH_UNCHANGED" if ok else "PATH_CHANGED",details
    path=_safe_rel(verifier.get("path"));raw=candidate/path
    if kind=="FILE_ABSENT":
        ok=not raw.exists() and not raw.is_symlink();details["path"]=path
        return ok,"FILE_ABSENT" if ok else "FILE_PRESENT",details
    try:
        p=_safe_candidate_path(candidate,path)
    except SemanticCellError as exc:
        return False,str(exc),{"kind":kind,"path":path}
    details["path"]=path
    if kind=="FILE_EXISTS":
        ok=p.is_file();return ok,"FILE_EXISTS" if ok else "FILE_MISSING",details
    if kind in {"FILE_CONTAINS","FILE_NOT_CONTAINS"}:
        if not p.is_file(): return False,"FILE_MISSING",details
        data=p.read_bytes()
        if len(data)>4_000_000: return False,"FILE_TOO_LARGE",details
        try: text=data.decode("utf-8")
        except UnicodeDecodeError: return False,"FILE_NOT_UTF8",details
        literal=str(verifier.get("literal") or "");found=literal in text
        details.update({"file_sha256":hashlib.sha256(data).hexdigest(),"literal_sha256":hashlib.sha256(literal.encode()).hexdigest()})
        ok=found if kind=="FILE_CONTAINS" else not found
        return ok,"LITERAL_PRESENT" if found else "LITERAL_ABSENT",details
    if kind=="PYTHON_AST_PARSE":
        if not p.is_file() or p.suffix!=".py": return False,"PYTHON_FILE_INVALID",details
        try: ast.parse(p.read_text(encoding="utf-8"),filename=str(p))
        except (SyntaxError,UnicodeDecodeError): return False,"PYTHON_PARSE_FAILED",details
        details["file_sha256"]=hashlib.sha256(p.read_bytes()).hexdigest()
        return True,"PYTHON_PARSE_PASS",details
    return False,"UNKNOWN_SEMANTIC_CELL_KIND",details

def evaluate_cells(
    task_text:str,
    *,
    baseline_root:str|pathlib.Path,
    candidate_root:str|pathlib.Path,
    expected_baseline_snapshot_sha256:str|None=None,
    expected_candidate_snapshot_sha256:str|None=None,
)->dict[str,Any]:
    try:
        baseline=pathlib.Path(baseline_root).resolve();candidate=pathlib.Path(candidate_root).resolve()
        if not baseline.is_dir() or baseline.is_symlink(): raise SemanticCellError("BASELINE_ROOT_INVALID")
        if not candidate.is_dir() or candidate.is_symlink(): raise SemanticCellError("CANDIDATE_ROOT_INVALID")
        plan=compile_cells(task_text)
        if plan.get("pass") is not True: raise SemanticCellError("CELL_COMPILATION_FAILED")
        bm,bsha=_manifest(baseline);cm,csha=_manifest(candidate)
        if expected_baseline_snapshot_sha256 is not None and bsha!=expected_baseline_snapshot_sha256:
            raise SemanticCellError("BASELINE_SNAPSHOT_MISMATCH")
        if expected_candidate_snapshot_sha256 is not None and csha!=expected_candidate_snapshot_sha256:
            raise SemanticCellError("CANDIDATE_SNAPSHOT_MISMATCH")
        changed=_changed(bm,cm)
        rows=[];passed=set();failed=set();unbound=set()
        for cell in plan["cells"]:
            ids=set(cell["obligation_ids"])
            if not isinstance(cell.get("verifier"),Mapping):
                unbound.update(ids)
                rows.append({"cell_id":cell["cell_id"],"obligation_ids":sorted(ids),"status":"UNBOUND","pass":False})
                continue
            ok,reason,details=_eval(cell["verifier"],candidate,changed)
            (passed if ok else failed).update(ids)
            rows.append({"cell_id":cell["cell_id"],"obligation_ids":sorted(ids),"status":"VERIFIED_PASS" if ok else "VERIFIED_FAIL","pass":ok,"reason":reason,"details":details})
        payload={
          "schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"MEASURED_SOURCE_GROUNDED_SEMANTIC_CELLS","pass":not failed,
          "task_contract_sha256":plan["task_contract_sha256"],
          "baseline_snapshot_sha256":bsha,"candidate_snapshot_sha256":csha,
          "changed_paths":changed,"cell_results":rows,
          "passed_obligation_ids":sorted(passed),"failed_obligation_ids":sorted(failed),"unbound_obligation_ids":sorted(unbound),
          "semantic_cell_program_sha256":hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
          "model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,
          "incremental_spend_usd":0,"terminal_authority":False,
          "hard_nonclaims":["ONLY_EXPLICIT_BOUNDED_SOURCE_GROUNDED_CELLS","UNBOUND_RAW_TASK_OBLIGATIONS_REMAIN_BLOCKING","NO_GENERAL_NATURAL_LANGUAGE_SEMANTIC_COMPLETENESS","NO_BENCHMARK_SCORE_OR_TERMINAL_AUTHORITY"],
        }
        payload["receipt_payload_sha256"]=_sha_obj(payload)
        return payload
    except Exception as exc:
        return {"schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"FAIL_CLOSED","pass":False,"errors":[type(exc).__name__+":"+str(exc)],"terminal_authority":False}

def run(args:Mapping[str,Any],root:str|pathlib.Path)->dict[str,Any]:
    if not isinstance(args,Mapping):
        return {"schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"FAIL_CLOSED","pass":False,"errors":["ARGS_NOT_OBJECT"],"terminal_authority":False}
    repo=pathlib.Path(root).resolve()
    return evaluate_cells(
      str(args.get("task_text") or ""),
      baseline_root=(repo/str(args.get("baseline_root") or ".")).resolve(),
      candidate_root=(repo/str(args.get("candidate_root") or ".")).resolve(),
      expected_baseline_snapshot_sha256=(str(args["expected_baseline_snapshot_sha256"]) if args.get("expected_baseline_snapshot_sha256") else None),
      expected_candidate_snapshot_sha256=(str(args["expected_candidate_snapshot_sha256"]) if args.get("expected_candidate_snapshot_sha256") else None),
    )
