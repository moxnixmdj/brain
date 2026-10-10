"""Fail-closed discovery of existing current-O11 proof instantiations."""
from __future__ import annotations
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime import current_escape_o11_objective_acceptance_law_gate_v1 as gate

SCHEMA="PROJECT_BRAIN_CURRENT_ESCAPE_O11_PROOF_INSTANTIATION_SEARCH_V1"
ROOTS=("canonical/governance","canonical/evidence","canonical/verification","canonical/action_intents")
MAX_BYTES=8_000_000

def _canon(x:Any)->bytes:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()

def _blob(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _sha(x:Mapping[str,Any])->str:
    return sha256(_canon(x)).hexdigest()

def _walk(x:Any):
    if isinstance(x,Mapping):
        yield x
        for v in x.values(): yield from _walk(v)
    elif isinstance(x,list):
        for v in x: yield from _walk(v)

def _claims(doc:Any):
    seen=set()
    for obj in _walk(doc):
        rows=[]
        if isinstance(obj.get("claim_spec"),Mapping): rows.append(obj["claim_spec"])
        if all(isinstance(obj.get(k),Mapping) for k in ("policy","evidence","current_identity")): rows.append(obj)
        for row in rows:
            d=_sha(row)
            if d not in seen:
                seen.add(d); yield row

def scan(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve(strict=True) if repo_root is not None else Path(__file__).resolve().parents[2]
    o,q,oq=gate._frontier(root)
    found=[]; parse=[]; nfiles=0; nbytes=0
    for relroot in ROOTS:
        base=(root/relroot).resolve()
        try: base.relative_to(root)
        except ValueError: continue
        if not base.is_dir() or base.is_symlink(): continue
        for p in sorted(base.rglob("*.json")):
            try:
                p=p.resolve(strict=True); p.relative_to(root)
            except (FileNotFoundError,ValueError): continue
            if not p.is_file() or p.is_symlink(): continue
            raw=p.read_bytes()
            if len(raw)>MAX_BYTES: continue
            nfiles+=1; nbytes+=len(raw)
            try: doc=json.loads(raw.decode())
            except Exception as exc:
                parse.append({"path":p.relative_to(root).as_posix(),"reason":type(exc).__name__}); continue
            for claim in _claims(doc):
                policy=claim.get("policy")
                pid=str(policy.get("predicate_id") or "") if isinstance(policy,Mapping) else ""
                if pid not in o: continue
                verdict=gate.evaluate({"obligation_id":pid,"claim_spec":claim},repo_root=root)
                found.append({
                    "obligation_id":pid,
                    "source_path":p.relative_to(root).as_posix(),
                    "source_git_blob_sha":_blob(raw),
                    "claim_spec_sha256":_sha(claim),
                    "gate_pass":verdict.get("pass") is True,
                    "gate_status":verdict.get("status"),
                    "gate_reason":verdict.get("reason"),
                    "proof_mode":verdict.get("proof_mode"),
                })
    uniq={}
    for r in found: uniq[(r["obligation_id"],r["source_git_blob_sha"],r["claim_spec_sha256"])]=r
    found=sorted(uniq.values(),key=lambda r:(not r["gate_pass"],r["obligation_id"],r["source_path"]))
    proved=sorted({r["obligation_id"] for r in found if r["gate_pass"]})
    missing=sorted(set(o)-set(proved))
    src={}
    for r in found:
        if r["gate_pass"]: src.setdefault(r["source_path"],set()).add(r["obligation_id"])
    multi=sorted(({"source_path":p,"proved_obligation_ids":sorted(v),"proved_row_count":len(v)} for p,v in src.items() if len(v)>1),key=lambda r:(-r["proved_row_count"],r["source_path"]))
    near={pid:[{k:r.get(k) for k in ("source_path","source_git_blob_sha","claim_spec_sha256","gate_status","gate_reason","proof_mode")} for r in found if r["obligation_id"]==pid and not r["gate_pass"]][:16] for pid in missing}
    return {
        "schema":SCHEMA,"status":"PASS__CURRENT_O11_PROOF_INSTANTIATION_SEARCH_COMPLETE","pass":True,
        "oq_status":oq.get("status"),"current_o_count":len(o),"current_q_count":len(q),
        "scanned_json_file_count":nfiles,"scanned_json_bytes":nbytes,"parse_failure_count":len(parse),"parse_failures":parse[:32],
        "candidate_count":len(found),"proved_candidate_count":sum(r["gate_pass"] for r in found),
        "proved_obligation_ids":proved,"proved_obligation_count":len(proved),
        "missing_obligation_ids":missing,"missing_obligation_count":len(missing),
        "multi_row_proof_sources":multi,"candidates":found,"near_misses":near,
        "all_o_rows_have_proved_candidate":not missing,
        "acceptance_authority":False,"acceptance_credit_delta":0,"capability_credit_delta":0,
        "ownership_credit_delta":0,"terminal_authority":False,"terminal_credit_delta":0,
    }

def run(args=None,root=None):
    return scan(repo_root=root)

if __name__=="__main__":
    print(json.dumps(scan(),indent=2,sort_keys=True))
