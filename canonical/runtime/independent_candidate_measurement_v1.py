from __future__ import annotations
import hashlib,json,math,os,pathlib,re,subprocess,sys
from typing import Any,Mapping
SCHEMA="PROJECT_BRAIN_INDEPENDENT_CANDIDATE_MEASUREMENT_V1"
CAPABILITY_ID="candidate.measurement.independent.content_addressed.v1"
MARKER="__BRAIN_MEASUREMENT__"
class MeasurementError(RuntimeError): pass
def _canon(x):return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)
def _sha(b):return hashlib.sha256(b).hexdigest()
def _safe_dir(root,raw):
 p=(root/str(raw or "")).resolve()
 if p==root or root not in p.parents or not p.is_dir() or p.is_symlink():raise MeasurementError("DIRECTORY_INVALID")
 return p
def _safe_file(root,raw):
 p=(root/str(raw or "")).resolve()
 if p==root or root not in p.parents or not p.is_file() or p.is_symlink():raise MeasurementError("FILE_INVALID")
 return p
def _rel(root,p):return str(p.relative_to(root)).replace("\\","/")
def _snapshot(root,p):
 rows=[]
 for q in sorted(p.rglob("*")):
  if q.is_symlink():raise MeasurementError("CANDIDATE_SYMLINK_FORBIDDEN:"+_rel(root,q))
  if not q.is_file():continue
  b=q.read_bytes();rows.append({"path":str(q.relative_to(p)).replace("\\","/"),"bytes":len(b),"sha256":_sha(b)})
 if not rows:raise MeasurementError("CANDIDATE_SNAPSHOT_EMPTY")
 payload={"files":rows}
 return {"sha256":_sha(_canon(payload).encode()),"file_count":len(rows),"files":rows}
def _field_rows(raw):
 if not isinstance(raw,Mapping) or not raw:raise MeasurementError("MEASUREMENT_FIELDS_INVALID")
 out={}
 for fid,row in raw.items():
  if not isinstance(fid,str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",fid):raise MeasurementError("FIELD_ID_INVALID:"+str(fid))
  if not isinstance(row,Mapping):raise MeasurementError("FIELD_ROW_INVALID:"+fid)
  extra=set(row)-{"type","dimension","value"}
  if extra:raise MeasurementError("FIELD_ROW_UNKNOWN_KEYS:"+fid)
  typ=str(row.get("type") or "");dim=str(row.get("dimension") or "");value=row.get("value")
  if typ not in {"integer","number","boolean","enum"} or not dim:raise MeasurementError("FIELD_TYPE_OR_DIMENSION_INVALID:"+fid)
  if typ=="integer" and (not isinstance(value,int) or isinstance(value,bool)):raise MeasurementError("FIELD_VALUE_TYPE_INVALID:"+fid)
  if typ=="number" and (not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(float(value))):raise MeasurementError("FIELD_VALUE_TYPE_INVALID:"+fid)
  if typ=="boolean" and not isinstance(value,bool):raise MeasurementError("FIELD_VALUE_TYPE_INVALID:"+fid)
  if typ=="enum" and not isinstance(value,str):raise MeasurementError("FIELD_VALUE_TYPE_INVALID:"+fid)
  if typ in {"boolean","enum"} and dim!="dimensionless":raise MeasurementError("NONNUMERIC_DIMENSION_INVALID:"+fid)
  out[fid]={"type":typ,"dimension":dim,"value":value}
 return {k:out[k] for k in sorted(out)}
def run(args:Mapping[str,Any],root:str|os.PathLike[str]):
 try:
  if not isinstance(args,Mapping):raise MeasurementError("ARGS_NOT_OBJECT")
  repo=pathlib.Path(root).resolve()
  cand=_safe_dir(repo,args.get("candidate_root"))
  verifier=_safe_file(repo,args.get("verifier_path"))
  if verifier==cand or cand in verifier.parents or verifier.parent==cand:raise MeasurementError("VERIFIER_INSIDE_CANDIDATE_FORBIDDEN")
  if verifier.parent==cand or cand==verifier.parent:raise MeasurementError("VERIFIER_CANDIDATE_NOT_DISJOINT")
  out=(repo/str(args.get("output_path") or "")).resolve()
  if out==repo or repo not in out.parents or cand==out or cand in out.parents:raise MeasurementError("OUTPUT_PATH_INVALID")
  timeout=max(1,min(int(args.get("timeout_s",30)),120))
  snap=_snapshot(repo,cand); vb=verifier.read_bytes()
  cmd=[sys.executable,"-I",str(verifier),str(cand)]
  try:r=subprocess.run(cmd,cwd=verifier.parent,text=True,capture_output=True,timeout=timeout,env={"PATH":os.environ.get("PATH",""),"PYTHONIOENCODING":"utf-8"})
  except subprocess.TimeoutExpired:raise MeasurementError("VERIFIER_TIMEOUT")
  lines=[x for x in r.stdout.splitlines() if x.startswith(MARKER)]
  if len(lines)!=1:raise MeasurementError("VERIFIER_MEASUREMENT_MARKER_COUNT_INVALID")
  try:payload=json.loads(lines[0][len(MARKER):])
  except Exception as e:raise MeasurementError("VERIFIER_MEASUREMENT_JSON_INVALID") from e
  if not isinstance(payload,Mapping) or set(payload)!={"fields"}:raise MeasurementError("VERIFIER_PAYLOAD_SHAPE_INVALID")
  fields=_field_rows(payload["fields"])
  receipt_payload={
   "candidate_snapshot_sha256":snap["sha256"],
   "verifier_sha256":_sha(vb),
   "verifier_path":_rel(repo,verifier),
   "command":["PYTHON_ISOLATED",_rel(repo,verifier),"<CANDIDATE_ROOT>"],
   "returncode":r.returncode,
   "stdout_sha256":_sha(r.stdout.encode()),
   "stderr_sha256":_sha(r.stderr.encode()),
   "fields":fields,
  }
  receipt={
   "schema":SCHEMA,"capability_id":CAPABILITY_ID,
   "status":"PASS__CONTENT_ADDRESSED_INDEPENDENT_MEASUREMENT" if r.returncode==0 else "FALSIFIED__INDEPENDENT_VERIFIER_NONZERO",
   "pass":r.returncode==0,
   **receipt_payload,
   "candidate_snapshot":snap,
   "receipt_sha256":_sha(_canon(receipt_payload).encode()),
   "measurement_source":"INDEPENDENT_VERIFIER_EXECUTION_NOT_BUILDER_DECLARATION",
   "verifier_inside_candidate":False,
   "model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,"incremental_spend_usd":0,
   "terminal_authority":False,
   "hard_nonclaims":["VERIFIER_SEMANTIC_ADEQUACY_MUST_BE_PROVED_OR_SOURCE_GROUNDED_SEPARATELY","NO_GENERAL_SOFTWARE_ACCEPTANCE_COMPLETENESS","NO_BENCHMARK_SCORE_OR_TERMINAL_CREDIT"]
  }
  out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
  receipt["output_path"]=_rel(repo,out);receipt["output_sha256"]=_sha(out.read_bytes());receipt["output_verified"]=True
  return receipt
 except Exception as exc:
  return {"schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"FAIL_CLOSED","pass":False,"errors":[type(exc).__name__+":"+str(exc)],"model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,"incremental_spend_usd":0,"terminal_authority":False}
